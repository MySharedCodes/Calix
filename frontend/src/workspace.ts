import { useCallback, useEffect, useRef, useState } from 'react';
import type { Cell, NotebookFile } from './types';
import { t } from './i18n';
import { parseWorkspace, serializeWorkspace } from './workspace-codec';

export type Document = NotebookFile & { id: string; path: string | null; updated: number; example?: string };
type Workspace = { version: 1; active: string; documents: Document[] };
const key = 'calix-workspace-v1';

export function useWorkspace(validate: (data: unknown) => NotebookFile, fallback: () => NotebookFile, onError: (error: string) => void) {
  const [workspace, setWorkspace] = useState<Workspace>(() => {
    try {
      const saved = parseWorkspace(localStorage.getItem(key) || 'null') as Workspace | null;
      if (saved?.version === 1 && Array.isArray(saved.documents) && saved.documents.length && saved.documents.length <= 100) {
        const ids = new Set<string>();
        const documents = saved.documents.map(doc => {
          if (typeof doc.id !== 'string' || !/^[\w-]{1,80}$/.test(doc.id) || ids.has(doc.id)) throw new Error('Invalid notebook ID');
          ids.add(doc.id);
          return { ...validate(doc), id: doc.id, path: typeof doc.path === 'string' ? doc.path : null, updated: Number(doc.updated) || Date.now(), example: typeof doc.example === 'string' ? doc.example : undefined };
        });
        return { version: 1, active: ids.has(saved.active) ? saved.active : documents[0].id, documents };
      }
    } catch { /* The legacy autosave remains a recovery source. */ }
    const id = crypto.randomUUID();
    return { version: 1, active: id, documents: [{ ...fallback(), id, path: null, updated: Date.now() }] };
  });
  const latest = useRef(workspace); latest.current = workspace;
  const persist = useCallback(() => {
    let legacy: string | null = null;
    try {
      // Migrate the old single-notebook backup without storing large outputs twice.
      legacy = localStorage.getItem('calix-notebook-v1');
      localStorage.removeItem('calix-notebook-v1');
      localStorage.setItem(key, serializeWorkspace(latest.current));
    } catch {
      if (legacy !== null) { try { localStorage.setItem('calix-notebook-v1', legacy); } catch { /* The prior workspace remains intact. */ } }
      onError('工作空间存储已满，请将笔记保存到文件');
    }
  }, [onError]);
  useEffect(() => { const timer = setTimeout(persist, 400); return () => clearTimeout(timer); }, [workspace, persist]);
  useEffect(() => {
    const visibility = () => { if (document.hidden) persist(); };
    window.addEventListener('pagehide', persist); document.addEventListener('visibilitychange', visibility);
    return () => { window.removeEventListener('pagehide', persist); document.removeEventListener('visibilitychange', visibility); };
  }, [persist]);
  const update = useCallback((patch: Partial<Document> | ((doc: Document) => Partial<Document>), id?: string) => {
    setWorkspace(previous => ({ ...previous, documents: previous.documents.map(doc => doc.id === (id || previous.active) ? { ...doc, ...(typeof patch === 'function' ? patch(doc) : patch), updated: Date.now() } : doc) }));
  }, []);
  const create = useCallback((notebook: NotebookFile, path: string | null = null, example?: string) => {
    const id = crypto.randomUUID();
    setWorkspace(previous => {
      if (previous.documents.length >= 100) { onError('最多保留 100 个笔记，请先导出并移除部分笔记'); return previous; }
      return { ...previous, active: id, documents: [...previous.documents, { ...notebook, id, path, updated: Date.now(), example }] };
    });
  }, [onError]);
  const activate = useCallback((id: string) => setWorkspace(previous => previous.documents.some(doc => doc.id === id) ? { ...previous, active: id } : previous), []);
  const remove = useCallback((id: string) => setWorkspace(previous => {
    const documents = previous.documents.filter(doc => doc.id !== id);
    if (!documents.length) {
      const fresh = crypto.randomUUID();
      documents.push({ format: 'calix-notebook', version: 1, id: fresh, path: null, updated: Date.now(), title: t('未命名笔记'), cells: [{ id: crypto.randomUUID(), mode: 'source', code: '' }] });
    }
    return { ...previous, documents, active: previous.active === id ? documents[0].id : previous.active };
  }), []);
  const current = workspace.documents.find(doc => doc.id === workspace.active)!;
  const setCells = useCallback((value: Cell[] | ((cells: Cell[]) => Cell[])) => update(doc => ({ cells: typeof value === 'function' ? value(doc.cells) : value })), [update]);
  return { ...workspace, current, setCells, update, create, activate, remove };
}
