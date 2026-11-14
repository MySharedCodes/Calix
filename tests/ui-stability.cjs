const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const output = path.resolve('work/stability-ui');
fs.mkdirSync(output, {recursive:true});

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CALIX_BROWSER === 'chromium' ? {} : {channel:'msedge'})});
  try {
    const page = await browser.newPage({viewport:{width:1360,height:960}});
    const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.addInitScript(() => {
      if (sessionStorage.getItem('stability-seeded')) return;
      localStorage.setItem('calix-language','zh');
      localStorage.setItem('calix-notebook-v1', JSON.stringify({format:'calix-notebook',version:1,title:'Recovery test',cells:[{mode:'source',code:'1+1'},{mode:'source',code:'2+2'}]}));
      sessionStorage.setItem('stability-seeded','1');
    });
    await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:5173');
    await page.waitForFunction(()=>localStorage.getItem('calix-workspace-v1'));
    await page.locator('.engine-status.ready').waitFor({timeout:30000});
    assert.equal(await page.locator('.cell').count(),2);
    await page.locator('.cell').last().getByRole('button',{name:'删除单元',exact:true}).click();
    assert.equal(await page.locator('.cell').count(),1);
    await page.getByRole('button',{name:'撤销单元操作',exact:true}).click();
    assert.equal(await page.locator('.cell').count(),2);
    assert.equal(await page.locator('.cm-content').last().innerText(),'2+2');
    await page.getByRole('button',{name:'重做单元操作',exact:true}).click();
    assert.equal(await page.locator('.cell').count(),1);
    await page.getByRole('button',{name:'撤销单元操作',exact:true}).click();
    await page.locator('.cell').last().getByRole('button',{name:'上移单元',exact:true}).click();
    assert.equal(await page.locator('.cm-content').first().innerText(),'2+2');
    await page.getByRole('button',{name:'撤销单元操作',exact:true}).click();
    assert.equal(await page.locator('.cm-content').first().innerText(),'1+1');
    await page.waitForFunction(()=>localStorage.getItem('calix-workspace-backup-v1'));
    await page.getByRole('button',{name:'恢复历史',exact:true}).click();
    const dialog=page.getByRole('dialog',{name:'恢复历史'});
    await dialog.getByRole('button',{name:/浏览器备份/}).click();
    await dialog.locator('.recovery-notebooks button').first().waitFor();
    await dialog.screenshot({path:path.join(output,'recovery.png')});
    await dialog.locator('.recovery-notebooks button').first().click();
    assert.match(await page.getByRole('textbox',{name:'Notebook 名称'}).inputValue(),/恢复副本/);
    assert.equal(await page.locator('.notebook-row').count(),2);
    // Storage damage must fall back to the preceding checkpoint instead of the starter.
    await page.evaluate(()=>localStorage.setItem('calix-workspace-v1','damaged-json'));
    await page.reload();
    await page.locator('.engine-status.ready').waitFor();
    assert.match(await page.getByRole('textbox',{name:'Notebook 名称'}).inputValue(),/Recovery test/);
    await page.evaluate(()=>localStorage.setItem('calix-workspace-v1',JSON.stringify({version:1,documents:[{id:'broken',format:'calix-notebook',version:1,title:'Broken',cells:[{mode:'source',code:null}]}]})));
    await page.reload();
    await page.locator('.engine-status.ready').waitFor();
    assert.match(await page.getByRole('textbox',{name:'Notebook 名称'}).inputValue(),/Recovery test/);
    // Quota failure must report the problem and retain the last good backup.
    await page.evaluate(()=>{
      window.originalSetItem=Storage.prototype.setItem;
      Storage.prototype.setItem=function(key,value){if(key==='calix-workspace-v1')throw new DOMException('Quota exceeded','QuotaExceededError');return window.originalSetItem.call(this,key,value);};
    });
    await page.getByRole('textbox',{name:'Notebook 名称'}).fill('Quota test');
    await page.getByText('工作空间存储已满，请将笔记保存到文件',{exact:true}).waitFor();
    assert.ok(await page.evaluate(()=>localStorage.getItem('calix-workspace-backup-v1')));
    await page.evaluate(()=>Storage.prototype.setItem=window.originalSetItem);
    const editor=page.locator('.cm-content').first();
    await editor.click();await page.keyboard.press('Control+a');await page.keyboard.insertText('UnknownSolver[x]');
    await page.keyboard.press('Control+Enter');
    await page.getByText('含未求值函数: UnknownSolver',{exact:true}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('Stability UI: structural undo/redo, recovery copy, corrupted storage, quota failure and symbolic-result status passed');
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
