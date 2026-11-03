const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP,mode=desktop?'desktop':'browser';
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto('http://127.0.0.1:8765');
  await page.getByText('原生核心就绪').waitFor({timeout:30000});
  const exp=page.getByTitle('展开侧栏',{exact:true});if(await exp.count())await exp.click();
  async function cell(code){
   await page.getByRole('button',{name:'新建笔记',exact:true}).first().click();
   const editor=page.locator('.cm-content').first();await editor.click();await page.keyboard.insertText(code);
   const response=page.waitForResponse(r=>r.url().endsWith('/api/evaluate')&&r.request().method()==='POST');
   await editor.press('Control+Enter');return(await(await response).json());
  }
  const pixels=canvas=>{
   const c=document.createElement('canvas');c.width=canvas.width;c.height=canvas.height;
   const ctx=c.getContext('2d');ctx.drawImage(canvas,0,0);const d=ctx.getImageData(0,0,c.width,c.height).data;
   let h=2166136261,colored=0;for(let i=0;i<d.length;i+=4){h=Math.imul(h^d[i],16777619);if(Math.max(d[i],d[i+1],d[i+2])-Math.min(d[i],d[i+1],d[i+2])>20)colored++;}
   return{hash:h,colored};
  };
  async function check(){
   const host=page.locator('.plot-canvas').last();await host.locator('canvas').waitFor();
   await page.evaluate(()=>document.querySelector('.notebook').style.paddingBottom='1200px');
   await host.scrollIntoViewIfNeeded();await page.waitForTimeout(700);
   assert.ok((await host.locator('canvas').evaluate(pixels)).colored>1000);
   const hover=async()=>{const b=await host.boundingBox();await page.mouse.move(b.x+b.width/2,b.y+b.height/2);};
   await host.locator('..').locator('.plot-tools span').click();await hover();
   const before=await host.locator('canvas').evaluate(pixels);const top=await page.evaluate(()=>scrollY);
   await page.mouse.wheel(0,top>0?-100:100);await page.waitForTimeout(300);
   assert.equal((await host.locator('canvas').evaluate(pixels)).hash,before.hash);
   assert.notEqual(await page.evaluate(()=>scrollY),top);
   await hover();await page.mouse.down();await page.mouse.up();await page.waitForTimeout(200);
   const active=await host.locator('canvas').evaluate(pixels),y=await page.evaluate(()=>scrollY);
   await page.mouse.wheel(0,-100);await page.waitForTimeout(500);
   assert.notEqual((await host.locator('canvas').evaluate(pixels)).hash,active.hash);
   assert.equal(await page.evaluate(()=>scrollY),y);
   await host.locator('..').locator('.plot-tools span').click();await hover();
   const after=await host.locator('canvas').evaluate(pixels);await page.mouse.wheel(0,-100);await page.waitForTimeout(300);
   assert.equal((await host.locator('canvas').evaluate(pixels)).hash,after.hash);
   // Notebook Ctrl+wheel continues to control notebook scale.
   const zoom=await page.evaluate(()=>localStorage.getItem('calix-notebook-zoom')||'100');
   await page.keyboard.down('Control');await page.mouse.wheel(0,-80);await page.keyboard.up('Control');await page.waitForTimeout(300);
   assert.notEqual(await page.evaluate(()=>localStorage.getItem('calix-notebook-zoom')),zoom);
  }
  assert.ok((await cell('Plot3D[Sin[x]*Cos[y],{x,-Pi,Pi},{y,-Pi,Pi}]')).ok);await check();
  await page.locator('.plot-output').last().screenshot({path:'work/ui/surface-wheel-'+mode+'-v0120.png'});
  const field={kind:'plot',plot_type:'field3d',field_kind:'gravity',title:'FieldScene interaction fixture',axes:['x','y','z'],bounds:[[-2,2],[-2,2],[-2,2]],masses:[1,1],times:[0,1],paths:[[[-1,0,0],[-.5,.3,0]],[[1,0,0],[.5,-.3,0]]],colors:['#bd455d','#178790'],labels:['1','2'],color_range:[-4,-.2],softening:.05,engine:'interaction fixture',elapsed_ms:0};
  await page.route('**/api/evaluate',async route=>{
   const code=route.request().postDataJSON().code;
   if(code==='FieldSceneTest[]')return route.fulfill({json:{ok:true,result:field}});
   if(code==='ToElementMesh[]')return route.fulfill({json:{ok:false,error:'PDE module is not installed. Run the Calix installer and select PDE module.'}});
   return route.continue();
  });
  assert.ok((await cell('FieldSceneTest[]')).ok);await check();
  await page.locator('.field-scene').screenshot({path:'work/ui/field-wheel-'+mode+'-v0120.png'});
  assert.equal((await cell('ToElementMesh[]')).ok,false);
  assert.match(await page.getByRole('alert').innerText(),/此功能需要 PDE module/);
  await page.getByRole('button',{name:'偏好设置',exact:true}).click();
  assert.ok(!(await page.getByRole('dialog').innerText()).includes('PDE'));
  await page.getByTitle('关闭设置').click();
  fs.writeFileSync('work/ui-interaction-v0120-'+mode+'-report.json',JSON.stringify({status:'passed',surfaceWheel:true,fieldWheel:true,outsideClickDeactivates:true,notebookCtrlWheel:true,deferredModuleMessage:true},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
