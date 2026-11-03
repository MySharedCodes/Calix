"""Exercise the packaged executable without importing the source implementation."""
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
import urllib.request
import os
from collections import deque

root = Path(__file__).resolve().parents[1]
executable = root / "release/backend/calix-service/calix-service.exe"
start = time.perf_counter()
process = subprocess.Popen([str(executable), "--port", "0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
lines = queue.Queue()
diagnostics = deque(maxlen=100)
def read_errors():
    for line in process.stderr:
        diagnostics.append(line)
threading.Thread(target=read_errors, daemon=True).start()
threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
try:
    ready = lines.get(timeout=30).strip().split()
    assert len(ready) == 3 and ready[0] == "CALIX_READY", ready
    startup = (time.perf_counter() - start) * 1000
    port, token = ready[1:]
    origin = f"http://127.0.0.1:{port}"

    def request(path, data=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(origin + "/api" + path, data=body, headers={"Content-Type": "application/json", "X-Calix-Token": token})
        with urllib.request.urlopen(req, timeout=200) as response:
            return json.load(response)

    health=request("/health")
    assert health['version']==json.loads((root/'package.json').read_text(encoding='utf-8'))['version']
    assert health["native"]
    assert set(health['cpu_features']['compiled'])=={'scalar','avx2','avx512','amx-int8'}
    first = time.perf_counter()
    assert request("/evaluate", {"session": "packaged", "code": "1+1"})["result"]["text"] == "2"
    assert request("/evaluate", {"session": "packaged", "code": "Sin[2*45[deg]]"})["result"]["text"] == "1"
    assert request("/evaluate", {"session": "packaged", "code": "α=3;x₁=2;α*x₁"})["result"]["text"] == "6"
    matrix=request('/evaluate',{'session':'packaged','code':'a=Table[N[1/(i+j),15],{i,1,32},{j,1,32}];Dot[a,a]'})
    assert matrix['ok'] and 'C++ /' in matrix['result']['engine']
    first_ms = (time.perf_counter() - first) * 1000
    count = 0
    for file in sorted((root / "examples").glob("*.calix")):
        print('Checking:', file.name, flush=True)
        request("/cancel/packaged", {})
        for cell in json.loads(file.read_text(encoding="utf-8"))["cells"]:
            if cell["mode"] == "markdown":
                continue
            result = request("/evaluate", {"session": "packaged", "code": cell["code"]})
            assert result["ok"], (file.name, cell["code"], result)
            count += 1
    request("/cancel/packaged", {})
    assert request("/evaluate", {"session": "packaged", "code": "x"})["result"]["text"] == "x"
    report = {"status": "passed", "startup_to_handshake_ms": round(startup, 2), "first_scalar_request_ms": round(first_ms, 2), "example_expressions": count, "native": True, "source_python_required": False,'cpu_features':health['cpu_features'],'matrix_path':matrix['result']['engine']}
    (root / "work/packaged-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
except Exception:
    (root / 'work/packaged-error.log').write_text(''.join(diagnostics), encoding='utf-8')
    raise
finally:
    process.terminate()
    process.wait(timeout=10)
