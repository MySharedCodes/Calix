const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try {
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto('http://127.0.0.1:8765');
  await page.setViewportSize({width:1440,height:1000});
  const expand=page.getByTitle('展开侧栏',{exact:true});if(await expand.count())await expand.click();
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  const errors=[],records=[];page.on('pageerror',e=>errors.push(e.message));
  const pixels=canvas=>{
   const c=document.createElement('canvas');c.width=canvas.width;c.height=canvas.height;
   const ctx=c.getContext('2d');ctx.drawImage(canvas,0,0);const d=ctx.getImageData(0,0,c.width,c.height).data;
   let colored=0,hash=2166136261;
   for(let i=0;i<d.length;i+=4){if(Math.max(d[i],d[i+1],d[i+2])-Math.min(d[i],d[i+1],d[i+2])>25)colored++;hash=Math.imul(hash^d[i],16777619);}
   return {colored,hash,width:c.width,height:c.height};
  };
  async function wheelTest(host,canvas=false){
   await host.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
   const value=()=>canvas?host.locator('canvas').evaluate(pixels).then(x=>x.hash):host.evaluate(e=>JSON.stringify(e._fullLayout.xaxis.range));
   const hover=async()=>{const b=await host.boundingBox();await page.mouse.move(b.x+b.width*.6,b.y+b.height*.5);};
   // A click on the plot toolbar deactivates its drawing surface.
   await host.locator('..').locator('.plot-tools span').click();
   await hover();const before=await value(),top=await page.evaluate(()=>document.scrollingElement.scrollTop);
   await page.mouse.wheel(0,-130);await page.waitForTimeout(300);
   assert.equal(await value(),before,'wheel changed an inactive plot');
   assert.notEqual(await page.evaluate(()=>document.scrollingElement.scrollTop),top,'inactive plot blocked notebook scrolling');
   await hover();await page.mouse.down();await page.mouse.up();await page.waitForTimeout(200);
   const active=await value(),activeTop=await page.evaluate(()=>document.scrollingElement.scrollTop);
   await page.mouse.wheel(0,-120);await page.waitForTimeout(500);
   assert.notEqual(await value(),active,'click did not activate wheel zoom');
   assert.equal(await page.evaluate(()=>document.scrollingElement.scrollTop),activeTop,'active zoom scrolled notebook');
   await host.locator('..').locator('.plot-tools span').click();await hover();
   const deactivated=await value();await page.mouse.wheel(0,-80);await page.waitForTimeout(300);
   assert.equal(await value(),deactivated,'outside click did not deactivate wheel zoom');
  }
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  assert.equal(await page.locator('.component-status').count(),0);
  assert.ok(!(await page.getByRole('dialog').innerText()).includes('PDE'));
  await page.getByTitle('关闭设置').click();
  for(const [title,id,count] of [
   ['齿轮啮合：接触与扭矩传递','gear',4],
   ['波动光学：石英与空气的反射和折射','quartz',3],
   ['格点色动力学：SU(3) 规范场与 Wilson 环','lattice',3]]){
   const start=Date.now();
   if(!await page.locator('.library-panel').count())await page.getByRole('button',{name:'计算示例',exact:true}).click();
   await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0,await page.locator('.katex-error').allTextContents());
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(n=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===n||document.querySelector('.notebook .error-message'),count,{timeout:360000});
   assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
   if(id!=='lattice'){
    const scene=page.locator('.scientific-scene').last();await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(800);
    const sample=await scene.locator('canvas').evaluate(pixels);
    assert.ok(sample.colored>3000,JSON.stringify(sample));
    await scene.screenshot({path:'work/ui/'+id+'-'+mode+'-v0120.png'});
    await wheelTest(scene.locator('.plot-canvas'),true);
    if(id==='gear')await wheelTest(page.locator('.js-plotly-plot').last());
    await page.setViewportSize({width:390,height:844});
    const collapse=page.getByTitle('收起侧栏',{exact:true});if(await collapse.count())await collapse.click();
    await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(400);
    assert.ok((await scene.locator('canvas').evaluate(pixels)).colored>500);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:'work/ui/'+id+'-mobile-'+mode+'-v0120.png'});
    await page.setViewportSize({width:1440,height:1000});
    const exp=page.getByTitle('展开侧栏',{exact:true});if(await exp.count())await exp.click();
   }else{
    await page.locator('.notebook .cell').last().scrollIntoViewIfNeeded();
    await page.screenshot({path:'work/ui/lattice-'+mode+'-v0120.png'});
   }
   await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count);
   records.push({title,cells:count,seconds:(Date.now()-start)/1000});console.log(id,'passed');
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync('work/ui-v0120-'+mode+'-report.json',JSON.stringify({status:'passed',records,errors,workers:8,clickToActivateWheel:true,preferencesComponentStatusRemoved:true},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
