import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, Calculator, Plus, Play, Square, RotateCcw, FolderOpen, Save, SaveAll, ChevronDown, Trash2, Copy, ArrowDownToLine, ArrowUp, ArrowDown, Check, X, PanelLeftClose, PanelLeftOpen, Sigma, FunctionSquare, Settings2, FilePlus2, LoaderCircle } from 'lucide-react';
import katex from 'katex';
import { Editor, assertCompleteInput } from './Editor';
import { Plot } from './Plot';
import { Animation } from './Animation';
import { ScientificScene } from './ScientificScene';
import { FieldScene } from './FieldScene';
import * as api from './api';
import type { Cell, Result, NotebookFile } from './types';
import { CalculatorView } from './CalculatorView';
import { MarkdownCell } from './MarkdownCell';
import starter from './starter.json';
import exampleNotebooks from './example-notebooks.json';
import legacyGear from './legacy-gear-v0121.json';
import legacyGear22 from './legacy-gear-v0122.json';
import { examples as libraryExamples, numericalExample } from './examples';
import { useWorkspace, type Document } from './workspace';
import { NotebookManager } from './NotebookManager';
import { parseNotebookJSON } from './notebook-json';
import { savePreference } from './preferences';
import { t, useLanguage, setLanguage, availableLanguages, installTranslations, restrictLanguage, type Language } from './i18n';
import { themeOptions, applyTheme, type Theme } from './themes';
import './help.css';

const Help = lazy(() => import('./Help'));

const makeCell = (code = '', mode: Cell['mode'] = 'source'): Cell => ({ id: crypto.randomUUID(), code, mode });
const initialCells = () => starter.cells.map(cell => makeCell(cell.code, cell.mode as Cell['mode']));

function readAutosave(): NotebookFile | null {
  try { const content = localStorage.getItem('calix-notebook-v1'); return content ? parseNotebookContent(content) : null; } catch { return null; }
}
function parseNotebookContent(content: string): NotebookFile {
  return validateNotebook(parseNotebookJSON(content));
}
function validateNotebook(data: unknown): NotebookFile {
  const file = data as NotebookFile;
  if (file?.format !== 'calix-notebook' || file.version !== 1 || !Array.isArray(file.cells) || file.cells.length > 200 || !file.cells.length) throw new Error(t("不是有效的 Calix Notebook v1 文件"));
  if (typeof file.title !== 'string' || file.title.length > 200) throw new Error(t("Notebook 标题无效"));
  const sources = file.cells.filter(cell => cell.mode !== 'markdown');
  const migrateGear = [legacyGear,legacyGear22].some(legacy => file.title === legacy.title && sources.length === legacy.sources.length && sources.every((cell,index) => cell.code === legacy.sources[index]));
  const updatedGear = migrateGear ? exampleNotebooks.find(notebook => notebook.title === legacyGear.title)?.cells.at(-1)?.code : undefined;
  return { ...file, cells: file.cells.map(cell => {
    if (typeof cell.code !== 'string' || cell.code.length > 24000 || !['source', 'math', 'markdown'].includes(cell.mode)) throw new Error(t("Notebook 单元无效"));
    if (cell.latex !== undefined && (typeof cell.latex !== 'string' || cell.latex.length > 24000)) throw new Error(t("数学输入内容无效"));
    const migrated = updatedGear && cell === sources.at(-1);
    const result = cell.mode === 'markdown' || migrated ? undefined : validateResult(cell.result);
    return { id: crypto.randomUUID(), code: migrated ? updatedGear : cell.code, latex: migrated ? undefined : cell.latex, mode: cell.mode === 'math' ? 'source' : cell.mode, result, error: typeof cell.error === 'string' ? cell.error.slice(0, 24000) : undefined, stale: !!result, executed: typeof cell.executed === 'number' ? cell.executed : undefined };
  }) };
}

