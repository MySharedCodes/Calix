const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'C:/Users/Numerical_Magic_Box/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9223') : await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = desktop ? browser.contexts()[0].pages().find(p => /tauri.localhost/.test(p.url())) : await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    if (desktop) {
      await page.addInitScript(key => { if (!sessionStorage.getItem(key)) { localStorage.clear(); sessionStorage.setItem(key, '1'); } }, `cases-reset-${Date.now()}`);
      await page.reload(); await page.setViewportSize({ width: 1440, height: 1000 });
    } else await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:8765');
    await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
    const cases = JSON.parse(fs.readFileSync('frontend/src/example-notebooks.json', 'utf8'));
    const records = [];
    for (const notebook of cases) {
      await page.getByRole('button', { name: '计算示例', exact: true }).click();
      assert.equal(await page.locator('.library-panel').getByRole('heading', { name: /挑战题|Challenge problems/ }).count(), 0);
      await page.locator('.library-panel').getByRole('button', { name: notebook.title, exact: true }).click();
      assert.equal(await page.getByLabel('Notebook 名称').inputValue(), notebook.title);
      const prose = await page.locator('.markdown-cell').allTextContents();
      assert.ok(prose.every(text => !/参考|来源|客观排名|归纳证明|最小反例/.test(text)));
      await page.getByRole('button', { name: '全部运行', exact: true }).click();
      const count = notebook.cells.filter(c => c.mode === 'source').length;
      await page.waitForFunction(count => document.querySelectorAll('.notebook .cell>.cell-body>.output').length === count || document.querySelector('.notebook .error-message'), count, { timeout: 60000 });
      assert.equal(await page.locator('.notebook .error-message').count(), 0, await page.locator('.notebook').innerText());
      const animation = page.locator('.animation-output');
      if (await animation.count()) {
        await animation.scrollIntoViewIfNeeded();
        const graph = animation.locator('.js-plotly-plot'); await graph.waitFor();
        const initial = await graph.evaluate(el => ({ points: el.data.at(-1).y, x: el._fullLayout.xaxis.range, y: el._fullLayout.yaxis.range }));
        const balls = notebook.title.startsWith('五球') ? 5 : 2;
        assert.equal(initial.points.length, balls);
        await animation.getByLabel('动画进度').fill('30'); await page.waitForTimeout(200);
        const later = await graph.evaluate(el => ({ points: el.data.at(-1).y, x: el._fullLayout.xaxis.range, y: el._fullLayout.yaxis.range, visible: el.querySelectorAll('.point').length,
          scaleX: el._fullLayout.xaxis._length / (el._fullLayout.xaxis.range[1]-el._fullLayout.xaxis.range[0]), scaleY: el._fullLayout.yaxis._length / (el._fullLayout.yaxis.range[1]-el._fullLayout.yaxis.range[0]) }));
        assert.notDeepEqual(initial.points, later.points);
        assert.equal(later.visible, balls);
        assert.deepEqual(initial.x, later.x); assert.deepEqual(initial.y, later.y);
        assert.ok(Math.abs(later.scaleX/later.scaleY-1) < 0.02);
        await page.screenshot({ path: `work/ui/${balls === 5 ? 'five-ball-chain' : 'elastic-double-pendulum'}-v016.png` });
      }
      const documents = await page.locator('.notebook-row').count();
      await page.getByRole('button', { name: '计算示例', exact: true }).click();
      await page.locator('.library-panel').getByRole('button', { name: notebook.title, exact: true }).click();
      assert.equal(await page.locator('.notebook-row').count(), documents);
      assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(), count);
      records.push({ title: notebook.title, cells: count, animation: await animation.count() > 0 });
    }
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1));
    await page.screenshot({ path: 'work/ui/cases-mobile-v016.png' });
    assert.deepEqual(errors, []);
    fs.writeFileSync('work/ui/cases-v016-report.json', JSON.stringify({ status: 'passed', desktop, mergedExamples: true, records, fixedAnimationAxes: true, movingBalls: true, equalSpatialScale: true, mobile: true, errors }, null, 2));
    console.log('Case notebooks passed:', records);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
