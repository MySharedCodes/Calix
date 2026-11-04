const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages().find(p=>/tauri.localhost/.test(p.url())):await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  if(desktop){await page.addInitScript(key=>{if(!sessionStorage.getItem(key)){localStorage.clear();sessionStorage.setItem(key,'1');}},`v0111-${Date.now()}`);await page.reload();await page.setViewportSize({width:1440,height:1000});}else await page.goto('http://127.0.0.1:8765');
  await page.getByText('原生核心就绪').waitFor({timeout:30000});
  const openCase=async title=>{await page.getByRole('button',{name:'计算示例',exact:true}).click();await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();};
  const pixel=canvas=>canvas.evaluate(c=>{const other=document.createElement('canvas');other.width=c.width;other.height=c.height;const ctx=other.getContext('2d');ctx.drawImage(c,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;let colored=0,hash=2166136261;for(let i=0;i<data.length;i+=4){if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)colored++;hash=Math.imul(hash^data[i],16777619);hash=Math.imul(hash^data[i+1],16777619);}return{colored,hash};});
  const cases=[JSON.parse(fs.readFileSync('frontend/src/starter.json','utf8')),...JSON.parse(fs.readFileSync('frontend/src/example-notebooks.json','utf8'))],records=[];
  for(const notebook of cases){
   await openCase(notebook.title);await page.getByRole('button',{name:'全部运行',exact:true}).click();
   const count=notebook.cells.filter(c=>c.mode!=='markdown').length;
   await page.waitForFunction(n=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===n||document.querySelector('.notebook .error-message'),count,{timeout:120000});
   assert.equal(await page.locator('.notebook .error-message').count(),0,await page.locator('.notebook').innerText());
   if(notebook.title.startsWith('空气阻力')){
    assert.match(await page.locator('.markdown-content').allTextContents().then(v=>v.join('\n')),/第一部分.*线性空气阻力/);
    assert.equal(await page.locator('.animation-output').count(),2);
   }
   const scenes=page.locator('.field-scene');
   for(let i=0;i<await scenes.count();i++){
    const scene=scenes.nth(i),canvas=scene.locator('canvas');await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(450);
    const before=await pixel(canvas);assert.ok(before.colored>1500,JSON.stringify(before));
    const name=notebook.title.startsWith('电流线圈')?'magnetic':`gravity-${i+1}`;
    const overlays=await page.addStyleTag({content:'.toolbar,.topbar,.statusbar{visibility:hidden!important}'});
    await scene.screenshot({path:`work/ui/${name}-v0111.png`});await overlays.evaluate(e=>e.remove());
    await scene.getByRole('slider',{name:'动画进度',exact:true}).press('End');await page.waitForTimeout(350);assert.notEqual((await pixel(canvas)).hash,before.hash);
    const endOverlay=await page.addStyleTag({content:'.toolbar,.topbar,.statusbar{visibility:hidden!important}'});await scene.screenshot({path:`work/ui/${name}-end-v0111.png`});await endOverlay.evaluate(e=>e.remove());
    const changed=await pixel(canvas);await scene.getByRole('slider',{name:'不透明度',exact:true}).press('Home');await page.waitForTimeout(300);assert.notEqual((await pixel(canvas)).hash,changed.hash);
    await scene.getByRole('slider',{name:'不透明度',exact:true}).press('ArrowRight');
    await scene.getByTitle('播放动画',{exact:true}).click();await page.waitForTimeout(700);await scene.getByTitle('暂停动画',{exact:true}).click();
    assert.ok(parseFloat((await scene.locator('.animation-controls output').innerText()).split('=')[1])>0);
    await canvas.scrollIntoViewIfNeeded();const box=await canvas.boundingBox();const rotated=await pixel(canvas);
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+80,box.y+box.height/2+30,{steps:10});await page.mouse.up();await page.waitForTimeout(350);assert.notEqual((await pixel(canvas)).hash,rotated.hash);
    await scene.getByRole('slider',{name:'不透明度',exact:true}).fill(name==='magnetic'?'0.7':'2.2');
    await page.setViewportSize({width:390,height:844});await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(400);assert.ok((await pixel(canvas)).colored>500);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await page.screenshot({path:`work/ui/${name}-mobile-v0111.png`});await page.setViewportSize({width:1440,height:1000});
   }
   records.push({title:notebook.title,cells:count,fieldScenes:await scenes.count()});
  }
  await page.getByRole('button',{name:'新建笔记',exact:true}).first().click();
  const source=fs.readFileSync('frontend/src/examples.ts','utf8'),ts=require('typescript'),vm=require('node:vm'),context={exports:{},require:()=>({default:JSON.parse(fs.readFileSync('frontend/src/example-labels.json','utf8'))})};vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context);
  for(const code of context.exports.examples.find(e=>e.title==='数据拟合').codes){
   await page.locator('.cm-content').first().click();await page.keyboard.press('Control+A');await page.keyboard.insertText('Clear[x,f,data,row,e,ys,y,residuals];\n'+code);
   const evaluated=page.waitForResponse(response=>response.url().endsWith('/api/evaluate')&&response.request().method()==='POST',{timeout:30000});
   await page.keyboard.press('Control+Enter');assert.ok((await evaluated).ok());
   await page.waitForFunction(()=>!document.querySelector('.notebook .cell.running'));
   await page.waitForFunction(()=>document.querySelector('.notebook .output')||document.querySelector('.notebook .error-message'),null,{timeout:30000});
   assert.equal(await page.locator('.notebook .error-message').count(),0);await page.waitForTimeout(450);
   assert.ok(await page.locator('.notebook .js-plotly-plot').count()>=2);
   const overlay=await page.addStyleTag({content:'.toolbar,.topbar,.statusbar{visibility:hidden!important}'});await page.locator('.notebook .output').screenshot({path:'work/ui/data-fitting-v0111.png'});await overlay.evaluate(e=>e.remove());
  }
  const gravityTitle=cases.find(n=>n.title.startsWith('多天体')).title;await openCase(gravityTitle);await page.waitForTimeout(800);
  assert.equal(await page.getByText(/工作空间存储已满|自动保存失败/).count(),0);
  await page.reload();await page.getByText('原生核心就绪').waitFor();assert.equal(await page.locator('.field-scene').count(),2);
  const restored=page.locator('.field-scene canvas').last();await restored.scrollIntoViewIfNeeded();await page.waitForTimeout(450);assert.ok((await pixel(restored)).colored>1000);
  assert.deepEqual(errors,[]);fs.writeFileSync('work/ui/fields-v0111-report.json',JSON.stringify({status:'passed',desktop,records,fittingVariants:3,playback:true,opacity:true,rotation:true,mobile:true,restoredFields:true,errors},null,2));console.log('0.1.11 field scenes and fitting UI passed',records);
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
