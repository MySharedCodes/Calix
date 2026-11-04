const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  await page.goto('file:///D:/Calix/docs/branding/Calix-logos-30/index.html');
  assert.equal(await page.locator('.concept').count(), 30);
  await page.locator('.concept').nth(29).click();
  assert.match(await page.locator('#selected-name').innerText(), /^30/);
  for (const mode of ['dark', 'mono', 'small']) { await page.locator('#' + mode).check(); assert.ok(await page.locator('#grid').evaluate((el, mode) => el.classList.contains(mode), mode)); await page.locator('#' + mode).uncheck(); }
  await page.screenshot({ path: 'work/ui/logo-contact-sheet-0.1.3.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  await page.screenshot({ path: 'work/ui/logo-gallery-mobile.png' });
  await browser.close(); console.log('Logo gallery passed: 30 concepts, selection, modes, desktop/mobile.');
})().catch(error => { console.error(error); process.exit(1); });
