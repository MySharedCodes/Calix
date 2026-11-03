import json
import math
import pickle
from pathlib import Path
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import InputError, parse
from backend.interpolation import SampledFunction


@pytest.mark.parametrize('code,expected', [
    ('Mean[{1,2,3,4}]', '5/2'), ('Median[{1,2,3,4}]', '5/2'),
    ('Variance[{1,2,3}]', '1'), ('StandardDeviation[{1,2,3}]', '1'),
    ('Quantile[{1,2,3,4},1/4]', '1'), ('Quartiles[{1,2,3,4}]', '{1, 2, 3}'),
    ('Covariance[{1,2,3},{2,4,6}]', '2'), ('Correlation[{1,2,3},{2,4,6}]', '1'),
    ('SpearmanRho[{1,2,2,4},{1,2,2,4}]', '1'),
    ('PDF[BinomialDistribution[10,1/2],5]', '63/256'),
    ('CDF[BinomialDistribution[10,1/2],5]', '319/512'),
    ('CDF[NormalDistribution[0,1],0]', '1/2'),
    ('Mean[ExponentialDistribution[1/5]]', '5'),
    ('Variance[PoissonDistribution[3]]', '3'),
    ('Fit[{{0,1},{1,3},{2,5}},{1,x},x]', '2*x + 1'),
])
def test_statistics(code, expected):
    assert Engine().execute(code)['text'] == expected


def test_hypothesis_tests():
    engine = Engine()
    assert abs(float(engine.execute('TTest[{1,2,3,4,5},0]')['text']) - 0.0132355995636827) < 1e-12
    assert float(engine.execute('ZTest[{1,2,3},2,1]')['text']) == 1


@pytest.mark.parametrize('code', ['Mean[{}]', 'Variance[{1}]', 'Correlation[{1,1},{2,3}]',
    'Quantile[{1,2},2]', 'Histogram[{1,2},0]', 'NormalDistribution[0,-1]',
    'Fit[{{0,1},{0,2}},{1,x},x]'])
def test_invalid_statistics(code):
    with pytest.raises((InputError, ValueError)):
        Engine().execute(code)


def test_unit_display_and_simplification():
    engine = Engine()
    converted = engine.execute('UnitConvert[1[m],"cm"]')
    assert converted['text'] == '100[cm]'
    assert r'[\mathrm{cm}]' in converted['latex']
    assert Engine().execute('UnitConvert[9.81[m/s^2],"cm/s^2"]')['text'].endswith('[cm / s^2]')
    assert engine.execute('2[kg]*3[m/s^2]')['text'] == '6[N]'
    assert engine.execute('Sin[2*45[deg]]')['text'] == '1'
    for expr, unit in [('kg*m/s^2', 'N'), ('N/m^2', 'Pa'), ('N*m', 'J'), ('J/s', 'W'), ('V/A', 'Ω')]:
        assert engine.execute(f'UnitSimplify["{expr}"]')['text'].endswith(f'[{unit}]')
    with pytest.raises(Exception): engine.execute('2[m]+3[s]')


def test_statistical_plots():
    engine = Engine()
    histogram = engine.execute('Histogram[{1,2,2,3,4},3]')
    assert sum(histogram['traces'][0]['y']) == 5
    assert histogram['traces'][0]['style'] == 'bars'
    assert engine.execute('ListPlot[{{1,2},{2,5}}]')['traces'][0]['style'] == 'markers'


def test_coupled_ode_integral_and_serialization():
    engine = Engine()
    result = engine.execute("v=NDSolveValue[{vx'[t]==-vx[t],vy'[t]==-2 vy[t],vx[0]==1,vy[0]==2},{vx[t],vy[t]},{t,0,2}]")
    assert 'InterpolatingFunction' in result['text'] and len(result['text']) < 400
    assert 'C++' in result['engine']
    engine.environment = pickle.loads(pickle.dumps(engine.environment))
    engine.execute('r=Integrate[v,{t,0,t}]')
    t = s.Symbol('t')
    assert abs(float(engine.environment['v'][0].subs(t,2)) - math.exp(-2)) < 1e-8
    assert abs(float(engine.environment['r'][0].subs(t,2)) - (1-math.exp(-2))) < 1e-8
    assert abs(float(engine.environment['r'][1].subs(t,2)) - (1-math.exp(-4))) < 1e-8
    plot = engine.execute('Plot[Part[r,1],{t,0,2}]')
    assert all(y is not None for y in plot['traces'][0]['y'])


def test_linear_drag_analytic_notebook():
    notebook = json.loads(Path('frontend/src/starter.json').read_text(encoding='utf-8'))
    engine = Engine()
    results=[]
    for cell in notebook['cells']:
        if cell['mode']!='source': continue
        result=engine.execute(cell['code'])
        results.append(result)
        if result['kind']=='animation': break
    t = s.Symbol('t')
    vx,vy=[a.to('m/s').magnitude for a in engine.environment['u']]
    rx,ry=[a.to('m').magnitude for a in engine.environment['r']]
    assert not any(value.has(s.Derivative,s.Integral) for value in (vx,vy,rx,ry))
    z=engine.environment['b'].to('kg/s').magnitude/engine.environment['m'].to('kg').magnitude
    angle=engine.environment['q'][1].to('radian').magnitude
    assert abs(float(vx.subs(t,0))-890*math.cos(float(angle)))<1e-9
    assert abs(float(vy.subs(t,0))-890*math.sin(float(angle)))<1e-9
    for residual in (s.diff(vx,t)+z*vx,s.diff(vy,t)+z*vy+s.Rational(981,100),s.diff(rx,t)-vx,s.diff(ry,t)-vy):
        assert abs(float(residual.subs(t,2)))<1e-9
    assert abs(float(rx.subs(t,0)))<1e-9 and abs(float(ry.subs(t,0)))<1e-9
    assert results[-1]['kind'] == 'animation'
    trace = results[-1]['plot']['traces'][0]
    assert abs(trace['x'][0])<1e-8 and abs(trace['y'][0])<1e-8
    assert all(y is not None and y >= -1e-5 for y in trace['y'])
    assert abs(trace['x'][-1]-7000)<1e-5 and abs(trace['y'][-1])<1e-5


def test_case_notebooks():
    notebooks = json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8'))
    assert len(notebooks) == 17
    assert not any('1988' in notebook['title'] or '2009' in notebook['title'] for notebook in notebooks)
    for notebook in notebooks:
        for cell in notebook['cells']:
            if cell['mode'] == 'markdown':
                assert not any(word in cell['code'] for word in ('来源', '参考', '客观排名', '归纳证明', '最小反例', '因此'))
