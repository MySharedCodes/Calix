const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto('http://127.0.0.1:8767');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByTitle('展开侧栏',{exact:true}).click().catch(()=>{});
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  if(desktop){
   const health=await page.evaluate(async()=>{const {port,token}=await window.__TAURI_INTERNALS__.invoke('connection_info');return(await fetch(`http://127.0.0.1:${port}/api/health`,{headers:{'X-Calix-Token':token}})).json();});
   assert.equal(health.version,'0.1.19');assert.deepEqual(health.components,{pde:true,languages:true,themes:true});
  }
  const errors=[],cases=[];page.on('pageerror',e=>errors.push(e.message));
  const pixelSample=c=>{
   const copy=document.createElement('canvas');copy.width=c.width;copy.height=c.height;
   const ctx=copy.getContext('2d');ctx.drawImage(c,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;
   let colored=0,hash=2166136261;
   for(let i=0;i<data.length;i+=4){if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)colored++;hash=Math.imul(hash^data[i],16777619);}
   return {colored,hash,width:c.width,height:c.height};
  };
  for(const [title,id,count] of [['石英与空气：电磁波反射和透射','quartz',3],['齿轮啮合：接触与扭矩传递','gear',4],['吊桥：混合维有限元受力分析','bridge',6]]){
   if(process.env.CALIX_TEST_CASE&&process.env.CALIX_TEST_CASE!==id)continue;
   await page.getByRole('button',{name:'计算示例',exact:true}).click();
   await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0,await page.locator('.katex-error').allTextContents());
   const start=Date.now();await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(n=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===n||document.querySelector('.notebook .error-message'),count,{timeout:300000});
   assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
   const scene=page.locator('.scientific-scene').last();await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(600);
   const canvas=scene.locator('canvas'),pixels=await canvas.evaluate(pixelSample);
   assert.ok(pixels.colored>300,JSON.stringify({id,pixels}));
   assert.ok(await scene.locator('.scalar-legend').count());
   await scene.screenshot({path:`work/ui/${id}-${mode}-v0119.png`});
   const box=await canvas.boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();
   await page.mouse.move(box.x+box.width/2+60,box.y+box.height/2+20,{steps:8});await page.mouse.up();await page.waitForTimeout(300);
   assert.notEqual((await canvas.evaluate(pixelSample)).hash,pixels.hash);
   await page.setViewportSize({width:390,height:844});
   await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});
   await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(400);
   assert.ok((await canvas.evaluate(pixelSample)).colored>100);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`work/ui/${id}-mobile-${mode}-v0119.png`});
   await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count);
   await page.setViewportSize({width:1440,height:1000});
   await page.getByTitle('展开侧栏',{exact:true}).click().catch(()=>{});
   cases.push({title,cells:count,seconds:(Date.now()-start)/1000,pixels});
   console.log(id,'passed');
  }
  assert.deepEqual(errors,[]);
  const report={status:'passed',cases,errors,workers:8};fs.writeFileSync(`work/ui-new-fem-${mode}-v0119-report.json`,JSON.stringify(report,null,2));console.log(report);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
