import { useEffect, useImperativeHandle, useRef, useState, type Ref } from 'react';
import { EditorState, Prec, Transaction } from '@codemirror/state';
import { EditorView, keymap, placeholder } from '@codemirror/view';
import { defaultKeymap, deleteCharBackward, history, historyKeymap } from '@codemirror/commands';
import { bracketMatching, indentOnInput } from '@codemirror/language';
import { autocompletion, closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete';
import { MathfieldElement } from 'mathlive';
import type { Cell } from './types';
import { latexToWolfram } from './mathjson';
import { Sigma, X } from 'lucide-react';
import { t, useLanguage } from './i18n';
import unitCatalog from './unit-catalog.json';
import { findSpecialSymbol, specialSymbols } from './special-symbols';
import { createPortal } from 'react-dom';
import { formulaDecorations, formulaSpans, putFormula, readFormulas, restoreFormulas, type FormulaSpan } from './rich-formulas';

const presentationNames = ['Labeled', 'DensityPlot3D', 'Graphics3D', 'Arrow', 'Style', 'Animate', 'Column', 'DSolveValue', 'NDSolveValue', 'Part', 'First', 'Last', 'Minimize', 'Maximize', 'FindMinimum', 'FindMaximum', 'Det', 'Inverse', 'Dot', 'Transpose', 'UnitSimplify', 'Mean', 'Median', 'Variance', 'StandardDeviation', 'Quantile', 'Quartiles', 'Covariance', 'Correlation', 'SpearmanRho', 'Counts', 'Commonest', 'Skewness', 'Kurtosis', 'Standardize', 'Fit', 'NormalDistribution', 'BinomialDistribution', 'PoissonDistribution', 'UniformDistribution', 'ExponentialDistribution', 'StudentTDistribution', 'ChiSquareDistribution', 'PDF', 'CDF', 'InverseCDF', 'Histogram', 'ListPlot', 'ListLinePlot'];
presentationNames.push('NBodySolve', 'NBodyPlot3D', 'MagneticFieldPlot3D', 'Show', 'TrigExpand', 'ComplexExpand', 'Together', 'Cancel', 'Normal');
presentationNames.push('Laplacian', 'Grad', 'Div', 'NDEigensystem', 'PDEInfo', 'PDEPlot', 'PDEValue', 'FEMBridgeSolve', 'WingFlowSolve');
presentationNames.push('ProjectileRange', 'ProjectileMaxRange', 'ProjectileOptimum', 'ProjectileVelocity', 'Magnitude');
const names = ['Sin', 'Cos', 'Tan', 'Exp', 'Log', 'Sqrt', 'Pi', 'Infinity', 'Solve', 'SolveValues', 'NSolve', 'FindRoot', 'D', 'Integrate', 'NIntegrate', 'Sum', 'Product', 'Limit', 'Series', 'Simplify', 'Expand', 'Factor', 'DSolve', 'NDSolve', 'RSolve', 'Hypergeometric2F1', 'Gamma', 'BesselJ', 'Plot', 'Plot3D', 'ParametricPlot', 'ParametricPlot3D', 'ContourPlot', 'DensityPlot', 'Assuming', 'UnitConvert', 'Quantity', 'Clear', 'N', 'TTest', 'ZTest', 'Table', 'If', 'Nothing', 'Flatten', 'Join', 'Accumulate', 'Permutations', 'Intersection', 'Count', 'IntegerQ', 'Mod', 'Graphics', 'Line', 'Point', 'Reduce', 'Numerator', 'Denominator', 'CoefficientList', 'IntegerLength', 'PowerMod', 'GCD'];

MathfieldElement.fontsDirectory = '/mathlive-fonts';
MathfieldElement.soundsDirectory = null;

export type EditorCommands = {
  insertText: (code: string, latex?: string, cursorOffset?: number) => void;
  insertTemplate: (latex: string) => void;
  insertSymbol: (alias: string) => void;
  showSymbols: () => void;
  backspace: () => void;
  clear: () => void;
  commit: () => string | null;
};

export function assertCompleteInput(latex: string | undefined, code: string) {
  if (readFormulas(latex, code).some(span => span.draft)) throw new Error(t('数学表达式尚未完成'));
}

function formulaSource(latex: string): Pick<FormulaSpan, 'code' | 'draft'> {
  try {
    const code = latexToWolfram(latex);
    if (code) return { code, draft: false };
  } catch { /* Incomplete formulas remain editable and are persisted with the cell. */ }
  return { code: '□', draft: true };
}

export function Editor({ cell, onChange, onRun, onFocus, commands }: { cell: Cell; onChange: (code: string, latex?: string) => void; onRun: (code?: string) => void; onFocus?: () => void; commands?: Ref<EditorCommands> }) {
  const host = useRef<HTMLDivElement>(null), view = useRef<EditorView | null>(null);
  const field = useRef<MathfieldElement | null>(null);
  const [error, setError] = useState('');
  const [popup, setPopup] = useState({ left: 0, top: 0 });
  const [symbolInput, setSymbolInput] = useState<string | null>(null);
  const symbolTarget = useRef<string | null>(null);
  const language = useLanguage();
  const callbacks = useRef({ onChange, onRun, onFocus });
  callbacks.current = { onChange, onRun, onFocus };
  const findField = (id: string) => host.current?.querySelector<MathfieldElement>(`math-field[data-formula-id="${id}"]`);
  const activeField = () => field.current?.isConnected ? field.current : null;
  const getSpan = (id: string) => view.current?.state.field(formulaSpans).find(span => span.id === id);
  const updateFormula = (id: string, mf: MathfieldElement) => {
    const editor = view.current, span = getSpan(id);
    if (!editor || !span) return;
    const latex = mf.value, source = formulaSource(latex);
    if (span.latex === latex && span.code === source.code && !!span.draft === !!source.draft) return;
    editor.dispatch({ changes: { from: span.from, to: span.to, insert: source.code },
      effects: putFormula.of({ ...span, ...source, latex, to: span.from + source.code.length }) });
    setError('');
  };
  const showSymbols = () => {
    const mf = activeField();
    symbolTarget.current = mf?.dataset.formulaId || null;
    const bounds = mf ? mf.getElementInfo(mf.position)?.bounds || mf.getBoundingClientRect() : view.current?.coordsAtPos(view.current.state.selection.main.head);
    if (bounds) setPopup({ left: Math.max(8, Math.min(bounds.left, innerWidth - Math.min(460, innerWidth - 16) - 8)), top: Math.max(8, Math.min(bounds.bottom + 6, innerHeight - 260)) });
    setSymbolInput(''); setError('');
  };
  const openTemplate = (latex: string) => {
    const mf = activeField();
    if (mf) { mf.insert(latex, { selectionMode: 'placeholder' }); updateFormula(mf.dataset.formulaId!, mf); mf.focus(); return; }
    const editor = view.current;
    if (!editor) return;
    latex = latex.replace(/#\d+/g, '\\placeholder{}');
    const { from, to } = editor.state.selection.main, id = crypto.randomUUID(), source = formulaSource(latex);
    editor.dispatch({ changes: { from, to, insert: source.code }, selection: { anchor: from + source.code.length },
      effects: putFormula.of({ id, from, to: from + source.code.length, latex, ...source }), scrollIntoView: true });
    requestAnimationFrame(() => { const inserted = findField(id); field.current = inserted || null; inserted?.focus(); if (source.draft) { inserted?.executeCommand('moveToMathfieldStart'); inserted?.executeCommand('moveToNextPlaceholder'); } }); setError('');
  };
  const commit = () => {
    const mf = activeField();
    if (mf) updateFormula(mf.dataset.formulaId!, mf);
    const editor = view.current;
    if (!editor) return '';
    const incomplete = editor.state.field(formulaSpans).find(span => span.draft);
    if (incomplete) { setError(t('数学表达式尚未完成')); findField(incomplete.id)?.focus(); return null; }
    setError(''); return editor.state.doc.toString();
  };
  const run = () => { const code = commit(); if (code !== null) requestAnimationFrame(() => callbacks.current.onRun(code)); };

  useEffect(() => {
    if (!host.current) return;
    const editor = new EditorView({ parent: host.current, state: EditorState.create({ doc: cell.code, extensions: [
      formulaDecorations({
        input: updateFormula,
        focus: (_id, mf) => { field.current = mf; callbacks.current.onFocus?.(); },
        blur: mf => { if (field.current === mf) field.current = null; },
        keydown: (id, mf, event) => {
          if (event.altKey && (event.code === 'Period' || event.key === '.')) return;
          if ((event.ctrlKey || event.shiftKey) && event.key === 'Enter') { event.preventDefault(); event.stopPropagation(); run(); }
          else if (event.ctrlKey && (event.key === '6' || event.key === '2')) { event.preventDefault(); event.stopPropagation(); mf.insert(event.key === '6' ? '^{#0}' : '\\sqrt{#0}', { selectionMode: 'placeholder' }); updateFormula(id, mf); }
          else if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); showSymbols(); }
        },
        moveOut: (id, direction) => {
          const span = getSpan(id); if (!span || !view.current) return;
          const anchor = direction === 'backward' || direction === 'upward' ? span.from : span.to;
          field.current = null; view.current.dispatch({ selection: { anchor } }); view.current.focus();
        },
      }),
      Prec.highest(keymap.of([{ key: 'Escape', run: () => { showSymbols(); return true; } }])),
      history(), bracketMatching(), indentOnInput(), closeBrackets(),
      autocompletion({ override: [context => {
        const before = context.state.sliceDoc(Math.max(0, context.pos - 1000), context.pos);
        if (/\[[^\[\]\n]*$/.test(before) && /(?:^|[\s\d)\]";=])\[[^\[\]\n]*$/.test(before)) {
          const unit = context.matchBefore(/[\p{L}_µΩ°]+/u);
          if (unit || context.explicit) return { from: unit?.from ?? context.pos, options: unitCatalog.map(item => ({ ...item, type: 'constant' })) };
        }
        const word = context.matchBefore(/[A-Za-z]+/);
        if (!word || (word.from === word.to && !context.explicit)) return null;
        return { from: word.from, options: [...names, ...presentationNames, 'EllipticK', 'EllipticE', 'LaguerreL', 'LegendreP', 'Pochhammer', 'FunctionExpand'].map(label => ({ label, type: 'function' })) };
      }] }),
      placeholder(t('输入表达式…')), EditorView.lineWrapping,
      keymap.of([{ key: 'Ctrl-Enter', run: () => { run(); return true; } }, { key: 'Shift-Enter', run: () => { run(); return true; } }, ...closeBracketsKeymap, ...defaultKeymap, ...historyKeymap]),
      keymap.of([{ key: 'Ctrl-6', run: () => { openTemplate('^{#0}'); return true; } }, { key: 'Ctrl-2', run: () => { openTemplate('\\sqrt{#0}'); return true; } }]),
      EditorView.updateListener.of(update => { if (update.docChanged || update.transactions.some(tr => tr.annotation(Transaction.addToHistory) !== false && tr.effects.some(effect => effect.is(putFormula) || effect.is(restoreFormulas)))) callbacks.current.onChange(update.state.doc.toString(), JSON.stringify(update.state.field(formulaSpans))); }),
      EditorView.domEventHandlers({ focus: event => { if (event.target === view.current?.contentDOM) field.current = null; callbacks.current.onFocus?.(); } }),
      EditorView.theme({ '&': { fontSize: '15px', backgroundColor: 'transparent' }, '.cm-content': { fontFamily: 'Consolas, Cascadia Code, monospace', padding: '12px 0', minHeight: '48px' }, '&.cm-focused': { outline: 'none' }, '.cm-scroller': { overflow: 'auto' }, '.cm-cursor': { borderLeftColor: '#087e80' } }),
    ] }) });
    view.current = editor;
    editor.dispatch({ effects: restoreFormulas.of(readFormulas(cell.latex, cell.code)), annotations: Transaction.addToHistory.of(false) });
    return () => { field.current = null; editor.destroy(); view.current = null; };
  }, [cell.id, cell.mode, language]);

  const insertSymbol = (alias: string) => {
    const item = findSpecialSymbol(alias);
    if (!item) { setError(t('未找到特殊符号') + ': ' + alias); return; }
    if (symbolInput !== null) field.current = symbolTarget.current ? findField(symbolTarget.current) || null : null;
    setSymbolInput(null); setError('');
    if (item.template) { openTemplate(item.template); return; }
    const mf = activeField();
    if (mf) { mf.insert(item.symbol!); updateFormula(mf.dataset.formulaId!, mf); mf.focus(); return; }
    const editor = view.current; if (!editor) return;
    const { from, to } = editor.state.selection.main;
    editor.dispatch({ changes: { from, to, insert: item.symbol! }, selection: { anchor: from + item.symbol!.length } }); editor.focus();
  };
  useImperativeHandle(commands, () => ({
    insertText: (code, latex, cursorOffset) => {
      const mf = activeField();
      if (mf && cursorOffset === undefined) { mf.insert(latex || code); updateFormula(mf.dataset.formulaId!, mf); mf.focus(); return; }
      if (mf) { if (commit() === null) return; const span = getSpan(mf.dataset.formulaId!); if (span) view.current?.dispatch({ selection: { anchor: span.to } }); field.current = null; }
      const editor = view.current; if (!editor) return;
      const { from, to } = editor.state.selection.main;
      editor.dispatch({ changes: { from, to, insert: code }, selection: { anchor: from + (cursorOffset ?? code.length) },
        effects: latex ? putFormula.of({ id: crypto.randomUUID(), from, to: from + code.length, code, latex }) : [] }); editor.focus();
    },
    insertTemplate: openTemplate, insertSymbol, showSymbols,
    backspace: () => { const mf = activeField(); if (mf) { mf.executeCommand('deleteBackward'); updateFormula(mf.dataset.formulaId!, mf); mf.focus(); } else if (view.current) { deleteCharBackward(view.current); view.current.focus(); } },
    clear: () => { field.current = null; setSymbolInput(null); setError(''); const editor = view.current; if (editor) { editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: '' }, effects: restoreFormulas.of([]) }); editor.focus(); } },
    commit,
  }));
  useEffect(() => {
    const editor = view.current;
    if (editor && editor.state.doc.toString() !== cell.code) editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: cell.code }, effects: restoreFormulas.of(readFormulas(cell.latex, cell.code)) });
  }, [cell.code, cell.latex]);
  useEffect(() => {
    if (symbolInput === null) return;
    const close = (event: Event) => { if (!(event.target instanceof Element && event.target.closest('.symbol-input'))) setSymbolInput(null); };
    window.addEventListener('resize', close); window.addEventListener('scroll', close, true);
    return () => { window.removeEventListener('resize', close); window.removeEventListener('scroll', close, true); };
  }, [symbolInput === null]);
  return <div className="unified-editor"><div className="expression-editor" ref={host} /><button className="formula-launch icon-button" title={t('插入公式')} onPointerDown={event => event.preventDefault()} onClick={() => openTemplate('#0')}><Sigma size={16} /></button>
    {symbolInput !== null && createPortal(<div className="symbol-input" style={popup} role="group" aria-label={t('特殊符号')}>
      <input autoFocus aria-label={t('特殊符号缩写')} value={symbolInput} onChange={event => setSymbolInput(event.target.value)} onKeyDown={event => {
        if (event.key === 'Escape' || event.key === 'Enter') { event.preventDefault(); event.stopPropagation(); if (symbolInput) insertSymbol(symbolInput); else { setSymbolInput(null); (symbolTarget.current && findField(symbolTarget.current) || view.current)?.focus(); } }
      }} />
      <div className="symbol-options">{specialSymbols.filter(item => item.aliases.some(alias => alias.toLowerCase().startsWith(symbolInput.toLowerCase()))).sort((a, b) => Number(!!b.template) - Number(!!a.template)).slice(0, 120).map((item, index) => <button key={`${item.name}-${index}`} title={`${item.name} · Esc-${item.aliases[0]}-Esc`} onClick={() => insertSymbol(item.aliases[0])}><span>{item.symbol || ({ Integral: '∫', DefiniteIntegral: '∫', Sum: '∑', Product: '∏', Sqrt: '√', Fraction: 'a/b', Superscript: 'xⁿ', Subscript: 'xₙ', Limit: 'lim' }[item.name])}</span><code>{item.aliases[0]}</code></button>)}</div>
      <button className="icon-button" title={t('关闭')} onClick={() => { setSymbolInput(null); (symbolTarget.current && findField(symbolTarget.current) || view.current)?.focus(); }}><X size={15} /></button>
    </div>, document.body)}
    {error && <div className="error-message" role="alert">{error}</div>}</div>;
}
