import json
import math
import pickle
from pathlib import Path
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import InputError


def test_table_scope_and_finite_search():
    engine = Engine()
    engine.execute('i=99')
    assert engine.execute('Table[i^2,{i,1,3}]')['text'] == '{1, 4, 9}'
    assert engine.execute('i')['text'] == '99'
    assert engine.execute('Table[i,{i,2,0,-1/2}]')['text'] == '{2, 3/2, 1, 1/2, 0}'
    assert engine.execute('Flatten[Table[If[i==j,{i,j},Nothing],{i,1,2},{j,1,2}],1]')['text'] == '{{1, 1}, {2, 2}}'
    assert engine.execute('Length[Intersection[{1,2},{3,4}]]')['text'] == '0'
    assert engine.execute('Count[Table[IntegerQ[Sqrt[i]],{i,1,9}],True]')['text'] == '3'
    assert engine.execute('Accumulate[{2,5,1,4}]')['text'] == '{2, 7, 8, 12}'
    with pytest.raises(InputError): engine.execute('Table[i,{i,1,100001}]')
    with pytest.raises(InputError): engine.execute('Permutations[{1,2,3,4,5,6,7,8,9}]')
    with pytest.raises(InputError): engine.execute('If[x>0,1,2]')
    assert engine.execute('i')['text'] == '99'


def test_native_multivariable_second_order_and_pickle():
    engine = Engine()
    engine.execute("solution=NDSolveValue[{a''[t]==-a[t],b''[t]==-4 b[t],c''[t]==-9 c[t],d''[t]==-16 d[t],a[0]==1,b[0]==2,c[0]==3,d[0]==4,a'[0]==0,b'[0]==0,c'[0]==0,d'[0]==0},{a[t],b[t],c[t],d[t]},{t,0,2}]")
    engine.environment = pickle.loads(pickle.dumps(engine.environment))
    t = s.Symbol('t')
    for i, expression in enumerate(engine.environment['solution'], 1):
        assert expression.free_symbols == {t}
        assert abs(float(expression.subs(t, 2))-i*math.cos(2*i)) < 2e-8
    graph = engine.execute('Plot[Total[solution],{t,0,2}]')
    assert 'C++' in graph['engine']
    assert all(value is not None for value in graph['traces'][0]['y'])
    with pytest.raises(InputError): engine.execute("NDSolveValue[{a''[t]==-a[t],a[0]==1},a[t],{t,0,1}]")
    with pytest.raises(InputError): engine.execute("NDSolveValue[{a'''[t]==-a[t],a[0]==1,a'[0]==0,a''[0]==0},a[t],{t,0,1}]")


def test_five_ball_exact_solution():
    notebook = next(item for item in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if item['title'].startswith('五球'))
    engine = Engine()
    for cell in [cell for cell in notebook['cells'] if cell['mode'] == 'source'][:2]:
        engine.execute(cell['code'])
    t = s.Symbol('t')
    positions = engine.environment['r_1']
    initial = engine.environment['r_0']
    substitution = dict(zip(engine.environment['q_2'], positions))
    for i, expression in enumerate(positions):
        assert not expression.has(s.Float, s.Integral, s.Derivative)
        assert s.simplify(expression.subs(t, 0)-initial[i]) == 0
        assert s.simplify(s.diff(expression,t).subs(t, 0)) == 0
        assert s.simplify(s.diff(expression,t,2)-engine.environment['e_1'][i].rhs.subs(substitution, simultaneous=True)) == 0
    assert s.simplify(s.diff(sum(positions)/5,t,2)-s.Rational(981,100)) == 0
    assert [s.simplify(s.diff(value,t,2).subs(t,0)) for value in positions] == [s.Rational(981,20),0,0,0,0]
    for i in range(4):
        values = engine.sample(positions[i+1]-positions[i], [t], [[j/100 for j in range(501)]])
        assert min(values) > 0


