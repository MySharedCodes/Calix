const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto('http://127.0.0.1:8765');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  const errors=[],records=[];let session,lastSource;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/evaluate')){session=r.postDataJSON().session;lastSource=r.postDataJSON().code;}});
  const expand=page.getByTitle('展开侧栏',{exact:true});if(await expand.count())await expand.click();
  const pixels=canvas=>{
   const c=document.createElement('canvas');c.width=canvas.width;c.height=canvas.height;
   const ctx=c.getContext('2d');ctx.drawImage(canvas,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;
   let colored=0;for(let i=0;i<data.length;i+=4)if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)colored++;
   return colored;
  };
  for(const [title,id,count] of [['齿轮啮合：接触与扭矩传递','gear',4],['波动光学：石英与空气的反射和折射','quartz',3]]){
   const start=Date.now();
   if(!await page.locator('.library-panel').count())await page.getByRole('button',{name:'计算示例',exact:true}).click();
   await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0);
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(n=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===n||document.querySelector('.notebook .error-message'),count,{timeout:420000});
   assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
   let metrics;
   if(id==='gear'){
    const connection=desktop?await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('connection_info')):{port:8765,token:'calix-local-development'};
    metrics=await page.evaluate(async({connection,session})=>{
     const response=await fetch(`http://127.0.0.1:${connection.port}/api/evaluate`,{method:'POST',headers:{'Content-Type':'application/json','X-Calix-Token':connection.token},body:JSON.stringify({session,code:'Labeled[{Max[p₁]*210000,Total[p₂]*42000000},"peak pressure [MPa], force [N]"]\nLabeled[{r,v}*210000,"element and nodal VM [MPa]"]\nLabeled[Table[{Length[Part[p,h]],Length[Part[f,h]]},{h,1,2}],"mesh sizes"]'})});return response.json();
    },{connection,session});assert.equal(metrics.ok,true);
    fs.writeFileSync(`work/gear-final-${mode}-v0121.json`,JSON.stringify(metrics,null,2));
   }
   const scenes=page.locator('.scientific-scene');
   assert.equal(await scenes.count(),id==='gear'?3:2);
   for(let i=0;i<await scenes.count();i++){
    const scene=scenes.nth(i);await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(700);
    assert.ok(await scene.locator('canvas').evaluate(pixels)>1500);
    await scene.screenshot({path:`work/ui/${id}-${i}-${mode}-v0121.png`});
   }
   await page.setViewportSize({width:390,height:844});
   const collapse=page.getByTitle('收起侧栏',{exact:true});if(await collapse.count())await collapse.click();
   await scenes.last().scrollIntoViewIfNeeded();await page.waitForTimeout(300);
   assert.ok(await scenes.last().locator('canvas').evaluate(pixels)>300);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`work/ui/${id}-mobile-${mode}-v0121.png`});
   await page.setViewportSize({width:1440,height:1000});
   if(id==='quartz'){
    const lastCode=lastSource;
    const connection=desktop?await page.evaluate(()=>window.__TAURI_INTERNALS__.invoke('connection_info')):{port:8765,token:'calix-local-development'};
    await page.evaluate(async({connection,session})=>{await fetch(`http://127.0.0.1:${connection.port}/api/cancel/${session}`,{method:'POST',headers:{'Content-Type':'application/json','X-Calix-Token':connection.token},body:'{}'});},{connection,session});
    await page.waitForTimeout(700);await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
    assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count);
    const calls=[];const listener=r=>{if(r.url().endsWith('/api/evaluate'))calls.push(r.postDataJSON().code);};
    page.on('request',listener);
    const completed=page.waitForResponse(r=>r.url().endsWith('/api/evaluate')&&r.request().postDataJSON().code===lastCode,{timeout:240000});
    const editor=page.locator('.cm-content').last();await editor.click();await editor.press('Control+Enter');
    assert.equal((await completed).status(),200);
    await page.waitForFunction(()=>document.querySelector('.statusbar')?.textContent.includes('就绪'),null,{timeout:30000});
    await page.waitForFunction(()=>document.querySelectorAll('.scientific-scene').length===2,null,{timeout:180000});
    await page.waitForTimeout(1000);
    assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
    assert.equal(calls.length,3,'cold final-cell run did not restore its two dependencies');
    page.off('request',listener);
   }
   records.push({title,seconds:(Date.now()-start)/1000,metrics});
   const exp=page.getByTitle('展开侧栏',{exact:true});if(await exp.count())await exp.click();
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/ui-v0121-${mode}-report.json`,JSON.stringify({status:'passed',workers:8,records,coldOpticsReplay:true,errors},null,2));
  console.log(JSON.stringify(records));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
