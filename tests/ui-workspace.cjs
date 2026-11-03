const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9223') : await chromium.launch({ headless: true, channel: 'msedge' });
  const context = desktop ? browser.contexts()[0] : await browser.newContext({ viewport: { width: 1360, height: 1000 }, acceptDownloads: true });
  const page = desktop ? context.pages().find(page => /tauri\.localhost/.test(page.url())) : await context.newPage();
  if (desktop) {
    await page.evaluate(() => sessionStorage.removeItem('calix-workspace-test-reset'));
    await page.addInitScript(() => {
      if (!sessionStorage.getItem('calix-workspace-test-reset')) { localStorage.clear(); sessionStorage.setItem('calix-workspace-test-reset', '1'); }
    });
    await page.reload();
  }
  const errors = []; page.on('pageerror', error => errors.push(String(error)));
  const enterCode = async code => {
    const editor = page.locator('.cm-content');
    await editor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText(code);
    assert.equal(await editor.innerText(), code);
  };
  if (!desktop) await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:5173');
  await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
  assert.equal(await page.locator('.document-subtitle').count(), 0);
  assert.equal(await page.locator('.brand span').last().innerText(), 'Calculation &\nInteractive Xpressions');
  await page.getByRole('button', { name: '新建笔记', exact: true }).first().click();
  await page.getByLabel('Notebook 名称').fill('Experiment A');
  await enterCode('x=41');
  await page.getByTitle('运行单元', { exact: true }).click();
  await page.locator('.result-meta').waitFor();
  await page.getByRole('button', { name: '新建笔记', exact: true }).first().click();
  await page.getByLabel('Notebook 名称').fill('Experiment B');
  await enterCode('x=7');
  await page.getByTitle('运行单元', { exact: true }).click();
  await page.locator('.result-meta').waitFor();
  await page.locator('.notebook-list').getByRole('button', { name: 'Experiment A', exact: true }).click();
  assert.equal(await page.locator('.cm-content').innerText(), 'x=41');
  await enterCode('x+1');
  await page.getByTitle('运行单元', { exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.formula')?.textContent.includes('42')).catch(async error => { console.log('A result:', await page.locator('.notebook').innerText()); throw error; });
  await page.locator('.notebook-list').getByRole('button', { name: 'Experiment B', exact: true }).click();
  await enterCode('x+1');
  await page.getByTitle('运行单元', { exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.formula')?.textContent.includes('8'));
  const rowB = page.locator('.notebook-row').filter({ has: page.getByRole('button', { name: 'Experiment B', exact: true }) });
  await rowB.getByTitle('重命名笔记').click();
  await page.getByLabel('笔记名称', { exact: true }).fill('Experiment Beta');
  await page.getByRole('dialog').getByRole('button', { name: '保存', exact: true }).click();
  assert.equal(await page.getByLabel('Notebook 名称').inputValue(), 'Experiment Beta');
  await page.locator('.notebook-row.selected').getByTitle('复制笔记').click();
  assert.equal(await page.getByLabel('Notebook 名称').inputValue(), 'Experiment Beta 副本');
  await page.locator('.notebook-row.selected').getByTitle('移除笔记').click();
  await page.getByRole('dialog').getByRole('button', { name: '移除', exact: true }).click();
  assert.equal(await page.locator('.notebook-row').count(), 3);

  await page.getByRole('button', { name: '新建笔记', exact: true }).first().click();
  await page.getByLabel('Notebook 名称').fill('Unified input');
  assert.equal(await page.getByRole('button', { name: '代码单元', exact: true }).count(), 0);
  assert.equal(await page.getByRole('button', { name: '数学单元', exact: true }).count(), 0);
  await enterCode('1+');
  await page.locator('.cm-content').focus(); await page.keyboard.press('Control+End'); await page.keyboard.press('Control+2');
  const math = page.locator('math-field'); await math.waitFor();
  assert.ok((await math.evaluate(mf => mf.value)).includes('sqrt'));
  await math.evaluate(mf => { mf.value = '\\sqrt{9}'; });
  await page.locator('.formula-composer').getByTitle('插入公式').click();
  assert.match(await page.locator('.cm-content').innerText(), /^1\+Sqrt\[9\]$/);
  await page.getByTitle('运行单元', { exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.formula')?.textContent.includes('4'));
  await page.getByTitle('插入公式', { exact: true }).click();
  await math.waitFor(); await math.focus(); await page.keyboard.press('Control+6');
  assert.ok((await math.evaluate(mf => mf.value)).includes('^'));
  await page.getByTitle('关闭公式输入').click();
  assert.match(await page.locator('.cm-content').innerText(), /^1\+Sqrt\[9\]$/);

  await page.getByRole('button', { name: '计算示例', exact: true }).click();
  await page.getByRole('button', { name: '显式数值计算', exact: true }).click();
  assert.equal(await page.getByLabel('Notebook 名称').inputValue(), 'Unified input');
  assert.equal(await page.locator('.cell').count(), 2);
  await page.locator('.cell').last().getByTitle('运行单元', { exact: true }).click();
  await page.locator('.cell').last().locator('.group-item').nth(9).waitFor();
  assert.equal(await page.locator('.cell').last().locator('.group-item').count(), 10);
  for (const name of ['解析最值', '数值最值']) {
    await page.getByRole('button', { name, exact: true }).click();
    assert.equal(await page.getByLabel('Notebook 名称').inputValue(), 'Unified input');
    await page.locator('.cell').last().getByTitle('运行单元', { exact: true }).click();
    await page.locator('.cell').last().locator('.js-plotly-plot').waitFor({ timeout: 30000 });
    assert.equal(await page.locator('.error-message').count(), 0);
  }
  await page.getByTitle('关闭示例').click();
  await page.getByRole('button', { name: '偏好设置', exact: true }).click();
  await page.getByLabel('最大 CPU Workers').fill('1');
  await page.waitForFunction(() => localStorage.getItem('calix-workers') === '1');
  await page.getByLabel('界面语言').selectOption('en');
  await page.getByRole('dialog', { name: 'Preferences' }).waitFor();
  assert.equal(await page.getByLabel('Maximum CPU Workers').inputValue(), '1');
  await page.getByTitle('Close preferences').click();
  await page.getByRole('button', { name: 'Calculation cell', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Examples', exact: true }).click();
  await page.getByRole('button', { name: 'Analytical extrema', exact: true }).click();
  assert.equal(await page.getByLabel('Notebook name', { exact: true }).inputValue(), 'Unified input');
  await page.getByTitle('Close examples').click();
  await page.screenshot({ path: 'work/ui/workspace-english-0.1.3.png' });
  await page.waitForTimeout(700); await page.reload();
  await page.getByText('Native engine ready').waitFor();
  assert.equal(await page.getByLabel('Notebook name', { exact: true }).inputValue(), 'Unified input');
  assert.equal(await page.locator('.notebook-row').count(), 4);
  await page.getByRole('button', { name: 'Preferences', exact: true }).click();
  assert.equal(await page.getByLabel('Maximum CPU Workers').inputValue(), '1');
  await page.getByLabel('Language', { exact: true }).selectOption('zh');
  await page.getByTitle('关闭设置').click();
  await page.locator('.notebook-list').getByRole('button', { name: 'Experiment A', exact: true }).click();
  assert.equal(await page.locator('.cm-content').innerText(), 'x+1');
  await page.screenshot({ path: 'work/ui/workspace-chinese-0.1.3.png' });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  await page.getByTitle('展开侧栏').click();
  await page.screenshot({ path: 'work/ui/workspace-mobile-0.1.3.png' });
  await page.locator('.notebook-list').getByRole('button', { name: 'Unified input', exact: true }).click();
  assert.equal(await page.getByLabel('Notebook 名称').inputValue(), 'Unified input');
  await page.getByTitle('收起侧栏').click();
  await page.getByTitle('插入公式', { exact: true }).first().click();
  await math.waitFor();
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  assert.deepEqual(errors, []);
  fs.writeFileSync('work/ui/workspace-report.json', JSON.stringify({ status: 'passed', isolatedSessions: true, notebookManagement: true, unifiedInput: true, numericalExamples: 10, bilingual: true, persistedWorkerLimit: 1, errors }, null, 2));

  // Old single-notebook autosaves and legacy math cells migrate without dropping input.
  if (!desktop) {
  const legacy = await browser.newContext();
  await legacy.addInitScript(() => localStorage.setItem('calix-notebook-v1', JSON.stringify({ format: 'calix-notebook', version: 1, title: 'Legacy notebook', cells: [{ id: 'old', mode: 'math', code: 'Sqrt[9]', latex: '\\sqrt{9}' }] })));
  const oldPage = await legacy.newPage(); await oldPage.goto(process.env.CALIX_URL || 'http://127.0.0.1:5173');
  await oldPage.getByText('原生核心就绪').waitFor();
  assert.equal(await oldPage.getByLabel('Notebook 名称').inputValue(), 'Legacy notebook');
  assert.equal(await oldPage.locator('.cm-content').innerText(), 'Sqrt[9]');
  await oldPage.getByTitle('运行单元', { exact: true }).click(); await oldPage.locator('.result-meta').waitFor();
  assert.equal(await oldPage.locator('.error-message').count(), 0);
  }
  await browser.close();
  console.log('Workspace UI passed: notebook isolation, management, unified formula/code input, bilingual UI, persisted Workers and legacy migration.');
})().catch(error => { console.error(error); process.exit(1); });
