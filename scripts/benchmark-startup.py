"""Measure a new service from launch to readiness and its first real requests."""
import argparse
import json
import os
from pathlib import Path
import queue
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def measure(command):
    started = time.perf_counter()
    env = dict(os.environ, CALIX_MAX_WORKERS='8')
    process = subprocess.Popen(command + ['--port', '0'], cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True).start()
    try:
        ready = lines.get(timeout=45).split()
        if len(ready) != 3 or ready[0] != 'CALIX_READY':
            raise RuntimeError('Service handshake failed')
        handshake_ms = (time.perf_counter() - started) * 1000
        origin = f'http://127.0.0.1:{ready[1]}/api'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def request(path, data=None):
            body = json.dumps(data).encode() if data is not None else None
            req = urllib.request.Request(origin + path, data=body,
                headers={'Content-Type': 'application/json', 'X-Calix-Token': ready[2]})
            with opener.open(req, timeout=45) as response:
                return json.load(response)

        request('/health')
        ready_ms = (time.perf_counter() - started) * 1000
        timings = []
        for code, expected in [('1+1', '2'), ('x=41;x+1', '42'), ('x', 'x')]:
            before = time.perf_counter()
            result = request('/evaluate', {'session': 'other' if code == 'x' else 'first', 'code': code})
            timings.append(round((time.perf_counter() - before) * 1000, 3))
            assert result['ok'] and result['result']['text'] == expected, result
        # Check the frozen runtime's deferred imports and state restoration too.
        for code, expected in [('q=3[m];UnitConvert[q,"cm"]', '300[cm]'),
                               ('UnitConvert[q,"mm"]', '3000[mm]'),
                               ('Integrate[Sin[x],{x,0,Pi}]', '2')]:
            result = request('/evaluate', {'session': 'checks', 'code': code})
            assert result['ok'] and result['result']['text'] == expected, result
        return {'handshake_ms': round(handshake_ms, 3), 'ready_ms': round(ready_ms, 3),
                'first_1_plus_1_ms': timings[0], 'second_request_ms': timings[1],
                'fresh_notebook_ms': timings[2], 'launch_to_first_answer_ms': round(ready_ms + timings[0], 3)}
    finally:
        process.terminate()
        process.wait(timeout=10)
        process.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/verification/startup.json')
    args = parser.parse_args()
    command = [str(args.executable)] if args.executable else [sys.executable, '-m', 'backend.service']
    runs = [measure(command) for _ in range(args.repeats)]
    report = {'command': command, 'workers': 8, 'runs': runs,
              'median_ms': {key: round(statistics.median(run[key] for run in runs), 3) for key in runs[0]},
              'scope': 'Fresh service processes; includes worker initialization in readiness and total. OS file cache is not flushed. No GUI or AI planning.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