function validateResult(value: unknown, depth = 0): Result | undefined {
  if (depth > 4) return undefined;
  if (!value || typeof value !== 'object') return undefined;
  const result = { ...value } as Result;
  const execution = result.execution;
  if (execution && (!Number.isInteger(execution.thread_limit) || execution.thread_limit < 1 || !Number.isInteger(execution.threads_used) || execution.threads_used < 1 || !execution.operations || typeof execution.operations !== 'object' || Array.isArray(execution.operations) || Object.keys(execution.operations).length > 32 || Object.values(execution.operations).some(operation => !operation || typeof operation.path !== 'string' || operation.path.length > 200 || !Number.isInteger(operation.calls) || operation.calls < 1 || !Number.isInteger(operation.threads_used) || operation.threads_used < 1))) delete result.execution;
  if (typeof result.engine !== 'string' || result.engine.length > 200 || typeof result.elapsed_ms !== 'number' || !Number.isFinite(result.elapsed_ms)) return undefined;
  if (result.label !== undefined && (typeof result.label !== 'string' || result.label.length > 240)) return undefined;
  if (result.kind === 'plot' && result.options?.box_ratios && (!Array.isArray(result.options.box_ratios) || result.options.box_ratios.length !== 3 || result.options.box_ratios.some(n => !Number.isFinite(n) || n <= 0))) return undefined;
  if (result.kind === 'group') {
    if (!Array.isArray(result.items) || !result.items.length || result.items.length > 40) return undefined;
    const items = result.items.map(item => validateResult(item, depth + 1));
    return items.every(Boolean) ? { ...result, items: items as Result[] } : undefined;
  }
  if (result.kind === 'animation') {
    const plot = (item: unknown) => {
      if (!item || typeof item !== 'object') return false;
      const checked = validateResult({ ...item, engine: result.engine, elapsed_ms: 0 }, depth + 1);
      return checked?.kind === 'plot' && ['curve', 'surface'].includes(checked.plot_type);
    };
    if (!['trajectory', 'frames'].includes(result.animation_type) || !plot(result.plot) || typeof result.parameter !== 'string' || result.parameter.length > 100) return undefined;
    if (!Array.isArray(result.values) || result.values.length < 2 || result.values.length > 4001 || result.values.some((n, i, a) => !Number.isFinite(n) || (i > 0 && n <= a[i - 1]))) return undefined;
    if (result.animation_type === 'frames' && (!Array.isArray(result.frames) || result.frames.length > 121 || result.frames.length !== result.values.length || result.frames.some(frame => !plot(frame) || frame.plot_type !== result.plot.plot_type || (frame.plot_type === 'curve' ? frame.traces?.length !== result.plot.traces?.length : frame.x?.length !== result.plot.x?.length || frame.y?.length !== result.plot.y?.length)))) return undefined;
    if (result.animation_type === 'trajectory' && (result.plot.plot_type !== 'curve' || result.plot.traces?.length !== 1 || result.plot.traces[0].x.length !== result.values.length)) return undefined;
    return result;
  }
  if (result.kind === 'expression') return typeof result.text === 'string' && result.text.length <= 100000 && typeof result.latex === 'string' && result.latex.length <= 100000 ? result : undefined;
  if (result.kind !== 'plot' || !['curve', 'curve3d', 'surface', 'parametric_surface', 'contour', 'density', 'volume', 'geometry3d', 'field3d'].includes(result.plot_type) || typeof result.title !== 'string' || !Array.isArray(result.axes) || result.axes.length > 3 || result.axes.some(a => typeof a !== 'string')) return undefined;
  const array = (a: unknown, limit: number) => Array.isArray(a) && a.length <= limit && a.every(v => v === null || (typeof v === 'number' && Number.isFinite(v)));
  if (result.scalar_legend && (!array(result.scalar_legend.range,2) || result.scalar_legend.range.length!==2 || !result.scalar_legend.range.every(Number.isFinite) || result.scalar_legend.range[0]>=result.scalar_legend.range[1] || typeof result.scalar_legend.label!=='string' || result.scalar_legend.label.length>160 || !Array.isArray(result.scalar_legend.colors) || result.scalar_legend.colors.length<2 || result.scalar_legend.colors.length>20 || result.scalar_legend.colors.some(c=>!/^#[a-fA-F0-9]{6}$/.test(c)))) return undefined;
  if (result.plot_type==='geometry3d' && result.primitives?.some(p=>p.colors && (p.type!=='triangle' || !Array.isArray(p.colors) || p.colors.length!==3 || p.colors.some(c=>!/^#[a-fA-F0-9]{6}$/.test(c))))) return undefined;
  if (result.plot_type==='density' && result.traces && (!Array.isArray(result.traces) || result.traces.length>20 || result.traces.some(t=>!array(t.x,10000) || !array(t.y,10000) || t.x.length!==t.y.length || typeof t.name!=='string'))) return undefined;
  if (result.plot_type === 'field3d') {
    const triple=(p:unknown)=>array(p,3)&&(p as number[]).length===3&&(p as number[]).every(Number.isFinite);
    if (!['gravity','magnetic'].includes(result.field_kind!) || !Array.isArray(result.bounds) || result.bounds.length!==3 || result.bounds.some(b=>!array(b,2)||b.length!==2||!b.every(Number.isFinite)||b[0]>=b[1]) || !array(result.color_range,2) || result.color_range!.length!==2 || !result.color_range!.every(Number.isFinite) || result.color_range![0]>=result.color_range![1]) return undefined;
    if (!Array.isArray(result.times)||result.times.length<2||result.times.length>1001||result.times.some((v,i,a)=>!Number.isFinite(v)||(i>0&&v<=a[i-1]))||!Array.isArray(result.paths)||result.paths.length<2||result.paths.length>(result.field_kind==='gravity'?5:6)||result.paths.some(p=>!Array.isArray(p)||p.length!==result.times!.length||p.some(v=>!triple(v)))) return undefined;
    if (!Array.isArray(result.colors)||result.colors.length!==result.paths.length||result.colors.some(c=>!/^#[0-9a-fA-F]{6}$/.test(c))||!Array.isArray(result.labels)||result.labels.length!==result.paths.length||result.labels.some(c=>typeof c!=='string'||c.length>120)) return undefined;
    if (result.field_kind==='gravity') {
      if (!Array.isArray(result.masses)||result.masses.length!==result.paths.length||result.masses.some(v=>!Number.isFinite(v)||v<=0)||!Number.isFinite(result.softening)||result.softening!<=0) return undefined;
    } else if (!Number.isInteger(result.size)||result.size!<17||result.size!>65||typeof result.volume!=='string'||result.volume.length!==4*Math.ceil(result.size!**3/3)||!/^[A-Za-z0-9+/]*={0,2}$/.test(result.volume)||!array(result.coils,8)||!result.coils!.length||!result.coils!.every(Number.isFinite)||!Array.isArray(result.field_lines)||result.field_lines.length>100||result.field_lines.some(p=>!Array.isArray(p)||p.length<2||p.length>1001||p.some(v=>!triple(v)))) return undefined;
  } else if (result.plot_type === 'volume') {
    if (!Number.isInteger(result.size) || result.size! < 17 || result.size! > 65 || typeof result.volume !== 'string' || result.volume.length !== 4*Math.ceil(result.size!**3/3) || !/^[A-Za-z0-9+/]*={0,2}$/.test(result.volume) || !Number.isFinite(result.density_max) || result.density_max! <= 0 || !Array.isArray(result.bounds) || result.bounds.length !== 3 || result.bounds.some(a => !array(a,2) || a.length !== 2 || a.some(v => v === null) || a[0] >= a[1])) return undefined;
  } else if (result.plot_type === 'geometry3d') {
    if (!Array.isArray(result.primitives) || !result.primitives.length || result.primitives.length > 48000 || result.primitives.some(p => !['line','arrow','point','triangle'].includes(p.type) || !/^#[a-fA-F0-9]{6}$/.test(p.color) || typeof p.label !== 'string' || p.label.length > 120 || !Array.isArray(p.points) || !p.points.length || p.points.length > 4000 || (p.type === 'arrow' && p.points.length !== 2) || (p.type === 'triangle' && p.points.length !== 3) || (p.type === 'line' && p.points.length < 2) || p.points.some(a => !array(a,3) || a.length !== 3 || a.some(v => v === null)))) return undefined;
  } else if (result.plot_type === 'curve' || result.plot_type === 'curve3d') {
    if (!Array.isArray(result.traces) || result.traces.length > 20 || result.traces.some(t => !array(t.x, 10000) || !array(t.y, 10000) || t.x.length !== t.y.length || typeof t.name !== 'string' || (result.plot_type === 'curve3d' && (!array(t.z, 10000) || t.z?.length !== t.x.length)))) return undefined;
  } else if (result.plot_type === 'parametric_surface') {
    if (!Number.isInteger(result.size) || result.size! < 2 || result.size! > 141 || !Array.isArray(result.coordinates) || result.coordinates.length !== 3 || result.coordinates.some(a => !array(a, 20000) || a.length !== result.size! ** 2)) return undefined;
  } else if (!array(result.x, 141) || !array(result.y, 141) || !Array.isArray(result.z) || result.z.length !== result.y!.length || result.z.some(row => !array(row, 141) || row.length !== result.x!.length)) return undefined;
  return result;
}

function Formula({ latex }: { latex: string }) {
  let html: string;
  try { html = katex.renderToString(latex, { throwOnError: false, displayMode: true, trust: false, strict: 'ignore', maxExpand: 1000 }); }
  catch { return <pre>{latex}</pre>; }
  return <div className="formula" dangerouslySetInnerHTML={{ __html: html }} />;
}

export function Output({ result, onInsert }: { result: Result; onInsert?: (text: string) => void }) {
  const [copied, setCopied] = useState(false);
  const unlabeled = useMemo(()=>({...result,label:undefined}),[result]);
  if (result.label) return <div className="labeled-output"><div className="output-label">{result.label} =</div><Output result={unlabeled} onInsert={onInsert} /></div>;
  if (result.kind === 'group') return <div className={`group-output ${result.items.every(item=>item.kind==='plot'&&item.plot_type==='volume')?'volume-grid':''}`}>{result.items.map((item, index) => <div className="group-item" key={index}><Output result={item} onInsert={onInsert} /></div>)}<ExecutionInfo result={result}/></div>;
  if (result.kind === 'animation') return <><Animation result={result} /><div className="result-meta"><span>{result.engine}</span><span>{result.elapsed_ms.toFixed(1)} ms</span></div></>;
  return <>
    {result.kind === 'plot' ? (result.plot_type==='field3d'?<FieldScene result={result}/>:['volume','geometry3d'].includes(result.plot_type) ? <ScientificScene result={result} /> : <Plot result={result} />) : <div className="expression-output"><Formula latex={result.latex} /><div className="output-actions"><button className="icon-button" title={t("复制结果")} onClick={async () => { await navigator.clipboard.writeText(result.text); setCopied(true); setTimeout(() => setCopied(false), 1200); }}>{copied ? <Check size={15} /> : <Copy size={15} />}</button>{onInsert && <button className="icon-button" title={t('复制到下一行输入')} onClick={() => onInsert(result.text)}><ArrowDownToLine size={15}/></button>}</div>{result.unresolved && <span className="unresolved">{t("保留符号形式")}</span>}</div>}
    <div className="result-meta"><span>{result.engine}</span><span>{result.elapsed_ms < 1000 ? `${result.elapsed_ms.toFixed(1)} ms` : `${(result.elapsed_ms / 1000).toFixed(2)} s`}</span></div><ExecutionInfo result={result}/>
  </>;
}

function ExecutionInfo({result}:{result:Result}) {
  const execution=result.execution;
  if (!execution || !Object.keys(execution.operations).length) return null;
  const paths=[...new Set(Object.values(execution.operations).map(operation=>operation.path))];
  return <div className="result-meta execution-info"><span>{paths.join(' · ')}</span><span>{execution.threads_used} / {execution.thread_limit} CPU Threads</span></div>;
}

export default function App() {
  const language = useLanguage();
  const [components, setComponents] = useState({ pde: false, languages: false, themes: false });
  const sortedExampleNotebooks = useMemo(() => [starter, ...exampleNotebooks].sort((a, b) =>
    t(a.title).localeCompare(t(b.title), language === 'zh' ? 'zh-CN-u-co-pinyin' : language, { numeric: true, sensitivity: 'base' })
  ), [language]);
  const [workspaceError, setWorkspaceError] = useState('');
  const reportWorkspaceError = useCallback((error: string) => setWorkspaceError(error), []);
  const workspace = useWorkspace(validateNotebook, () => readAutosave() || { format: 'calix-notebook', version: 1, title: starter.title, cells: initialCells() }, reportWorkspaceError);
  const { cells, title } = workspace.current;
  const setCells = workspace.setCells;
  const setTitle = (title: string) => workspace.update({ title });
  const [zoom, setZoom] = useState(() => { const n = Number(localStorage.getItem('calix-notebook-zoom')); return Number.isFinite(n) && n >= 70 && n <= 160 ? n : 100; });
  const notebookRef = useRef<HTMLElement>(null);
  const lastExample = useRef<Record<string, number>>({});
  const lastNumerical = useRef('');
  const [mode, setMode] = useState<'notebook' | 'calculator'>('notebook');
  const [calculatorBusy, setCalculatorBusy] = useState(false);
  const [sidebar, setSidebar] = useState(() => innerWidth >= 760);
  const [library, setLibrary] = useState(false);
  const [settings, setSettings] = useState(false);
  const [help, setHelp] = useState(false);
  const [theme, setTheme] = useState<Theme>('white');
  const [digits, setDigits] = useState(() => Math.min(1000, Math.max(2, Number(localStorage.getItem('calix-digits')) || 16)));
  const [workers, setWorkers] = useState(1);
  const [cpuCount, setCpuCount] = useState(1);
  const [workersSaving, setWorkersSaving] = useState(false);
  const [status, setStatus] = useState<'connecting' | 'ready' | 'error'>('connecting');
  const [native, setNative] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState('');
  const [activeCell, setActiveCell] = useState<string | null>(null);
  const session = useRef<string>(crypto.randomUUID());
  const cellsRef = useRef(cells); cellsRef.current = cells;
  const busyRef = useRef(false);
  const execution = useRef(0);
  const cancelled = useRef(false);
  const init = useRef(false);
  const liveSessions = useRef(new Set<string>());
  const sessionCells = useRef(new Map<string,Map<string,string>>());
  const filePath = useRef<string | null>(null);
  filePath.current = workspace.current.path;
  session.current = workspace.current.id;
  useEffect(() => { execution.current = Math.max(0, ...cellsRef.current.map(cell => cell.executed || 0)); setActiveCell(null); }, [workspace.active]);
  const fileInput = useRef<HTMLInputElement>(null);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toast = useCallback((message: string) => { setNotice(message); if (noticeTimer.current) clearTimeout(noticeTimer.current); noticeTimer.current = setTimeout(() => setNotice(''), 5000); }, []);
  useEffect(() => {
    if (!api.desktop) return;
    void import('@tauri-apps/api/core').then(async ({ invoke }) => {
      const handoff = await invoke<[string, string] | null>('startup_notebook');
      if (handoff) {
        const [path, content] = handoff;
        workspace.create(parseNotebookContent(content), path);
        setMode('notebook');
      }
    }).catch(error => toast(String(error)));
  }, []);

  const runOne = useCallback(async (id: string, source?: string) => {
    const cell = cellsRef.current.find(c => c.id === id);
    const code = source ?? cell?.code ?? '';
    if (!cell || !code.trim() || cell.mode === 'markdown') return true;
    setBusy(id);
    try {
      assertCompleteInput(cell.latex, code);
      const result = await api.evaluate(session.current, code);
      liveSessions.current.add(session.current);
      const completed=sessionCells.current.get(session.current)||new Map<string,string>();
      completed.set(id,code);sessionCells.current.set(session.current,completed);
      const index = ++execution.current;
      setCells(previous => previous.map(c => c.id === id ? { ...c, result, error: undefined, stale: c.code !== code, executed: index } : c));
      return true;
    } catch (error) {
      const message = String(error instanceof Error ? error.message : error);
      sessionCells.current.get(session.current)?.delete(id);
      if (/variables were cleared|session variables|process stopped|process exited|Calculation exceeded/i.test(message)) {
        liveSessions.current.delete(session.current);sessionCells.current.delete(session.current);
      }
      setCells(previous => previous.map(c => c.id === id ? { ...c, error: message.includes('PDE module is not installed.') ? t('此功能需要 PDE module。请重新运行安装包并勾选 PDE module。') : message, result: undefined, stale: false } : c));
      return false;
    } finally { setBusy(null); }
  }, []);

  useEffect(() => {
    const element = notebookRef.current;
    if (!element || mode !== 'notebook') return;
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey) return;
      event.preventDefault();
      event.stopPropagation();
      if (event.deltaY) setZoom(previous => Math.min(160, Math.max(70, previous + (event.deltaY < 0 ? 5 : -5))));
    };
    element.addEventListener('wheel', wheel, { passive: false, capture: true });
    return () => element.removeEventListener('wheel', wheel, { capture: true });
  }, [mode]);
  useEffect(() => { savePreference('calix-notebook-zoom', String(zoom)); }, [zoom]);

  useEffect(() => {
    const media = matchMedia('(max-width: 760px)');
    const update = () => setSidebar(!media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  const run = useCallback(async (id: string, source?: string) => {
    if (busyRef.current || status !== 'ready') return;
    busyRef.current = true; cancelled.current = false;
    try {
      const prior = cellsRef.current.slice(0,cellsRef.current.findIndex(cell => cell.id===id)).filter(cell=>cell.mode!=='markdown' && cell.code.trim());
      const completed=sessionCells.current.get(session.current);
      if (prior.some(cell=>completed?.get(cell.id)!==cell.code) && (workspace.current.example || prior.some(cell=>cell.executed || cell.result))) {
        await api.cancel(session.current);
        liveSessions.current.delete(session.current);sessionCells.current.delete(session.current);
        for (const cell of prior) if (cancelled.current || !(await runOne(cell.id))) return;
      }
      if (!cancelled.current) await runOne(id,source);
    } finally { busyRef.current = false; }
  }, [runOne, status, workspace.current.example]);

  const runAll = useCallback(async () => {
    if (busyRef.current || status !== 'ready') return;
    busyRef.current = true; cancelled.current = false;
    try {
      await api.cancel(session.current);
      liveSessions.current.delete(session.current);
      sessionCells.current.delete(session.current);
      execution.current = 0;
      setCells(previous => previous.map(c => ({ ...c, stale: !!c.result })));
      for (const cell of cellsRef.current) {
        if (cancelled.current || !(await runOne(cell.id))) break;
      }
    } catch (error) { toast(String(error)); }
    finally { busyRef.current = false; setBusy(null); }
  }, [runOne, status, toast]);

  useEffect(() => {
    if (init.current) return;
    init.current = true;
    api.connect().then(async health => {
      setComponents(health.components);
      if (health.components.languages) installTranslations(await api.componentResource('languages'));
      restrictLanguage();
      if (health.components.themes) {
        const style = document.createElement('style'); style.id = 'calix-theme-pack'; style.textContent = (await api.componentResource('themes')).css; document.head.appendChild(style);
        const saved = localStorage.getItem('calix-theme') as Theme;
        if (themeOptions.some(item => item.id === saved)) { setTheme(saved); applyTheme(saved); }
      } else applyTheme('white');
      setNative(health.native); setCpuCount(health.cpu_count);
      const requested = Number(localStorage.getItem('calix-workers'));
      const maximum = Math.min(health.cpu_count, Math.max(1, Math.floor(requested || health.max_workers)));
      await api.configureWorkers(maximum); setWorkers(maximum); savePreference('calix-workers', String(maximum)); setStatus('ready');
    }).catch(error => { setStatus('error'); toast(String(error)); });
  }, [toast]);
  useEffect(() => { if (workspaceError) { toast(t(workspaceError)); setWorkspaceError(''); } }, [workspaceError, toast]);
  useEffect(() => { savePreference('calix-digits', String(digits)); }, [digits]);

  const save = useCallback(async (saveAs = false) => {
    if (mode === 'calculator') return false;
    const content = JSON.stringify({ format: 'calix-notebook', version: 1, title, cells }, null, 2);
    try {
      if (api.desktop) {
        const { save: dialog } = await import('@tauri-apps/plugin-dialog');
        const { invoke } = await import('@tauri-apps/api/core');
        const path = !saveAs && filePath.current ? filePath.current : await dialog({ defaultPath: `${title}.cixnb`, filters: [{ name: 'Calix Notebook', extensions: ['cixnb'] }] });
        if (!path) return false;
        await invoke('write_notebook', { path, content }); workspace.update({ path });
      } else {
        const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }));
        const anchor = document.createElement('a'); anchor.href = url; anchor.download = `${title}.cixnb`; anchor.click(); URL.revokeObjectURL(url);
      }
      toast(t("Notebook 已保存"));
      return true;
    } catch (error) { toast(String(error)); return false; }
  }, [cells, title, toast, mode]);

  const loadContent = useCallback(async (content: string) => {
    if (busyRef.current) throw new Error(t("请先停止当前计算"));
    const notebook = parseNotebookContent(content);
    workspace.create(notebook); execution.current = 0; setMode('notebook');
    toast(t("已打开 Notebook；会话变量已清空"));
  }, [toast, workspace.create]);

  const open = useCallback(async () => {
    if (busyRef.current || calculatorBusy) { toast(t('请先停止当前计算')); return; }
    if (status !== 'ready') { toast(t("计算引擎正在启动，请稍后打开文件")); return; }
    try {
      if (api.desktop) {
        const { open: dialog } = await import('@tauri-apps/plugin-dialog');
        const { invoke } = await import('@tauri-apps/api/core');
        const path = await dialog({ multiple: false, filters: [{ name: 'Calix Notebook', extensions: ['cixnb', 'clxnb', 'calix'] }] });
        if (typeof path !== 'string') return;
        const content = await invoke<string>('read_notebook', { path });
        const notebook = parseNotebookContent(content);
        if (busyRef.current) throw new Error(t('请先停止当前计算'));
        workspace.create(notebook, path); setMode('notebook');
      } else fileInput.current?.click();
    } catch (error) { toast(String(error)); }
  }, [loadContent, toast, status, workspace.create, calculatorBusy]);

  const addCell = (code = '', mode: Cell['mode'] = 'source') => {
    if (calculatorBusy) return;
    const cell = makeCell(code, mode);
    setCells(previous => [...previous, cell]); setActiveCell(cell.id); setMode('notebook');
    setTimeout(() => document.getElementById(cell.id)?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 80);
  };
  const insertOutput = (origin: string, code: string) => {
    if (code.length > 24000 || cellsRef.current.length >= 200) { toast(t('结果过长或单元数量已达上限')); return; }
    const cell = makeCell(code);
    setCells(previous => {
      const index = previous.findIndex(item => item.id === origin);
      return index < 0 ? previous : [...previous.slice(0, index + 1), cell, ...previous.slice(index + 1)];
    });
    setActiveCell(cell.id);
    setTimeout(() => { const element = document.getElementById(cell.id); element?.scrollIntoView({ block: 'center', behavior: 'smooth' }); (element?.querySelector('.cm-content') as HTMLElement | null)?.focus(); }, 80);
  };
  const openNotebookExample = (example: typeof starter) => {
    if (busyRef.current || calculatorBusy || status !== 'ready') return;
    const exampleKey = `${example.title}@0.1.23`;
    const existing = workspace.documents.find(doc => doc.example === exampleKey);
    if (existing) workspace.activate(existing.id);
    else workspace.create({ format: 'calix-notebook', version: 1, title: t(example.title), cells: example.cells.map(cell => makeCell(cell.code, cell.mode as Cell['mode'])) }, null, exampleKey);
    setMode('notebook');
    setLibrary(false);
  };
  const revealNotebook = async (doc: Document) => {
    if (!api.desktop) { toast(t('文件位置与源文件删除功能仅在桌面版可用')); return; }
    if (!doc.path) { toast(t('此笔记尚未保存到磁盘')); return; }
    try { const { invoke } = await import('@tauri-apps/api/core'); await invoke('reveal_notebook', { path: doc.path }); }
    catch (error) { toast(String(error)); }
  };
  const removeNotebook = async (doc: Document, deleteFile: boolean) => {
    if (busyRef.current) throw new Error(t('请先停止当前计算'));
    if (deleteFile) {
      if (!api.desktop || !doc.path) throw new Error(t('此笔记尚未保存到磁盘'));
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('delete_notebook', { path: doc.path });
      const key = (path: string) => path.replace(/\\/g, '/').toLowerCase();
      workspace.documents.filter(other => other.id !== doc.id && other.path && key(other.path) === key(doc.path!)).forEach(other => workspace.update({ path: null }, other.id));
    }
    void api.cancel(doc.id).catch(() => {});
    workspace.remove(doc.id);
  };

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'F1') { event.preventDefault(); setHelp(true); }
      if (event.ctrlKey && event.key.toLowerCase() === 's') { event.preventDefault(); void save(event.shiftKey); }
      if (event.ctrlKey && event.key.toLowerCase() === 'o') { event.preventDefault(); void open(); }
    };
    window.addEventListener('keydown', handler); return () => window.removeEventListener('keydown', handler);
  }, [save, open]);

  const stop = useCallback(async () => {
    cancelled.current = true;
    await api.cancel(session.current);
    liveSessions.current.delete(session.current);
    sessionCells.current.delete(session.current);
    setCells(previous => previous.map(c => ({ ...c, stale: !!c.result })));
    toast(t("计算已停止，会话变量已清空"));
  }, [setCells, toast]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (mode === 'notebook' && busyRef.current && event.altKey && (event.code === 'Period' || event.key === '.')) {
        event.preventDefault(); event.stopPropagation();
        void stop().catch(error => toast(String(error)));
      }
    };
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [mode, stop, toast]);
  const restart = async () => {
    if (busyRef.current) return;
    await api.cancel(session.current); liveSessions.current.delete(session.current); sessionCells.current.delete(session.current); execution.current = 0;
    setCells(previous => previous.map(c => ({ ...c, stale: !!c.result })));
    toast(t("计算会话已重启"));
  };
  const newNotebook = async () => {
    if (busyRef.current || calculatorBusy || status !== 'ready') return;
    workspace.create({ format: 'calix-notebook', version: 1, title: t('未命名笔记'), cells: [makeCell()] }); setMode('notebook');
  };
  const change = (id: string, code: string, latex?: string) => {
    const changedIndex = cellsRef.current.findIndex(c => c.id === id);
    setCells(previous => previous.map((c, index) => c.id === id ? { ...c, code, latex, error: undefined, stale: !!c.result } : index > changedIndex ? { ...c, stale: !!c.result } : c));
  };
  const move = (id: string, offset: number) => setCells(previous => {
    const index = previous.findIndex(c => c.id === id), next = index + offset;
    if (next < 0 || next >= previous.length) return previous;
    const output = [...previous]; [output[index], output[next]] = [output[next], output[index]];
    return output.map(c => ({ ...c, stale: !!c.result }));
  });

  return <div className={`app ${sidebar ? '' : 'sidebar-collapsed'}`}>
    <aside className="sidebar">
      <div className="brand"><img src="/calix-mark.svg" width={39} height={39} alt="Calix" /><div><strong>Calix</strong><span>Calculation &amp;<br />Interactive Xpressions</span></div></div>
      <div className="workspace-label">{t("文件")}</div>
      <nav className="navigation secondary"><button onClick={() => void newNotebook()} disabled={!!busy || calculatorBusy}><FilePlus2 size={17} /><span>{t("新建笔记")}</span></button><button onClick={() => void open()} disabled={!!busy || calculatorBusy}><FolderOpen size={17} /><span>{t("打开")}</span></button><button disabled={mode==='calculator'} onClick={() => void save()}><Save size={17} /><span>{t("保存")}</span></button><button disabled={mode==='calculator'} onClick={() => void save(true)}><SaveAll size={17} /><span>{t("另存为")}</span></button></nav>
      <div className="sidebar-divider" />
      <div className="workspace-label">{t("工作空间")}</div>
      <nav className="navigation">
        <button disabled={calculatorBusy} className={mode === 'notebook' ? 'selected' : ''} onClick={() => setMode('notebook')}><BookOpen size={18} /><span>CIX Notebook</span><span className="nav-count">{cells.length}</span></button>
        <button disabled={!!busy} className={mode === 'calculator' ? 'selected' : ''} onClick={() => setMode('calculator')}><Calculator size={18} /><span>{t("传统计算器面板")}</span></button>
      </nav>
      <NotebookManager documents={workspace.documents} active={workspace.active} desktop={api.desktop} disabled={!!busy || calculatorBusy || status !== 'ready'}
        onNew={() => void newNotebook()} onSelect={id => { if (!busyRef.current) { workspace.activate(id); setMode('notebook'); } }}
        onRename={(id, title) => workspace.update({ title }, id)}
        onCopy={doc => { workspace.create({ format: 'calix-notebook', version: 1, title: doc.title + t(' 副本'), cells: doc.cells.map(cell => ({ ...cell, id: crypto.randomUUID(), stale: !!cell.result })) }); setMode('notebook'); }}
        onDelete={removeNotebook} onReveal={doc => void revealNotebook(doc)} />
      <div className="sidebar-divider" />
      <button className={`library-button ${library ? 'selected' : ''}`} onClick={() => setLibrary(!library)}><FunctionSquare size={18} /><span>{t("计算示例")}</span><ChevronDown className={library ? 'rotated' : ''} size={15} /></button>
      <div className="sidebar-bottom"><button onClick={() => setHelp(true)} title="F1"><BookOpen size={17} />{t('帮助')}</button><button onClick={() => setSettings(true)}><Settings2 size={17} />{t("偏好设置")}</button><div className="version">Calix <span>0.1.27 · Preview</span></div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumb"><button className="icon-button" title={sidebar ? t("收起侧栏") : t("展开侧栏")} onClick={() => setSidebar(!sidebar)}>{sidebar ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}</button><span>{t("工作空间")}</span><span className="slash">/</span><strong>{mode === 'notebook' ? 'Notebook' : t("传统计算器面板")}</strong></div><div className={`engine-status ${status}`}><span className="status-dot" />{status === 'connecting' ? t("连接引擎") : status === 'error' ? t("引擎离线") : native ? t("原生核心就绪") : t("符号引擎就绪")}{status === 'error' && <button title={t("重新连接")} onClick={() => { setStatus('connecting'); api.connect().then(h => { setNative(h.native); setStatus('ready'); }).catch(e => { setStatus('error'); toast(String(e)); }); }}><RotateCcw size={14} /></button>}</div></header>
      {mode === 'notebook' ? <>
        <div className="notebook-header"><div className="document-title"><div className="document-icon"><BookOpen size={22} /></div><div><input aria-label={t("Notebook 名称")} value={title} maxLength={100} onChange={e => setTitle(e.target.value)} /></div></div><div className="document-actions"><button className="subtle-button" title={t("保存")} onClick={() => void save()}><Save size={16} /><span>{t("保存")}</span></button><button className="subtle-button" title={t("另存为")} onClick={() => void save(true)}><SaveAll size={16} /><span>{t("另存为")}</span></button></div></div>
        <div className="toolbar"><div className="toolbar-group"><button className="primary-button" onClick={() => void runAll()} disabled={!!busy || status !== 'ready'}><Play size={15} fill="currentColor" /><span>{t("全部运行")}</span></button><button className="icon-button" title={t("停止计算")} disabled={!busy} onClick={() => void stop()}><Square size={16} /></button><button className="icon-button" title={t("重启会话")} disabled={!!busy || status !== 'ready'} onClick={() => void restart()}><RotateCcw size={16} /></button><span className="toolbar-separator" /><button className="subtle-button" onClick={() => addCell()}><Sigma size={17} /><span>{t("计算单元")}</span></button><button className="subtle-button" onClick={() => addCell('', 'markdown')}><BookOpen size={16} /><span>{t("文字单元")}</span></button></div><div className="notebook-controls"><button className="zoom-reset subtle-button" title={t("恢复 100%")} onClick={() => setZoom(100)}>{zoom}%</button><span className="cell-count">{cells.length} {t('个单元')}</span></div></div>
        <main className="notebook" aria-label="Notebook" ref={notebookRef} style={{ zoom: zoom / 100 }}>
          {cells.map((cell, index) => <section id={cell.id} key={cell.id} className={`cell ${activeCell === cell.id ? 'active' : ''} ${busy === cell.id ? 'running' : ''}`}>
            <div className="cell-gutter"><button title={t("运行单元")} aria-label={`${t('运行单元')} ${index + 1}`} onClick={() => void run(cell.id)} disabled={cell.mode === 'markdown' || !!busy || status !== 'ready'}>{busy === cell.id ? <LoaderCircle className="spin" size={17} /> : <Play size={15} />}</button><span>{index + 1}</span></div>
            <div className="cell-body"><div className="cell-header"><span className="input-label">{cell.mode === 'markdown' ? 'Text' : `In[${cell.executed ?? ' '}]:=`}</span><div className="cell-actions"><span className="input-mode">{cell.mode === 'markdown' ? t("文字单元") : t("计算单元")}</span><button title={t("上移单元")} disabled={index === 0 || !!busy} onClick={() => move(cell.id, -1)}><ArrowUp size={14} /></button><button title={t("下移单元")} disabled={index === cells.length - 1 || !!busy} onClick={() => move(cell.id, 1)}><ArrowDown size={14} /></button><button title={t("复制单元")} onClick={() => setCells(p => [...p.slice(0, index + 1), { ...cell, id: crypto.randomUUID(), result: undefined, executed: undefined }, ...p.slice(index + 1)])}><Copy size={14} /></button><button title={t("删除单元")} disabled={!!busy} onClick={() => setCells(p => p.length > 1 ? p.filter(c => c.id !== cell.id).map(c => ({ ...c, stale: !!c.result })) : [makeCell()])}><Trash2 size={14} /></button></div></div>
              {cell.mode === 'markdown' ? <MarkdownCell value={cell.code} onChange={code => change(cell.id, code)} /> : <Editor cell={cell} onChange={(code, latex) => change(cell.id, code, latex)} onRun={code => void run(cell.id, code)} onFocus={() => setActiveCell(cell.id)} />}
              {busy === cell.id && <div className="pending"><LoaderCircle size={14} className="spin" />{t("计算中")}</div>}
              {cell.error && <div className="error-message" role="alert">{cell.error}</div>}
              {cell.result && <div className={`output ${cell.stale ? 'stale' : ''}`}><div className="output-label">Out[{cell.executed ?? ' '}]= {cell.stale && <span>{t("待重新计算")}</span>}</div><Output result={cell.result} onInsert={text => insertOutput(cell.id, text)} /></div>}
            </div>
          </section>)}
          <button className="add-cell" onClick={() => addCell()} title={t("添加计算单元")}><Plus size={18} /></button>
        </main>
      </> : <CalculatorView ready={status === 'ready'} digits={digits} toast={toast} onBusyChange={setCalculatorBusy} />}
      <footer className="statusbar"><span><span className="tiny-dot" />{t("本地计算")}</span><span>{busy || calculatorBusy ? t("计算中") : t("就绪")}</span><span className="statusbar-right">{t(mode === 'notebook' ? 'Notebook' : 'Calculator')}<span>UTF-8</span></span></footer>
    </div>
    {library && <aside className="library-panel"><div className="panel-heading"><strong>{t("计算示例")}</strong><button title={t("关闭示例")} className="icon-button" onClick={() => setLibrary(false)}><X size={17} /></button></div><div className="example-group">{sortedExampleNotebooks.map(example => <button key={example.title} disabled={!!busy || status !== 'ready'} onClick={() => openNotebookExample(example)}><span>{t(example.title)}</span><BookOpen size={14} /></button>)}</div>{[...new Set(libraryExamples.map(e => e.group))].map(group => <div key={group} className="example-group"><h3>{t(group)}</h3>{libraryExamples.filter(e => e.group === group).map(example => <button key={example.title} onClick={() => { if (busyRef.current || status !== 'ready') return; const previous = lastExample.current[example.title]; const choices = example.codes.map((_, i) => i).filter(i => example.codes.length === 1 || i !== previous); const selected = choices[Math.floor(Math.random() * choices.length)]; lastExample.current[example.title] = selected; let code = example.codes[selected]; if (example.title === '显式数值计算') { code = numericalExample(lastNumerical.current); lastNumerical.current = code; } addCell(code); if (innerWidth < 1100) setLibrary(false); }}><span>{t(example.title)}</span><Plus size={14} /></button>)}</div>)}</aside>}
    {settings && <div className="modal-backdrop" onClick={() => setSettings(false)}><section className="settings-modal" role="dialog" aria-label={t("偏好设置")} onClick={e => e.stopPropagation()}><div className="panel-heading"><strong>{t("偏好设置")}</strong><button title={t("关闭设置")} className="icon-button" onClick={() => setSettings(false)}><X size={18} /></button></div><label>{t("数值近似有效位数")}<input type="number" min={2} max={1000} value={digits} onChange={e => setDigits(Math.min(1000, Math.max(2, Number(e.target.value) || 16)))} /></label><label>{t('最大 CPU Workers')}<input aria-label={t('最大 CPU Workers')} type="number" min={1} max={cpuCount} step={1} disabled={!!busy || workersSaving || status !== 'ready'} value={workers} onChange={event => {
      const value = Math.min(cpuCount, Math.max(1, Math.floor(Number(event.target.value) || 1)));
      setWorkersSaving(true);
      void api.configureWorkers(value).then(() => { setWorkers(value); savePreference('calix-workers', String(value)); }).catch(error => toast(String(error))).finally(() => setWorkersSaving(false));
    }} /></label><label>{t('界面语言')}<select aria-label={t('界面语言')} value={language} onChange={event => setLanguage(event.target.value as Language)}>{availableLanguages().map(item => <option key={item.code} value={item.code}>{item.name}</option>)}</select></label><fieldset className="theme-picker"><legend>{t('页面皮肤')}</legend>{themeOptions.filter(item => components.themes || item.id === 'white').map(item => <button key={item.id} aria-label={t(item.name)} title={t(item.name)} aria-pressed={theme === item.id} onClick={() => { setTheme(item.id); applyTheme(item.id); }}><i style={{ background: item.color }}/></button>)}</fieldset><div className="settings-info"><span>{t("计算核心")}</span><strong>{native ? 'C++ / Boost + SymPy' : 'SymPy'}</strong></div><div className="settings-info"><span>{t("版本")}</span><strong>0.1.27 Preview</strong></div><div className="settings-info"><span>{t("许可证")}</span><strong>Proprietary · Third-party notices included</strong></div></section></div>}
    {help && <Suspense fallback={null}><Help onClose={() => setHelp(false)} onNotebook={async source => {
      if (busyRef.current || calculatorBusy || status !== 'ready') throw new Error(t('请先停止当前计算'));
      await loadContent(source);
    }}/></Suspense>}
    {notice && <div className="toast" role="status">{notice}<button title={t("关闭通知")} onClick={() => setNotice('')}><X size={14} /></button></div>}
    <input ref={fileInput} type="file" accept=".cixnb,.clxnb,.calix,.json" hidden onChange={async e => { const file = e.target.files?.[0]; if (file) { try { if (file.size > 10_000_000) throw new Error(t("Notebook 文件超过 10 MB")); await loadContent(await file.text()); } catch (err) { toast(String(err)); } } e.target.value = ''; }} />
  </div>;
}
