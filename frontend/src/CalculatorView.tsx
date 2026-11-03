import { t } from './i18n';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Copy, Delete, LoaderCircle, Omega, Play, Square, Trash2 } from 'lucide-react';
import * as api from './api';
import type { Cell, Result } from './types';
import { Output } from './App';
import { Editor, type EditorCommands } from './Editor';

const pages = [
  { title: '基础', keys: ['Sin','Cos','Tan','(',')','Sqrt','Log','Exp','^','°','7','8','9','/','Pi','4','5','6','*','E','1','2','3','-','I','0','.',',','+','Run'] },
  { title: '函数', keys: ['ArcSin','ArcCos','ArcTan','Sinh','Cosh','Tanh','Abs','!','Gamma','Beta','Erf','BesselJ','BesselY','AiryAi','Zeta','Hypergeometric2F1','HypergeometricPFQ','Binomial','Floor','Ceiling','Re','Im','Conjugate','Log10','N','Det','Inverse','Mean','StandardDeviation','Run'] },
  { title: '求解', keys: ['Sum','Product','Limit','Series','D','Integrate','NIntegrate','Solve','NSolve','FindRoot','DSolve','RSolve','Simplify','Expand','Factor','UnitConvert','Transpose','Eigenvalues','Together','ComplexExpand','Plot','Plot3D','ParametricPlot','ContourPlot','Animate','Minimize','Maximize','FindMinimum','FindMaximum','Run'] },
];
const utilityLabels: Record<string,string> = { Det:'行列式',Inverse:'逆矩阵',Mean:'平均值',StandardDeviation:'标准差',Transpose:'转置',Eigenvalues:'特征值',Together:'通分',ComplexExpand:'复数化简',Animate:'动画',Minimize:'解析最小值',Maximize:'解析最大值',FindMinimum:'数值最小值',FindMaximum:'数值最大值' };
const utilityTemplates: Record<string,string> = {
  Det:'Det[{{2,1},{1,3}}]', Inverse:'Inverse[{{2,1},{1,3}}]',
  Mean:'Mean[{1,2,3,4,5}]', StandardDeviation:'StandardDeviation[{1,2,3,4,5}]',
  Transpose:'Transpose[{{1,2,3},{4,5,6}}]', Eigenvalues:'Eigenvalues[{{2,1},{1,2}}]',
  Together:'Together[1/(x-1)-1/(x+1)]', ComplexExpand:'ComplexExpand[(x+I*y)*(x-I*y)]',
  Animate:'Animate[Plot[Sin[x-t],{x,0,2 Pi}],{t,0,2 Pi}]',
  Minimize:'Minimize[x^2-4*x+5,x]', Maximize:'Maximize[-x^2+4*x+1,x]',
  FindMinimum:'FindMinimum[x^2+Sin[x],{x,-2,2}]', FindMaximum:'FindMaximum[-x^2+Cos[x],{x,-2,2}]',
};
const compactLabels: Record<string,string> = { UnitConvert:'换算单位',ComplexExpand:'复数式' };
const labels: Record<string,string> = { Sin:'sin',Cos:'cos',Tan:'tan',Sqrt:'√',Log:'ln',Exp:'eˣ',Pi:'π','*':'×','/':'÷','^':'xʸ',I:'ⅈ',Infinity:'∞',Log10:'log₁₀',Hypergeometric2F1:'₂F₁',HypergeometricPFQ:'ₚFq',Conjugate:'z̄',UnitConvert:'单位换算',Quantity:'单位量',ParametricPlot:'参数曲线',ContourPlot:'等高线',NIntegrate:'∫ ≈',FindRoot:'数值求根',ArcSin:'sin⁻¹',ArcCos:'cos⁻¹',ArcTan:'tan⁻¹',Sinh:'sinh',Cosh:'cosh',Tanh:'tanh',Abs:'|x|',Gamma:'Γ',Beta:'B',Erf:'erf',BesselJ:'Jₙ',BesselY:'Yₙ',AiryAi:'Ai',Zeta:'ζ',Binomial:'Cₙᵏ',Floor:'⌊x⌋',Ceiling:'⌈x⌉',Re:'Re',Im:'Im',N:'≈',Sum:'∑',Product:'∏',Limit:'lim',Series:'级数',D:'∂ₓ',Integrate:'∫',Solve:'解析求解',NSolve:'数值求解',DSolve:'微分方程',RSolve:'差分方程',Simplify:'化简',Expand:'展开',Factor:'因式分解',Plot:'曲线',Plot3D:'曲面','->':'→','==':'=' };
const symbols: Record<string,string> = {Sum:'sum',Product:'prod',Limit:'lim',D:'pdiff',Integrate:'intt',Sqrt:'sqrt',Abs:'abs',Conjugate:'conj','^':'sup'};
const mathTemplates: Record<string,string> = {Sin:'\\sin\\left(#0\\right)',Cos:'\\cos\\left(#0\\right)',Tan:'\\tan\\left(#0\\right)',Log:'\\ln\\left(#0\\right)',Exp:'e^{#0}',ArcSin:'\\arcsin\\left(#0\\right)',ArcCos:'\\arccos\\left(#0\\right)',ArcTan:'\\arctan\\left(#0\\right)',Sinh:'\\sinh\\left(#0\\right)',Cosh:'\\cosh\\left(#0\\right)',Tanh:'\\tanh\\left(#0\\right)',Floor:'\\lfloor#0\\rfloor',Ceiling:'\\lceil#0\\rceil',Gamma:'\\Gamma\\left(#0\\right)'};
const constants: Record<string,string> = {Pi:'\\pi',Infinity:'\\infty',I:'\\imaginaryI','*':'\\times','/':'\\div','°':'\\degree'};
const templates: Record<string,string> = { Sum:'Sum[k, {k, 1, 10}]',Product:'Product[k, {k, 1, 5}]',Limit:'Limit[Sin[x]/x, x -> 0]',Series:'Series[Exp[x], {x, 0, 5}]',D:'D[Sin[x], x]',Integrate:'Integrate[Sin[x], x]',NIntegrate:'NIntegrate[Sin[x], {x, 0, Pi}]',Solve:'Solve[x^2 == 2, x]',NSolve:'NSolve[x^2 == 2, x]',FindRoot:'FindRoot[Cos[x]-x, {x, 0, 1}]',DSolve:"DSolve[{y'[x]==-y[x],y[0]==1}, y[x], x]",RSolve:'RSolve[{a[n+1]==2 a[n],a[0]==1}, a[n], n]',UnitConvert:'UnitConvert[1[m], "cm"]',Quantity:'Quantity[1, "m"]',Plot:'Plot[Sin[x], {x, -Pi, Pi}]',Plot3D:'Plot3D[Sin[x] Cos[y], {x,-Pi,Pi}, {y,-Pi,Pi}]',ParametricPlot:'ParametricPlot[{Cos[t],Sin[t]}, {t,0,2 Pi}]',ContourPlot:'ContourPlot[x^2+y^2, {x,-2,2}, {y,-2,2}]',Hypergeometric2F1:'Hypergeometric2F1[1/2,1/2,1,1/2]',HypergeometricPFQ:'HypergeometricPFQ[{1,1},{2},1/2]',BesselJ:'BesselJ[0,1]',BesselY:'BesselY[0,1]',Beta:'Beta[2,3]',Binomial:'Binomial[10,3]'};
const unary = new Set(['Sin','Cos','Tan','Sqrt','Log','Exp','ArcSin','ArcCos','ArcTan','Sinh','Cosh','Tanh','Abs','Gamma','Erf','AiryAi','Zeta','Floor','Ceiling','Re','Im','Conjugate','Simplify','Expand','Factor','N']);

