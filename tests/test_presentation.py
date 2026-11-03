import sympy as s

from backend.engine import Engine
from backend.presentation import expression_latex, expression_text
from backend.syntax import parse


def test_integral_radicals_merge_in_display_and_reusable_text():
    engine = Engine()
    result = engine.execute('Integrate[x^4*Exp[-3*x^2],{x,-Infinity,Infinity}]')
    assert result['latex'] == r'\frac{\sqrt{3 \pi}}{36}'
    assert '3*Pi' in result['text']
    assert s.simplify(engine.evaluate(parse(result['text']))
                      - s.sqrt(3*s.pi)/36) == 0


def test_display_leaves_kernel_structure_unchanged():
    engine = Engine()
    engine.execute('a=Sqrt[3]*Sqrt[Pi]')
    assert engine.environment['a'] == s.sqrt(3)*s.sqrt(s.pi)
    assert engine.environment['a'].is_Mul
    assert engine.execute('a')['latex'] == r'\sqrt{3 \pi}'


def test_nested_equations_lists_units_and_signs():
    engine = Engine()
    assert engine.execute('{Sqrt[3]*Sqrt[Pi],-Sqrt[2]*Sqrt[Pi]/3}')['latex'] == (
        r'\left\{\sqrt{3 \pi}, - \frac{\sqrt{2 \pi}}{3}\right\}')
    assert r'\sqrt{3 \pi}' in engine.execute('Sqrt[3]*Sqrt[Pi][m]')['latex']
    equation = s.Eq(s.Symbol('x'), s.sqrt(3)*s.sqrt(s.pi), evaluate=False)
    assert expression_latex(equation) == r'x = \sqrt{3 \pi}'


def test_complex_branches_and_unknown_signs_are_not_forced():
    x,y = s.symbols('x y')
    assert expression_latex(s.sqrt(x)*s.sqrt(y)) == r'\sqrt{x} \sqrt{y}'
    assert Engine().execute('Sqrt[-2]*Sqrt[-3]')['text'] == '-6^(1/2)'
    a,b = s.symbols('a b', positive=True)
    assert expression_latex(s.sqrt(a)*s.sqrt(b)) == r'\sqrt{a b}'
    assert expression_latex(1/(s.sqrt(a)*s.sqrt(b))) == r'\frac{1}{\sqrt{a b}}'
    # At x=y=-1, sqrt(x)*sqrt(y)=-1 while sqrt(x*y)=1.
    original = s.sqrt(x)*s.sqrt(y)
    assert original.subs({x:-1,y:-1}) == -1
    assert 'x^(1/2)*y^(1/2)' == expression_text(original)


def test_reciprocals_and_piecewise_format_without_printer_recursion():
    x=s.Symbol('x')
    assert expression_latex(1/(x+1)) == r'\frac{1}{x + 1}'
    assert expression_latex(s.Piecewise((1/x,x>0),(0,True))).startswith(r'\begin{cases}')
