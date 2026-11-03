"""Compact equivalent radicals at print time, without rewriting kernel values."""
import sympy as s
from sympy.printing.latex import LatexPrinter
from sympy.printing.mathematica import MCodePrinter
from sympy.printing.str import StrPrinter
from sympy.printing.codeprinter import CodePrinter


def _merge_roots(expression):
    if not expression.is_Mul:
        return expression
    groups = {}
    for factor in expression.args:
        if (factor.is_Pow and factor.exp in (s.S.Half, -s.S.Half)
                and factor.base.is_positive is True):
            groups.setdefault(factor.exp, []).append(factor)
    merge = {exponent:factors for exponent,factors in groups.items() if len(factors)>1}
    if not merge:
        return expression
    removed = {factor for factors in merge.values() for factor in factors}
    factors = [factor for factor in expression.args if factor not in removed]
    factors.extend(s.Pow(s.Mul(*(factor.base for factor in group)), exponent, evaluate=False)
                   for exponent,group in merge.items())
    return s.Mul(*factors,evaluate=False)


class _CompactRadicals:
    def _print_Mul(self, expression):
        merged = _merge_roots(expression)
        if merged is expression or merged.is_Mul:
            return super()._print_Mul(merged)
        return self._print(merged)


class _Latex(_CompactRadicals, LatexPrinter):
    pass


class _Wolfram(MCodePrinter):
    def _print_Mul(self, expression):
        merged = _merge_roots(expression)
        if merged is expression:
            return super()._print_Mul(expression)
        return CodePrinter._print_Mul(self, merged) if merged.is_Mul else self._print(merged)


class _String(_CompactRadicals, StrPrinter):
    pass


def expression_latex(value):
    return _Latex().doprint(value)


def expression_text(value):
    return _Wolfram().doprint(value)


def expression_string(value):
    return _String().doprint(value)
