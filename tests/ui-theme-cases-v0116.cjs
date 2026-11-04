const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]||await browser.contexts()[0].waitForEvent('page'):await browser.newPage({viewport:{width:1440,height:1000}});
  if(desktop)await page.waitForURL(/tauri.localhost/,{timeout:30000});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(desktop){assert.ok(process.env.WEBVIEW2_USER_DATA_FOLDER?.includes('v0116-test'),'Only clear an isolated test profile');await page.evaluate(()=>{localStorage.clear();sessionStorage.clear()});await page.reload()}else await page.goto('http://127.0.0.1:8765');
  await page.setViewportSize({width:1440,height:1000});await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  fs.mkdirSync('work/ui',{recursive:true});
  const colors=[];
  for(const [name,id,color] of [['简洁白','white',null],['深空黑','black',null],['少女粉','pink','#b7467d'],['海洋蓝','ocean','#146f9b'],['森林绿','forest','#357347']]){
   await page.getByRole('button',{name:'偏好设置',exact:true}).click();await page.getByRole('button',{name,exact:true}).click();await page.getByTitle('关闭设置',{exact:true}).click();
   const content=await page.locator('.brand img').evaluate(img=>getComputedStyle(img).content);
   if(color){
    const svg=decodeURIComponent(content);assert.ok(svg.includes(color),id);
    const pixel=await page.locator('.brand img').evaluate(async img=>{const url=getComputedStyle(img).content.slice(5,-2);const picture=new Image();picture.src=url;await picture.decode();const c=document.createElement('canvas');c.width=c.height=100;const ctx=c.getContext('2d');ctx.drawImage(picture,0,0,100,100);return Array.from(ctx.getImageData(5,50,1,1).data)});
    assert.deepEqual(pixel.slice(0,3),[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)));colors.push({theme:id,color,pixel});
   }else assert.equal(content,'normal');
   if(id==='pink'){
    const pattern=await page.locator('.notebook').evaluate(el=>getComputedStyle(el).backgroundImage);
    const svg=decodeURIComponent(pattern);assert.ok(svg.includes('340'));assert.ok(svg.includes('ellipse'));assert.ok(!/star|polygon/i.test(svg));
   }
   await page.screenshot({path:`work/ui/theme-${id}-${mode}-v0116.png`});
  }
  await page.reload();await page.getByText('原生核心就绪',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),'forest');
  const cases=[];
  for(const title of ['空气阻力下的二维抛体运动','高考数学：2022 全国乙卷理科第20题']){
   await page.getByRole('button',{name:'计算示例',exact:true}).click();await page.locator('.library-panel').getByRole('button',{name:title,exact:true}).click();
   assert.equal(await page.locator('.katex-error').count(),0,JSON.stringify(await page.locator('.katex-error').allTextContents()));
   assert.equal(await page.locator('.markdown-content pre').count(),0,'Prose must render as prose');
   const expected=title.startsWith('空气')?7:4;
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(count=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===count||document.querySelector('.notebook .error-message'),expected,{timeout:120000});
   assert.equal(await page.locator('.notebook .error-message').count(),0,await page.locator('.notebook .error-message').allTextContents());
   assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),expected);
   if(title.startsWith('空气')){
    const animation=page.locator('.animation-output').last();await animation.scrollIntoViewIfNeeded();
    const progress=animation.getByRole('slider',{name:'动画进度',exact:true});assert.equal(await progress.inputValue(),'0');
    await animation.getByTitle('播放动画',{exact:true}).click();await page.waitForTimeout(500);await animation.getByTitle('暂停动画',{exact:true}).click();assert.ok(Number(await progress.inputValue())>0);
    const plot=animation.locator('.js-plotly-plot');await plot.waitFor();assert.ok(await plot.locator('.scatterlayer path').count()>0);
    await page.screenshot({path:`work/ui/drag-animation-${mode}-v0116.png`});
   }else{
    const plot=page.locator('.plot-output').last();await plot.scrollIntoViewIfNeeded();
    await plot.locator('.scatterlayer path').first().waitFor();
    assert.deepEqual(await plot.locator('.js-plotly-plot').evaluate(el=>el.layout.yaxis.range),[-2.5,2.5]);
    await page.screenshot({path:`work/ui/conic-${mode}-v0116.png`});
   }
   await page.setViewportSize({width:390,height:844});await page.getByTitle('收起侧栏',{exact:true}).click().catch(()=>{});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`work/ui/${title.startsWith('空气')?'drag':'conic'}-mobile-${mode}-v0116.png`});await page.setViewportSize({width:1440,height:1000});
   if(await page.getByTitle('展开侧栏',{exact:true}).count())await page.getByTitle('展开侧栏',{exact:true}).click();
   cases.push({title,calculationCells:expected});
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/ui-theme-cases-${mode}-v0116-report.json`,JSON.stringify({status:'passed',colors,pinkAnimals:true,starsRemoved:true,whiteAndBlackOriginalMark:true,cases,animationPlayback:true,mobileWidth:390,errors},null,2));
  console.log('Theme marks, wallpaper and new cases passed:',mode);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
