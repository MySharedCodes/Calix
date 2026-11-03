import { t } from './i18n';
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Check, Pencil } from 'lucide-react';

export function MarkdownCell({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [editing, setEditing] = useState(!value.trim());
  return <div className="markdown-cell">
    <button className="markdown-toggle icon-button" title={editing ? t("预览文字单元") : t("编辑文字单元")} onClick={() => setEditing(!editing)}>{editing ? <Check size={16} /> : <Pencil size={16} />}</button>
    {editing ? <textarea aria-label={t("文字单元内容")} value={value} onChange={e => onChange(e.target.value)} onKeyDown={e => { if (e.shiftKey && e.key === 'Enter') { e.preventDefault(); setEditing(false); } }} autoFocus /> : <div className="markdown-content" onDoubleClick={() => setEditing(true)}><ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[[rehypeKatex, { trust: false, strict: 'ignore' }]]}>{value}</ReactMarkdown></div>}
  </div>;
}
