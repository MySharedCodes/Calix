import numpy as np
import pytest
import sympy as s

from backend.dense import machine_matrix
from backend.engine import Engine
from backend.syntax import InputError, parse


def test_extrema_preserve_exact_order_and_high_precision():
    engine = Engine()
    values = [s.Rational(1, 3), s.Rational(1, 3) + s.Rational(1, 10**100)]
    engine.environment['a'] = values
    assert engine.evaluate(parse('Max[a]')) == values[1]
    assert engine.evaluate(parse('Min[a]')) == values[0]
    values = [s.Float('1.000000000000000000000000000001', 60), s.Float(1, 60)]
    engine.environment['a'] = values
    assert engine.evaluate(parse('Max[a]')) == values[0]
    assert engine.execute('Max[{x,2}]')['text'] == 'Max[2, x]'
    assert engine.execute('Min[]')['text'] == 'Infinity'
    assert engine.execute('Max[]')['text'] == '-Infinity'


def test_matrix_packing_excludes_exact_symbolic_and_high_precision():
    assert machine_matrix([[s.Rational(1, 3), 2]]) is None
    assert machine_matrix([[s.Float(1, 70), 2]]) is None
    assert machine_matrix([[1., s.Symbol('x')]]) is None
    assert machine_matrix([[1., 10**100]]) is None
    assert machine_matrix([[float('inf'), 2.]]) is None
    engine = Engine()
    assert engine.execute('Inverse[{{1/3,0},{0,1/7}}]')['text'] == '{{3, 0}, {0, 7}}'
    result = engine.evaluate(parse('Transpose[{{N[1/3,60],0},{0,1}}]'))
    assert isinstance(result, s.MatrixBase) and result[0, 0]._prec > 150


@pytest.mark.parametrize('translation', [(0., 0.), (3., -7.)])
def test_numeric_triangle_gradient_and_area(translation):
    engine = Engine()
    q = np.array([[0., 0.], [2., 0.], [.2, 1.]])
    gradient = np.array([[.001, -.002], [.003, -.004]])
    engine.environment.update(q=q.tolist(), u=(q @ gradient.T + translation).tolist())
    actual = engine.evaluate(parse('''g={{-1,-1},{1,0},{0,1}};
        Dot[Transpose[u],g,Inverse[Dot[Transpose[q],g]]]'''))
    assert isinstance(actual, np.ndarray)
    assert np.allclose(actual, gradient, rtol=1e-11, atol=1e-14)
    area = engine.evaluate(parse('Abs[Det[Dot[Transpose[q],g]]]/2'))
    assert float(area) == pytest.approx(1.)
    engine.environment['a'] = actual
    assert np.allclose(engine.evaluate(parse('Dot[a,a]')), gradient @ gradient)


def test_numeric_inverse_reports_singular_matrix():
    engine = Engine()
    engine.environment['a'] = np.array([[1., 2.], [2., 4.]])
    with pytest.raises(InputError, match='singular'):
        engine.execute('Inverse[a]')


def test_native_coordinate_mean_preserves_exact_and_high_precision():
    engine = Engine()
    engine.environment['q'] = [[1., 2.], [2., 3.], [3., 4.]]
    assert engine.evaluate(parse('Mean[q]')) == [2., 3.]
    assert engine.execute('Mean[{{1,2},{2,3}}]')['text'] == '{3/2, 5/2}'
    value = engine.evaluate(parse('Mean[{N[1/3,60],N[1/3,60]}]'))
    assert value._prec > 150
