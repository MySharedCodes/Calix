const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto(process.env.CALIX_TEST_URL);
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  const errors=[],records=[];let session;
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',r=>{if(r.url().endsWith('/api/evaluate'))session=r.postDataJSON().session;});
  page.on('response',async response=>{
   if(!response.url().endsWith('/api/evaluate'))return;
   const data=await response.json();const item={ok:data.ok,error:data.error,elapsed:data.result?.elapsed_ms,execution:data.result?.execution};records.push(item);console.log(JSON.stringify(item));
  });
  await page.getByRole('button',{name:'计算示例',exact:true}).click();
  await page.locator('.library-panel').getByRole('button',{name:'齿轮啮合：接触与扭矩传递',exact:true}).click();
  await page.getByRole('button',{name:'全部运行',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.statusbar')?.textContent.includes('计算中'),null,{timeout:10000});
  await page.waitForFunction(()=>document.querySelector('.statusbar')?.textContent.includes('就绪'),null,{timeout:600000});
  assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
  assert.equal(records.length,4);assert.ok(records.every(r=>r.ok));
  assert.equal(records[1].execution.operations.fem_assembly.threads_used,8);
  const scenes=page.locator('.scientific-scene');assert.equal(await scenes.count(),3);
  const pixels=canvas=>{const c=document.createElement('canvas');c.width=canvas.width;c.height=canvas.height;const ctx=c.getContext('2d');ctx.drawImage(canvas,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<data.length;i+=4)if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)n++;return n;};
  for(let i=0;i<3;i++){await scenes.nth(i).scrollIntoViewIfNeeded();await page.waitForTimeout(800);assert.ok(await scenes.nth(i).locator('canvas').evaluate(pixels)>1500);await scenes.nth(i).screenshot({path:`work/ui/gear-${i}-${desktop?'desktop':'browser'}-v0122.png`});}
  await page.setViewportSize({width:390,height:844});const collapse=page.getByTitle('收起侧栏',{exact:true});if(await collapse.count())await collapse.click();
  await scenes.last().scrollIntoViewIfNeeded();await page.waitForTimeout(800);assert.ok(await scenes.last().locator('canvas').evaluate(pixels)>300);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:`work/ui/gear-mobile-${desktop?'desktop':'browser'}-v0122.png`});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/ui-v0122-${desktop?'desktop':'browser'}-report.json`,JSON.stringify({status:'passed',records,errors},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
