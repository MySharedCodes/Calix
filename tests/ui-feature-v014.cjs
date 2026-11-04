const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9223') : await chromium.launch({ channel: 'msedge', headless: true });
  const page = desktop ? browser.contexts()[0].pages().find(p => /tauri.localhost/.test(p.url())) : await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  if (desktop) {
    await page.addInitScript(key => { if (!sessionStorage.getItem(key)) { localStorage.clear(); sessionStorage.setItem(key, '1'); } }, `feature-reset-${Date.now()}`);
    await page.reload();
  } else await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:8765');
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
  assert.equal(await page.locator('.cell').count(), 8);
  const title = await page.getByLabel('Notebook 名称').inputValue();
  assert.match(title, /^空气阻力/);
  assert.equal((await page.locator('.cm-content').nth(1).innerText()), 'r = Integrate[v, {t,0,t}]');
  await page.getByRole('button', { name: '全部运行', exact: true }).click();
  await page.locator('.animation-output .js-plotly-plot').waitFor({ timeout: 60000 });
  assert.equal(await page.locator('.error-message').count(), 0);
  await page.getByLabel('动画进度').fill('400');
  await page.getByTitle('播放动画').click();
  await page.waitForTimeout(400);
  await page.getByTitle('暂停动画').click();
  assert.ok(Number(await page.getByLabel('动画进度').inputValue()) > 400);
  await page.screenshot({ path: 'work/ui/quadratic-drag-v014.png' });
  const insert = async name => {
    await page.getByRole('button', { name: '计算示例', exact: true }).click();
    await page.locator('.library-panel').getByRole('button', { name, exact: true }).click();
    if (await page.getByTitle('关闭示例').count()) await page.getByTitle('关闭示例').click();
    assert.equal(await page.locator('.notebook-row').count(), 1);
    assert.equal(await page.getByLabel('Notebook 名称').inputValue(), title);
    return page.locator('.cell').last();
  };
  const run = async cell => {
    await cell.getByTitle('运行单元', { exact: true }).click();
    await cell.locator('.result-meta').last().waitFor({ timeout: 60000 });
    assert.equal(await cell.locator('.error-message').count(), 0, await cell.innerText());
  };
  let cell = await insert('显式数值计算');
  assert.equal(await page.locator('.cell').count(), 9);
  const first = (await cell.locator('.cm-content').innerText()).split('\n').slice(1,-1);
  assert.equal(first.length, 10);
  await run(cell); assert.equal(await cell.locator('.group-item').count(), 10);
  cell = await insert('显式数值计算');
  const second = (await cell.locator('.cm-content').innerText()).split('\n').slice(1,-1);
  assert.ok(first.every((line,i) => line !== second[i]));
  assert.equal(await page.locator('.cell').count(), 10);
  cell = await insert('单位运算'); await run(cell);
  assert.equal(await cell.locator('.group-item').count(), 5);
  cell = await insert('描述统计'); await run(cell);
  assert.ok(await cell.locator('.js-plotly-plot').evaluate(el => el.data[0].type === 'bar'));
  await page.screenshot({ path: 'work/ui/statistics-v014.png' });
  await page.getByRole('button', { name: '单位运算器', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: '计算', exact: true }).click();
  await page.getByRole('dialog').locator('.formula').waitFor();
  assert.match(await page.getByRole('dialog').locator('.formula').innerText(), /N/);
  await page.screenshot({ path: 'work/ui/unit-calculator-v014.png' });
  await page.getByRole('dialog').getByRole('button', { name: '插入计算单元', exact: true }).click();
  assert.match(await page.locator('.cell').last().locator('.cm-content').innerText(), /UnitSimplify/);
  for (const name of ['高考物理：2016 全国Ⅲ卷第25题最后一问','高考数学：2008 江西理科第22题','IMO 1988 第6题：韦达跳跃','IMO 2009 第6题：蚱蜢跳跃']) {
    const before = await page.locator('.notebook-row').count();
    await page.getByRole('button', { name: '计算示例', exact: true }).click();
    await page.locator('.library-panel').getByRole('button', { name, exact: true }).click();
    assert.equal(await page.locator('.notebook-row').count(), before + 1);
    assert.equal(await page.getByLabel('Notebook 名称').inputValue(), name);
    const added = page.locator('.cell');
    for (let i=0; i<await added.count(); i++) if (await added.nth(i).locator('.cm-content').count()) await run(added.nth(i));
    await page.getByRole('button', { name: '计算示例', exact: true }).click();
    await page.locator('.library-panel').getByRole('button', { name, exact: true }).click();
    assert.equal(await page.locator('.notebook-row').count(), before + 1);
    if (name.includes('江西')) {
      const canvas = page.locator('.plot-canvas canvas').last();
      await canvas.scrollIntoViewIfNeeded(); await page.waitForTimeout(250);
      assert.ok(await canvas.evaluate(c => c.width > 100 && c.height > 100));
      await page.screenshot({ path: 'work/ui/challenge-surface-v015.png' });
    }
  }
  assert.equal(await page.locator('.error-message').count(), 0);
  await page.locator('.notebook-list').getByRole('button', { name: '高考数学：2008 江西理科第22题', exact: true }).click();
  const canvas = page.locator('.plot-canvas canvas').last();
  await canvas.scrollIntoViewIfNeeded(); await page.waitForTimeout(250);
  await page.screenshot({ path: 'work/ui/challenge-surface-v014.png' });
  const pixels = await canvas.evaluate(c => {
    const gl = c.getContext('webgl2') || c.getContext('webgl'); if (!gl) return false;
    const pixels = new Uint8Array(4*c.width*c.height); gl.readPixels(0,0,c.width,c.height,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    let colored=0; for(let i=0;i<pixels.length;i+=4) if(Math.max(pixels[i],pixels[i+1],pixels[i+2])-Math.min(pixels[i],pixels[i+1],pixels[i+2])>30) colored++;
    return { colored, width:c.width, height:c.height };
  });
  assert.ok(pixels.colored>1000, JSON.stringify(pixels));
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1));
  await page.screenshot({ path: 'work/ui/features-mobile-v014.png' });
  assert.deepEqual(errors, []);
  fs.writeFileSync('work/ui/feature-v015-report.json', JSON.stringify({ status:'passed', desktop, exampleInsertion:true, randomRows:10, unitExamples:5, statistics:true, quadraticDrag:true, challenges:4, separateNotebooks:true, surfacePixels:true, mobile:true, errors },null,2));
  await browser.close(); console.log('Feature UI passed: insertion, ten random rows, five units, statistics, quadratic drag, four separate challenge notebooks, surface pixels and mobile.');
})().catch(e => { console.error(e); process.exit(1); });
