import { useEffect, useMemo, useRef, useState } from 'react';
import { ListTree, Search, X } from 'lucide-react';
import { textHeadings, type NotebookHeading } from './text-document';
import type { Cell } from './types';
import { t } from './i18n';

export function NotebookContents({ cells, notebookId, onNavigate }: { cells: Cell[]; notebookId: string; onNavigate: (cellId: string) => void }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState('');
  const root = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const cache = useRef(new Map<string, { source: string; headings: NotebookHeading[] }>());
  const headings = useMemo(() => {
    const next = new Map<string, { source: string; headings: NotebookHeading[] }>();
    const all = cells.filter(cell => cell.mode === 'markdown').flatMap(cell => {
      const previous = cache.current.get(cell.id);
      const entry = previous?.source === cell.code ? previous : { source: cell.code, headings: textHeadings(cell.code, cell.id) };
      next.set(cell.id, entry);
      return entry.headings;
    });
    cache.current = next;
    return all;
  }, [cells]);
  const hasHeadings = headings.length > 0;
  useEffect(() => { setQuery(''); setActive(''); }, [notebookId]);
  useEffect(() => {
    setOpen(hasHeadings && window.matchMedia('(min-width: 1000px)').matches);
  }, [notebookId, hasHeadings]);
  useEffect(() => {
    if (!open) return;
    search.current?.focus({ preventScroll: true });
    if (!window.matchMedia('(min-width: 1000px)').matches) root.current?.scrollIntoView({ behavior: 'instant', block: 'start' });
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); button.current?.focus(); } };
    document.addEventListener('keydown', escape);
    return () => { document.removeEventListener('keydown', escape); };
  }, [open]);
  if (!headings.length) return null;
  const filtered = headings.filter(heading => heading.title.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const navigate = (heading: NotebookHeading) => {
    onNavigate(heading.cellId);
    document.getElementById(heading.cellId)?.querySelector('.markdown-cell')?.dispatchEvent(new Event('calix-preview-text'));
    setActive(heading.id);
    if (!window.matchMedia('(min-width: 1000px)').matches) setOpen(false);
    // Preview must commit before an editing cell's heading is available.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      const target = document.getElementById(heading.id) ?? document.getElementById(heading.cellId);
      target?.scrollIntoView({ behavior: 'instant', block: 'start' });
      target?.focus({ preventScroll: true });
    }));
  };
  return <div className={`notebook-contents ${open ? 'is-open' : 'is-closed'}`} ref={root}>
    <section className="contents-panel" aria-label={t('笔记本目录')} aria-hidden={!open} inert={!open}>
      <div className="contents-heading"><strong>{t('目录')}</strong><span>{headings.length}</span><button title={t('关闭目录')} onClick={() => { setOpen(false); button.current?.focus(); }}><X size={17} /></button></div>
      <label className="contents-search"><Search size={16} /><input ref={search} aria-label={t('搜索标题')} placeholder={t('搜索标题')} value={query} onChange={e => setQuery(e.target.value)} /></label>
      <nav aria-label={t('标题列表')}>{filtered.map(heading => <button key={heading.id} aria-current={active === heading.id ? 'location' : undefined} style={{ paddingInlineStart: 12 + (heading.level - 1) * 12 }} onClick={() => navigate(heading)}><span className="contents-level">H{heading.level}</span><span>{heading.title || t('未命名标题')}</span></button>)}{!filtered.length && <p>{t('没有匹配的标题')}</p>}</nav>
    </section>
    <button ref={button} className="contents-fab" title={t('打开目录')} aria-label={t('打开目录')} aria-expanded={open} onClick={() => setOpen(!open)}><ListTree size={21} /><span>{t('目录')}</span><span className="contents-count">{headings.length}</span></button>
  </div>;
}