def test_graphics_frames_are_finite_and_move():
    result = Engine().execute('Animate[Graphics[{Line[{{0,0},{Sin[t],-Cos[t]}}],Point[{Sin[t],-Cos[t]}]}],{t,0,2}]')
    assert result['kind'] == 'animation'
    assert len(result['frames']) == 61
    assert result['frames'][0]['traces'][1]['style'] == 'markers'
    assert result['frames'][0]['traces'][1]['x'] != result['frames'][-1]['traces'][1]['x']
    assert result['plot']['options']['equal_aspect']
    with pytest.raises(InputError): Engine().execute('Graphics[{Line[{{0,0},{Infinity,1}}]}]')


def run_case(prefix):
    notebook = next(item for item in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if item['title'].startswith(prefix))
    engine = Engine()
    results = [engine.execute(cell['code']) for cell in notebook['cells'] if cell['mode'] == 'source']
    return engine, results


def test_exact_integer_polynomial_and_inequality_functions():
    engine = Engine()
    assert engine.execute('Numerator[13/17]')['text'] == '13'
    assert engine.execute('Denominator[13/17]')['text'] == '17'
    assert engine.execute('CoefficientList[2+3 x^2 y,{x,y}]')['text'] == '{{2, 0}, {0, 0}, {0, 3}}'
    assert engine.execute('CoefficientList[0,{x,y}]')['text'] == '{{0}}'
    assert engine.execute('PowerMod[1978,103,1000]')['text'] == '352'
    assert engine.execute('IntegerLength[-1000]')['text'] == '4'
    assert engine.execute('IntegerLength[0]')['text'] == '1'
    assert engine.execute('IntegerLength[8,2]')['text'] == '4'
    assert engine.execute('GCD[12,-18,30]')['text'] == '6'
    assert 'x < 2' in engine.execute('Reduce[{x^2<4,x>0},x,Reals]')['text']
    with pytest.raises(InputError): engine.execute('PowerMod[2,-1,7]')
    with pytest.raises(InputError): engine.execute('CoefficientList[1/x,x]')
    with pytest.raises(InputError): engine.execute('Reduce[x+y>0,x,Reals]')
    with pytest.raises(InputError): engine.execute('IntegerLength[2,1]')
    graph = engine.execute('Plot[{x,x^2},{x,0,1},PlotLegends->{"linear","square"}]')
    assert [trace['name'] for trace in graph['traces']] == ['linear', 'square']
    with pytest.raises(InputError): engine.execute('Plot[{x,x^2},{x,0,1},PlotLegends->{"one"}]')


def test_gaokao_exact_bounds_and_imo_results():
    engine, results = run_case('高考数学')
    assert engine.environment['b_5'] == [1, 2]
    assert engine.environment['c_3'] == [[s.true, s.true]]*4
    assert s.simplify(engine.environment['f_8'].subs(s.Symbol('x'),1)-(s.sqrt(2)+s.Rational(1,3))) == 0
    assert results[0]['items'][2]['text'].count('x') >= 2
    harmonic, _ = run_case('IMO 1979')
    p, q = harmonic.environment['p'], harmonic.environment['q']
    assert s.gcd(p,q) == 1 and p % 1979 == 0 and q % 1979 != 0
    powers, _ = run_case('IMO 1978')
    assert powers.environment['b_2'] == 106
    assert powers.environment['w_1'] == [[3, 103, 352]]
    assert powers.environment['b_2'] < powers.environment['b_4']+1


