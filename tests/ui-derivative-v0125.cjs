const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],calls=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/api/evaluate'))calls.push(r.postDataJSON().code);});
  await page.addInitScript(()=>localStorage.setItem('calix-workspace-v1',JSON.stringify({version:1,active:'derivative',documents:[{format:'calix-notebook',version:1,id:'derivative',title:'Derivative',path:null,updated:1,cells:[{id:'input',mode:'source',code:''}]}]})));
  await page.goto(process.env.CALIX_TEST_URL||'http://127.0.0.1:8766');await page.waitForSelector('.engine-status.ready');
  await page.getByRole('button',{name:'传统计算器面板',exact:true}).click();await page.getByRole('tab',{name:'求解',exact:true}).click();
  const button=page.locator('.calculator-keys').getByRole('button',{name:'∂ₓ',exact:true});
  assert.ok((await button.getAttribute('title')).includes('Esc-pdiff-Esc'));await button.click();
  const inline=page.locator('.calculator-cell .cm-content math-field');await inline.waitFor();
  assert.ok((await inline.evaluate(f=>f.value)).includes('\\partial'));
  assert.equal(await page.locator('.formula-composer').count(),0);
  await page.waitForFunction(()=>document.activeElement?.matches('.calculator-cell .inline-formula'));
  await page.keyboard.type('x');await page.keyboard.press('Tab');await page.keyboard.type('x^2+y^2');await page.keyboard.press('Control+Enter');
  await page.waitForFunction(()=>document.querySelector('.history-item span')?.textContent==='2*x',null,{timeout:15000});
  await page.screenshot({path:'work/ui/derivative-calculator-v0125.png'});
  await inline.evaluate(f=>{f.value='\\partial_{x}^{2}\\left(x^3\\right)';f.dispatchEvent(new Event('input',{bubbles:true}));});
  await page.locator('.calculator-keys .equals').click();
  await page.waitForFunction(()=>document.querySelector('.history-item span')?.textContent==='6*x',null,{timeout:15000});
  await page.getByRole('button',{name:/^CIX Notebook/}).click();
  await page.locator('.cell .cm-content').first().click();await page.keyboard.press('Escape');
  await page.getByRole('textbox',{name:'特殊符号缩写',exact:true}).fill('pdiff');await page.keyboard.press('Escape');
  const notebook=page.locator('.cell .inline-formula').first();await notebook.waitFor();
  await page.waitForFunction(()=>document.activeElement?.matches('.cell .inline-formula'));
  await page.keyboard.type('y');await page.keyboard.press('Tab');await page.keyboard.type('x*y+y^2');await page.keyboard.press('Control+Enter');
  await page.waitForFunction(()=>document.querySelector('.cell .result-meta')?.textContent.includes('SymPy'),null,{timeout:15000});
  assert.ok(calls.at(-1).startsWith('D[')&&calls.at(-1).endsWith(',y]'));
  assert.equal(await page.locator('.error-message').count(),0);assert.deepEqual(errors,[]);
  fs.writeFileSync('work/ui-derivative-v0125-report.json',JSON.stringify({status:'passed',subscriptPartialButton:true,inlineEditableDerivative:true,realKeyboard:true,secondDerivative:true,notebookShortcut:true,calls,errors},null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
