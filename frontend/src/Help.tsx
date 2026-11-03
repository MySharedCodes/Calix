import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { BookOpen, Search, X } from 'lucide-react';
import { t, useLanguage } from './i18n';
import overview from '../../README.md?raw';
import start from '../../docs/GETTING-STARTED.md?raw';
import englishStart from '../../docs/GETTING-STARTED.en.md?raw';
import guide from '../../docs/USER-GUIDE.md?raw';
import troubleshooting from '../../docs/TROUBLESHOOTING.md?raw';
import examples from '../../docs/EXAMPLES.md?raw';
import installation from '../../docs/INSTALLATION.md?raw';
import syntax from '../../docs/SUPPORTED-SYNTAX.md?raw';
import units from '../../docs/STATISTICS-AND-UNITS.md?raw';
import pde from '../../docs/PDE.md?raw';
import cpu from '../../docs/CPU-ACCELERATION.md?raw';
import api from '../../API.md?raw';
import ai from '../../AI-CONTROL.md?raw';
import development from '../../docs/DEVELOPMENT.md?raw';
import contributing from '../../CONTRIBUTING.md?raw';
import security from '../../SECURITY.md?raw';
import index from '../../docs/README.md?raw';

// Resolve relative links using their source document, including files outside docs/.
const supplements = import.meta.glob([
  '../../README.zh-CN.md', '../../LICENSE', '../../docs/ROADMAP.md',
  '../../docs/RELEASING.md', '../../docs/BUILD-NOTES.md',
  '../../docs/LICENSE-REVIEW.md', '../../docs/CHANGES-0.1.27.md',
], { query: '?raw', import: 'default' });
const notebooks = import.meta.glob('../../examples/*.calix', { query: '?raw', import: 'default' });
const pictures = import.meta.glob('../../docs/images/*.png', { eager: true, query: '?url', import: 'default' });
const articles = [
  ['docs/GETTING-STARTED.md', '快速上手', start],
  ['docs/GETTING-STARTED.en.md', 'Get Started (EN)', englishStart],
  ['docs/USER-GUIDE.md', '使用帮助', guide],
  ['docs/TROUBLESHOOTING.md', '故障排查', troubleshooting],
  ['docs/EXAMPLES.md', '案例目录', examples],
  ['docs/INSTALLATION.md', '安装说明', installation],
  ['README.md', 'English Overview', overview],
  ['docs/SUPPORTED-SYNTAX.md', 'Syntax Reference (EN)', syntax],
  ['docs/STATISTICS-AND-UNITS.md', 'Statistics & Units (EN)', units],
  ['docs/PDE.md', 'PDE module (EN)', pde],
  ['docs/CPU-ACCELERATION.md', 'CPU & SIMD (EN)', cpu],
  ['AI-CONTROL.md', 'AI Control (EN)', ai],
  ['API.md', 'CLI / API (EN)', api],
  ['docs/DEVELOPMENT.md', '开发与构建', development],
  ['CONTRIBUTING.md', 'Contributing (EN)', contributing],
  ['SECURITY.md', 'Security (EN)', security],
  ['docs/README.md', '文档目录', index],
].map(([path, title, source]) => ({ path, title, source }));

const slug = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}_\s-]/gu, '').trim().replace(/\s/g, '-');

