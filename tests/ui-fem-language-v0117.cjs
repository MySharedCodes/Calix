const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');

(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(desktop){assert.ok(process.env.WEBVIEW2_USER_DATA_FOLDER?.includes('v0117-test'));await page.waitForURL(/tauri.localhost/,{timeout:30000});}
  else await page.goto('http://127.0.0.1:8765');
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width:1440,height:1000});
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  assert.equal(await page.getByRole('spinbutton',{name:'最大 CPU Workers',exact:true}).inputValue(),'8');
  assert.equal(await page.getByRole('spinbutton',{name:'最大 CPU Workers',exact:true}).getAttribute('max'),'24');
  await page.getByTitle('关闭设置',{exact:true}).click();
  fs.mkdirSync('work/ui',{recursive:true});
  const cases=[];
  const sample=c=>{
   const copy=document.createElement('canvas');copy.width=c.width;copy.height=c.height;
   const ctx=copy.getContext('2d');ctx.drawImage(c,0,0);const bytes=ctx.getImageData(0,0,c.width,c.height).data;
   let colored=0,hash=2166136261;
   for(let i=0;i<bytes.length;i+=4){if(Math.max(bytes[i],bytes[i+1],bytes[i+2])-Math.min(bytes[i],bytes[i+1],bytes[i+2])>20)colored++;hash=Math.imul(hash^bytes[i],16777619);}
   return {colored,hash,width:c.width,height:c.height};
  };
  for(const [title,id,count] of [['吊桥：混合维有限元受力分析','bridge',5],['机翼：稳态流场与湍流闭合','wing',3],['类氢离子：薛定谔方程解析解','hydrogen',4]]){
   await page.getByRole('button',{name:'计算示例',exact:true}).click();
   await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0,await page.locator('.katex-error').allTextContents());
   assert.equal(await page.locator('.markdown-content pre').count(),0);
   assert.ok(!(await page.locator('.cm-content').allTextContents()).join('\n').match(/WingFlowSolve|FEMBridgeSolve/));
   const started=Date.now();
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(expected=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===expected||document.querySelector('.notebook .error-message'),count,{timeout:240000});
   assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count);
   const seconds=(Date.now()-started)/1000,pixels=[];
   if(id==='wing'){
    assert.equal(await page.locator('.js-plotly-plot').count(),4);
    const density=page.locator('.js-plotly-plot').nth(1);
    const data=await density.evaluate(el=>el.data[0].z.flat().filter(x=>x!==null));
    assert.ok(data.length>5000);assert.ok(Math.max(...data)-Math.min(...data)>.1);
    await density.scrollIntoViewIfNeeded();await density.screenshot({path:`work/ui/wing-${mode}-v0117.png`});
   }else{
    const scenes=page.locator('.scientific-scene');assert.equal(await scenes.count(),id==='bridge'?2:6);
    for(let i=0;i<await scenes.count();i++){
     const scene=scenes.nth(i);await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
     const canvas=scene.locator('canvas');const before=await canvas.evaluate(sample);
     assert.ok(before.colored>200,JSON.stringify({id,i,before}));pixels.push(before);
     if(i===0){
      await scene.screenshot({path:`work/ui/${id}-${mode}-v0117.png`});
      const bounds=await canvas.boundingBox();await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+70,bounds.y+bounds.height/2+20,{steps:10});await page.mouse.up();await page.waitForTimeout(400);
      assert.notEqual((await canvas.evaluate(sample)).hash,before.hash);
     }
    }
   }
   await page.setViewportSize({width:390,height:844});
   await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});
   const visual=page.locator(id==='wing'?'.plot-output':'.scientific-scene').last();await visual.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   if(id!=='wing')assert.ok((await visual.locator('canvas').evaluate(sample)).colored>100);
   await page.screenshot({path:`work/ui/${id}-mobile-${mode}-v0117.png`});
   await page.setViewportSize({width:1440,height:1000});
   await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count,'Saved outputs must survive reload');
   if(await page.getByTitle('展开侧栏',{exact:true}).count())await page.getByTitle('展开侧栏',{exact:true}).click();
   cases.push({title,calculationCells:count,seconds,pixels});
  }
  assert.deepEqual(errors,[]);
  const report={status:'passed',workers:8,physicalCores:24,desktop,mobileWidth:390,cases,errors};
  fs.writeFileSync(`work/ui-fem-language-${mode}-v0117-report.json`,JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
