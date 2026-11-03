const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try {
    const page=await browser.newPage();
    await page.addInitScript(()=>{
      if(!sessionStorage.getItem('autosave-initialized')){
        localStorage.clear();
        localStorage.setItem('calix-notebook-v1',JSON.stringify({format:'calix-notebook',version:1,title:'Legacy notebook',cells:[{id:'legacy',mode:'source',code:'Sqrt[9]'}]}));
        sessionStorage.setItem('autosave-initialized','1'); window.failWorkspaceSave=true;
      }
      const original=Storage.prototype.setItem;
      Storage.prototype.setItem=function(key,value){
        if(key==='calix-workspace-v1' && window.failWorkspaceSave) throw new DOMException('Simulated storage quota','QuotaExceededError');
        return original.call(this,key,value);
      };
    });
    await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:8765');
    await page.getByText('原生核心就绪').waitFor();
    await page.getByText('工作空间存储已满，请将笔记保存到文件',{exact:true}).waitFor();
    assert.equal(await page.getByLabel('Notebook 名称').inputValue(),'Legacy notebook');
    assert.equal(await page.locator('.cm-content').innerText(),'Sqrt[9]');
    assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('calix-notebook-v1')).title),'Legacy notebook');
    await page.evaluate(()=>window.failWorkspaceSave=false);
    await page.getByLabel('Notebook 名称').fill('Recovered notebook');
    await page.waitForTimeout(600);
    assert.equal(await page.evaluate(()=>localStorage.getItem('calix-notebook-v1')),null);
    assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('calix-workspace-v1')).documents[0].title),'Recovered notebook');
    await page.reload(); await page.getByText('原生核心就绪').waitFor();
    assert.equal(await page.getByLabel('Notebook 名称').inputValue(),'Recovered notebook');
    assert.equal(await page.locator('.cm-content').innerText(),'Sqrt[9]');
    fs.writeFileSync('work/ui/autosave-v018-report.json',JSON.stringify({status:'passed',legacyMigration:true,quotaFailureRetainsBackup:true,retryPersistsWorkspace:true,reloadRetainsInput:true},null,2));
    console.log('Autosave migration, quota recovery and reload passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