def test_large_pendulum_and_falling_ball_comparison():
    engine, results = run_case('弹性双摆')
    t = s.Symbol('t')
    assert float(engine.environment['x_0'][0]) > 1
    assert engine.environment['θ_1'] == s.pi/3
    assert engine.environment['θ_2'] == -s.pi/4
    assert sum(result['kind'] == 'animation' for result in results) == 1
    energy = engine.environment['H']
    values = [float(energy.subs(t,6*i/100)) for i in range(101)]
    assert max(values)-min(values) < 2e-6
    positions = engine.environment['r_1']
    for i in range(101):
        point = [float(value.subs(t,6*i/100)) for value in positions]
        assert math.hypot(*point[:2]) > 0.05
        assert math.hypot(point[2]-point[0],point[3]-point[1]) > 0.05
    chain, results = run_case('五球')
    assert chain.environment['b_3'].subs(t,0) == 0
    assert chain.environment['n_2'].subs(t,0) == 0
    assert chain.environment['f_1'] == s.Rational(981,200)*t**2
    comparison = results[-2]['items'][0]
    assert [trace['name'] for trace in comparison['traces']] == ['最下方小球', '倒数第二个小球', '自由落体']
    assert comparison['traces'][0]['x'][-1] == 5
    assert results[-1]['values'][-1] == 5
    baseline = results[-2]['items'][1]['traces'][-1]
    assert baseline['name'] == '自由落体（零基线）'
    assert set(baseline['y']) == {0}
    assert len(baseline['x']) == 801


def test_planar_three_body_conservation_and_orbit():
    engine, results = run_case('多天体')
    t = s.Symbol('t')
    motion = engine.environment['r_1']
    initial = [float(value) for value in engine.environment['p_0']]
    assert len(motion) == 6
    for sample in range(101):
        at = 6.3259*sample/100
        points = [float(value.subs(t,at)) for value in motion]
        assert abs(sum(points[::2])) < 1e-7 and abs(sum(points[1::2])) < 1e-7
        for i in range(3):
            for j in range(i):
                assert math.hypot(points[2*i]-points[2*j],points[2*i+1]-points[2*j+1]) > 0.1
        for component in engine.environment['p_1']:
            assert abs(float(component.subs(t,at))) < 1e-7
        assert abs(float(engine.environment['L'].subs(t,at))) < 2e-6
        assert abs(float(engine.environment['H'].subs(t,at)-engine.environment['H'].subs(t,0))) < 2e-6
    assert max(abs(float(value.subs(t,6.3259))-start) for value,start in zip(motion,initial)) < 5e-5
    animation = results[2]
    assert animation['kind'] == 'animation'
    assert animation['plot']['plot_type'] == 'surface'
    assert len(animation['frames']) == 61
    assert len(animation['frames'][0]['z']) == 41
    assert animation['frames'][0]['z'] != animation['frames'][7]['z']
    for frame in animation['frames']:
        assert all(value is not None and math.isfinite(value) and value < 0 for row in frame['z'] for value in row)
    expected = -2/math.sqrt(initial[0]**2+initial[1]**2+0.15**2)-1/0.15
    assert abs(animation['frames'][0]['z'][20][20]-expected) < 1e-8


def test_surface_animation_scope_and_gaokao_physics_symbols():
    engine = Engine()
    engine.execute('a=9')
    animation = engine.execute('Animate[Plot3D[a*Cos[x]*Cos[y],{x,-1,1},{y,-1,1},BoxRatios->{1,1,1/2}],{a,0,1}]')
    assert engine.execute('a')['text'] == '9'
    assert animation['frames'][0]['z'][20][20] == 0
    assert abs(animation['frames'][-1]['z'][20][20]-1) < 1e-12
    assert animation['plot']['options']['box_ratios'] == [1,1,0.5]
    with pytest.raises(InputError): engine.execute('Plot3D[x*y,{x,0,1},{y,0,1},BoxRatios->{1,0,1}]')
    with pytest.raises(InputError): engine.execute('Plot[x,{x,0,1},BoxRatios->{1,1,1}]')
    physics, results = run_case('高考物理')
    assert s.Symbol('S') in physics.environment['Φ'].free_symbols
    assert s.Symbol('area') not in physics.environment['Φ'].free_symbols
    assert s.simplify(physics.environment['F']-s.Symbol('B_0')*s.Symbol('ℓ')*(s.Symbol('k')*s.Symbol('S')+s.Symbol('B_0')*s.Symbol('ℓ')*s.Symbol('v_0'))/s.Symbol('R')) == 0
