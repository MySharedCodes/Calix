"""Repeat CLI timings using an isolated, warm installed service."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('label')
args = parser.parse_args()
folder = root / 'work' / ('ai-overhead-' + args.label)
folder.mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'LOCALAPPDATA': str(folder / 'local')}
launcher = root / 'App/calix-cli.exe'
def call(*arguments):
    started = time.perf_counter()
    process = subprocess.run([str(launcher), *map(str,arguments)], cwd=folder, env=env,
        capture_output=True,text=True,encoding='utf8',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
    seconds = time.perf_counter()-started
    assert process.returncode == 0, process.stdout + process.stderr
    return seconds,json.loads(process.stdout)

call('start','--workers','8')
try:
    version=call('status')[1]['version']
    inputs={
        'single': ['eval','--code','1+1'],
        'six_cells':['run',root/'work/ai-benchmark-v0126/calix-02/problem.cixnb'],
    }
    code='\n'.join(cell['code'] for cell in json.loads((root/'work/ai-benchmark-v0126/calix-02/problem.cixnb').read_text(encoding='utf8'))['cells'])
    (folder/'six.wl').write_text(code,encoding='utf8')
    inputs['six_in_one']=['eval','--file','six.wl']
    measurements=[]
    for operation,command in inputs.items():
        for index in range(8):
            seconds,result=call(*command)
            assert result['ok']
            measurements.append({'operation':operation,'trial':index,'seconds':seconds,'warmup':index==0})
    medians={name:statistics.median(row['seconds'] for row in measurements if row['operation']==name and not row['warmup']) for name in inputs}
    result={'version':version,'label':args.label,'medians':medians,'measurements':measurements}
    if args.label != 'v0126':
        process=subprocess.Popen([str(launcher),'pipe','--brief'],cwd=folder,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf8',creationflags=subprocess.CREATE_NO_WINDOW)
        timings=[]
        try:
            for index in range(21):
                started=time.perf_counter()
                process.stdin.write(json.dumps({'id':index,'code':'1+1'})+'\n')
                process.stdin.flush()
                response=json.loads(process.stdout.readline())
                elapsed=time.perf_counter()-started
                assert response['ok'] and response['result']['text']=='2'
                if index:
                    timings.append(elapsed)
            process.stdin.close()
            assert process.wait(timeout=15)==0
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        result['pipe_roundtrip']={'median_seconds':statistics.median(timings),'seconds':timings,
            'note':'20 sequential request/response pairs after excluding first startup request'}
    (folder/'timing.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))
finally:
    call('stop')
