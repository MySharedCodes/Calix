const{spawn,execFile,execFileSync}=require('node:child_process');
const fs=require('node:fs');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 const app=spawn('D:/Calix/release/Calix-portable/Calix.exe',[],{windowsHide:true,env:{...process.env,CALIX_MAX_WORKERS:'8',WEBVIEW2_USER_DATA_FOLDER:'D:/Calix/work/webview-v0123-test',WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9223'}});
 app.on('exit',(code,signal)=>fs.writeFileSync('work/desktop-process-v0123.json',JSON.stringify({code,signal,time:new Date().toISOString()})));
 app.stderr.on('data',data=>fs.appendFileSync('work/desktop-stderr-v0123.log',data));
 try{
  for(let i=0;i<100;i++){try{const response=await fetch('http://127.0.0.1:9223/json/version');if(response.ok)break;}catch(e){if(app.exitCode!==null)throw Error('Desktop exited');}await delay(300);}
  await new Promise((resolve,reject)=>execFile(process.execPath,['tests/ui-v0123.cjs'],{env:{...process.env,CALIX_DESKTOP:'1'},windowsHide:true,timeout:720000},(error,stdout,stderr)=>{console.log(stdout);if(stderr)console.error(stderr);error?reject(error):resolve();}));
 }finally{
  if(app.exitCode===null){execFileSync('powershell.exe',['-NoProfile','-Command',`$p=Get-Process -Id ${app.pid};$null=$p.CloseMainWindow()`],{windowsHide:true});for(let i=0;i<100&&app.exitCode===null;i++)await delay(100);if(app.exitCode===null)throw Error('Test app did not close gracefully');}
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
