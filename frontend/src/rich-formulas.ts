import { StateEffect, StateField } from '@codemirror/state';
import { Decoration, EditorView, WidgetType } from '@codemirror/view';
import { MathfieldElement } from 'mathlive';
import { invertedEffects } from '@codemirror/commands';

export type FormulaSpan = { id: string; from: number; to: number; latex: string; code: string; draft?: boolean };
export type FormulaHandlers = {
  input: (id: string, field: MathfieldElement) => void;
  focus: (id: string, field: MathfieldElement) => void;
  blur: (field: MathfieldElement) => void;
  keydown: (id: string, field: MathfieldElement, event: KeyboardEvent) => void;
  moveOut: (id: string, direction: string) => void;
};
export const putFormula = StateEffect.define<FormulaSpan>();
export const restoreFormulas = StateEffect.define<FormulaSpan[]>();

export function readFormulas(value: string | undefined, code: string): FormulaSpan[] {
  try {
    const spans: unknown = JSON.parse(value || '[]');
    if (!Array.isArray(spans) || spans.length > 200) return [];
    const ids = new Set<string>();
    return spans.filter((span): span is FormulaSpan => !!span && Number.isInteger(span.from) && Number.isInteger(span.to)
      && span.from >= 0 && span.to > span.from && span.to <= code.length && typeof span.latex === 'string'
      && span.latex.length <= 24000 && typeof span.code === 'string' && code.slice(span.from, span.to) === span.code)
      .sort((a, b) => a.from - b.from).filter((span, i, all) => i === 0 || span.from >= all[i - 1].to)
      .map(span => {
        const id = typeof span.id === 'string' && /^[\w-]{1,80}$/.test(span.id) && !ids.has(span.id) ? span.id : crypto.randomUUID();
        ids.add(id); return { ...span, id, draft: span.draft === true };
      });
  } catch { return []; }
}

export const formulaSpans = StateField.define<FormulaSpan[]>({
  create: () => [],
  update(spans, transaction) {
    let next = spans.filter(span => {
      let touched = false;
      transaction.changes.iterChangedRanges((from, to) => {
        if (from < span.to && to > span.from) touched = true;
      });
      return !touched;
    })
      .map(span => ({ ...span, from: transaction.changes.mapPos(span.from, 1), to: transaction.changes.mapPos(span.to, -1) }));
    if (!transaction.docChanged) next = spans;
    for (const effect of transaction.effects) {
      if (effect.is(restoreFormulas)) next = effect.value;
      if (effect.is(putFormula)) next = [...next.filter(span => span.to <= effect.value.from || span.from >= effect.value.to), effect.value];
    }
    return next.sort((a, b) => a.from - b.from);
  },
});

class FormulaWidget extends WidgetType {
  constructor(readonly span: FormulaSpan, readonly handlers: FormulaHandlers) { super(); }
  eq(other: FormulaWidget) { return JSON.stringify(this.span) === JSON.stringify(other.span); }
  toDOM() {
    const host = document.createElement('span');
    host.className = 'inline-formula-host';
    host.contentEditable = 'false';
    const field = new MathfieldElement();
    field.contentEditable = 'true';
    field.value = this.span.latex;
    field.className = 'inline-formula';
    field.dataset.formulaId = this.span.id;
    field.toggleAttribute('data-draft', !!this.span.draft);
    field.setAttribute('aria-label', 'Formula');
    field.mathVirtualKeyboardPolicy = 'manual';
    const { id } = this.span;
    field.addEventListener('input', event => { event.stopPropagation(); this.handlers.input(id, field); });
    field.addEventListener('focus', () => this.handlers.focus(id, field));
    field.addEventListener('blur', () => this.handlers.blur(field));
    field.addEventListener('keydown', event => this.handlers.keydown(id, field, event), { capture: true });
    field.addEventListener('move-out', event => { event.preventDefault(); this.handlers.moveOut(id, event.detail.direction); });
    host.appendChild(field);
    return host;
  }
  updateDOM(dom: HTMLElement) {
    const field = dom.querySelector('math-field');
    if (!(field instanceof MathfieldElement) || field.dataset.formulaId !== this.span.id) return false;
    // Retain the live field and its caret when the executable source changes length.
    if (field.value !== this.span.latex) field.setValue(this.span.latex, { silenceNotifications: true });
    field.toggleAttribute('data-draft', !!this.span.draft);
    return true;
  }
  ignoreEvent() { return true; }
}

export function formulaDecorations(handlers: FormulaHandlers) {
  const decorations = StateField.define({
    create: () => Decoration.none,
    update: (_value, transaction) => Decoration.set(transaction.state.field(formulaSpans).map(span =>
      Decoration.replace({ widget: new FormulaWidget(span, handlers) }).range(span.from, span.to))),
    provide: field => EditorView.decorations.from(field),
  });
  return [formulaSpans, decorations, EditorView.atomicRanges.of(view => view.state.field(decorations)),
    invertedEffects.of(transaction => transaction.docChanged || transaction.effects.some(effect => effect.is(putFormula) || effect.is(restoreFormulas))
      ? [restoreFormulas.of(transaction.startState.field(formulaSpans))] : [])];
}
