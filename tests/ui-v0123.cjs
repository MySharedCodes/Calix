const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),zlib=require('node:zlib');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto(process.env.CALIX_TEST_URL||'http://127.0.0.1:8766');
  await page.getByText('原生核心就绪',{exact:true}).waitFor({timeout:30000});
  const errors=[],records=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',async response=>{
   if(!response.url().endsWith('/api/evaluate'))return;
   const data=await response.json();const item={ok:data.ok,error:data.error,elapsed:data.result?.elapsed_ms,execution:data.result?.execution};records.push(item);console.log(JSON.stringify(item));
  });
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  await page.getByRole('spinbutton',{name:'最大 CPU Workers',exact:true}).fill('8');await page.getByTitle('关闭设置',{exact:true}).click();
  await page.getByRole('button',{name:'计算示例',exact:true}).click();
  await page.locator('.library-panel').getByRole('button',{name:'齿轮啮合：接触与扭矩传递',exact:true}).click();
  if(process.env.CALIX_REUSE_GEAR){
   let raw=await page.evaluate(()=>localStorage.getItem('calix-workspace-v1'));if(raw.startsWith('calix-zlib-v1:'))raw=zlib.inflateSync(Buffer.from(raw.slice(14),'base64')).toString();
   const saved=JSON.parse(raw);const document=saved.documents.find(d=>d.id===saved.active);
   records.push(...document.cells.filter(c=>c.mode!=='markdown').map(c=>({ok:!!c.result,error:c.error,elapsed:c.result?.elapsed_ms,execution:c.result?.execution})));
  }else{
   await page.getByRole('button',{name:'全部运行',exact:true}).click();
   await page.waitForFunction(()=>document.querySelector('.statusbar')?.textContent.includes('计算中'),null,{timeout:10000});
   await page.waitForFunction(()=>document.querySelector('.statusbar')?.textContent.includes('就绪'),null,{timeout:600000});
  }
  assert.equal(await page.locator('.error-message').count(),0,await page.locator('.error-message').allTextContents());
  assert.equal(records.length,4);assert.ok(records.every(r=>r.ok));
  assert.equal(records[1].execution.operations.fem_assembly.threads_used,8);
  const solve=records.find(record=>record.execution?.operations?.sparse_solve)?.execution.operations.sparse_solve;assert.equal(solve.path,'oneMKL PARDISO');assert.equal(solve.threads_used,8);assert.equal(solve.calls,24);
  const scenes=page.locator('.scientific-scene');assert.equal(await scenes.count(),3);
  const pixels=canvas=>{const c=document.createElement('canvas');c.width=canvas.width;c.height=canvas.height;const ctx=c.getContext('2d');ctx.drawImage(canvas,0,0);const data=ctx.getImageData(0,0,c.width,c.height).data;let n=0;for(let i=0;i<data.length;i+=4)if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)n++;return n;};
  const coloredPixels=[];
  for(let i=0;i<3;i++){await scenes.nth(i).scrollIntoViewIfNeeded();await page.waitForTimeout(800);const count=await scenes.nth(i).locator('canvas').evaluate(pixels);assert.ok(count>1500);coloredPixels.push(count);await scenes.nth(i).screenshot({path:`work/ui/gear-${i}-${desktop?'desktop':'browser'}-v0123.png`});}
  assert.ok((await scenes.first().innerText()).includes('clipped above scale'));
  await page.setViewportSize({width:390,height:844});const collapse=page.getByTitle('收起侧栏',{exact:true});if(await collapse.count())await collapse.click();
  await scenes.first().scrollIntoViewIfNeeded();await page.waitForTimeout(800);assert.ok(await scenes.first().locator('canvas').evaluate(pixels)>300);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:`work/ui/gear-mobile-${desktop?'desktop':'browser'}-v0123.png`});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/ui-v0123-${desktop?'desktop':'browser'}-report.json`,JSON.stringify({status:'passed',runAllCompleted:true,renderingCheckedAfterRestart:!!process.env.CALIX_REUSE_GEAR,records,coloredPixels,errors},null,2));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
