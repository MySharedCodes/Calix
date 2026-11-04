const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
  let browser;
  for (let attempt = 0; attempt < 60; attempt++) {
    try { browser = await chromium.connectOverCDP('http://127.0.0.1:9223'); break; }
    catch (error) { if (attempt === 59) throw error; await new Promise(resolve => setTimeout(resolve, 300)); }
  }
  const context = browser.contexts()[0];
  const page = context.pages().find(p => /tauri\.localhost/.test(p.url())) || context.pages()[0];
  await page.waitForURL(/tauri\.localhost|tauri:\/\/localhost/, { timeout: 30000 });
  await page.waitForLoadState('domcontentloaded');
  await page.evaluate(() => sessionStorage.removeItem('calix-smoke-test-reset'));
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('calix-smoke-test-reset')) { localStorage.clear(); sessionStorage.setItem('calix-smoke-test-reset', '1'); }
  });
  await page.reload();
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
  const info = await page.evaluate(async () => {
    const invoke = window.__TAURI_INTERNALS__.invoke;
    const connection = await invoke('connection_info');
    const path = 'D:\\Calix\\work\\desktop-test.calix';
    const content = JSON.stringify({ format: 'calix-notebook', version: 1, title: 'Desktop test', cells: [{ id: 'a', mode: 'source', code: '1+1' }] });
    await invoke('write_notebook', { path, content });
    const loaded = await invoke('read_notebook', { path });
    return { port: connection.port, same: loaded === content };
  });
  assert.ok(info.same, 'Desktop file roundtrip failed');
  const response = await page.evaluate(async () => {
    const { port, token } = await window.__TAURI_INTERNALS__.invoke('connection_info');
    const response = await fetch(`http://127.0.0.1:${port}/api/evaluate`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Calix-Token': token }, body: JSON.stringify({ session: 'desktop-smoke', code: 'FindRoot[x^2-2,{x,0,2}]' }) });
    return response.json();
  });
  assert.ok(response.ok, JSON.stringify(response));
  assert.ok(Math.abs(Number(response.result.text) - Math.sqrt(2)) < 1e-10);
  const symbolic = await page.evaluate(async () => {
    const { port, token } = await window.__TAURI_INTERNALS__.invoke('connection_info');
    const response = await fetch(`http://127.0.0.1:${port}/api/evaluate`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Calix-Token': token }, body: JSON.stringify({ session: 'desktop-smoke', code: "DSolve[{y''[x]+y[x]==0,y[0]==1,y'[0]==0},y[x],x]" }) });
    return response.json();
  });
  assert.ok(symbolic.ok && symbolic.result.text.includes('Cos[x]'), JSON.stringify(symbolic));
  await page.getByRole('button', { name: '全部运行', exact: true }).click();
  await page.locator('.cell').last().locator('.result-meta').first().waitFor({ timeout: 30000 });
  await page.locator('.js-plotly-plot').first().waitFor();
  await page.getByRole('button', { name: '计算示例' }).click();
  await page.getByRole('button', { name: '三维曲面', exact: true }).click();
  await page.locator('.cell-gutter button').last().click();
  await page.locator('.plot-canvas canvas').waitFor({ timeout: 30000 });
  await page.getByRole('button', { name: '关闭示例' }).click();
  await page.locator('.plot-canvas canvas').last().scrollIntoViewIfNeeded();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: 'D:/Calix/work/ui/desktop-tauri.png', fullPage: true });
  assert.equal(await page.locator('.error-message').count(), 0);
  assert.deepEqual(errors, []);
  fs.writeFileSync('D:/Calix/work/desktop-report.json', JSON.stringify({ status: 'passed', variant: process.env.CALIX_DESKTOP_VARIANT || 'build', port: info.port, file_roundtrip: info.same, second_order_initial_condition: true, engine: response.result.engine, errors }, null, 2));
  console.log('Desktop smoke passed: packaged Tauri, packaged Python service, native DLL, file roundtrip, 2D/3D rendering.');
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
