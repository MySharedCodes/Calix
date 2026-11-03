const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),{spawn,execFileSync}=require('node:child_process');
const directory=process.env.CALIX_PREFS_PROFILE||'D:/Calix/work/webview-v0121-test';
const expected={'calix-digits':'32','calix-workers':'8','calix-language':'ja','calix-theme':'ocean','calix-notebook-zoom':'115'};
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function launch(){
 const child=spawn('D:/Calix/release/Calix-portable/Calix.exe',[],{windowsHide:true,env:{...process.env,CALIX_MAX_WORKERS:'8',WEBVIEW2_USER_DATA_FOLDER:directory,WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:'--remote-debugging-port=9223'}});
 for(let i=0;i<100;i++){
  try{const browser=await chromium.connectOverCDP('http://127.0.0.1:9223');const page=browser.contexts()[0].pages()[0];await page.waitForSelector('.engine-status.ready',{timeout:30000});return{child,browser,page};}
  catch(error){if(child.exitCode!==null)throw new Error('Desktop exited '+child.exitCode);await delay(300);}
 }
 throw new Error('Desktop did not start');
}
async function close(app){
 execFileSync('powershell.exe',['-NoProfile','-Command',`$p=Get-Process -Id ${app.child.pid}; $null=$p.CloseMainWindow()`],{windowsHide:true});
 for(let i=0;i<100&&app.child.exitCode===null;i++)await delay(100);
 assert.notEqual(app.child.exitCode,null,'Desktop did not close gracefully');
 await app.browser.close().catch(()=>{});
}
(async()=>{
 let app=await launch();
 try{
  const page=app.page;await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  await page.getByLabel('数值近似有效位数').fill('32');
  await page.getByLabel('最大 CPU Workers',{exact:true}).fill('8');
  await page.getByRole('button',{name:'海洋蓝',exact:true}).click();
  await page.getByLabel('界面语言',{exact:true}).selectOption('ja');
  await page.locator('.settings-modal .panel-heading button').click();
  await page.evaluate(()=>{
   const host=document.querySelector('.notebook');for(let i=0;i<3;i++)host.dispatchEvent(new WheelEvent('wheel',{deltaY:-100,ctrlKey:true,bubbles:true,cancelable:true}));
  });
  await page.waitForFunction(expected=>Object.entries(expected).every(([k,v])=>localStorage.getItem(k)===v),expected,{timeout:10000});
  for(let i=0;i<100;i++){
   if(fs.existsSync(directory+'/preferences.json')&&JSON.stringify(JSON.parse(fs.readFileSync(directory+'/preferences.json','utf8')))===JSON.stringify(Object.fromEntries(Object.entries(expected).sort())))break;
   await delay(100);
  }
  assert.deepEqual(JSON.parse(fs.readFileSync(directory+'/preferences.json','utf8')),expected);
  // Remove the browser cache so the next process must restore the native file.
  await page.evaluate(keys=>keys.forEach(k=>localStorage.removeItem(k)),Object.keys(expected));
  await close(app);app=await launch();
  await app.page.waitForFunction(expected=>Object.entries(expected).every(([k,v])=>localStorage.getItem(k)===v),expected,{timeout:30000});
  assert.equal(await app.page.evaluate(()=>document.documentElement.lang),'ja');
  assert.equal(await app.page.evaluate(()=>document.documentElement.dataset.theme),'ocean');
  await app.page.locator('.sidebar-bottom button').click();
  assert.equal(await app.page.locator('.settings-modal input').nth(0).inputValue(),'32');
  assert.equal(await app.page.locator('.settings-modal input').nth(1).inputValue(),'8');
  await app.page.screenshot({path:'D:/Calix/work/ui/preferences-restart-v0121.png'});
  const report={status:'passed',actualProcessRestart:true,browserPreferenceCacheCleared:true,nativeFile:directory+'/preferences.json',restored:expected};
  fs.writeFileSync('D:/Calix/work/preferences-restart-v0121.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report));
 }finally{if(app.child.exitCode===null)await close(app);}
})().catch(error=>{console.error(error);process.exitCode=1;});
