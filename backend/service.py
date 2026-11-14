"""Loopback-only service with isolated, cancellable symbolic sessions."""
import argparse
import asyncio
import hmac
import multiprocessing as mp
import os
import pickle
from pathlib import Path
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.components import capabilities
from backend.hardware import physical_cores, default_workers


def worker(connection):
    from backend.engine import Engine
    engine = Engine()
    default_assumptions = engine.assumptions
    while True:
        try:
            command = connection.recv()
        except EOFError:
            return
        if command is None:
            return
        try:
            from backend.native import kernel
            from backend.hardware import limit_process_cores
            threads=command.get('threads',1)
            affinity=limit_process_cores(threads)
            kernel.configure_threads(threads)
            state = command["state"]
            if state is None:
                engine.environment.clear()
                engine.assumptions = default_assumptions
            else:
                payload, uses_units = state
                if uses_units:
                    from backend import units  # Register Pint before unpickling quantities.
                engine.environment, engine.assumptions = pickle.loads(payload)
            result = engine.execute(command["code"])
            result['execution']['affinity']=affinity
            response = {"ok": True, "result": result}
            if command.get('runtime_info'):
                response['runtime_info'] = {'native': kernel.available, 'cpu_features': kernel.cpu_features()}
        except Exception as exc:
            message = str(exc) or type(exc).__name__
            response = {"ok": False, "error": message[:1800], "error_type": type(exc).__name__}
        # The HTTP process stores opaque state; it need not import symbolic/unit
        # libraries merely to transfer an isolated notebook between workers.
        import sys
        response['state'] = (pickle.dumps((engine.environment, engine.assumptions), protocol=pickle.HIGHEST_PROTOCOL), 'backend.units' in sys.modules)
        connection.send(response)


class WorkerPool:
    def __init__(self, maximum=2):
        self.maximum = maximum
        self.condition = threading.Condition()
        self.entries = []
        self.runtime_info = None

    def warmup(self):
        # Prepare one reusable process, not one heavyweight process per CPU core.
        # Use the real evaluation path so parsing, printers and native setup are ready.
        result = Session(self).run('1+1', 'startup-warmup', timeout=30, runtime_info=True)
        if not result.get('ok') or result['result']['text'] != '2':
            raise RuntimeError('Calculation worker initialization failed')

    def acquire(self, deadline):
        with self.condition:
            while True:
                for entry in self.entries[:]:
                    if not entry[0].is_alive() and not entry[2]:
                        self.destroy(entry)
                        self.entries.remove(entry)
                for entry in self.entries:
                    if not entry[2]:
                        entry[2] = True
                        return entry
                if len(self.entries) < self.maximum:
                    parent, child = mp.get_context("spawn").Pipe()
                    process = mp.get_context("spawn").Process(target=worker, args=(child,), daemon=True)
                    process.start()
                    child.close()
                    entry = [process, parent, True]
                    self.entries.append(entry)
                    return entry
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise HTTPException(408, "Worker queue timed out")
                self.condition.wait(min(remaining, 0.05))

    def release(self, entry, discard=False):
        with self.condition:
            if discard:
                self.destroy(entry)
                if entry in self.entries:
                    self.entries.remove(entry)
            else:
                entry[2] = False
            self.condition.notify_all()

    @staticmethod
    def destroy(entry):
        process, connection, _ = entry
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        connection.close()

    def configure(self, maximum):
        with self.condition:
            if maximum == self.maximum:
                return
            if any(entry[2] for entry in self.entries):
                raise HTTPException(409, "Wait for running calculations before changing Workers")
            while len(self.entries) > maximum:
                self.destroy(self.entries.pop())
            self.maximum = maximum
            self.condition.notify_all()

    def close(self):
        with self.condition:
            for entry in self.entries:
                self.destroy(entry)
            self.entries.clear()


