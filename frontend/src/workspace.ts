import { useCallback, useEffect, useRef, useState } from 'react';
import type { Cell, NotebookFile } from './types';
import { t } from './i18n';
import { isRecoverableWorkspace, parseWorkspace, serializeWorkspace } from './workspace-codec';
import { emptyHistory, recordStructure, travel, type CellHistory } from './workspace-history';
import { persistLocal, persistDisk } from './recovery-store';

export type Document = NotebookFile & { id: string; path: string | null; updated: number; example?: string };
type Workspace = { version: 1; active: string; documents: Document[]; histories?: Record<string, CellHistory> };
const key = 'calix-workspace-v1';

export function useWorkspace(validate: (data: unknown) => NotebookFile, fallback: () => NotebookFile, onError: (error: string) => void) {
  const [workspace, setWorkspace] = useState<Workspace>(() => {
    try {
      let saved: Workspace | null = null;
      for (const name of [key, 'calix-workspace-backup-v1']) {
        try {
          const candidate = parseWorkspace(localStorage.getItem(name) || 'null') as Workspace | null;
          if (isRecoverableWorkspace(candidate)) { saved = candidate; break; }
        } catch { /* Try the preceding local checkpoint. */ }
      }
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
  const checkpoint = useRef(false);
  const persist = useCallback(() => {
    const value = { version: 1, active: latest.current.active, documents: latest.current.documents };
    const force = checkpoint.current; checkpoint.current = false;
    try {
      persistLocal(serializeWorkspace(value), force);
      localStorage.removeItem('calix-notebook-v1');
    } catch {
      onError('工作空间存储已满，请将笔记保存到文件');
    }
    void persistDisk(value, force).catch(() => onError('磁盘恢复副本写入失败，请将笔记保存到文件'));
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
    checkpoint.current = true;
    const histories = { ...previous.histories }; delete histories[id];
    const documents = previous.documents.filter(doc => doc.id !== id);
    if (!documents.length) {
      const fresh = crypto.randomUUID();
      documents.push({ format: 'calix-notebook', version: 1, id: fresh, path: null, updated: Date.now(), title: t('未命名笔记'), cells: [{ id: crypto.randomUUID(), mode: 'source', code: '' }] });
    }
    return { ...previous, documents, histories, active: previous.active === id ? documents[0].id : previous.active };
  }), []);
  const current = workspace.documents.find(doc => doc.id === workspace.active)!;
  const setCells = useCallback((value: Cell[] | ((cells: Cell[]) => Cell[])) => {
    setWorkspace(previous => {
      const doc = previous.documents.find(item => item.id === previous.active)!;
      const cells = typeof value === 'function' ? value(doc.cells) : value;
      if (!cells.length || cells.length > 200) { onError('笔记最多包含 200 个单元'); return previous; }
      const before = previous.histories?.[doc.id] || emptyHistory();
      const history = recordStructure(doc.cells, cells, before);
      if (history.past !== before.past) checkpoint.current = true;
      return { ...previous, documents: previous.documents.map(item => item.id === doc.id ? { ...doc, cells, updated: Date.now() } : item), histories: { ...previous.histories, [doc.id]: history } };
    });
  }, [onError]);
  const navigateHistory = useCallback((direction: 'undo' | 'redo') => {
    checkpoint.current = true;
    setWorkspace(previous => {
      const doc = previous.documents.find(item => item.id === previous.active)!;
      const result = travel(doc.cells, previous.histories?.[doc.id] || emptyHistory(), direction);
      return { ...previous, documents: previous.documents.map(item => item.id === doc.id ? { ...doc, cells: result.cells, updated: Date.now() } : item), histories: { ...previous.histories, [doc.id]: result.history } };
    });
  }, []);
  return { ...workspace, current, setCells, update, create, activate, remove, navigateHistory,
    canUndo: !!workspace.histories?.[workspace.active]?.past.length, canRedo: !!workspace.histories?.[workspace.active]?.future.length };
}