function KeyLabel({ text }: { text:string }) {
  const label=useRef<HTMLSpanElement>(null);
  useLayoutEffect(()=>{
    const span=label.current,button=span?.parentElement;
    if(!span||!button)return;
    const fit=()=>{
      const style=getComputedStyle(button);
      const height=button.clientHeight-parseFloat(style.paddingTop)-parseFloat(style.paddingBottom);
      let size=parseFloat(style.fontSize);
      span.style.fontSize=`${size}px`;
      while(size>9&&(span.getBoundingClientRect().height>height||span.scrollWidth>span.clientWidth)){
        size-=0.5;span.style.fontSize=`${size}px`;
      }
    };
    fit();const observer=new ResizeObserver(fit);observer.observe(button);
    return()=>observer.disconnect();
  },[text]);
  return <span ref={label} style={{display:'block',maxWidth:'100%',lineHeight:1.15}}>{text}</span>;
}

export function CalculatorView({ ready, digits, toast, onBusyChange }: { ready: boolean; digits: number; toast: (s: string) => void; onBusyChange: (busy:boolean) => void }) {
  const [cell, setCell] = useState<Cell>(()=>({id:crypto.randomUUID(),mode:'source',code:''}));
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(0);
  const [history, setHistory] = useState<{ input: string; latex?:string; result: Result }[]>([]);
  const session = useRef(crypto.randomUUID());
  const commands = useRef<EditorCommands>(null);
  const running = useRef(false), generation = useRef(0);
  const cellRef=useRef(cell);cellRef.current=cell;
  const run = async (approximate = false, source?:string) => {
    if (running.current || !ready) return;
    const input=source??commands.current?.commit();
    if (!input?.trim()) return;
    const ticket=++generation.current;
    running.current=true;setBusy(true);onBusyChange(true);setError('');
    try { const output = await api.evaluate(session.current, approximate ? `N[${input},${digits}]` : input); if(ticket!==generation.current)return;setResult(output); setHistory(p => [{ input, latex:cellRef.current.latex, result: output }, ...p].slice(0,40)); }
    catch(e) { if(ticket===generation.current)setError(e instanceof Error ? e.message : String(e)); }
    finally { if(ticket===generation.current){running.current=false;setBusy(false);onBusyChange(false);} }
  };
  const stop = async () => {
    if(!running.current)return;
    ++generation.current;
    try { await api.cancel(session.current); }
    catch(e){setError(e instanceof Error?e.message:String(e));}
    finally {running.current=false;setBusy(false);onBusyChange(false);}
  };
  const stopRef=useRef(stop);stopRef.current=stop;
  useEffect(()=>{
    const key=(event:KeyboardEvent)=>{if(event.altKey&&event.code==='Period'){event.preventDefault();void stopRef.current();}};
    const id=session.current;
    window.addEventListener('keydown',key);
    return()=>{window.removeEventListener('keydown',key);++generation.current;void api.cancel(id).catch(()=>{});};
  },[]);
  const insert = (key: string) => {
    if(symbols[key])commands.current?.insertSymbol(symbols[key]);
    else if(mathTemplates[key])commands.current?.insertTemplate(mathTemplates[key]);
    else if(unary.has(key))commands.current?.insertText(`${key}[]`,undefined,key.length+1);
    else if(key==='Log10')commands.current?.insertText('Log[10,]',undefined,7);
    else { const template=utilityTemplates[key]||templates[key]; commands.current?.insertText(template||key,constants[key],template?.length); }
  };
  return <main className="calculator-workspace"><div className="calculator-main">
    <div className="calculator-title"><h1>{t("传统计算器面板")}</h1></div>
    <section className={`calculator-cell ${busy?'running':''}`}><div className="cell-header"><span className="input-label">In[1]:=</span><div className="calculator-cell-tools"><button className="icon-button" title={t('特殊符号')} onPointerDown={e=>e.preventDefault()} onClick={()=>commands.current?.showSymbols()}><Omega size={18}/></button><button className="icon-button" title={busy?t('停止计算')+' · Alt+.':t('运行单元')+' · Ctrl+Enter'} disabled={!ready} onPointerDown={e=>e.preventDefault()} onClick={()=>busy?void stop():void run()}>{busy?<Square size={16}/>:<Play size={16}/>}</button></div></div><Editor cell={cell} commands={commands} onChange={(code,latex)=>setCell(p=>({...p,code,latex}))} onRun={source=>void run(false,source)}/>{busy&&<div className="pending"><LoaderCircle size={14} className="spin"/>{t('计算中')}</div>}{error?<div className="error-message" role="alert">{error}</div>:result?<div className="output"><div className="output-label">Out[1]=</div><Output result={result}/></div>:null}</section>
    <div className="calculator-actions"><button title={t('清空')} disabled={busy} onPointerDown={e=>e.preventDefault()} onClick={()=>{commands.current?.clear();setResult(null);setError('');}}>AC</button><button title={t("删除")} onPointerDown={e=>e.preventDefault()} onClick={()=>commands.current?.backspace()}><Delete size={19}/></button><button title={t("数值近似")} disabled={busy||!ready} onPointerDown={e=>e.preventDefault()} onClick={()=>void run(true)}>≈</button><button title={t("复制结果")} disabled={!result||result.kind!=='expression'} onClick={()=>{if(result?.kind==='expression')void navigator.clipboard.writeText(result.text).then(()=>toast(t("结果已复制")));}}><Copy size={17}/></button></div>
    <div className="keypad-pages"><button title={t("上一页按钮")} onClick={()=>setPage((page+2)%3)}><ChevronLeft size={16}/></button><div className="segmented" role="tablist" aria-label={t("按钮页")}>{pages.map((p,i)=><button key={t(p.title)} role="tab" aria-selected={page===i} className={page===i?'selected':''} onClick={()=>setPage(i)}>{t(p.title)}</button>)}</div><button title={t("下一页按钮")} onClick={()=>setPage((page+1)%3)}><ChevronRight size={16}/></button></div>
    <div className="calculator-keys">{pages[page].keys.map(key=><button key={key} title={key==='Run'?`${t('运行单元')} · Ctrl+Enter`:utilityLabels[key]?`${t(utilityLabels[key])} · ${key}`:symbols[key]?`${key} · Esc-${symbols[key]}-Esc`:key} aria-label={key==='Run'?t('计算'):undefined} className={`${/^\d$|\./.test(key)?'number':'function'} ${key==='Run'?'equals':''}`} disabled={key==='Run'&&(busy||!ready)} onPointerDown={e=>e.preventDefault()} onClick={()=>key==='Run'?void run():insert(key)}>{key==='Run'?(busy?<LoaderCircle className="spin" size={20}/>:<Play size={20}/>):<KeyLabel text={t(compactLabels[key]||utilityLabels[key]||labels[key]||key)}/>}</button>)}</div>
  </div><aside className="calculator-history"><div className="panel-heading"><strong>{t("历史记录")}</strong><button title={t("清空历史")} className="icon-button" disabled={!history.length} onClick={()=>setHistory([])}><Trash2 size={16}/></button></div>{history.map((entry,i)=><button className="history-item" key={i} disabled={busy} onClick={()=>{commands.current?.clear();setCell(p=>({...p,code:entry.input,latex:entry.latex}));setResult(entry.result);setError('');}}><code>{entry.input}</code><span>{entry.result.kind==='expression'?entry.result.text:entry.result.kind==='plot'?entry.result.title:entry.result.kind==='animation'?t("动画"):t("多个结果")}</span></button>)}</aside></main>;
}
