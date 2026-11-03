const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const {unzlibSync,strFromU8}=require('fflate');
const parseSaved=raw=>JSON.parse(raw.startsWith('calix-zlib-v1:')?strFromU8(unzlibSync(Buffer.from(raw.slice(14),'base64'))):raw);

(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(desktop){assert.ok(process.env.WEBVIEW2_USER_DATA_FOLDER?.includes('v0118-test'));await page.waitForURL(/tauri.localhost/,{timeout:30000});}
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
  for(const [title,id,count] of [['吊桥：混合维有限元受力分析','bridge',6],['机翼：稳态流场与湍流闭合','wing',3]]){
   if(process.env.CALIX_TEST_CASE && process.env.CALIX_TEST_CASE!==id)continue;
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
    assert.equal(await page.locator('.js-plotly-plot').count(),3);
    const density=page.locator('.js-plotly-plot').nth(1);
    const data=await density.evaluate(el=>el.data[0].z.flat().filter(x=>x!==null));
    assert.ok(data.length>5000);assert.ok(Math.max(...data)-Math.min(...data)>.1);
    const types=await density.evaluate(el=>el.data.map(t=>t.type));
    assert.equal(types[0],'heatmap');assert.ok(types.length>5);assert.ok(types.slice(1).every(t=>t==='scatter'));
    await density.scrollIntoViewIfNeeded();await density.screenshot({path:`work/ui/wing-${mode}-v0118.png`});
   }else{
    const scenes=page.locator('.scientific-scene');assert.equal(await scenes.count(),3);
    assert.match(await scenes.last().locator('.scalar-legend').innerText(),/MPa/);
    for(let i=0;i<await scenes.count();i++){
     const scene=scenes.nth(i);await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
     const canvas=scene.locator('canvas');const before=await canvas.evaluate(sample);
     assert.ok(before.colored>200,JSON.stringify({id,i,before}));pixels.push(before);
     if(i===0){
      await scene.screenshot({path:`work/ui/${id}-${mode}-v0118.png`});
      const bounds=await canvas.boundingBox();await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);await page.mouse.down();await page.mouse.move(bounds.x+bounds.width/2+70,bounds.y+bounds.height/2+20,{steps:10});await page.mouse.up();await page.waitForTimeout(400);
      assert.notEqual((await canvas.evaluate(sample)).hash,before.hash);
     }
     if(i===1)await scene.screenshot({path:`work/ui/bridge-deformation-${mode}-v0118.png`});
     if(i===2)await scene.screenshot({path:`work/ui/bridge-stress-${mode}-v0118.png`});
    }
   }
   await page.setViewportSize({width:390,height:844});
   await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});
   const visual=id==='wing'?page.locator('.plot-output').nth(1):page.locator('.scientific-scene').last();await visual.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   if(id!=='wing')assert.ok((await visual.locator('canvas').evaluate(sample)).colored>100);
   await page.screenshot({path:`work/ui/${id}-mobile-${mode}-v0118.png`});
   await page.setViewportSize({width:1440,height:1000});
   const rawSaved=await page.evaluate(()=>localStorage.getItem('calix-workspace-v1'));
   const decodedSaved=parseSaved(rawSaved);
   fs.writeFileSync(`work/${id}-${mode}-v0118-saved.json`,JSON.stringify(decodedSaved));
   await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),count,'Saved outputs must survive reload');
   if(id==='bridge'){
    assert.match(await page.locator('.scalar-legend').innerText(),/MPa/);
    const saved=decodedSaved.documents.find(d=>d.id===decodedSaved.active);
    const cloud=saved.cells.at(-1).result.items.at(-1);
    const triangles=cloud.primitives.filter(p=>p.type==='triangle');
    assert.ok(triangles.length>3000);assert.ok(new Set(triangles.flatMap(p=>p.colors)).size>20);
    for(const x of [-20,20])for(const y of [-5,5]){
     const tower=triangles.filter(p=>p.points.every(v=>Math.abs(v[0]-x)<.6&&Math.abs(v[1]-y)<.6));
     assert.ok(tower.length>100);const z=tower.flatMap(p=>p.points.map(v=>v[2]));assert.equal(Math.min(...z),0);assert.equal(Math.max(...z),24);
    }
   }else{
    const data=await page.locator('.js-plotly-plot').nth(1).evaluate(el=>el.data);
    assert.ok(data.length>5&&data[0].type==='heatmap');
   }
   if(await page.getByTitle('展开侧栏',{exact:true}).count())await page.getByTitle('展开侧栏',{exact:true}).click();
   cases.push({title,calculationCells:count,seconds,pixels});
  }
  assert.equal(await page.getByText(/工作空间存储已满/).count(),0);
  await page.getByRole('button',{name:'新建笔记',exact:true}).first().click();
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  await page.getByRole('button',{name:'海洋蓝',exact:true}).click();
  await page.getByTitle('关闭设置',{exact:true}).click();
  const ocean=await page.locator('.main-shell').evaluate(async el=>{
   const style=getComputedStyle(el),url=style.backgroundImage.slice(5,-2),picture=new Image();picture.src=url;await picture.decode();
   const c=document.createElement('canvas');c.width=400;c.height=280;const ctx=c.getContext('2d');ctx.drawImage(picture,0,0);const bytes=ctx.getImageData(0,0,400,280).data;
   let colored=0;for(let i=3;i<bytes.length;i+=4)if(bytes[i]>10)colored++;
   return {repeat:style.backgroundRepeat,position:style.backgroundPosition,size:style.backgroundSize,svg:decodeURIComponent(url),colored};
  });
  assert.equal(ocean.repeat,'no-repeat');assert.ok(ocean.colored>15000);assert.ok(ocean.svg.includes('M60 127'));assert.equal((ocean.svg.match(/<svg/g)||[]).length,1);
  await page.screenshot({path:`work/ui/ocean-${mode}-v0118.png`});
  await page.setViewportSize({width:390,height:844});await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});
  await page.waitForFunction(()=>document.querySelector('.app').classList.contains('sidebar-collapsed'));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:`work/ui/ocean-mobile-${mode}-v0118.png`});
  await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),'ocean');
  assert.deepEqual(errors,[]);
  const report={status:'passed',workers:8,physicalCores:24,desktop,mobileWidth:390,cases,ocean:{singleOrca:true,noRepeat:true,coloredPixels:ocean.colored},errors};
  fs.writeFileSync(`work/ui-fem-language-${mode}-v0118-report.json`,JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
