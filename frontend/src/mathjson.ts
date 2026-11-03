import { t } from './i18n';
import { ComputeEngine } from '@cortex-js/compute-engine';
import characters from '../../backend/characters.json';

const ce = new ComputeEngine();
const names: Record<string, string> = { Pi: 'Pi', ExponentialE: 'E', ImaginaryUnit: 'I', PositiveInfinity: 'Infinity', NegativeInfinity: '(-Infinity)' };
for (const [name, character, , latex] of characters) {
  if (/^[α-ωΑ-Ωϐ-Ͽ]$/u.test(character)) names[latex] ??= character;
  names[name] ??= character;
}
const calls: Record<string, string> = {
  Sin: 'Sin', Cos: 'Cos', Tan: 'Tan', Arcsin: 'ArcSin', Arccos: 'ArcCos', Arctan: 'ArcTan',
  Sinh: 'Sinh', Cosh: 'Cosh', Tanh: 'Tanh', Sqrt: 'Sqrt', Exp: 'Exp', Ln: 'Log',
  Abs: 'Abs', Factorial: 'Factorial', Gamma: 'Gamma', Floor: 'Floor', Ceil: 'Ceiling',
};

export function latexToWolfram(latex: string): string {
  if (!latex.trim()) return '';
  const expression = ce.parse(latex, { canonical: false });
  function visit(json: unknown): string {
    if (typeof json === 'number') return String(json);
    if (typeof json === 'string') {
      if (json === 'Nothing' || json === 'Missing') throw new Error(t("数学表达式尚未完成"));
      const styled = json.match(/^([A-Za-z])_(calligraphic|script|fraktur|doublestruck|bold)$/);
      if (styled) {
        const prefix = ({ calligraphic: 'sc', script: 'sc', fraktur: 'fr', doublestruck: 'ds', bold: 'bo' })[styled[2]];
        const character = characters.find(row => row.slice(2).includes(prefix + styled[1]));
        if (character) return character[1];
      }
      if (json === 'RealNumbers') return 'Reals';
      if (json === 'ComplexNumbers') return 'Complexes';
      if (json === 'Integers') return 'Integers';
      return names[json] || json;
    }
    if (json && !Array.isArray(json) && typeof json === 'object') {
      const item = json as { num?: string; sym?: string; fn?: unknown[] };
      if (item.num !== undefined) return String(item.num);
      if (item.sym !== undefined) return visit(item.sym);
      if (item.fn !== undefined) return visit(item.fn);
    }
    if (!Array.isArray(json) || typeof json[0] !== 'string') throw new Error(t("不支持的数学输入结构"));
    const [head, ...args] = json;
    if (head === 'Error') throw new Error(t("数学表达式尚未完成或无法解析"));
    if (head === 'InvisibleOperator' && args.length === 2 && Array.isArray(args[0])
      && args[0][0] === 'PartialDerivative' && args[0][1] === 'Nothing') {
      const variable = visit(args[0][2]);
      if (!/^[\p{L}][₀-₉]*$/u.test(variable)) throw new Error(t('数学表达式尚未完成或无法解析'));
      const order = args[0][3] === 'Nothing' ? '1' : visit(args[0][3]);
      if (!/^[1-9]\d*$/.test(order)) throw new Error(t('数学表达式尚未完成或无法解析'));
      return `D[${visit(args[1])},${order === '1' ? variable : `{${variable},${order}}`}]`;
    }
    if (head === 'Limit' && Array.isArray(args[0]) && args[0][0] === 'Function') {
      return `Limit[${visit(args[0][1])},${visit(args[0][2])}->${visit(args[1])}]`;
    }
    if (head === 'Subscript') {
      const base = visit(args[0]), index = visit(args[1]);
      if (!/^[\p{L}]$/u.test(base) || !/^\d+$/.test(index)) throw new Error(t('下标需要单字母和非负整数'));
      return base + [...index].map(digit => '₀₁₂₃₄₅₆₇₈₉'[Number(digit)]).join('');
    }
    if (head === 'Matrix') return visit(args[0]);
    const values = args.map(visit);
    if (head === 'Add') return `(${values.join('+')})`;
    if (head === 'Multiply' || head === 'InvisibleOperator') return `(${values.join('*')})`;
    if (head === 'Divide' || head === 'Rational') return `(${values[0]}/${values[1]})`;
    if (head === 'Subtract') return `(${values[0]}-${values[1]})`;
    if (head === 'Negate') return `(-${values[0]})`;
    if (head === 'Power') return `(${values[0]}^${values[1]})`;
    if (head === 'Root') return `(${values[0]}^(1/${values[1] || '2'}))`;
    if (head === 'Square') return `(${values[0]}^2)`;
    if (head === 'Degrees') return `(${values[0]}*Pi/180)`;
    if (head === 'Equal') return `${values[0]}==${values[1]}`;
    if (head === 'OverBar' || head === 'Conjugate') return `Conjugate[${values[0]}]`;
    if (head === 'Delimiter') return `(${values[0]})`;
    if (head === 'List' || head === 'Tuple') return `{${values.join(',')}}`;
    if (['Integrate', 'Sum', 'Product'].includes(head)) return `${head}[${values.join(',')}]`;
    if (head === 'Log') return values.length === 1 ? `Log[10,${values[0]}]` : `Log[${values[1]},${values[0]}]`;
    if (calls[head]) return `${calls[head]}[${values.join(',')}]`;
    throw new Error(t('不支持的数学输入结构')+': '+head);
  }
  return visit(expression.json);
}
