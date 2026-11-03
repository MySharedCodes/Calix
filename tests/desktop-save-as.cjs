const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  const waitForTitle = async (path, title) => {
    for (let attempt = 0; attempt < 60; attempt++) {
      if (fs.existsSync(path) && JSON.parse(fs.readFileSync(path, 'utf8')).title === title) return;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    throw new Error(`Save did not write ${title} to ${path}`);
  };
  const page = browser.contexts()[0].pages().find(page => /tauri\.localhost/.test(page.url()));
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByText('原生核心就绪').waitFor();
  await page.evaluate(() => {
    const original = window.fetch;
    window.calixOriginalFetch = original;
    window.calixSaveDialogs = 0;
    window.fetch = (url, options) => {
      if (decodeURIComponent(String(url)).includes('plugin:dialog|save')) {
        return Promise.resolve(new Response(JSON.stringify(`D:\\Calix\\work\\save-as-${++window.calixSaveDialogs}.calix`), { headers: { 'Content-Type': 'application/json', 'Tauri-Response': 'ok' } }));
      }
      return original(url, options);
    };
  });
  try {
    await page.getByLabel('Notebook 名称').fill('Save Original');
    await page.locator('.document-actions').getByRole('button', { name: '保存', exact: true }).click();
    await page.getByRole('status').filter({ hasText: 'Notebook 已保存' }).waitFor();
    assert.equal(JSON.parse(fs.readFileSync('work/save-as-1.calix', 'utf8')).title, 'Save Original');
    await page.getByLabel('Notebook 名称').fill('Save Copy');
    await page.locator('.document-actions').getByRole('button', { name: '另存为', exact: true }).click();
    await waitForTitle('work/save-as-2.calix', 'Save Copy');
    assert.equal(JSON.parse(fs.readFileSync('work/save-as-2.calix', 'utf8')).title, 'Save Copy');
    assert.equal(JSON.parse(fs.readFileSync('work/save-as-1.calix', 'utf8')).title, 'Save Original');
    await page.getByLabel('Notebook 名称').fill('Save Copy Updated');
    await page.locator('.document-actions').getByRole('button', { name: '保存', exact: true }).click();
    await waitForTitle('work/save-as-2.calix', 'Save Copy Updated');
    assert.equal(JSON.parse(fs.readFileSync('work/save-as-2.calix', 'utf8')).title, 'Save Copy Updated');
    assert.equal(await page.evaluate(() => window.calixSaveDialogs), 2);
    const animation = page.locator('.animation-output').first();
    await animation.scrollIntoViewIfNeeded();
    await animation.getByLabel('动画进度').fill('400');
    await animation.getByTitle('播放动画').click();
    await page.waitForTimeout(350);
    await animation.getByTitle('暂停动画').click();
    assert.ok(Number(await animation.getByLabel('动画进度').inputValue()) > 400);
    const header = await page.locator('.toolbar').boundingBox();
    assert.ok(header.y >= 0 && header.y < 2);
    fs.writeFileSync('work/desktop-save-as-report.json', JSON.stringify({ status: 'passed', dialogPathChanges: 2, preservesOriginal: true, animationPlayback: true, stickyToolbar: true }, null, 2));
    console.log('Desktop save-as passed: original preserved, copy updated, animation playback and sticky toolbar.');
  } finally {
    await page.evaluate(() => { window.fetch = window.calixOriginalFetch; });
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });
