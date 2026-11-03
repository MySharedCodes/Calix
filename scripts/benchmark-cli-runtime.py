"""Measure prepared tools separately from the time an AI takes to drive them."""
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import time

root = Path(__file__).resolve().parents[1]
bench = root / 'work/ai-benchmark-v0126'
folder = bench / 'prepared-runtime'
folder.mkdir(exist_ok=True)
shutil.copy2(bench / 'free-02/compute.py', folder / 'compute.py')
shutil.copy2(bench / 'calix-02/problem.cixnb', folder / 'problem.cixnb')
commands = {
    'calix': [str(root / 'calix-cli.exe'), 'run', 'problem.cixnb', '--output', 'calix.json'],
    'free': [str(root / '.venv/Scripts/python.exe'), 'compute.py'],
}
measurements = []
for index in range(6):
    routes = ['calix', 'free'] if index % 2 == 0 else ['free', 'calix']
    for route in routes:
        started = time.perf_counter()
        process = subprocess.run(commands[route], cwd=folder, capture_output=True,
            text=True, encoding='utf8', timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
        elapsed = time.perf_counter() - started
        assert process.returncode == 0, process.stdout + process.stderr
        measurements.append({'route': route, 'trial': index, 'seconds': elapsed,
                             'warmup_excluded': index == 0})
medians = {route: statistics.median(item['seconds'] for item in measurements
    if item['route'] == route and item['trial'] > 0) for route in commands}
result = {'note': 'Prepared inputs; Calix service already warm. Includes each client/script startup and output writing; excludes AI planning and GUI. First pair excluded as warmup.',
    'commands': commands, 'measurements': measurements, 'median_seconds': medians,
    'free_over_calix': medians['free'] / medians['calix']}
(folder / 'timing.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result, indent=2))
