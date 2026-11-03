import json,subprocess,queue,threading,urllib.request,os
from pathlib import Path
root=Path(__file__).resolve().parents[1]
process=subprocess.Popen([str(root/'release/backend/calix-service/calix-service.exe'),'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW,env={**os.environ,'CALIX_MAX_WORKERS':'8'})
lines=queue.Queue();threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
try:
    _,port,token=lines.get(timeout=30).strip().split()
    def request(path,data=None):
        req=urllib.request.Request(f'http://127.0.0.1:{port}/api{path}',data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-Calix-Token':token})
        with urllib.request.urlopen(req,timeout=120) as response:return json.load(response)
    health=request('/health');assert health['version']=='0.1.22' and health['native']
    checks=[]
    for threads in [8,1,8]:
        request('/settings',{'max_workers':threads})
        result=request('/evaluate',{'session':'frozen-runtime','code':'a=Table[N[1/(i+j),15],{i,1,128},{j,1,128}];Dot[a,a]'})
        assert result['ok'],result
        execution=result['result']['execution'];assert execution['threads_used']==execution['thread_limit']==threads
        assert execution['affinity']['physical_cores']==threads
        assert execution['operations']['matrix_product']['path']==health['cpu_features']['selected']
        checks.append(execution)
    result=request('/evaluate',{'session':'scope','code':'a=4;Block[{a,p},a=7;p=Labeled[Plot[x^2,{x,0,1}],"curve"];{p,a}]'})
    assert result['ok'] and len(result['result']['items'])==2
    assert request('/evaluate',{'session':'scope','code':'a'})['result']['text']=='4'
    result=request('/evaluate',{'session':'missing','code':'Length[c]'})
    assert not result['ok'] and 'Length input is undefined' in result['error']
    report={'status':'passed','version':health['version'],'cpu':health['cpu_features'],'workersTransitions':checks,'plotScoping':True,'missingDependencyDiagnostic':True}
    (root/'work/frozen-runtime-v0122-report.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
finally:process.terminate();process.wait(timeout=10)
