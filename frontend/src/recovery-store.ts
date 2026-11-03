import { isRecoverableWorkspace, parseWorkspace, serializeWorkspace } from './workspace-codec';

export type Revision = { id: string; modified: number; bytes: number };
const key = 'calix-workspace-v1';
const backup = 'calix-workspace-backup-v1';
let running: Promise<void> | null = null;
let pending: { content: string; checkpoint: boolean } | null = null;
export function persistLocal(content: string, checkpoint = false) {
  const previous = localStorage.getItem(key);
  if (previous && previous !== content && (checkpoint || !localStorage.getItem(backup))) {
    try { localStorage.setItem(backup, previous); } catch { /* Preserve the primary copy when the backup quota is full. */ }
  }
  localStorage.setItem(key, content);
}
export function persistDisk(workspace: unknown, checkpoint: boolean): Promise<void> {
  if (!('__TAURI_INTERNALS__' in window)) return Promise.resolve();
  pending = { content: JSON.stringify(workspace), checkpoint: checkpoint || !!pending?.checkpoint };
  if (running) return running;
  running = (async () => {
    const { invoke } = await import('@tauri-apps/api/core');
    while (pending) {
      const next = pending; pending = null;
      await invoke('write_recovery', next);
    }
  })().finally(() => { running = null; });
  return running;
}
export async function listRecovery(): Promise<Revision[]> {
  if ('__TAURI_INTERNALS__' in window) {
    const { invoke } = await import('@tauri-apps/api/core');
    return invoke('list_recovery');
  }
  const value = localStorage.getItem(backup);
  return value ? [{ id: 'browser-backup', modified: 0, bytes: new Blob([value]).size }] : [];
}
export async function readRecovery(id: string): Promise<unknown> {
  if ('__TAURI_INTERNALS__' in window) {
    const { invoke } = await import('@tauri-apps/api/core');
    return JSON.parse(await invoke<string>('read_recovery', { id }));
  }
  if (id !== 'browser-backup') throw new Error('Invalid recovery revision');
  return parseWorkspace(localStorage.getItem(backup) || 'null');
}
export async function listFileVersions(path: string): Promise<Revision[]> {
  const { invoke } = await import('@tauri-apps/api/core');
  return invoke('list_file_versions', { path });
}
export async function readFileVersion(path: string, id: string): Promise<unknown> {
  const { invoke } = await import('@tauri-apps/api/core');
  return JSON.parse(await invoke<string>('read_file_version', { path, id }));
}
export async function restoreDiskWorkspace() {
  if (!('__TAURI_INTERNALS__' in window)) return;
  try {
    const existing = parseWorkspace(localStorage.getItem(key) || 'null') as { version?: number; documents?: unknown[] } | null;
    if (isRecoverableWorkspace(existing)) return;
  } catch { /* Recover from the on-disk copy if browser storage is missing or damaged. */ }
  for (const revision of await listRecovery()) {
    try {
      const workspace = await readRecovery(revision.id) as { version?: number; documents?: unknown[] } | null;
      if (isRecoverableWorkspace(workspace)) {
        localStorage.setItem(key, serializeWorkspace(workspace));
        return;
      }
    } catch { /* An older revision can still be usable. */ }
  }
}
