"""Run portable browser checks using owned, temporary local service processes."""
from pathlib import Path
import os
import json
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
(ROOT/'work').mkdir(exist_ok=True)


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_url(url):
    for _ in range(100):
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except (OSError, urllib.error.URLError):
            time.sleep(.2)
    raise RuntimeError(f'Local test service did not start: {url}')


service_port, ui_port = port(), port()
env = dict(os.environ, CALIX_BACKEND_URL=f'http://127.0.0.1:{service_port}', CALIX_URL=f'http://127.0.0.1:{ui_port}')
processes = []
started = time.perf_counter()
passed = False
with (ROOT/'work/ui-runner.log').open('w', encoding='utf-8') as log:
    try:
        processes.append(subprocess.Popen([sys.executable, '-m', 'backend.service', '--port', str(service_port), '--token', 'calix-local-development'], cwd=ROOT, env=env, stdout=log, stderr=log))
        processes.append(subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--config', 'frontend/vite.config.ts', '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'], cwd=ROOT, env=env, stdout=log, stderr=log))
        wait_url(f'http://127.0.0.1:{ui_port}')
        for test in ('tests/ui-stability.cjs', 'tests/ui-help.cjs'):
            subprocess.run(['node', test], cwd=ROOT, env=env, check=True, timeout=180)
        passed = True
    finally:
        for process in reversed(processes):
            if os.name == 'nt' and process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=log, stderr=log)
            elif process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        evidence = ROOT/'work/verification'
        evidence.mkdir(exist_ok=True)
        (evidence/'browser-ui.json').write_text(json.dumps({'passed': passed, 'seconds': round(time.perf_counter()-started,3), 'checks': ['workspace recovery and undo', 'offline help and calculator']}, indent=2)+'\n', encoding='utf-8')
