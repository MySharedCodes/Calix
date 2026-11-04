const { chromium } = require(process.env.CALIX_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
  try {
    const page = browser.contexts()[0].pages().find(p => /tauri.localhost/.test(p.url()));
    const folder = path.resolve('work/file-management-v015'); fs.mkdirSync(folder, { recursive: true });
    const keep = path.join(folder, 'keep source.calix'), remove = path.join(folder, 'delete source.clxnb');
    const missing = path.join(folder, 'missing.calix');
    const content = { format: 'calix-notebook', version: 1, title: 'fixture', cells: [{ mode: 'source', code: '1+1' }] };
    fs.writeFileSync(keep, JSON.stringify(content)); fs.writeFileSync(remove, JSON.stringify(content));
    await page.addInitScript(({ keep, remove, missing, content, seed }) => {
      if (sessionStorage.getItem(seed)) return;
      sessionStorage.setItem(seed, '1');
      localStorage.setItem('calix-language', 'zh');
      const documents = [['keep', keep], ['delete', remove], ['other copy', remove], ['missing', missing], ['unsaved', null]].map(([title, path], index) => ({ ...content, title, path, id: `fixture-${index}`, updated: Date.now() }));
      localStorage.setItem('calix-workspace-v1', JSON.stringify({ version: 1, active: documents[0].id, documents }));
    }, { keep, remove, missing, content, seed: `file-test-${Date.now()}` });
    await page.reload(); await page.getByText('原生核心就绪').waitFor({ timeout: 30000 });
    assert.equal(await page.getByTitle('打开文件位置', { exact: true }).count(), 5);
    const row = name => page.locator('.notebook-row').filter({ has: page.getByRole('button', { name, exact: true }) });
    await row('unsaved').getByTitle('打开文件位置').click();
    await page.getByRole('status').filter({ hasText: '此笔记尚未保存到磁盘' }).waitFor();
    await row('keep').getByTitle('打开文件位置').click();
    const selectedFile = keep.replace(/'/g, "''");
    let selected = false;
    for (let attempt = 0; attempt < 12; attempt++) {
      await page.waitForTimeout(250);
      const selection = execFileSync('powershell.exe', ['-NoProfile', '-Command', `$shell = New-Object -ComObject Shell.Application; @($shell.Windows()) | ForEach-Object { try { @($_.Document.SelectedItems()) | Where-Object Path -eq '${selectedFile}' | ForEach-Object { 'selected' } } catch {} }`], { encoding: 'utf8', windowsHide: true });
      if (selection.includes('selected')) { selected = true; break; }
    }
    assert.ok(selected, 'Explorer must select the exact source file, including spaces in its path');
    await row('keep').getByTitle('移除笔记').click();
    assert.equal(await page.getByLabel('同时删除磁盘源文件').isChecked(), false);
    await page.getByRole('dialog').getByRole('button', { name: '移除', exact: true }).click();
    await row('keep').waitFor({ state: 'detached' }); assert.ok(fs.existsSync(keep));
    await row('delete').getByTitle('移除笔记').click();
    await page.getByLabel('同时删除磁盘源文件').check();
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    const confirmation = page.getByRole('dialog', { name: '确认删除源文件', exact: true });
    await confirmation.waitFor(); assert.ok(fs.existsSync(remove));
    assert.ok((await confirmation.innerText()).includes(remove));
    await confirmation.getByRole('button', { name: '取消', exact: true }).click();
    assert.ok(fs.existsSync(remove)); assert.equal(await row('delete').count(), 1);
    await row('delete').getByTitle('移除笔记').click();
    assert.equal(await page.getByLabel('同时删除磁盘源文件').isChecked(), false);
    await page.getByLabel('同时删除磁盘源文件').check();
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    await page.getByRole('button', { name: '永久删除源文件', exact: true }).click();
    await row('delete').waitFor({ state: 'detached' }); assert.ok(!fs.existsSync(remove));
    await page.waitForTimeout(700);
    assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('calix-workspace-v1')).documents.find(d => d.title === 'other copy').path), null);
    await row('missing').getByTitle('移除笔记').click();
    await page.getByLabel('同时删除磁盘源文件').check();
    await page.getByRole('button', { name: '下一步', exact: true }).click();
    await page.getByRole('button', { name: '永久删除源文件', exact: true }).click();
    await page.getByRole('alert').waitFor(); assert.equal(await row('missing').count(), 1);
    await page.screenshot({ path: 'work/ui/file-management-v015.png' });
    await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
    await row('unsaved').getByTitle('移除笔记').click();
    assert.ok(await page.getByLabel('同时删除磁盘源文件').isDisabled());
    await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click();
    await page.getByRole('button', { name: '偏好设置', exact: true }).click();
    await page.getByLabel('界面语言').selectOption('en'); await page.getByTitle('Close preferences').click();
    await row('missing').getByTitle('Remove notebook').click();
    await page.getByLabel('Also delete the source file on disk').check();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    await page.getByRole('dialog', { name: 'Confirm source file deletion' }).waitFor();
    await page.getByRole('button', { name: 'Cancel', exact: true }).click();
    const report = { status: 'passed', keepsSourceByDefault: true, secondConfirmation: true, cancellation: true, actualSourceDeletion: true, sharedSourceDetached: true, missingFileKeepsNotebook: true, unsavedSourceDisabled: true, opensExplorer: true, english: true };
    fs.writeFileSync('work/ui/desktop-files-v015-report.json', JSON.stringify(report, null, 2));
    console.log(report);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
