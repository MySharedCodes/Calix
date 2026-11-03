const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async()=>{
  const desktop=!!process.env.CALIX_DESKTOP;
  const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
  try {
    const context=desktop?browser.contexts()[0]:await browser.newContext({viewport:{width:1440,height:1000}});
    const page=desktop?context.pages().find(p=>/tauri.localhost/.test(p.url())):await context.newPage();
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    page.on('console',m=>{if(m.type()==='error') errors.push(m.text());});
    if(desktop) {
      await page.addInitScript(key=>{if(!sessionStorage.getItem(key)){localStorage.clear();sessionStorage.setItem(key,'1');}},`v0110-reset-${Date.now()}`);
      await page.reload(); await page.setViewportSize({width:1440,height:1000});
    } else await page.goto('http://127.0.0.1:8765');
    await page.getByText('原生核心就绪').waitFor({timeout:30000}).catch(async error=>{console.error(errors,await page.locator('body').innerText());await page.screenshot({path:'work/ui/scientific-v0110-error.png'});throw error;});
    assert.equal(await page.getByRole('button',{name:/CIX Notebook/}).count(),1);
    await page.getByRole('button',{name:'偏好设置',exact:true}).click();
    await page.getByLabel('界面语言',{exact:true}).selectOption('en');
    await page.getByTitle('Close preferences',{exact:true}).click();
    await page.getByRole('button',{name:'New notebook',exact:true}).first().click();
    assert.equal(await page.locator('.document-title input').inputValue(),'Untitled CIX notebook');
    await page.getByRole('button',{name:'Preferences',exact:true}).click();
    await page.getByLabel('Language',{exact:true}).selectOption('zh');
    await page.getByTitle('关闭设置',{exact:true}).click();
    const pixels=async canvas=>canvas.evaluate(canvas=>{
      const copy=document.createElement('canvas');copy.width=canvas.width;copy.height=canvas.height;
      const ctx=copy.getContext('2d');ctx.drawImage(canvas,0,0);
      const data=ctx.getImageData(0,0,copy.width,copy.height).data;
      let colored=0,hash=2166136261;
      for(let i=0;i<data.length;i+=4){if(Math.max(data[i],data[i+1],data[i+2])-Math.min(data[i],data[i+1],data[i+2])>25)colored++;hash=Math.imul(hash^data[i],16777619);hash=Math.imul(hash^data[i+1],16777619);}
      return {colored,hash,width:copy.width,height:copy.height};
    });
    const starter=JSON.parse(fs.readFileSync('frontend/src/starter.json','utf8'));
    const cases=[starter,...JSON.parse(fs.readFileSync('frontend/src/example-notebooks.json','utf8'))];
    const records=[];
    for(const notebook of cases) {
      await page.getByRole('button',{name:'计算示例',exact:true}).click();
      await page.locator('.library-panel').getByRole('button',{name:notebook.title,exact:true}).click();
      await page.getByRole('button',{name:'全部运行',exact:true}).click();
      const count=notebook.cells.filter(c=>c.mode!=='markdown').length;
      await page.waitForFunction(count=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===count||document.querySelector('.notebook .error-message'),count,{timeout:90000});
      assert.equal(await page.locator('.notebook .error-message').count(),0,await page.locator('.notebook').innerText());
      assert.ok(await page.locator('.notebook .output-label').count()>=count);
      if(notebook.title.startsWith('电流线圈')) {
        const scene=page.locator('.scientific-scene');
        assert.match(await scene.innerText(),/线圈 R = 0.1 m/);
        assert.match(await scene.innerText(),/磁场方向/);
        const canvas=scene.locator('canvas'); await canvas.scrollIntoViewIfNeeded(); await page.waitForTimeout(500);
        const state=await pixels(canvas);assert.ok(state.colored>1500,JSON.stringify(state));
        await scene.screenshot({path:'work/ui/coil-scene-v0110.png'});
        const box=await canvas.boundingBox();
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+100,box.y+box.height/2+35,{steps:10});await page.mouse.up();
        await page.waitForTimeout(300);assert.notEqual((await pixels(canvas)).hash,state.hash);
        await page.setViewportSize({width:390,height:844});await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(350);
        assert.ok((await pixels(canvas)).colored>500);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.screenshot({path:'work/ui/coil-scene-mobile-v0110.png'});
        await page.setViewportSize({width:1440,height:1000});
      }
      if(notebook.title.startsWith('类氢')) {
        assert.equal(await page.locator('.probability-cloud').count(),6);
        assert.equal(await page.locator('.notebook .plot-output:not(.probability-cloud)').count(),0);
        const hashes=[];
        for(let i=0;i<6;i++) {
          const cloud=page.locator('.probability-cloud').nth(i),canvas=cloud.locator('canvas');
          await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(350);
          const state=await pixels(canvas);assert.ok(state.colored>800,JSON.stringify({i,...state}));hashes.push(state.hash);
          await cloud.screenshot({path:`work/ui/cloud-${i+1}-v0110.png`});
        }
        assert.equal(new Set(hashes).size,6);
        const overlay=await page.addStyleTag({content:'.toolbar,.topbar,.statusbar{visibility:hidden!important}'});
        await page.locator('.volume-grid').screenshot({path:'work/ui/hydrogen-clouds-v0110.png'});
        await overlay.evaluate(element=>element.remove());
        const cloud=page.locator('.probability-cloud').last(),canvas=cloud.locator('canvas');
        await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(300);const before=await pixels(canvas);
        await cloud.getByRole('slider').focus();await page.keyboard.press('Home');await page.waitForTimeout(350);
        assert.notEqual((await pixels(canvas)).hash,before.hash);
        const box=await canvas.boundingBox();await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.mouse.move(box.x+box.width/2+70,box.y+box.height/2+30,{steps:10});await page.mouse.up();
        await page.waitForTimeout(300);assert.notEqual((await pixels(canvas)).hash,before.hash);
        await cloud.getByRole('slider').press('End');
        await page.setViewportSize({width:390,height:844});await canvas.scrollIntoViewIfNeeded();await page.waitForTimeout(350);
        assert.ok((await pixels(canvas)).colored>500);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.screenshot({path:'work/ui/hydrogen-cloud-mobile-v0110.png'});
        await page.setViewportSize({width:1440,height:1000});
      }
      records.push({title:notebook.title,cells:count});
    }
    await page.waitForTimeout(800);
    assert.equal(await page.getByText(/自动保存失败|工作空间存储已满/).count(),0);
    await page.reload();await page.getByText('原生核心就绪').waitFor();
    assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),4);
    assert.equal(await page.locator('.probability-cloud').count(),6);
    assert.ok(await page.locator('.output-label').count()>10);
    const restored=page.locator('.probability-cloud canvas').last();await restored.scrollIntoViewIfNeeded();await page.waitForTimeout(500);
    assert.ok((await pixels(restored)).colored>800);
    assert.deepEqual(errors,[]);
    fs.writeFileSync('work/ui/scientific-v0110-report.json',JSON.stringify({status:'passed',desktop,naming:true,labels:true,sixVolumeClouds:true,coilGeometryAndField:true,rotation:true,opacity:true,mobile:true,restoredOutputs:true,records,errors},null,2));
    console.log('0.1.10 scientific UI passed:',records);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
