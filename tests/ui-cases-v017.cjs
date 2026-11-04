const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');

(async () => {
  const desktop = !!process.env.CALIX_DESKTOP;
  const browser = desktop ? await chromium.connectOverCDP('http://127.0.0.1:9223') : await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = desktop ? browser.contexts()[0].pages().find(p => /tauri.localhost/.test(p.url())) : await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    if (desktop) {
      await page.addInitScript(key => { if (!sessionStorage.getItem(key)) { localStorage.clear(); sessionStorage.setItem(key, '1'); } }, `v017-reset-${Date.now()}`);
      await page.reload(); await page.setViewportSize({ width: 1440, height: 1000 });
    } else await page.goto(process.env.CALIX_URL || 'http://127.0.0.1:8765');
    await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
    await page.getByRole('button', { name: '新建笔记', exact: true }).first().click();
    const editor = page.locator('.cm-content');
    const enter = async code => { await editor.click(); await page.keyboard.press('Control+A'); await page.keyboard.insertText(code); };
    await enter('2+2'); await page.keyboard.press('Control+Enter');
    await page.waitForFunction(() => document.querySelector('.formula annotation')?.textContent.trim() === '4').catch(async error => {
      console.log('Ctrl+Enter diagnostic:', await page.locator('.notebook').innerText());
      console.log('Formula diagnostic:', await page.locator('.formula').allInnerTexts());
      await page.screenshot({ path: 'work/ui/keyboard-failure-v017.png' }); throw error;
    });
    await enter('Integrate[Exp[Sin[x^7]],x]'); await page.keyboard.press('Control+Enter');
    await page.locator('.pending').waitFor(); await page.keyboard.press('Alt+.');
    await page.getByText('计算已停止，会话变量已清空', { exact: true }).waitFor();
    await page.locator('.pending').waitFor({ state: 'hidden' });
    await enter('2+3'); await page.keyboard.press('Control+Enter');
    await page.waitForFunction(() => document.querySelector('.formula annotation')?.textContent.trim() === '5');
    await page.keyboard.press('Alt+.');
    assert.equal(await page.locator('.formula annotation').textContent(), '5');
    await enter('Integrate[Exp[Sin[x^7]],x]');
    await page.getByRole('button', { name: '计算单元', exact: true }).click();
    await page.locator('.cm-content').last().click(); await page.keyboard.insertText('999');
    await page.getByRole('button', { name: '全部运行', exact: true }).click();
    await page.locator('.pending').waitFor(); await page.keyboard.press('Alt+.');
    await page.locator('.pending').waitFor({ state: 'hidden' });
    assert.equal(await page.locator('.cell').last().locator('.output').count(), 0);

    const starter = JSON.parse(fs.readFileSync('frontend/src/starter.json', 'utf8'));
    const cases = [starter, ...JSON.parse(fs.readFileSync('frontend/src/example-notebooks.json', 'utf8'))];
    const records = [];
    for (const notebook of cases) {
      await page.getByRole('button', { name: '计算示例', exact: true }).click();
      const library = page.locator('.library-panel');
      assert.equal(await library.getByRole('button', { name: /IMO 1988|IMO 2009/ }).count(), 0);
      const uniform = await library.locator('.example-group').first().locator(':scope > button').evaluateAll(buttons => buttons.map(button => ({ tag: button.firstElementChild.tagName, last: button.lastElementChild.tagName, classes: button.className })));
      assert.equal(uniform.length, 8);
      assert.ok(uniform.every(row => JSON.stringify(row) === JSON.stringify(uniform[0])));
      if (notebook === starter) await page.screenshot({ path: 'work/ui/examples-v017.png' });
      await library.getByRole('button', { name: notebook.title, exact: true }).click();
      assert.equal(await page.getByLabel('Notebook 名称').inputValue(), notebook.title);
      await page.getByRole('button', { name: '全部运行', exact: true }).click();
      const count = notebook.cells.filter(cell => cell.mode === 'source').length;
      await page.waitForFunction(count => document.querySelectorAll('.notebook .cell>.cell-body>.output').length === count || document.querySelector('.notebook .error-message'), count, { timeout: 60000 });
      assert.equal(await page.locator('.notebook .error-message').count(), 0, await page.locator('.notebook').innerText());
      const animation = page.locator('.animation-output');
      if (await animation.count()) {
        assert.equal(await animation.count(), 1);
        await animation.scrollIntoViewIfNeeded();
        const graph = animation.locator('.js-plotly-plot'); await graph.waitFor();
        await page.waitForTimeout(150);
        const before = await graph.evaluate(el => ({ x: el._fullLayout.xaxis.range, y: el._fullLayout.yaxis.range, points: [el.data.at(-1).x, el.data.at(-1).y] }));
        const balls = notebook.title.startsWith('五球') ? 5 : notebook.title.startsWith('三天体') ? 3 : notebook.title.startsWith('弹性') ? 2 : 1;
        await animation.getByLabel('动画进度').fill('30'); await page.waitForTimeout(250);
        const after = await graph.evaluate(el => ({ x: el._fullLayout.xaxis.range, y: el._fullLayout.yaxis.range, points: [el.data.at(-1).x, el.data.at(-1).y], count: el.querySelectorAll('.point').length,
          sx: el._fullLayout.xaxis._length/(el._fullLayout.xaxis.range[1]-el._fullLayout.xaxis.range[0]), sy: el._fullLayout.yaxis._length/(el._fullLayout.yaxis.range[1]-el._fullLayout.yaxis.range[0]) }));
        assert.equal(after.count, balls); assert.notDeepEqual(before.points, after.points);
        if (notebook !== starter) {
          assert.deepEqual(before.x, after.x); assert.deepEqual(before.y, after.y);
          assert.ok(Math.abs(after.sx/after.sy-1) < 0.02);
        }
        await page.screenshot({ path: `work/ui/${balls === 5 ? 'five-ball-chain' : balls === 3 ? 'three-body' : balls === 2 ? 'elastic-double-pendulum' : 'projectile'}-v017.png` });
      }
      if (notebook.title.startsWith('高考数学')) {
        const cell = page.locator('.cell').filter({ has: page.locator('.cm-content', { hasText: 'bounds=Sort' }) });
        await cell.locator('canvas').scrollIntoViewIfNeeded();
        const painted = await cell.locator('canvas').evaluate(canvas => {
          const copy = document.createElement('canvas'); copy.width = canvas.width; copy.height = canvas.height;
          const context = copy.getContext('2d'); context.drawImage(canvas, 0, 0);
          const pixels = context.getImageData(0, 0, copy.width, copy.height).data;
          let colored = 0; for (let i = 0; i < pixels.length; i += 4) if (Math.max(...pixels.slice(i, i+3))-Math.min(...pixels.slice(i, i+3)) > 30) colored++;
          return colored;
        });
        assert.ok(painted > 5000); await page.screenshot({ path: 'work/ui/analytic-bounds-v017.png' });
      }
      if (notebook.title.startsWith('五球')) {
        const cell = page.locator('.cell').filter({ has: page.locator('.cm-content', { hasText: 'bottom=Part' }) });
        await cell.locator('.plot-output').first().scrollIntoViewIfNeeded();
        assert.deepEqual(await cell.locator('.legendtext').first().evaluate(el => [...el.closest('.legend').querySelectorAll('.legendtext')].map(label => label.textContent)), ['最下方小球','倒数第二个小球','自由落体']);
        await page.screenshot({ path: 'work/ui/falling-comparison-v017.png' });
      }
      const documents = await page.locator('.notebook-row').count();
      await page.getByRole('button', { name: '计算示例', exact: true }).click();
      await library.getByRole('button', { name: notebook.title, exact: true }).click();
      assert.equal(await page.locator('.notebook-row').count(), documents);
      assert.equal(await page.locator('.notebook .cell>.cell-body>.output').count(), count);
      records.push({ title: notebook.title, cells: count, animation: await animation.count() > 0 });
    }
    await page.getByRole('button', { name: '偏好设置', exact: true }).click();
    await page.getByLabel('界面语言', { exact: true }).selectOption('en');
    await page.getByTitle('Close preferences', { exact: true }).click();
    await page.getByRole('button', { name: 'Examples', exact: true }).click();
    const projectile = page.locator('.library-panel').getByRole('button', { name: 'Projectile motion with quadratic air resistance', exact: true });
    assert.equal(await projectile.locator('span').count(), 1);
    assert.equal(await projectile.locator('svg').count(), 1);
    await page.screenshot({ path: 'work/ui/examples-english-v017.png' });
    await page.getByTitle('Close examples', { exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1));
    await page.screenshot({ path: 'work/ui/cases-mobile-v017.png' });
    assert.deepEqual(errors, []);
    fs.writeFileSync('work/ui/cases-v017-report.json', JSON.stringify({ status: 'passed', desktop, ctrlEnter: true, altPeriodCancel: true, uniformExamples: true, records, movingBalls: true, fixedAnimationAxes: true, equalSpatialScale: true, mobile: true, errors }, null, 2));
    console.log('0.1.7 desktop=',desktop,'cases and shortcuts passed:', records);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
