"""Independent arithmetic, residual and conservation checks for the public core."""
from fractions import Fraction
import math
import random
import statistics

import pytest

from backend.engine import Engine
from backend.syntax import InputError, parse
from pint.errors import DimensionalityError


def value(code):
    return Engine().evaluate(parse(code))


@pytest.mark.parametrize('seed', range(12))
def test_exact_arithmetic_against_python_fractions(seed):
    rng = random.Random(seed)
    a, b, c, d = [rng.randint(1, 1000) for _ in range(4)]
    expected = (Fraction(a, b) + Fraction(c, d)) * (Fraction(a, b) - Fraction(c, d))
    answer = value(f'({a}/{b}+{c}/{d})*({a}/{b}-{c}/{d})')
    assert Fraction(int(answer.p), int(answer.q)) == expected


@pytest.mark.parametrize('degree', [2, 3, 5, 8, 12])
def test_polynomial_derivatives_at_rational_points(degree):
    # The expected derivative is evaluated with Python rational arithmetic, not another symbolic call.
    x = Fraction(2, 3)
    expected = degree*x**(degree-1) - 6*x + 5
    answer = value(f'ReplaceAll[D[x^{degree}-3*x^2+5*x-7,x],x->2/3]')
    assert Fraction(int(answer.p), int(answer.q)) == expected


@pytest.mark.parametrize('frequency', [1, 3, 9])
def test_quadrature_against_closed_form(frequency):
    answer = float(value(f'NIntegrate[Exp[-x]*Cos[{frequency}*x],{{x,0,2}}]'))
    b = frequency
    expected = (1+math.exp(-2)*(-math.cos(2*b)+b*math.sin(2*b)))/(1+b*b)
    assert abs(answer-expected) < 2e-11


@pytest.mark.parametrize('scale', [1, 17, 10000])
def test_bracketed_root_residual(scale):
    root = float(value(f'FindRoot[x^3-{scale},{{x,0,{scale+1}}}]'))
    assert abs(root**3-scale)/scale < 1e-10


def test_ode_against_sine_and_energy_conservation():
    engine = Engine()
    engine.execute("u=NDSolveValue[{q''[t]==-q[t],q[0]==0,q'[0]==1},q[t],{t,0,12}];")
    for i in range(49):
        time = i/4
        position = float(engine.evaluate(parse(f'u[{time}]')))
        velocity = float(engine.evaluate(parse(f'ReplaceAll[D[u[t],t],t->{time}]')))
        assert abs(position-math.sin(time)) < 2e-7
        assert abs(velocity-math.cos(time)) < 2e-6
        assert abs(position*position+velocity*velocity-1) < 4e-6


def test_statistics_against_python_standard_library():
    data = [12, 5, 19, -4, 8, 8, 11]
    source = '{'+','.join(map(str, data))+'}'
    assert float(value(f'Mean[{source}]')) == pytest.approx(statistics.mean(data))
    assert float(value(f'Variance[{source}]')) == pytest.approx(statistics.variance(data))
    assert float(value(f'StandardDeviation[{source}]')) == pytest.approx(statistics.stdev(data))


def test_unit_round_trip_and_affine_temperature():
    assert float(value('UnitConvert[UnitConvert[650[gr],"g"],"gr"]').magnitude) == pytest.approx(650)
    assert float(value('UnitConvert[0[degC],"K"]').magnitude) == pytest.approx(273.15)
    assert float(value('UnitConvert[1[kg]*1[m/s^2],"N"]').magnitude) == 1
    with pytest.raises((InputError, ValueError, DimensionalityError)):
        value('1[m]+1[s]')


def test_complex_branches_are_not_cancelled():
    answer = complex(value('Sqrt[-1]*Sqrt[-1]'))
    assert answer == -1
    assert complex(value('Log[-1]')) == pytest.approx(complex(0, math.pi))


def test_unevaluated_results_are_distinguishable():
    assert Engine().execute('UnknownSolver[x]')['evaluation_status'] == 'symbolic'
    assert Engine().execute('UnknownSolver[x]')['symbolic_functions'] == ['UnknownSolver']
    assert Engine().execute('Integrate[Exp[x^x],x]')['evaluation_status'] == 'unevaluated'
    assert Engine().execute('1+1')['evaluation_status'] == 'evaluated'
    assert Engine().execute("DSolve[{y'[t]==-y[t],y[0]==1},y[t],t]")['evaluation_status'] == 'evaluated'
    assert Engine().execute('{UnknownSolver[x],1}')['evaluation_status'] == 'symbolic'
