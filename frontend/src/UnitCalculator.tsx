import { useEffect, useRef, useState } from 'react';
import { Play, Plus, X } from 'lucide-react';
import * as api from './api';
import type { Result } from './types';
import { Output } from './App';
import { t } from './i18n';

export function UnitCalculator({ onClose, onInsert }: { onClose: () => void; onInsert: (code: string) => void }) {
  const [input, setInput] = useState('kg*m/s^2');
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const session = useRef(crypto.randomUUID());
  const mounted = useRef(true);
  const code = `UnitSimplify[${JSON.stringify(input)}]`;
  useEffect(() => { mounted.current = true; const id = session.current; return () => { mounted.current = false; void api.cancel(id); }; }, []);
  const calculate = async () => {
    setBusy(true); setError(''); setResult(undefined);
    try { const value = await api.evaluate(session.current, code); if (mounted.current) setResult(value); }
    catch (e) { if (mounted.current) setError(String(e)); }
    finally { if (mounted.current) setBusy(false); }
  };
  return <div className="modal-backdrop" onClick={onClose}><section className="settings-modal unit-calculator" role="dialog" aria-modal="true" aria-label={t('单位运算器')} onClick={e => e.stopPropagation()}>
    <div className="panel-heading"><strong>{t('单位运算器')}</strong><button className="icon-button" title={t('关闭')} onClick={onClose}><X size={17} /></button></div>
    <form onSubmit={e => { e.preventDefault(); if (!busy) void calculate(); }}>
      <label htmlFor="unit-expression">{t('单位表达式')}</label>
      <input id="unit-expression" value={input} maxLength={1000} onChange={e => { setInput(e.target.value); setResult(undefined); setError(''); }} autoFocus />
      <div className="unit-presets">{['kg*m/s^2','N/m^2','N*m','J/s','V/A'].map(unit => <button key={unit} type="button" onClick={() => { setInput(unit); setResult(undefined); setError(''); }}>{unit}</button>)}</div>
      <div className="unit-actions"><button className="primary-button" disabled={busy || !input.trim()}><Play size={15} />{t('计算')}</button><button type="button" className="subtle-button" disabled={busy || !input.trim()} onClick={() => onInsert(code)}><Plus size={15} />{t('插入计算单元')}</button></div>
    </form>
    {error && <p className="error-message" role="alert">{error}</p>}{result && <Output result={result} />}
  </section></div>;
}
