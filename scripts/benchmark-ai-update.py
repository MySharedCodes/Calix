"""Repeat the same six-problem Harness task with the installed optimized CLI."""
import json
import argparse
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import time

root=Path(__file__).resolve().parents[1]
previous=runpy.run_path(str(root/'scripts/benchmark-deepseek.py'),run_name='benchmark_definition')
parser=argparse.ArgumentParser()
parser.add_argument('--folder',default='ai-benchmark-v0127')
args=parser.parse_args()
folder=root/'work'/args.folder
folder.mkdir(exist_ok=True)
runs=[]
for trial in (1,2):
    target=folder/f'calix-{trial:02}'
    target.mkdir(exist_ok=False)
    for name in ('AGENTS.md','AI-CONTROL.md','API.md'):
        shutil.copy2(root/'App'/name,target/name)
    task=previous['PROBLEMS']
    (target/'task.txt').write_text(task,encoding='utf8')
    start_time=time.strftime('%Y-%m-%dT%H:%M:%S%z')
    started=time.perf_counter()
    with (target/'events.jsonl').open('w',encoding='utf8') as out,(target/'stderr.txt').open('w',encoding='utf8') as err:
        process=subprocess.Popen([str(previous['HARNESS']),'--profile','headless','--patch',str(previous['PATCH']),'--json','-'],
            cwd=target,env={**os.environ,'DSH_PERMISSION_MODE':'danger-full-access','CALIX_MAX_WORKERS':'8'},
            stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,encoding='utf8',creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps({'trial':trial,'event':'started','pid':process.pid}),flush=True)
        try:
            process.communicate(task,timeout=900)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
    seconds=time.perf_counter()-started
    events=[]
    for line in (target/'events.jsonl').read_text(encoding='utf8',errors='replace').splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    result={'trial':trial,'version':'0.1.27','started_at':start_time,'wall_seconds':seconds,
        'returncode':process.returncode,'tool_calls':sum(e.get('type')=='tool_call' for e in events),
        'final':next((e.get('text') for e in reversed(events) if e.get('type')=='final'),None)}
    (target/'execution.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    runs.append(result)
    (folder/'executions.json').write_text(json.dumps(runs,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'trial':trial,'seconds':seconds,'tool_calls':result['tool_calls'],'finished':bool(result['final'])}),flush=True)
