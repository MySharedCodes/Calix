import { useEffect, useRef, useState } from 'react';
import { BookOpen, Copy, FolderOpen, Pencil, Plus, Trash2, X } from 'lucide-react';
import type { Document } from './workspace';
import { t } from './i18n';

export function NotebookManager({ documents, active, disabled, desktop, onSelect, onNew, onRename, onCopy, onDelete, onReveal }: {
  documents: Document[]; active: string; disabled: boolean; onSelect: (id: string) => void; onNew: () => void;
  desktop: boolean; onRename: (id: string, title: string) => void; onCopy: (doc: Document) => void;
  onDelete: (doc: Document, deleteFile: boolean) => Promise<void>; onReveal: (doc: Document) => void;
}) {
  const [dialog, setDialog] = useState<{ doc: Document; type: 'rename' | 'delete' } | null>(null);
  const [name, setName] = useState('');
  const [deleteFile, setDeleteFile] = useState(false);
  const [confirmFile, setConfirmFile] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const close = () => { if (!pending) setDialog(null); };
  const list = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const container = list.current, selected = container?.querySelector('.selected');
    if (!container || !selected) return;
    const bounds = container.getBoundingClientRect(), row = selected.getBoundingClientRect();
    if (row.bottom > bounds.bottom) container.scrollTop += row.bottom - bounds.bottom;
    else if (row.top < bounds.top) container.scrollTop += row.top - bounds.top;
  }, [active]);
  return <>
    <div className="notebook-list-heading"><span>{t('笔记管理')}</span><button title={t('新建笔记')} className="icon-button" disabled={disabled} onClick={onNew}><Plus size={15} /></button></div>
    <div className="notebook-list" aria-label={t('笔记管理')} ref={list}>
      {documents.map(doc => <div className={`notebook-row ${doc.id === active ? 'selected' : ''}`} key={doc.id}>
        <button className="notebook-select" title={doc.title} disabled={disabled} onClick={() => onSelect(doc.id)}><BookOpen size={14} /><span>{doc.title}</span></button>
        <div className="notebook-row-actions">
          <button title={t('打开文件位置')} disabled={disabled} onClick={() => onReveal(doc)}><FolderOpen size={12} /></button>
          <button title={t('重命名笔记')} disabled={disabled} onClick={() => { setConfirmFile(false); setError(''); setDialog({ doc, type: 'rename' }); setName(doc.title); }}><Pencil size={12} /></button>
          <button title={t('复制笔记')} disabled={disabled} onClick={() => onCopy(doc)}><Copy size={12} /></button>
          <button title={t('移除笔记')} disabled={disabled} onClick={() => { setDeleteFile(false); setConfirmFile(false); setError(''); setDialog({ doc, type: 'delete' }); }}><Trash2 size={12} /></button>
        </div>
      </div>)}
    </div>
    {dialog && <div className="modal-backdrop" onClick={close}><form className="settings-modal" role="dialog" aria-label={t(confirmFile ? '确认删除源文件' : dialog.type === 'rename' ? '重命名笔记' : '移除笔记')} onClick={event => event.stopPropagation()} onSubmit={async event => {
      event.preventDefault();
      if (pending) return;
      if (dialog.type === 'rename') { if (!name.trim()) return; onRename(dialog.doc.id, name.trim()); setDialog(null); return; }
      if (deleteFile && !confirmFile) { setConfirmFile(true); return; }
      setPending(true); setError('');
      try { await onDelete(dialog.doc, deleteFile); setDialog(null); }
      catch (error) { setError(String(error)); }
      finally { setPending(false); }
    }}>
      <div className="panel-heading"><strong>{t(confirmFile ? '确认删除源文件' : dialog.type === 'rename' ? '重命名笔记' : '移除笔记')}</strong><button type="button" title={t('关闭')} disabled={pending} onClick={close}><X size={16} /></button></div>
      {dialog.type === 'rename' ? <input className="notebook-rename" aria-label={t('笔记名称')} value={name} maxLength={100} onChange={event => setName(event.target.value)} autoFocus /> : <>
        <p className="notebook-delete-message">{dialog.doc.title}<br />{t(confirmFile ? '将永久删除以下源文件，不会放入回收站。此操作无法撤销。' : '仅移除工作空间中的副本，磁盘文件不受影响。')}</p>
        {dialog.doc.path && <p className="notebook-file-path">{dialog.doc.path}</p>}
        {!confirmFile && <label className="delete-file-option"><input type="checkbox" checked={deleteFile} disabled={!desktop || !dialog.doc.path} onChange={event => setDeleteFile(event.target.checked)} />{t('同时删除磁盘源文件')}</label>}
        {!dialog.doc.path && <p className="file-hint">{t('此笔记尚未保存到磁盘')}</p>}
        {!desktop && <p className="file-hint">{t('文件位置与源文件删除功能仅在桌面版可用')}</p>}
      </>}
      {error && <p className="error-message" role="alert">{error}</p>}
      <div className="dialog-actions"><button type="button" disabled={pending} onClick={close}>{t('取消')}</button><button type="submit" className={confirmFile ? 'danger-button' : 'primary-button'} disabled={pending || (dialog.type === 'rename' && !name.trim())}>{t(pending ? '处理中' : dialog.type === 'rename' ? '保存' : confirmFile ? '永久删除源文件' : deleteFile ? '下一步' : '移除')}</button></div>
    </form></div>}
  </>;
}
