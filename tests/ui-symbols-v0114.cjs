const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),ts=require('typescript');
(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP('http://127.0.0.1:9223'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages().find(p=>/tauri.localhost/.test(p.url())):await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(desktop){await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});await page.reload();await page.setViewportSize({width:1440,height:1000});}else await page.goto('http://127.0.0.1:8765');
  await page.getByText('原生核心就绪').waitFor({timeout:30000});
  await page.getByRole('button',{name:'新建笔记',exact:true}).first().click();
  const editor=page.locator('.cm-content').first();
  const setCode=async code=>{await editor.click();await page.keyboard.press('Control+A');await page.keyboard.insertText(code);};
  const shortcut=async alias=>{await editor.press('Escape');const input=page.getByRole('textbox',{name:'特殊符号缩写',exact:true});await input.fill(alias);await input.press('Escape');};
  const run=async()=>{
   const response=page.waitForResponse(r=>r.url().endsWith('/api/evaluate')&&r.request().method()==='POST',{timeout:30000});
   await editor.press('Control+Enter');const data=await(await response).json();assert.ok(data.ok,JSON.stringify(data));return data.result;
  };
  await shortcut('a');assert.equal(await editor.innerText(),'α');
  await page.keyboard.insertText('=3;α^2');assert.equal((await run()).text,'9');
  await setCode('');await shortcut('intt');
  const mf=page.locator('math-field');await mf.waitFor();
  assert.match(await mf.evaluate(el=>el.value),/\\int/);
  assert.match(await mf.evaluate(el=>el.value),/placeholder/);
  await page.keyboard.type('x^2');await page.keyboard.press('ArrowRight');await page.keyboard.press('Tab');await page.keyboard.type('x');
  const entered=await mf.evaluate(el=>el.value);assert.ok(!entered.includes('placeholder'),entered);
  await page.getByRole('button',{name:'插入',exact:true}).click();
  assert.match(await editor.innerText(),/Integrate/,JSON.stringify({entered,error:await page.locator('.error-message').allTextContents()}));assert.match((await run()).text,/x\^3/);
  await setCode('');await shortcut('dint');assert.match(await mf.evaluate(el=>el.value),/\\int_/);
  await mf.evaluate(el=>{el.value=String.raw`\int_0^1 x^2\,\mathrm{d}x`;});
  await page.getByRole('button',{name:'插入',exact:true}).click();assert.equal((await run()).text,'1/3');
  await setCode('');await shortcut('sub');await mf.evaluate(el=>{el.value=String.raw`x_{12}`;});await page.getByRole('button',{name:'插入',exact:true}).click();
  await page.keyboard.insertText('=7;x₁₂+1');assert.equal((await run()).text,'8');
  await setCode('');await shortcut('sum');await mf.evaluate(el=>{el.value=String.raw`\sum_{k=1}^{10} k^2`;});await page.getByRole('button',{name:'插入',exact:true}).click();assert.equal((await run()).text,'385');
  await editor.press('Escape');const input=page.getByRole('textbox',{name:'特殊符号缩写',exact:true});await input.fill('unknown');await input.press('Escape');assert.ok(await page.getByText('未找到特殊符号: unknown',{exact:true}).count());await input.fill('inf');await input.press('Escape');assert.match(await editor.innerText(),/∞/);
  await setCode('UnitConvert[1[kg/(m*s)],"kg/(m*s)"]');const unit=await run();assert.match(unit.text,/m · s/);assert.match(unit.latex,/\\cdot/);assert.ok(!unit.latex.includes('\\frac'));
  await page.screenshot({path:`work/ui/symbols-${desktop?'desktop':'browser'}-v0114.png`});
  const context={exports:{}};vm.runInNewContext(ts.transpileModule(fs.readFileSync('frontend/src/locales.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText,context);
  const locales=context.exports.extraTranslations;
  for(const locale of ['ja','fr','ru','de','es']){
   await page.locator('.sidebar-bottom>button').click();const dialog=page.getByRole('dialog');assert.equal(await dialog.locator('select option').count(),7);await dialog.locator('select').selectOption(locale);
   assert.equal(await page.evaluate(()=>document.documentElement.lang),locale);assert.equal(await dialog.getByRole('combobox',{name:locales[locale]['界面语言'],exact:true}).count(),1);
   await dialog.locator('.panel-heading .icon-button').click();
   await page.getByRole('button',{name:locales[locale]['计算示例'],exact:true}).click();
   const titles=await page.locator('.library-panel .example-group').first().locator('button span').allTextContents();
   assert.equal(titles.length,12);assert.deepEqual(titles,[...titles].sort((a,b)=>a.localeCompare(b,locale,{numeric:true,sensitivity:'base'})));
   assert.ok(titles.includes(locales[locale]['空气阻力下的二维抛体运动']));
   await page.getByTitle(locales[locale]['关闭示例'],{exact:true}).click();
   await page.setViewportSize({width:390,height:844});await page.waitForTimeout(100);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.screenshot({path:`work/ui/language-${locale}-${desktop?'desktop':'browser'}-v0114.png`});await page.setViewportSize({width:1440,height:1000});
  }
  await page.reload();await page.getByText(locales.es['原生核心就绪'],{exact:true}).waitFor();assert.equal(await page.evaluate(()=>document.documentElement.lang),'es');
  await page.locator('.sidebar-bottom>button').click();await page.getByRole('dialog').locator('select').selectOption('zh');await page.getByTitle('关闭设置',{exact:true}).click();
  await setCode('');await shortcut('intt');await page.screenshot({path:`work/ui/integral-template-${desktop?'desktop':'browser'}-v0114.png`});
  assert.deepEqual(errors,[]);
  const report={status:'passed',desktop,greekShortcut:true,integralSlotsTypedWithKeyboard:true,definiteIntegral:true,subscripts:true,summation:true,unknownAliasRecovery:true,unitDots:true,languages:Object.keys(locales),localePersistence:true,mobile:true,errors};
  fs.writeFileSync(`work/ui/symbols-${desktop?'desktop':'browser'}-v0114-report.json`,JSON.stringify(report,null,2));console.log(report);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
