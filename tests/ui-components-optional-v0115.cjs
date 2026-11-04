const {chromium}=require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert=require('node:assert/strict'),fs=require('fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  await page.addInitScript(()=>{localStorage.setItem('calix-language','es');localStorage.setItem('calix-theme','ocean')});
  await page.route('**/api/health',async route=>{const response=await route.fetch();const data=await response.json();await route.fulfill({response,json:{...data,components:{pde:false,languages:false,themes:false}}})});
  await page.goto('http://127.0.0.1:8765');
  await page.getByText('Native engine ready',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.lang),'en');
  assert.equal(await page.evaluate(()=>document.documentElement.dataset.theme),'white');
  await page.getByRole('button',{name:'Preferences',exact:true}).click();
  assert.equal(await page.getByRole('dialog').locator('select option').count(),2);
  assert.equal(await page.locator('.theme-picker button').count(),1);
  await page.getByTitle('Close preferences',{exact:true}).click();
  await page.getByRole('button',{name:'Examples',exact:true}).click();
  assert.equal(await page.locator('.library-panel .example-group').first().locator('button').count(),12);
  assert.equal(await page.getByRole('button',{name:'Analytical PDE solutions',exact:true}).count(),0);
  fs.writeFileSync('work/ui-optional-components-v0115-report.json',JSON.stringify({status:'passed',coreLanguages:2,coreThemes:1,pdeExamplesHidden:true,missingLanguageFallback:'en',missingThemeFallback:'white'},null,2));
  console.log('Optional component UI fallback passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
