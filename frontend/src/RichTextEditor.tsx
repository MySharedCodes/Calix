import { useEffect, useRef, useState } from 'react';
import { EditorContent, useEditor, useEditorState } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Markdown } from '@tiptap/markdown';
import { TextStyle } from '@tiptap/extension-text-style';
import { TableKit } from '@tiptap/extension-table';
import Mathematics from '@tiptap/extension-mathematics';
import { Bold, Italic, Underline, Strikethrough, List, ListOrdered, Undo2, Redo2, RemoveFormatting, Sigma, Check, X } from 'lucide-react';
import { t } from './i18n';
import { fontSizes, safeFontSize } from './text-document';

const SizedText = TextStyle.extend({
  addAttributes() {
    return {
      fontSize: {
        default: null,
        parseHTML: element => safeFontSize(element.getAttribute('data-cix-size') ?? element.style.fontSize) ?? null,
        renderHTML: attrs => {
          const size = safeFontSize(attrs.fontSize);
          return size ? { 'data-cix-size': String(size), style: `font-size:${size}px` } : {};
        },
      },
    };
  },
  renderMarkdown: (node, helpers) => {
    const text = helpers.renderChildren(node);
    const size = safeFontSize(node.attrs?.fontSize);
    return size ? `<span data-cix-size="${size}">${text}</span>` : text;
  },
});

export default function RichTextEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const latest = useRef(value);
  const change = useRef(onChange); change.current = onChange;
  const [limit, setLimit] = useState(false);
  const [formula, setFormula] = useState<{ latex: string; pos?: number; block?: boolean } | null>(null);
  const editor = useEditor({
    extensions: [StarterKit.configure({ link: { openOnClick: false }, heading: { levels: [1, 2, 3, 4, 5, 6] } }),
      SizedText, TableKit, Markdown,
      Mathematics.configure({
        katexOptions: { trust: false, strict: 'ignore', throwOnError: false, maxExpand: 1000 },
        inlineOptions: { onClick: (node, pos) => setFormula({ latex: node.attrs.latex, pos }) },
        blockOptions: { onClick: (node, pos) => setFormula({ latex: node.attrs.latex, pos, block: true }) },
      })],
    content: value,
    contentType: 'markdown',
    autofocus: 'end',
    editorProps: { attributes: { 'aria-label': t('文字单元内容'), class: 'markdown-content rich-text-content', role: 'textbox', 'aria-multiline': 'true' } },
    onUpdate: ({ editor }) => {
      const next = editor.getMarkdown();
      if (next.length > 24000) {
        setLimit(true);
        editor.commands.setContent(latest.current, { contentType: 'markdown', emitUpdate: false });
        return;
      }
      latest.current = next;
      setLimit(false);
      change.current(next);
    },
  });
  useEffect(() => {
    if (editor && value !== latest.current) {
      latest.current = value;
      editor.commands.setContent(value, { contentType: 'markdown', emitUpdate: false });
    }
  }, [editor, value]);
  const state = useEditorState({ editor, selector: ({ editor }) => editor ? {
    level: editor.isActive('heading') ? editor.getAttributes('heading').level : 0,
    size: editor.getAttributes('textStyle').fontSize ?? '',
    bold: editor.isActive('bold'), italic: editor.isActive('italic'), underline: editor.isActive('underline'),
    strike: editor.isActive('strike'), bullet: editor.isActive('bulletList'), ordered: editor.isActive('orderedList'),
    undo: editor.can().undo(), redo: editor.can().redo(),
  } : null });
  if (!editor || !state) return null;
  const tools = [
    [t('粗体'), Bold, state.bold, () => editor.chain().focus().toggleBold().run()],
    [t('斜体'), Italic, state.italic, () => editor.chain().focus().toggleItalic().run()],
    [t('下划线'), Underline, state.underline, () => editor.chain().focus().toggleUnderline().run()],
    [t('删除线'), Strikethrough, state.strike, () => editor.chain().focus().toggleStrike().run()],
    [t('项目符号'), List, state.bullet, () => editor.chain().focus().toggleBulletList().run()],
    [t('编号列表'), ListOrdered, state.ordered, () => editor.chain().focus().toggleOrderedList().run()],
  ] as const;
  return <div className="rich-text-editor">
    <div className="text-format-toolbar" role="toolbar" aria-label={t('文字格式')}>
      <select aria-label={t('段落样式')} value={state.level} onChange={e => {
        const level = Number(e.target.value) as 1 | 2 | 3 | 4 | 5 | 6;
        if (level) editor.chain().focus().setHeading({ level }).run(); else editor.chain().focus().setParagraph().run();
      }}><option value={0}>{t('正文')}</option>{[1, 2, 3, 4, 5, 6].map(n => <option key={n} value={n}>{t('标题')} {n}</option>)}</select>
      <select aria-label={t('字号')} value={state.size} onChange={e => {
        const fontSize = safeFontSize(e.target.value) ?? null;
        editor.chain().focus().setMark('textStyle', { fontSize }).run();
      }}><option value="">{t('默认字号')}</option>{fontSizes.map(n => <option key={n} value={n}>{n} px</option>)}</select>
      {tools.map(([label, Icon, active, action]) => <button key={label} title={label} aria-label={label} aria-pressed={active} onMouseDown={e => e.preventDefault()} onClick={action}><Icon size={16} /></button>)}
      <button title={t('清除格式')} onMouseDown={e => e.preventDefault()} onClick={() => editor.chain().focus().unsetAllMarks().clearNodes().run()}><RemoveFormatting size={16} /></button>
      <button title={t('插入公式')} onMouseDown={e => e.preventDefault()} onClick={() => setFormula({ latex: '' })}><Sigma size={16} /></button>
      <button title={t('撤销')} disabled={!state.undo} onClick={() => editor.chain().focus().undo().run()}><Undo2 size={16} /></button>
      <button title={t('重做')} disabled={!state.redo} onClick={() => editor.chain().focus().redo().run()}><Redo2 size={16} /></button>
    </div>
    {formula && <form className="text-formula-editor" onSubmit={e => {
      e.preventDefault();
      if (formula.pos !== undefined) {
        if (formula.block) editor.commands.updateBlockMath({ pos: formula.pos, latex: formula.latex });
        else editor.commands.updateInlineMath({ pos: formula.pos, latex: formula.latex });
      } else editor.chain().focus().insertInlineMath({ latex: formula.latex }).run();
      setFormula(null);
    }}><input autoFocus aria-label={t('公式输入')} value={formula.latex} onChange={e => setFormula({ ...formula, latex: e.target.value })} maxLength={4000} /><button title={t('插入')} type="submit"><Check size={16} /></button><button title={t('取消')} type="button" onClick={() => setFormula(null)}><X size={16} /></button></form>}
    <EditorContent editor={editor} />
    {limit && <div role="alert">{t('文字单元最多 24000 个字符')}</div>}
  </div>;
}
