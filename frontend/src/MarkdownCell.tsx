import { t } from './i18n';
import { lazy, Suspense, useEffect, useLayoutEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { Check, Pencil, CodeXml } from 'lucide-react';
import { rehypeHeadingIds, safeFontSize, textSchema } from './text-document';
import './text-cell.css';
import { TextSymbolInput, textSymbolLatex, type SymbolAnchor } from './TextSymbolInput';

const RichTextEditor = lazy(() => import('./RichTextEditor'));

export function MarkdownCell({ cellId, value, onChange }: { cellId: string; value: string; onChange: (value: string) => void }) {
  const [editing, setEditing] = useState(!value.trim());
  const [source, setSource] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [symbols, setSymbols] = useState<SymbolAnchor | null>(null);
  const selection = useRef({ from: 0, to: 0 });
  const pendingCaret = useRef<number | null>(null);
  useLayoutEffect(() => {
    if (pendingCaret.current === null || !textarea.current) return;
    const position = pendingCaret.current; pendingCaret.current = null;
    textarea.current.focus(); textarea.current.setSelectionRange(position, position);
  });
  useEffect(() => {
    const preview = () => setEditing(false);
    const el = root.current;
    el?.addEventListener('calix-preview-text', preview);
    return () => el?.removeEventListener('calix-preview-text', preview);
  }, []);
  return <div className="markdown-cell" ref={root}>
    <div className="text-cell-actions">
      {editing && <button className="icon-button" title={t('Markdown 源码')} aria-pressed={source} onClick={() => setSource(!source)}><CodeXml size={16} /></button>}
      <button className="icon-button" title={editing ? t("预览文字单元") : t("编辑文字单元")} onClick={() => setEditing(!editing)}>{editing ? <Check size={16} /> : <Pencil size={16} />}</button>
    </div>
    {editing ? source ? <textarea ref={textarea} aria-label={t("文字单元内容")} maxLength={24000} value={value} onChange={e => onChange(e.target.value)} onKeyDown={e => {
      if (e.key === 'Escape' && !e.nativeEvent.isComposing) {
        e.preventDefault(); e.stopPropagation();
        selection.current = { from: e.currentTarget.selectionStart, to: e.currentTarget.selectionEnd };
        setSymbols(e.currentTarget.getBoundingClientRect());
      } else if (e.shiftKey && e.key === 'Enter') { e.preventDefault(); setEditing(false); }
    }} autoFocus /> : <Suspense fallback={null}><RichTextEditor value={value} onChange={onChange} /></Suspense> : <div className="markdown-content" onDoubleClick={() => setEditing(true)}><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeRaw, [rehypeSanitize, textSchema], [rehypeHeadingIds, { cellId }], [rehypeKatex, { trust: false, strict: 'ignore', maxExpand: 1000 }]]} components={{ span: ({ node, children, ...props }) => {
      const size = safeFontSize(node?.properties.dataCixSize);
      return <span {...props} style={size ? { fontSize: size } : props.style}>{children}</span>;
    } }}>{value}</ReactMarkdown></div>}
    {symbols && <TextSymbolInput anchor={symbols} onClose={() => { setSymbols(null); textarea.current?.focus(); }} onInsert={symbol => {
      const latex = textSymbolLatex(symbol);
      const text = latex ? `$${latex}$` : symbol.symbol || symbol.name;
      const { from, to } = selection.current;
      if (value.length - (to - from) + text.length > 24000) return;
      pendingCaret.current = from + text.length;
      onChange(value.slice(0, from) + text + value.slice(to)); setSymbols(null);
    }} />}
  </div>;
}