export default function Help({ onClose, onNotebook }: { onClose: () => void; onNotebook: (source: string) => Promise<void> }) {
  const language = useLanguage();
  const [article, setArticle] = useState(articles.find(item => item.path === (language === 'zh' ? 'docs/GETTING-STARTED.md' : 'docs/GETTING-STARTED.en.md'))!);
  const [query, setQuery] = useState('');
  const [message, setMessage] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const content = useRef<HTMLElement>(null);
  const pending = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    const previous = document.activeElement as HTMLElement | null;
    const scroll = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.showModal();
    searchInput.current?.focus();
    return () => {
      mounted.current = false;
      document.body.style.overflow = scroll;
      previous?.focus({ preventScroll: true });
    };
  }, []);

  useEffect(() => { content.current?.scrollTo(0, 0); }, [article]);
  const select = (next: typeof article) => { setArticle(next); setMessage(''); };
  const matches = articles.filter(item => `${item.title}\n${item.source}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()));
  const resolve = (href: string) => new URL(href, `https://calix.local/${article.path}`);
  const navigate = async (href: string) => {
    if (pending.current) return;
    pending.current = true;
    try {
      const target = resolve(href);
      const path = decodeURIComponent(target.pathname.slice(1));
      if (path !== article.path) {
        const known = articles.find(item => item.path === path);
        if (known) select(known);
        else {
          if (pictures[`../../${path}`]) { select({ path, title: path, source: `![Calix](/${path})` }); return; }
          const loader = supplements[`../../${path}`] || notebooks[`../../${path}`];
          if (!loader) { setMessage(`${t('文件位置')}：${path}`); return; }
          const source = String(await loader());
          if (!mounted.current) return;
          if (path.startsWith('examples/')) { await onNotebook(source); onClose(); return; }
          select({ path, title: path, source });
        }
      }
      if (target.hash) requestAnimationFrame(() => {
        const id = decodeURIComponent(target.hash.slice(1));
        const node = Array.from(content.current?.querySelectorAll('[id]') || []).find(el => el.id === id);
        node?.scrollIntoView({ block: 'start' });
      });
    } catch (error) { if (mounted.current) setMessage(String(error)); }
    finally { pending.current = false; }
  };

  return <dialog ref={dialog} className="help-dialog" aria-labelledby="help-title" onCancel={event => { event.preventDefault(); onClose(); }} onKeyDown={event => {
    if (event.key === 'F1') { event.preventDefault(); event.stopPropagation(); }
    if (event.ctrlKey && ['s','o'].includes(event.key.toLowerCase())) { event.preventDefault(); event.stopPropagation(); }
  }}>
    <div className="help-header"><BookOpen size={19}/><strong id="help-title">{t('帮助')} · Calix</strong><span>0.1.27</span><button className="icon-button" aria-label={t('关闭帮助')} onClick={onClose}><X size={19}/></button></div>
    <div className="help-layout">
      <nav className="help-navigation" aria-label={t('帮助目录')}>
        <label className="help-search"><Search size={16}/><input ref={searchInput} value={query} onChange={event => setQuery(event.target.value)} placeholder={t('搜索帮助')} aria-label={t('搜索帮助')}/></label>
        <div className="help-topics">{matches.map(item => <button key={item.path} aria-current={article.path === item.path ? 'page' : undefined} onClick={() => select(item)}>{t(item.title)}</button>)}{!matches.length && <p role="status">{t('没有匹配的文档')}</p>}</div>
      </nav>
      <article className="help-content markdown-content" ref={content} tabIndex={0} aria-label={t('帮助正文')}>
        <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[[rehypeKatex, { trust: false, strict: 'ignore' }]]} components={{
          h1: ({ children }) => <h1 id={slug(String(children))}>{children}</h1>,
          h2: ({ children }) => <h2 id={slug(String(children))}>{children}</h2>,
          h3: ({ children }) => <h3 id={slug(String(children))}>{children}</h3>,
          a: ({ href, children }) => {
            if (!href) return <span>{children}</span>;
            if (/^https?:\/\//i.test(href)) return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
            if (/^[a-z][a-z0-9+.-]*:/i.test(href)) return <span>{children}</span>;
            return <a href={href} onClick={event => { event.preventDefault(); void navigate(href); }}>{children}</a>;
          },
          img: ({ src, alt }) => {
            const path = src ? decodeURIComponent(resolve(src).pathname.slice(1)) : '';
            const picture = pictures[`../../${path}`];
            return picture ? <img src={String(picture)} alt={alt} loading="lazy"/> : <span>{alt}</span>;
          },
        }}>{article.source}</ReactMarkdown>
      </article>
    </div>
    <div className="help-footer" role="status">{message || article.path}</div>
  </dialog>;
}
