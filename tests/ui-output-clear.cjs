const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const out=path.resolve('work/ui-output-clear');
fs.mkdirSync(out,{recursive:true});
const expression={kind:'expression',text:'7',latex:'7',engine:'test',elapsed_ms:0};
const file={format:'calix-notebook',version:1,title:'Clear outputs test',cells:[
 {id:'text',mode:'markdown',code:'# 保留标题\n\n正文与 $x^2$。'},
 {id:'definition',mode:'source',code:'a=7;a',result:expression,executed:1},
 {id:'dependent',mode:'source',code:'a^2',result:{kind:'group',items:[expression,{kind:'plot',plot_type:'curve',title:'test',axes:['x','y'],traces:[{name:'x',x:[0,1],y:[0,1]}],engine:'test',elapsed_ms:0}],engine:'test',elapsed_ms:0},executed:2},
 {id:'error',mode:'source',code:'Sqrt[9]',error:'old calculation error',executed:3}
]};
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.CALIX_BROWSER === 'chromium' ? {} : {channel:'msedge'})});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:960},acceptDownloads:true});
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:5187');
  await page.locator('.engine-status.ready').waitFor({timeout:30000});
  await page.locator('input[type=file]').setInputFiles({name:'clear.cixnb',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(file))});
  await page.waitForFunction(()=>document.querySelector('input[aria-label="Notebook 名称"]')?.value==='Clear outputs test');
  const clear=page.getByRole('button',{name:'清空全部输出',exact:true});
  assert.equal(await page.locator('.output').count(),2);
  assert.equal(await page.locator('.error-message').count(),1);
  await page.keyboard.press('Escape');
  await clear.click();
  assert.equal(await page.locator('.output,.error-message').count(),0);
  assert.equal(await page.locator('.cell').count(),4);
  assert.equal(await clear.isDisabled(),true);
  assert.match(await page.locator('.markdown-content').innerText(),/保留标题/);
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'保存',exact:true}).last().click();
  const download=await downloadPromise, savedFile=path.join(out,'empty.cixnb');
  await download.saveAs(savedFile);
  const saved=JSON.parse(fs.readFileSync(savedFile,'utf8'));
  assert.deepEqual(saved.cells.map(cell=>cell.code),file.cells.map(cell=>cell.code));
  for(const cell of saved.cells) for(const field of ['result','error','stale','executed']) assert.equal(field in cell,false,field);
  await page.route('**/api/evaluate',async route=>{await new Promise(resolve=>setTimeout(resolve,200));await route.continue();});
  await page.locator('.cell').nth(1).getByRole('button',{name:'运行单元 2',exact:true}).click();
  await page.locator('.cell.running').waitFor();
  assert.equal(await clear.isDisabled(),true);
  await page.waitForFunction(()=>!document.querySelector('.cell.running'));
  assert.match(await page.locator('.output').innerText(),/7/);
  await clear.click();
  await page.locator('.cell').nth(2).getByRole('button',{name:'运行单元 3',exact:true}).click();
  await page.locator('.output').waitFor();
  assert.match(await page.locator('.output').innerText(),/49/);
  await clear.click();
  await page.waitForTimeout(500);
  await page.reload();
  await page.locator('.engine-status.ready').waitFor();
  assert.equal(await page.locator('.output,.error-message').count(),0);
  assert.equal(await page.locator('.cell').count(),4);
  assert.deepEqual(errors,[]);
  console.log('Clear outputs: expressions, groups, plots, errors, save/reopen, busy guard and retained variables passed');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
