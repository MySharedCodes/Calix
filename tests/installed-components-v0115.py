"""Smoke an actual installed core or full optional-component configuration."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
import queue
import urllib.request
import uuid

parser=argparse.ArgumentParser()
parser.add_argument('--minimal',action='store_true')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
installed=root/'App'
process=subprocess.Popen([str(installed/'backend/calix-service.exe'),'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
lines=queue.Queue();errors=[]
threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
threading.Thread(target=lambda:errors.extend(process.stderr.readlines()),daemon=True).start()
try:
    ready=lines.get(timeout=30).split();assert ready[0]=='CALIX_READY',ready
    origin=f'http://127.0.0.1:{ready[1]}/api'
    def request(path,data=None):
        req=urllib.request.Request(origin+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Calix-Token':ready[2]})
        with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
    health=request('/health');assert health['version']=='0.1.15',health
    wanted=not args.minimal
    assert health['components']=={'pde':wanted,'languages':wanted,'themes':wanted},health
    assert request('/evaluate',{'session':'installed-components','code':'Integrate[Sin[x],x]'})['result']['text']=='-Cos[x]'
    pde=request('/evaluate',{'session':'installed-components','code':'DSolveValue[{D[u[x,y],{y,2}]==-6,u[x,0]==0,u[x,1]==0},u[x,y],{x,y}]'})
    assert pde['ok']==wanted,pde
    if args.minimal:
        assert 'not installed' in pde['error']
        assert not (installed/'components/pde').exists()
        assert not (installed/'components/languages.json').exists()
        assert not (installed/'components/themes.css').exists()
    else:
        result=request('/evaluate',{'session':'installed-components','code':'v=NDSolveValue[{D[u[x,t],t]==D[u[x,t],{x,2}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]},u[x,t],{x,0,1},{t,0,1}];PDEValue[v,{1/2,1/10}]'})
        assert result['ok'],result
        assert abs(float(result['result']['text'])-.3727078)<.001
        assert len(request('/components/languages'))==5
        assert 'data-theme=black' in request('/components/themes')['css']
    report={'status':'passed','installed':str(installed),'version':health['version'],'components':health['components'],'coreCalculation':True,'pdeResult':pde['ok']}
    (root/f'work/installed-components-{ "minimal" if args.minimal else "full" }-v0115-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:
    process.terminate();process.wait(timeout=10)
