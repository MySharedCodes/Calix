const {chromium}=require('C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');

(async()=>{
 const desktop=!!process.env.CALIX_DESKTOP;
 const browser=desktop?await chromium.connectOverCDP(process.env.CALIX_CDP||'http://127.0.0.1:9232'):await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=desktop?browser.contexts()[0].pages()[0]:await browser.newPage({viewport:{width:1440,height:1000}});
  if(!desktop)await page.goto(process.env.CALIX_TEST_URL||'http://127.0.0.1:5175');
  await page.waitForSelector('.engine-status.ready',{timeout:30000});
  const errors=[],records=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.getByRole('button',{name:'传统计算器面板',exact:true}).click();
  for(const tab of ['基础','函数','求解']){
   await page.getByRole('tab',{name:tab,exact:true}).click();
   assert.equal(await page.locator('.calculator-keys>button').count(),30);
   assert.equal(await page.locator('.calculator-keys').getByRole('button',{name:'计算',exact:true}).count(),1);
   const text=await page.locator('.calculator-keys>button').allTextContents();
   for(const symbol of ['[m]','[s]','[deg]','[',']','{','}','=','==','->','∞'])assert.ok(!text.includes(symbol),symbol);
  }
  for(const [tab,name,expected] of [
   ['函数','行列式','5'],['函数','逆矩阵',null],['函数','平均值','3'],['函数','标准差',null],
   ['求解','转置',null],['求解','特征值',null],['求解','通分',null],['求解','复数化简','x^2 + y^2'],
   ['求解','解析最小值',null],['求解','解析最大值',null],['求解','数值最小值',null],['求解','数值最大值',null],['求解','动画',null],
  ]){
   await page.getByRole('button',{name:'AC',exact:true}).click();
   await page.getByRole('tab',{name:tab,exact:true}).click();
   await page.locator('.calculator-keys').getByRole('button',{name:name==='复数化简'?'复数式':name,exact:true}).click();
   assert.ok((await page.locator('.calculator-cell .cm-content').textContent()).includes('['));
   assert.equal(await page.locator('.symbol-input').count(),0);
   const pending=page.waitForResponse(response=>response.url().endsWith('/api/evaluate'));
   await page.locator('.calculator-keys').getByRole('button',{name:'计算',exact:true}).click();
   const response=await (await pending).json();
   assert.ok(response.ok,JSON.stringify(response));
   if(expected)assert.equal(response.result.text,expected);
   if(name==='动画'){
    assert.equal(response.result.kind,'animation');
    await page.waitForFunction(()=>!!document.querySelector('.animation-output .js-plotly-plot')?.data?.length);
    await page.getByTitle('播放动画',{exact:true}).click();
    await page.waitForFunction(()=>Number(document.querySelector('.animation-controls input[type=range]')?.value)>0);
    await page.getByTitle('暂停动画',{exact:true}).click();
   }
   records.push({name,kind:response.result.kind,text:response.result.text});
   await page.waitForFunction(()=>!document.querySelector('.calculator-cell.running'));
   assert.equal(await page.locator('.error-message').count(),0);
  }
  await page.getByRole('button',{name:'AC',exact:true}).click();
  await page.screenshot({path:`work/ui/calculator-keypad-${desktop?'desktop':'browser'}.png`,fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const collapse=page.getByTitle('收起侧栏',{exact:true});if(await collapse.count())await collapse.click();
  const languages=desktop?['zh']:['zh','en','ja','fr','ru','de','es'];
  for(const language of languages){
   if(language!=='zh'){
    await page.evaluate(value=>localStorage.setItem('calix-language',value),language);
    await page.reload();await page.waitForSelector('.engine-status.ready',{timeout:30000});
    if(await page.locator('.app.sidebar-collapsed').count())await page.locator('.topbar .icon-button').first().click();
    await page.locator('.navigation button').filter({hasText:/Calculator panel|電卓パネル|Calculatrice classique|Панель калькулятора|Rechnerfeld|Panel de calculadora/}).click();
    if(!await page.locator('.app.sidebar-collapsed').count())await page.locator('.topbar .icon-button').first().click();
   }
   for(let index=0;index<3;index++){
    await page.getByRole('tab').nth(index).click();
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),language);
    const overflow=await page.locator('.calculator-keys>button').evaluateAll(buttons=>buttons.filter(button=>{
     const text=button.querySelector('span')?.firstChild;
     if(!text)return false;
     const range=document.createRange();range.selectNode(text);
     const box=button.getBoundingClientRect(),content=range.getBoundingClientRect();
     return content.height>box.height-4||content.width>box.width+1;
    }).map(button=>button.textContent));
    assert.deepEqual(overflow,[],`${language} page ${index}`);
   }
  }
  await page.screenshot({path:`work/ui/calculator-keypad-mobile-${desktop?'desktop':'browser'}.png`,fullPage:true});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(`work/calculator-keypad-${desktop?'desktop':'browser'}-report.json`,JSON.stringify({status:'passed',records,languages,errors},null,2));
  console.log(`Passed ${records.length} calculator commands and ${languages.length} languages`);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
