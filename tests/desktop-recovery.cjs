const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const net = require('node:net');
const { spawn, spawnSync } = require('node:child_process');

const output = path.resolve('work/verification/desktop-recovery');
const profile = path.join(output, `profile-${Date.now()}`);
const notebookPath = path.join(output, '恢复测试 notebook.cixnb');
fs.mkdirSync(output, { recursive: true });
let child, browser;
async function stop() {
  if (child && child.exitCode === null) spawnSync('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' });
  child = null;
  if (browser) { await browser.close().catch(() => {}); browser = null; }
}
const invoke = (page, command, args = {}) => page.evaluate(({ command, args }) => window.__TAURI_INTERNALS__.invoke(command, args), { command, args });

(async () => {
  const server = net.createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  async function launch() {
    child = spawn(path.resolve(process.env.CALIX_DESKTOP_EXE || 'src-tauri/target/release/calix.exe'), [], {
      windowsHide: true, stdio: 'ignore', env: { ...process.env, WEBVIEW2_USER_DATA_FOLDER: profile,
        WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${port}`, CALIX_MAX_WORKERS: '8' },
    });
    for (let attempt = 0; attempt < 100; attempt++) {
      if (child.exitCode !== null) throw new Error(`Desktop exited: ${child.exitCode}`);
      try { if ((await fetch(`http://127.0.0.1:${port}/json/version`)).ok) break; } catch {}
      await new Promise(resolve => setTimeout(resolve, 250));
    }
    browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
    const context = browser.contexts()[0];
    let page;
    for (let attempt = 0; attempt < 100; attempt++) {
      page = context.pages().find(item => /tauri\.localhost/.test(item.url()));
      if (page) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    assert.ok(page, 'Desktop WebView must open');
    await page.locator('.engine-status.ready').waitFor({ timeout: 45000 });
    return page;
  }
  try {
    let page = await launch();
    const doc = title => ({ format: 'calix-notebook', version: 1, title, cells: [{ id: 'cell-1', mode: 'source', code: '123+456' }] });
    await invoke(page, 'write_notebook', { path: notebookPath, content: JSON.stringify(doc('Previous file')) });
    await invoke(page, 'write_notebook', { path: notebookPath, content: JSON.stringify(doc('Saved document')) });
    const versions = await invoke(page, 'list_file_versions', { path: notebookPath });
    assert.ok(versions.length);
    assert.equal(JSON.parse(await invoke(page, 'read_file_version', { path: notebookPath, id: versions[0].id })).title, 'Previous file');
    await assert.rejects(() => invoke(page, 'read_recovery', { id: '../preferences.json' }));
    await page.addInitScript(({ doc, notebookPath }) => {
      if (sessionStorage.getItem('desktop-recovery-seeded')) return;
      sessionStorage.setItem('desktop-recovery-seeded', '1');
      localStorage.setItem('calix-language', 'zh');
      localStorage.setItem('calix-workspace-v1', JSON.stringify({ version: 1, active: 'desktop-doc', documents: [{ ...doc, id: 'desktop-doc', path: notebookPath }] }));
    }, { doc: doc('Saved document'), notebookPath });
    await invoke(page, 'write_preferences', { preferences: { 'calix-language': 'zh', 'calix-workers': '8' } });
    await page.reload();
    await page.locator('.engine-status.ready').waitFor();
    await page.getByRole('button', { name: '恢复历史', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: '恢复历史' });
    await dialog.locator('nav button').filter({ hasText: '文件历史' }).first().click();
    await dialog.locator('.recovery-notebooks button').getByText('Previous file', { exact: true }).waitFor();
    await dialog.screenshot({ path: path.join(output, 'file-history.png') });
    await dialog.locator('.recovery-notebooks button').first().click();
    assert.match(await page.getByRole('textbox', { name: 'Notebook 名称' }).inputValue(), /Previous file.*恢复副本/);
    assert.equal(await page.locator('.notebook-row').count(), 2);
    await page.getByRole('textbox', { name: 'Notebook 名称' }).fill('Desktop disk recovery');
    await page.waitForFunction(async () => {
      const saved = JSON.parse(await window.__TAURI_INTERNALS__.invoke('read_recovery', { id: 'latest.data' }));
      return saved.documents.some(doc => doc.title === 'Desktop disk recovery');
    });
    await page.evaluate(() => {
      localStorage.setItem('calix-workspace-v1', JSON.stringify({ version: 1, documents: [{ id: 'broken', cells: [] }] }));
      localStorage.removeItem('calix-workspace-backup-v1');
    });
    await new Promise(resolve => setTimeout(resolve, 500));
    await stop();
    // Remove only this test profile's browser database, keeping native recovery intact.
    const browserStorage = path.resolve(profile, 'EBWebView/Default/Local Storage');
    assert.ok(browserStorage.startsWith(path.resolve(profile) + path.sep));
    fs.rmSync(browserStorage, { recursive: true, force: true });
    const recoveryPath = path.join(profile, 'recovery/latest.data');
    const disk = JSON.parse(fs.readFileSync(recoveryPath, 'utf8'));
    disk.documents.find(doc => doc.id === disk.active).title = 'Recovered from disk only';
    fs.writeFileSync(recoveryPath, JSON.stringify(disk));
    page = await launch();
    assert.equal(await page.getByRole('textbox', { name: 'Notebook 名称' }).inputValue(), 'Recovered from disk only');
    assert.equal(await page.locator('.cm-content').first().innerText(), '123+456');
    assert.equal(await page.evaluate(() => localStorage.getItem('calix-workers')), '8');
    await page.locator('.cm-content').first().click();
    await page.keyboard.press('Control+Enter');
    await page.locator('.cell .formula').filter({ hasText: '579' }).waitFor();
    await page.screenshot({ path: path.join(output, 'recovered-desktop.png') });
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify({ passed: true, version: '0.1.28', checks: ['native saved-file history', 'recovery opens copy', 'restart from disk after missing browser storage', 'worker preference retained', 'recovered calculation'], isolated_profile: true }, null, 2));
    console.log('Desktop recovery: file history, recovery copy, process restart, missing browser storage and preferences passed');
  } finally { await stop(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
