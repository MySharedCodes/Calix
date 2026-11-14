import { useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { t } from './i18n';
import { findSpecialSymbol, specialSymbols, type SpecialSymbol } from './special-symbols';

export type SymbolAnchor = { left: number; bottom: number };
export function TextSymbolInput({ anchor, onInsert, onClose }: { anchor: SymbolAnchor; onInsert: (symbol: SpecialSymbol) => void; onClose: () => void }) {
  const [alias, setAlias] = useState('');
  const [error, setError] = useState(false);
  const insert = (name: string) => {
    const symbol = findSpecialSymbol(name);
    if (symbol) onInsert(symbol); else setError(true);
  };
  return createPortal(<div className="symbol-input" role="group" aria-label={t('特殊符号')} style={{
    left: Math.max(8, Math.min(anchor.left, innerWidth - Math.min(460, innerWidth - 16) - 8)),
    top: Math.max(8, Math.min(anchor.bottom + 6, innerHeight - 260)),
  }} onKeyDown={event => {
    if (event.key === 'Escape' || event.key === 'Enter') {
      event.preventDefault(); event.stopPropagation();
      if (alias) insert(alias); else onClose();
    }
  }}>
    <input autoFocus aria-label={t('特殊符号缩写')} value={alias} onChange={event => { setAlias(event.target.value); setError(false); }} />
    <div className="symbol-options">{specialSymbols.filter(item => item.aliases.some(name => name.toLowerCase().startsWith(alias.toLowerCase()))).slice(0, 120).map((item, index) =>
      <button key={`${item.name}-${index}`} title={`${item.name} · Esc-${item.aliases[0]}-Esc`} onMouseDown={event => event.preventDefault()} onClick={() => insert(item.aliases[0])}><span>{item.symbol || item.name}</span><code>{item.aliases[0]}</code></button>)}</div>
    <button className="icon-button" title={t('关闭')} onClick={onClose}><X size={15} /></button>
    {error && <span role="alert">{t('未找到特殊符号')}: {alias}</span>}
  </div>, document.body);
}

export const textSymbolLatex = (symbol: SpecialSymbol) => symbol.template?.replace(/#\d+/g, '\\square');