class Session:
    def __init__(self, pool=None):
        self.pool = pool or WorkerPool(1)
        self.owns_pool = pool is None
        self.state = None
        self.lock = threading.Lock()
        self.process = None
        self.connection = None
        self.generation = 0
        self.last_used = time.monotonic()
        self.request_id = None

    def stop(self):
        self.generation += 1
        self.state = None
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=2)
        self.process, self.connection, self.request_id = None, None, None
        if self.owns_pool:
            self.pool.close()

    def run(self, code, request_id, timeout=180, runtime_info=False):
        if not self.lock.acquire(blocking=False):
            raise HTTPException(409, "This session is busy")
        try:
            self.last_used = time.monotonic()
            generation = self.generation
            deadline = time.monotonic() + timeout
            entry = self.pool.acquire(deadline)
            self.process, self.connection = entry[:2]
            self.request_id = request_id
            connection = self.connection
            if generation != self.generation:
                raise HTTPException(409, "Calculation cancelled")
            connection.send({"code": code, "state": self.state,"threads":self.pool.maximum, 'runtime_info': runtime_info})
            while time.monotonic() < deadline:
                if generation != self.generation:
                    raise HTTPException(409, "Calculation cancelled; session variables were cleared")
                try:
                    if connection.poll(0.05):
                        result = connection.recv()
                        if generation != self.generation:
                            raise HTTPException(409, "Calculation cancelled")
                        self.state = result.pop("state")
                        if 'runtime_info' in result:
                            self.pool.runtime_info = result.pop('runtime_info')
                        self.request_id = None
                        return result
                except (EOFError, OSError):
                    raise HTTPException(409, "Calculation process stopped; session variables were cleared") from None
                if not self.process or not self.process.is_alive():
                    self.stop()
                    raise HTTPException(500, "Calculation process exited; session variables were cleared")
            self.stop()
            raise HTTPException(408, f"Calculation exceeded {timeout:g} seconds; session variables were cleared")
        finally:
            if 'entry' in locals():
                self.pool.release(entry, discard=generation != self.generation or not entry[0].is_alive())
            self.process, self.connection = None, None
            self.last_used = time.monotonic()
            self.lock.release()


class Evaluation(BaseModel):
    session: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    code: str = Field(min_length=1, max_length=24000)
    timeout_seconds: float = Field(default=180, ge=0.01, le=3600, allow_inf_nan=False)


class WorkerSettings(BaseModel):
    max_workers: int = Field(ge=1, le=physical_cores(), strict=True)


class OpenUI(BaseModel):
    notebook: str | None = Field(default=None, max_length=32760)


