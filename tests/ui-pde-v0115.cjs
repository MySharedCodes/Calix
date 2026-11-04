const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages().find(p=>/tauri.localhost/.test(p.url())):await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  fs.mkdirSync('work/ui',{recursive:true});
  if(desktop){await page.evaluate(()=>{localStorage.clear();sessionStorage.clear()});await page.reload();await page.setViewportSize({width:1440,height:1000})}else await page.goto('http://127.0.0.1:8765');
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('button',{name:'新建笔记',exact:true}).first().click();
  const first=page.locator('.cell').first();
  await first.locator('.cm-content').fill('Labeled[2^10,"value"]\nDet[{{1,2},{3,4}}]');
  let response=page.waitForResponse(r=>r.url().endsWith('/api/evaluate')&&r.request().method()==='POST');
  await first.locator('.cm-content').press('Control+Enter');assert.ok((await(await response).json()).ok);
  assert.equal(await first.getByTitle('复制到下一行输入',{exact:true}).count(),2);
  await first.getByTitle('复制到下一行输入',{exact:true}).nth(1).click();
  assert.equal(await page.locator('.cell').nth(1).locator('.cm-content').innerText(),'-2');
  await first.getByTitle('复制到下一行输入',{exact:true}).nth(0).click();
  assert.equal(await page.locator('.cell').nth(1).locator('.cm-content').innerText(),'1024');
  assert.equal(await page.locator('.cell').nth(2).locator('.cm-content').innerText(),'-2');
  const notebookCount=await page.locator('.notebook-row').count();
  assert.equal(notebookCount,2);
  const themes=[['简洁白','white'],['深空黑','black'],['少女粉','pink'],['海洋蓝','ocean'],['森林绿','forest']];
  for(const [name,id] of themes){
   await page.getByRole('button',{name:'偏好设置',exact:true}).click();
   await page.getByRole('button',{name,exact:true}).click();
   assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),id);
   await page.getByTitle('关闭设置',{exact:true}).click();
   const colors=await page.evaluate(()=>({fg:getComputedStyle(document.documentElement).color,bg:getComputedStyle(document.documentElement).backgroundColor}));assert.notEqual(colors.fg,colors.bg);
   await page.screenshot({path:`work/ui/theme-${id}-${desktop?'desktop':'browser'}-v0115.png`});
  }
  await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),'forest');
  const records=[];
  for(const title of ['吊桥：混合维有限元受力分析','机翼：稳态流场与湍流闭合']){
   await page.getByRole('button',{name:'计算示例',exact:true}).click();
   await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0,JSON.stringify(await page.locator('.katex-error').evaluateAll(elements=>elements.map(e=>({text:e.textContent,error:e.getAttribute('title')})))));
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(()=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===2||document.querySelector('.notebook .error-message'),null,{timeout:120000});
   assert.equal(await page.locator('.notebook .error-message').count(),0,await page.locator('.notebook .error-message').allTextContents());
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),2);
   const allText=(await page.locator('.notebook .output').allTextContents()).join(' ');
   assert.match(allText,title.startsWith('吊桥')?/relative residual/:/C_L/);
   const visual=page.locator(title.startsWith('吊桥')?'.scientific-scene':'.plot-output').first();
   await visual.scrollIntoViewIfNeeded();
   await visual.locator('canvas').first().waitFor({timeout:20000}).catch(()=>{});
   const pixels=[];
   if(title.startsWith('吊桥')){
    for(const index of [0,1,2]){
     const scene=page.locator('.scientific-scene').nth(index);await scene.scrollIntoViewIfNeeded();
     await page.waitForTimeout(600);
     const sample=c=>{const s=document.createElement('canvas');s.width=c.width;s.height=c.height;const ctx=s.getContext('2d');ctx.drawImage(c,0,0);const p=ctx.getImageData(0,0,s.width,s.height).data;let colored=0,hash=2166136261;for(let j=0;j<p.length;j+=4){if(Math.max(p[j],p[j+1],p[j+2])-Math.min(p[j],p[j+1],p[j+2])>30)colored++;hash=Math.imul(hash^p[j],16777619)}return {colored,hash,width:c.width,height:c.height}};
     const result=await scene.locator('canvas').evaluate(sample);
     assert.ok(result.colored>500,JSON.stringify(result));pixels.push(result);
     await scene.screenshot({path:`work/ui/bridge-${index}-${desktop?'desktop':'browser'}-v0115.png`});
     if(index===1){
      const box=await scene.locator('canvas').boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+80,box.y+box.height/2+30,{steps:10});await page.mouse.up();await page.waitForTimeout(350);
      assert.notEqual((await scene.locator('canvas').evaluate(sample)).hash,result.hash);
      await page.setViewportSize({width:390,height:844});await scene.scrollIntoViewIfNeeded();await page.waitForTimeout(400);
      assert.ok((await scene.locator('canvas').evaluate(sample)).colored>200);
      await scene.screenshot({path:`work/ui/bridge-mobile-${desktop?'desktop':'browser'}-v0115.png`});
      await page.setViewportSize({width:1440,height:1000});
     }
    }
   }else{
    await page.locator('.plot-output').nth(1).scrollIntoViewIfNeeded();await page.waitForTimeout(500);await page.locator('.plot-output').nth(1).screenshot({path:`work/ui/wing-speed-${desktop?'desktop':'browser'}-v0115.png`});
    assert.equal(await page.locator('.js-plotly-plot').count(),5);
   }
   // Saved results must survive notebook validation, including FE triangles.
   await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),2);
   records.push({title,pixels});
  }
  await page.setViewportSize({width:390,height:844});
  await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:`work/ui/pde-mobile-${desktop?'desktop':'browser'}-v0115.png`});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/ui-pde-${desktop?'desktop':'browser'}-v0115-report.json`,JSON.stringify({status:'passed',outputInsertion:true,originInsertionOrder:true,themePersistence:true,themes:5,records,mobileWidth:390,errors},null,2));
  console.log('PDE, output insertion and themes UI passed',desktop?'desktop':'browser');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
