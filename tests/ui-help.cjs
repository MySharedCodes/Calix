const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const output = path.resolve('work/docs-ui');
fs.mkdirSync(output, { recursive: true });
fs.mkdirSync('docs/images', { recursive: true });

(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9227') : await chromium.launch({ headless: true, ...(process.env.CALIX_BROWSER === 'chromium' ? {} : { channel: 'msedge' }) });
  try {
    const context = desktop ? browser.contexts()[0] : await browser.newContext({ viewport: { width: 1400, height: 1040 } });
    const page = desktop ? context.pages().find(item => /tauri\.localhost/.test(item.url())) : await context.newPage();
    assert.ok(page, 'Calix WebView must be open');
    await page.setViewportSize({ width: 1400, height: 1040 });
    // Desktop runs require a dedicated WEBVIEW2_USER_DATA_FOLDER on CDP port 9227.
    if (desktop) await page.evaluate(() => sessionStorage.removeItem('docs-demo'));
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    await page.addInitScript(() => {
      if (sessionStorage.getItem('docs-demo')) return;
      localStorage.removeItem('calix-workspace-v1');
      localStorage.setItem('calix-language', 'zh');
      localStorage.setItem('calix-notebook-v1', JSON.stringify({
        format: 'calix-notebook', version: 1, title: 'Units, exact answers and a curve',
        cells: [
          { mode: 'markdown', code: '# 有量纲的计算与解析积分\n单位参与运算，精确表达式保持精确形式。$f(t)=e^{-t}\\cos(2t)$。' },
          { mode: 'source', code: 'UnitConvert[72[km/h], "m/s"]\nFactor[x^4 - 1]\nIntegrate[x^4 Exp[-3 x^2], {x, -Infinity, Infinity}]' },
          { mode: 'source', code: 'Plot[Exp[-t] Cos[2 t], {t,0,10}]' },
        ],
      }));
      sessionStorage.setItem('docs-demo', '1');
    });
    if (desktop) await page.reload();
    else await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:5173');
    await page.locator('.engine-status.ready').waitFor({ timeout: 30000 });
    assert.equal(await page.getByRole('textbox', { name: 'Notebook 名称' }).inputValue(), 'Units, exact answers and a curve');
    await page.locator('.cm-content').first().click();
    const before = await page.locator('.cm-content').allTextContents();
    await page.keyboard.press('F1');
    const dialog = page.getByRole('dialog', { name: '帮助 · Calix' });
    await dialog.waitFor();
    await page.getByRole('heading', { name: '快速上手 / Get Started' }).waitFor();
    await page.keyboard.press('F1');
    assert.equal(await dialog.count(), 1);
    const search = page.getByRole('textbox', { name: '搜索帮助' });
    await search.fill('PARDISO');
    assert.ok(await dialog.locator('.help-topics button').count() >= 1);
    await search.fill('no-such-help-topic-xyz');
    await page.getByText('没有匹配的文档').waitFor();
    await search.fill('');
    await dialog.getByRole('button', { name: '使用帮助', exact: true }).click();
    await page.getByRole('heading', { name: 'Calix 使用帮助' }).waitFor();
    await page.keyboard.press('Control+s');
    assert.equal(await dialog.isVisible(), true);
    await dialog.screenshot({ path: path.join(output, 'help-desktop.png') });
    // Native modal focus stays in the help window.
    await dialog.getByRole('button', { name: '关闭帮助' }).focus();
    for (let index = 0; index < 25; index++) {
      await page.keyboard.press('Tab');
      assert.ok(await page.evaluate(() => document.querySelector('dialog').contains(document.activeElement)));
    }
    await page.keyboard.press('Escape');
    assert.equal(await dialog.count(), 0);
    assert.deepEqual(await page.locator('.cm-content').allTextContents(), before);
    await page.locator('.cm-editor.cm-focused').waitFor();

    await page.keyboard.press('F1');
    await page.getByRole('dialog').getByRole('button', { name: '安装说明', exact: true }).click();
    await page.getByRole('link', { name: '快速上手', exact: true }).click();
    await page.getByRole('heading', { name: '快速上手 / Get Started' }).waitFor();
    await page.setViewportSize({ width: 390, height: 844 });
    const bounds = await page.getByRole('dialog').boundingBox();
    assert.ok(bounds.x >= 0 && bounds.x + bounds.width <= 390);
    assert.equal(await page.evaluate(() => {
      const article = document.querySelector('.help-content');
      return article.scrollWidth > article.clientWidth + 1;
    }), false);
    await page.getByRole('dialog').screenshot({ path: path.join(output, 'help-mobile.png') });
    await page.keyboard.press('Escape');
    await page.setViewportSize({ width: 1400, height: 1040 });
    await page.getByRole('button', { name: '全部运行', exact: true }).click();
    await page.locator('.cell').last().locator('.plot-container').waitFor({ timeout: 30000 });
    await page.waitForFunction(() => !document.querySelector('.cell.running'));
    assert.equal(await page.locator('.error-message').count(), 0);
    await page.locator('.js-plotly-plot').waitFor();
    await page.evaluate(() => document.fonts.ready);
    for (let index = 0; index < 6; index++) await page.locator('.notebook').dispatchEvent('wheel', { deltaY: 100, ctrlKey: true });
    await page.waitForFunction(() => document.querySelector('.zoom-reset')?.textContent === '70%');
    await page.setViewportSize({ width: 1400, height: 1280 });
    await page.screenshot({ path: process.env.CALIX_CAPTURE_DOCS && !desktop ? 'docs/images/notebook.png' : path.join(output, 'notebook-preview.png') });
    await page.setViewportSize({ width: 1400, height: 1040 });
    await page.getByRole('button', { name: '传统计算器面板', exact: true }).click();
    const editor = page.locator('.calculator-cell .cm-content');
    await editor.click();
    await page.keyboard.insertText('Integrate[Sin[x], {x,0,Pi}]');
    await page.keyboard.press('Control+Enter');
    await page.locator('.calculator-cell .formula').waitFor({ timeout: 15000 });
    await page.screenshot({ path: process.env.CALIX_CAPTURE_DOCS && !desktop ? 'docs/images/calculator.png' : path.join(output, 'calculator-preview.png') });
    await page.keyboard.press('F1');
    await page.getByRole('dialog').getByRole('button', { name: '案例目录', exact: true }).click();
    await page.getByRole('link', { name: '弹性双摆', exact: true }).click();
    await page.waitForFunction(() => !document.querySelector('dialog'));
    assert.match(await page.getByRole('textbox', { name: 'Notebook 名称' }).inputValue(), /弹性双摆/);

    await page.getByRole('button', { name: '偏好设置', exact: true }).click();
    await page.getByRole('combobox', { name: '界面语言' }).selectOption('en');
    await page.getByRole('button', { name: 'Close preferences' }).click();
    if (desktop) await page.waitForFunction(async () => (await window.__TAURI_INTERNALS__.invoke('read_preferences'))['calix-language'] === 'en');
    await page.reload();
    await page.locator('.engine-status.ready').waitFor();
    await page.keyboard.press('F1');
    await page.getByRole('heading', { name: 'Get Started', exact: true }).waitFor();
    await page.getByRole('dialog').getByRole('link', { name: 'LICENSE', exact: true }).click();
    await page.getByRole('article').getByText('All rights reserved.', { exact: false }).first().waitFor();
    assert.deepEqual(errors, []);
    console.log('Help: F1, navigation, search, focus, mobile layout, notebook preservation, example opening and screenshots passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