def create_app(token=None, frontend=None, role='desktop'):
    @asynccontextmanager
    async def lifespan(app):
        try:
            await asyncio.to_thread(app.state.pool.warmup)
            yield
        finally:
            for session in app.state.sessions.values():
                session.stop()
            app.state.pool.close()

    app = FastAPI(title="Calix local computation service", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.token = token or secrets.token_urlsafe(32)
    app.state.sessions = {}
    app.state.role = role
    app.state.shutdown = None
    app.state.pool = WorkerPool(default_workers())
    app.add_middleware(CORSMiddleware, allow_origins=["http://tauri.localhost", "tauri://localhost", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type", "X-Calix-Token"])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.headers.get("host", "").split(":")[0]
        if host not in ("127.0.0.1", "localhost", "testserver"):
            return JSONResponse({"detail": "Loopback requests only"}, status_code=403)
        if request.method != "OPTIONS" and request.url.path.startswith("/api/") and request.url.path != "/api/health":
            supplied = request.headers.get("x-calix-token", "")
            if not hmac.compare_digest(supplied, app.state.token):
                return JSONResponse({"detail": "Invalid local session token"}, status_code=403)
        return await call_next(request)

    @app.get("/api/health")
    def health():
        from backend.components import capabilities
        return {"status": "ok", "version": "0.1.28", **app.state.pool.runtime_info, "abi": 1, "api_version": 1,
                "cpu_count": physical_cores(), "logical_cpu_count": os.cpu_count() or 1, "max_workers": app.state.pool.maximum, "components": capabilities()}

    @app.get('/api/capabilities')
    def api_capabilities():
        return {'application': 'Calix', 'api_version': 1, 'pid': os.getpid(), 'role': app.state.role,
                'language': 'Wolfram-language subset', 'schema': '/api/openapi.json',
                'limits': {'code_characters': 24000, 'sessions': 128, 'timeout_seconds': [0.01, 3600]},
                'result_kinds': ['expression', 'plot', 'animation', 'group'], 'components': capabilities(),
                'cli_features': ['multiline_eval', 'brief_stdout', 'persistent_jsonl'],
                'desktop_handoff': {'endpoint': '/api/open-ui', 'notebook_extensions': ['.cixnb', '.clxnb', '.calix'],
                                    'cli': 'run INPUT.cixnb --output RESULTS.json --open-ui',
                                    'live_kernel_transfer': False}}

    @app.get('/api/openapi.json', include_in_schema=False)
    def api_schema():
        schema = app.openapi()
        schema.setdefault('components', {}).setdefault('securitySchemes', {})['LocalToken'] = {
            'type': 'apiKey', 'in': 'header', 'name': 'X-Calix-Token'}
        for path, operations in schema['paths'].items():
            for operation in operations.values():
                if path != '/api/health':
                    operation['security'] = [{'LocalToken': []}]
        return schema

    @app.get('/api/sessions')
    def list_sessions():
        return {'sessions': [{'session': key, 'busy': value.lock.locked(), 'request_id': value.request_id,
                              'idle_seconds': round(max(0, time.monotonic() - value.last_used), 3)}
                             for key, value in list(app.state.sessions.items())]}

    @app.post('/api/shutdown')
    async def shutdown():
        if app.state.role != 'cli' or not app.state.shutdown:
            raise HTTPException(409, 'Close the Calix desktop window to stop its service')
        asyncio.get_running_loop().call_later(.1, app.state.shutdown)
        return {'ok': True}

    @app.post('/api/open-ui')
    def open_ui(body: OpenUI = OpenUI()):
        from backend.launcher import open_user_interface
        try:
            return {'ok': True, 'ui': open_user_interface(body.notebook) if body.notebook else open_user_interface()}
        except (ValueError, OSError) as exc:
            raise HTTPException(503, str(exc)) from None

    @app.get('/api/components/{name}')
    def component_resource(name: str):
        import json
        from backend.components import ROOT, capabilities
        if name not in ('languages', 'themes') or not capabilities()[name]:
            raise HTTPException(404, 'Optional component is not installed')
        resource = ROOT / ('languages.json' if name == 'languages' else 'themes.css')
        content = resource.read_text(encoding='utf-8')
        return json.loads(content) if name == 'languages' else {'css': content}

    @app.post("/api/settings")
    def settings(body: WorkerSettings):
        app.state.pool.configure(body.max_workers)
        return {"max_workers": app.state.pool.maximum}

    @app.post("/api/evaluate")
    async def evaluate(body: Evaluation):
        sessions = app.state.sessions
        if body.session not in sessions:
            if len(sessions) >= 128:
                stale = [key for key, value in sessions.items() if not value.lock.locked() and time.monotonic()-value.last_used > 300]
                for key in stale:
                    sessions.pop(key).stop()
                if len(sessions) >= 128:
                    raise HTTPException(429, "Too many active calculation sessions")
            sessions[body.session] = Session(app.state.pool)
        result = await asyncio.to_thread(sessions[body.session].run, body.code, body.request_id, body.timeout_seconds)
        return {**result, 'session': body.session, 'request_id': body.request_id}

    @app.post("/api/cancel/{session}")
    async def cancel(session: str):
        target = app.state.sessions.pop(session, None)
        if target:
            await asyncio.to_thread(target.stop)
        return {"ok": True, "variables_cleared": True}

    if frontend and Path(frontend).is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    return app


def main():
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", default=os.environ.get("CALIX_TOKEN"))
    parser.add_argument("--frontend")
    parser.add_argument('--publish-connection', action='store_true')
    parser.add_argument('--connection-id')
    parser.add_argument('--role', choices=('desktop', 'cli'), default='desktop')
    parser.add_argument('--workers', type=int)
    args = parser.parse_args()
    from backend.lifecycle import own_process_tree
    own_process_tree()
    if args.workers is not None and not 1 <= args.workers <= physical_cores():
        parser.error(f'Workers must be between 1 and {physical_cores()}')
    app = create_app(args.token, args.frontend, args.role)
    if args.workers is not None:
        app.state.pool.configure(args.workers)
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", args.port))
    sock.listen(128)
    port = sock.getsockname()[1]
    from backend.discovery import publish
    connection_file = publish(port, app.state.token, args.role, args.connection_id) if args.publish_connection else None
    print(f"CALIX_READY {port} {app.state.token}", flush=True)
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False, loop="asyncio", log_config=None))
    app.state.shutdown = lambda: setattr(server, 'should_exit', True)
    try:
        server.run(sockets=[sock])
    finally:
        if connection_file:
            connection_file.unlink(missing_ok=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
