import multiprocessing as mp
import time
from fastapi.testclient import TestClient
from backend.service import create_app, Session


def test_handshake_socket_already_listening(monkeypatch, capsys):
    import socket
    import uvicorn
    from backend.service import main
    import backend.lifecycle
    observed = []

    def run(server, sockets):
        ready = capsys.readouterr().out.strip().split()
        assert ready[0] == 'CALIX_READY' and ready[2] == 'test-token'
        try:
            with socket.create_connection(('127.0.0.1', int(ready[1])), timeout=1):
                observed.append(True)
        finally:
            sockets[0].close()

    monkeypatch.setattr('sys.argv', ['calix-service', '--port', '0', '--token', 'test-token'])
    monkeypatch.setattr(backend.lifecycle, 'own_process_tree', lambda: None)
    monkeypatch.setattr(uvicorn.Server, 'run', run)
    main()
    assert observed == [True]


def test_service_auth_and_origin():
    with TestClient(create_app("test-token")) as client:
        assert client.get("/api/health").json()["native"]
        assert client.post("/api/evaluate", json={"session": "a", "code": "1+1"}).status_code == 403
        assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 403
        preflight = client.options("/api/evaluate", headers={"Origin": "http://tauri.localhost", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-calix-token"})
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_session_persistence_and_reset():
    with TestClient(create_app("test-token")) as client:
        headers = {"x-calix-token": "test-token"}
        def evaluate(session, code):
            response = client.post("/api/evaluate", headers=headers, json={"session": session, "code": code})
            assert response.status_code == 200, response.text
            return response.json()
        assert evaluate("a", "x=41")["ok"]
        assert evaluate("a", "x+1")["result"]["text"] == "42"
        assert evaluate("b", "x")["result"]["text"] == "x"
        assert not evaluate("a", "Sin[")["ok"]
        assert evaluate("a", "x")["result"]["text"] == "41"
        assert client.post("/api/cancel/a", headers=headers).status_code == 200
        assert evaluate("a", "x")["result"]["text"] == "x"


def test_service_validation():
    with TestClient(create_app("test-token")) as client:
        headers = {"x-calix-token": "test-token"}
        assert client.post("/api/evaluate", headers=headers, json={"session": "../x", "code": "1"}).status_code == 422
        assert client.post("/api/evaluate", headers=headers, json={"session": "a", "code": ""}).status_code == 422


def test_timeout_terminates_worker():
    from fastapi import HTTPException
    session = Session()
    try:
        try:
            session.run("Integrate[Exp[Sin[x^7]], x]", "timeout-test", timeout=0.01)
            assert False, "Expected timeout"
        except HTTPException as exc:
            assert exc.status_code == 408
        assert session.process is None
        assert session.run("2+2", "after-timeout")["result"]["text"] == "4"
    finally:
        session.stop()


def test_worker_limit_reuses_process_and_preserves_notebook_state():
    with TestClient(create_app("test-token")) as client:
        headers = {"x-calix-token": "test-token"}
        assert client.post('/api/settings', headers=headers, json={"max_workers": 1}).status_code == 200
        def evaluate(session, code):
            response = client.post('/api/evaluate', headers=headers, json={"session": session, "code": code})
            assert response.status_code == 200, response.text
            assert response.json()["ok"], response.text
            return response.json()["result"]
        assert evaluate('first', 'x=41')["text"] == '41'
        pid = client.app.state.pool.entries[0][0].pid
        assert evaluate('second', 'x=7')["text"] == '7'
        assert evaluate('first', 'x+1')["text"] == '42'
        assert client.app.state.pool.entries[0][0].pid == pid
        assert len(client.app.state.pool.entries) == 1
        evaluate('units', 'length=3[m]+20[cm]')
        assert '16/5' in evaluate('units', 'length')["text"]
        for i in range(12):
            evaluate(f'notebook-{i}', f'a={i}')
        assert len(client.app.state.pool.entries) == 1
        assert evaluate('first', 'x')["text"] == '41'
        assert client.post('/api/settings', headers=headers, json={"max_workers": 0}).status_code == 422
        assert client.post('/api/settings', headers=headers, json={"max_workers": 1.5}).status_code == 422


def test_worker_queue_and_cancel_preserve_other_sessions():
    import concurrent.futures
    from fastapi import HTTPException
    from backend.service import WorkerPool
    pool = WorkerPool(1)
    a, b = Session(pool), Session(pool)
    try:
        assert b.run('x=27', 'init')["ok"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            slow = executor.submit(a.run, 'Integrate[Exp[Sin[x^7]],x]', 'slow')
            deadline = time.monotonic() + 5
            while not a.process and time.monotonic() < deadline:
                time.sleep(.01)
            waiting = executor.submit(b.run, 'x+1', 'queued')
            time.sleep(.1)
            assert len(pool.entries) == 1
            pool.configure(1)
            assert pool.maximum == 1
            try:
                pool.configure(2)
                assert False, 'Settings must not change during a calculation'
            except HTTPException as error:
                assert error.status_code == 409
            a.stop()
            try:
                slow.result(timeout=5)
                assert False, 'Expected cancellation'
            except HTTPException as error:
                assert error.status_code == 409
            assert waiting.result(timeout=10)["result"]["text"] == '28'
    finally:
        a.stop(); b.stop(); pool.close()
