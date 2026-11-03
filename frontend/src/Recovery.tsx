import { useEffect, useRef, useState } from 'react';
import { History, X } from 'lucide-react';
import { listRecovery, readRecovery, listFileVersions, readFileVersion, type Revision } from './recovery-store';
import type { NotebookFile } from './types';
import { t } from './i18n';

export default function Recovery({ onClose, onRestore, filePath }: { onClose: () => void; onRestore: (notebook: unknown) => void; filePath: string | null }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [revisions, setRevisions] = useState<Revision[]>([]);
  const [selected, setSelected] = useState('');
  const [documents, setDocuments] = useState<NotebookFile[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const generation = useRef(0);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    let cancelled = false;
    void Promise.allSettled([listRecovery(), filePath && '__TAURI_INTERNALS__' in window ? listFileVersions(filePath) : Promise.resolve([])]).then(results => {
      if (cancelled) return;
      setRevisions(results.flatMap((result, index) => result.status === 'fulfilled' ? result.value.map(item => ({ ...item, id: (index ? 'file:' : 'workspace:') + item.id })) : []));
      const failed = results.find(result => result.status === 'rejected');
      if (failed?.status === 'rejected') setError(String(failed.reason));
    }).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; ++generation.current; previous?.focus({ preventScroll: true }); };
  }, []);
  const select = async (id: string) => {
    const request = ++generation.current;
    setSelected(id); setError(''); setDocuments([]); setLoading(true);
    try {
      const file = id.startsWith('file:');
      const revision = id.slice(id.indexOf(':') + 1);
      const value = file ? { version: 1, documents: [await readFileVersion(filePath!, revision)] } : await readRecovery(revision) as { version?: number; documents?: NotebookFile[] };
      if (request !== generation.current) return;
      if (value?.version !== 1 || !Array.isArray(value.documents) || value.documents.length > 100) throw new Error(t('恢复数据无效'));
      setDocuments((value.documents as NotebookFile[]).filter(doc => doc && typeof doc.title === 'string' && Array.isArray(doc.cells)));
    } catch (error) { if (request === generation.current) setError(String(error)); }
    finally { if (request === generation.current) setLoading(false); }
  };
  return <dialog ref={dialog} className="recovery-dialog" aria-label={t('恢复历史')} onCancel={event => { event.preventDefault(); onClose(); }}>
    <div className="panel-heading"><History size={18}/><strong>{t('恢复历史')}</strong><button className="icon-button" aria-label={t('关闭')} onClick={onClose}><X size={18}/></button></div>
    <div className="recovery-layout"><nav aria-label={t('恢复版本')}>{revisions.map(item => <button key={item.id} aria-current={item.id === selected ? 'page' : undefined} onClick={() => void select(item.id)}><span>{item.modified ? new Date(item.modified).toLocaleString() : t('浏览器备份')}</span><small>{t(item.id.startsWith('file:') ? '文件历史' : '工作空间')} · {(item.bytes / 1024).toFixed(1)} KB{item.id.endsWith(':latest.data') ? ` · ${t('最近副本')}` : ''}</small></button>)}</nav>
    <div className="recovery-notebooks">{documents.map((doc, index) => <button key={index} onClick={() => { try { onRestore(doc); onClose(); } catch (error) { setError(String(error)); } }}><History size={17}/><span>{typeof doc.title === 'string' ? doc.title : t('未命名笔记')}</span></button>)}{!loading && !documents.length && <p>{t(revisions.length ? '选择恢复版本' : '暂无恢复历史')}</p>}{loading && <p>{t('处理中')}</p>}{error && <p className="error-message" role="alert">{error}</p>}</div></div>
  </dialog>;
}
