import { strFromU8, strToU8, zlibSync, unzlibSync } from 'fflate';

const prefix = 'calix-zlib-v1:';

export function isRecoverableWorkspace(value: unknown): boolean {
  if (!value || typeof value !== 'object') return false;
  const workspace = value as { version?: number; documents?: unknown[] };
  if (workspace.version !== 1 || !Array.isArray(workspace.documents) || !workspace.documents.length || workspace.documents.length > 100) return false;
  const ids = new Set<string>();
  return workspace.documents.every(value => {
    if (!value || typeof value !== 'object') return false;
    const doc = value as { id?: string; format?: string; version?: number; title?: string; cells?: unknown[] };
    if (typeof doc.id !== 'string' || !/^[\w-]{1,80}$/.test(doc.id) || ids.has(doc.id)) return false;
    ids.add(doc.id);
    return doc.format === 'calix-notebook' && doc.version === 1 && typeof doc.title === 'string' && doc.title.length <= 200 &&
      Array.isArray(doc.cells) && doc.cells.length > 0 && doc.cells.length <= 200 && doc.cells.every(value => {
        if (!value || typeof value !== 'object') return false;
        const cell = value as { mode?: string; code?: string; latex?: string };
        return ['source', 'math', 'markdown'].includes(cell.mode || '') && typeof cell.code === 'string' && cell.code.length <= 24000 &&
          (cell.latex === undefined || typeof cell.latex === 'string' && cell.latex.length <= 24000);
      });
  });
}

export function serializeWorkspace(value: unknown): string {
  const json = JSON.stringify(value);
  if (json.length < 1_000_000) return json;
  const bytes = zlibSync(strToU8(json), { level: 1 });
  let binary = '';
  for (let i = 0; i < bytes.length; i += 32768) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 32768));
  }
  return prefix + btoa(binary);
}

export function parseWorkspace(value: string): unknown {
  if (!value.startsWith(prefix)) return JSON.parse(value);
  const bytes = Uint8Array.from(atob(value.slice(prefix.length)), c => c.charCodeAt(0));
  const inflated = unzlibSync(bytes);
  return JSON.parse(strFromU8(inflated));
}
