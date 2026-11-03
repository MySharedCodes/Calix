const{chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const b=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await b.newPage({viewport:{width:1440,height:1000}}),calls=[];
 const doc={format:'calix-notebook',version:1,title:'Dependency check',id:'dependencies',path:null,updated:1,example:'runtime-check',cells:['a=3','b=a+2','a*b'].map((code,i)=>({id:'c'+i,mode:'source',code}))};
 await page.addInitScript(doc=>localStorage.setItem('calix-workspace-v1',JSON.stringify({version:1,active:doc.id,documents:[doc]})),doc);
 await page.goto('http://127.0.0.1:8765');await page.waitForSelector('.engine-status.ready');
 page.on('request',r=>{if(r.url().endsWith('/api/evaluate'))calls.push(r.postDataJSON().code);});
 const run=async(index)=>{
  const response=page.waitForResponse(r=>r.url().endsWith('/api/evaluate')&&r.request().postDataJSON().code===(index===0?'a=3':'a*b'));
  const editor=page.locator('.cm-content').nth(index);await editor.click();await editor.press('Control+Enter');assert.equal((await response).status(),200);
  await page.waitForFunction(()=>!document.querySelector('.statusbar')?.textContent.includes('计算中'));await page.waitForTimeout(150);
  assert.equal(await page.locator('.error-message').count(),0);
 };
 await run(0);assert.deepEqual(calls.splice(0),['a=3']);
 await run(2);assert.deepEqual(calls.splice(0),['a=3','b=a+2','a*b']);
 await run(2);assert.deepEqual(calls.splice(0),['a*b']);
 await page.reload();await page.waitForSelector('.engine-status.ready');await run(2);assert.deepEqual(calls.splice(0),['a=3','b=a+2','a*b']);
 assert.ok((await page.locator('.cell').last().innerText()).includes('15'));
 fs.writeFileSync('work/ui-dependencies-v0122-report.json',JSON.stringify({status:'passed',partialSessionReplay:true,warmLastCell:true,reloadReplay:true},null,2));
}finally{await b.close()}})().catch(e=>{console.error(e);process.exitCode=1});
