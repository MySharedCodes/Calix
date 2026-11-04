const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9223') : await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = desktop ? browser.contexts()[0].pages().find(p => /tauri.localhost/.test(p.url())) : await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    if (desktop) {
      await page.addInitScript(key => { if (!sessionStorage.getItem(key)) { localStorage.clear(); sessionStorage.setItem(key, '1'); } }, `v019-reset-${Date.now()}`);
      await page.reload(); await page.setViewportSize({ width: 1440, height: 1000 });
    } else await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:8765');
    await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
    assert.equal(await page.getByRole('button', { name: '单位运算器', exact: true }).count(), 0);
    await page.getByRole('button', { name: '新建笔记', exact: true }).first().click();
    const editor = page.locator('.cm-content');
    const enter = async code => { await editor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText(code); };
    await enter('1['); await page.keyboard.type('micro', {delay:80});
    await page.locator('.cm-tooltip-autocomplete').waitFor();
    assert.match(await page.locator('.cm-tooltip-autocomplete').innerText(), /micrometer/);
    await page.screenshot({ path:'work/ui/unit-completion-v019.png' });
    await page.keyboard.press('Escape');
    await enter('v=72;Column[{[kg*m/s^2],2[牛顿]*3[米],1[kg/(m*s)],UnitConvert[v[km/h],"m/s"],UnitConvert[1["µm"],"nm"]}]');
    await page.keyboard.press('Control+Enter');
    await page.locator('.output').waitFor();
    assert.deepEqual(await page.locator('.formula annotation').allTextContents(), ['1\\;[\\mathrm{N}]','6\\;[\\mathrm{J}]','1\\;[\\mathrm{Pa}\\,\\mathrm{s}]','20\\;[\\frac{\\mathrm{m}}{\\mathrm{s}}]','1000\\;[\\mathrm{nm}]']);
    assert.equal(await page.locator('.error-message').count(),0);
    await page.screenshot({path:'work/ui/integrated-units-v019.png'});

    const canvasState = async canvas => canvas.evaluate(canvas => {
      const copy=document.createElement('canvas'); copy.width=canvas.width; copy.height=canvas.height;
      const context=copy.getContext('2d'); context.drawImage(canvas,0,0);
      const pixels=context.getImageData(0,0,copy.width,copy.height).data;
      let colored=0, hash=2166136261;
      for(let i=0;i<pixels.length;i+=4) {
        if(Math.max(pixels[i],pixels[i+1],pixels[i+2])-Math.min(pixels[i],pixels[i+1],pixels[i+2])>25) colored++;
        hash=Math.imul(hash ^ pixels[i],16777619); hash=Math.imul(hash ^ pixels[i+1],16777619);
      }
      return {colored,hash};
    });
    const starter=JSON.parse(fs.readFileSync('frontend/src/starter.json','utf8'));
    const cases=[starter,...JSON.parse(fs.readFileSync('frontend/src/example-notebooks.json','utf8'))];
    const records=[];
    for(const notebook of cases) {
      await page.getByRole('button',{name:'计算示例',exact:true}).click();
      await page.locator('.library-panel').getByRole('button',{name:notebook.title,exact:true}).click();
      await page.getByRole('button',{name:'全部运行',exact:true}).click();
      const count=notebook.cells.filter(cell=>cell.mode==='source').length;
      await page.waitForFunction(count=>document.querySelectorAll('.notebook .cell>.cell-body>.output').length===count||document.querySelector('.notebook .error-message'),count,{timeout:60000});
      assert.equal(await page.locator('.notebook .error-message').count(),0,await page.locator('.notebook').innerText());
      if(notebook.title.startsWith('电流线圈')||notebook.title.startsWith('类氢')) {
        const id=notebook.title.startsWith('电流线圈')?'coil-particle':'hydrogen-ion';
        const canvas=page.locator('.notebook canvas').last();
        await canvas.scrollIntoViewIfNeeded(); await page.waitForTimeout(500);
        const before=await canvasState(canvas); assert.ok(before.colored>1000);
        await page.screenshot({path:`work/ui/${id}-v019.png`});
        const box=await canvas.boundingBox();
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2); await page.mouse.down();
        await page.mouse.move(box.x+box.width/2+80,box.y+box.height/2+25,{steps:8}); await page.mouse.up();
        await page.waitForTimeout(300); assert.notEqual((await canvasState(canvas)).hash,before.hash);
        await page.setViewportSize({width:390,height:844});
        await canvas.scrollIntoViewIfNeeded(); await page.waitForTimeout(350);
        assert.ok((await canvasState(canvas)).colored>500);
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        await page.screenshot({path:`work/ui/${id}-mobile-v019.png`});
        await page.setViewportSize({width:1440,height:1000});
      }
      records.push({title:notebook.title,cells:count});
    }
    await page.waitForTimeout(700);
    assert.equal(await page.getByText(/自动保存失败|工作空间存储已满/).count(),0);
    await page.reload(); await page.getByText('原生核心就绪').waitFor();
    assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(),4);
    assert.equal(await page.locator('.notebook-row').count(),12);
    const restored=page.locator('.notebook canvas').last(); await restored.scrollIntoViewIfNeeded(); await page.waitForTimeout(400);
    assert.ok((await canvasState(restored)).colored>1000);
    await page.getByRole('button',{name:'偏好设置',exact:true}).click();
    await page.getByLabel('界面语言',{exact:true}).selectOption('en');
    await page.getByTitle('Close preferences',{exact:true}).click();
    assert.equal(await page.getByRole('button',{name:'Unit calculator',exact:true}).count(),0);
    await page.getByRole('button',{name:'Examples',exact:true}).click();
    assert.equal(await page.locator('.library-panel').getByRole('button',{name:'Charged particle near a current loop',exact:true}).count(),1);
    assert.equal(await page.locator('.library-panel').getByRole('button',{name:'Hydrogen-like ion: analytical Schrodinger solution',exact:true}).count(),1);
    assert.deepEqual(errors,[]);
    fs.writeFileSync('work/ui/units-physics-v019-report.json',JSON.stringify({status:'passed',desktop,integratedUnits:true,completion:true,noUnitSidebar:true,rendered3d:true,rotation:true,mobile:true,restoredOutputs:true,records,errors},null,2));
    console.log('0.1.9 units and physical notebooks passed:',records);
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
