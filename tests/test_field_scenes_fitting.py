import json
import math
from pathlib import Path
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import InputError
from backend.interpolation import SampledFunction


def test_native_two_body_orbit_and_scene():
    engine=Engine()
    engine.execute('orbit=NBodySolve[{1,1},{{-1/2,0},{1/2,0}},{{0,-1/Sqrt[2]},{0,1/Sqrt[2]}},{t,0,1}]')
    orbit=engine.environment['orbit'];t=s.Symbol('t')
    assert all(isinstance(value,SampledFunction) for row in orbit for value in row)
    for at in (0,0.25,0.5,1):
        assert abs(float(orbit[0][0].subs(t,at))+0.5*math.cos(math.sqrt(2)*at))<2e-8
        assert abs(float(orbit[0][1].subs(t,at))+0.5*math.sin(math.sqrt(2)*at))<2e-8
    scene=engine.execute('NBodyPlot3D[orbit,{1,1},{t,0,1}]')
    assert scene['plot_type']=='field3d' and scene['field_kind']=='gravity'
    assert len(scene['paths'])==2 and len(scene['paths'][0])==301
    assert all(p[2]==0 for row in scene['paths'] for p in row)
    assert scene['softening']==0.12 and scene['color_range'][1]<0
    assert 'C++' in scene['engine']


@pytest.mark.parametrize('code',[
    'NBodySolve[{1,1}]',
    'NBodySolve[{1,-1},{{0,0},{1,0}},{{0,0},{0,0}},{t,0,1}]',
    'NBodySolve[{1,1},{{0,0},{0,0}},{{0,0},{0,0}},{t,0,1}]',
    'NBodySolve[{1,1},{{0,0},{1,0}},{{0,0,0},{0,0,0}},{t,0,1}]',
    'NBodyPlot3D[{{t,0},{1,t}},{1},{t,0,1}]',
    'MagneticFieldPlot3D[{1,0,0},{x,x,z},{0},{{t,0,0},{0,t,0}},{t,0,1}]',
    'Show[1,2]',
])
def test_invalid_field_scene_inputs(code):
    with pytest.raises(InputError):Engine().execute(code)


def test_quadratic_drag_velocity_integral_and_energy_loss():
    notebook=json.loads(Path('frontend/src/starter.json').read_text(encoding='utf-8'))
    assert any('第一部分' in c['code'] for c in notebook['cells'] if c['mode']=='markdown')
    engine=Engine()
    results=[engine.execute(c['code']) for c in notebook['cells'] if c['mode']!='markdown']
    assert len(results)==7
    t=s.Symbol('t')
    velocity=[v.to('m/s').magnitude for v in engine.environment['u']]
    position=[v.to('m').magnitude for v in engine.environment['r']]
    assert all(isinstance(v,SampledFunction) for v in velocity+position)
    assert abs(float(position[0].subs(t,0)))<1e-12
    initial=0.5*890**2
    duration=float(engine.environment['q'][2].to('s').magnitude)
    previous=initial
    for i in range(1,101):
        at=duration*i/100
        values=[float(v.subs(t,at)) for v in velocity]
        energy=sum(v*v for v in values)/2+9.81*float(position[1].subs(t,at))
        assert energy<previous
        previous=energy
    assert results[-1]['kind']=='animation' and abs(results[-1]['values'][-1]-duration)<1e-10


def test_many_body_spatial_conservation():
    notebook=next(n for n in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if n['title'].startswith('多天体'))
    engine=Engine()
    results=[engine.execute(c['code']) for c in notebook['cells'] if c['mode']!='markdown']
    assert results[3]['field_kind']=='gravity' and len(results[3]['paths'])==4
    scene=results[4]
    assert len(scene['paths'])==5
    assert any(abs(p[2])>0.5 for row in scene['paths'] for p in row)
    t=s.Symbol('t');energy=engine.environment['H_1'];momentum=engine.environment['p_2']
    energy0=float(energy.subs(t,0))
    for at in (0,0.2,0.6,1.2):
        assert abs(float(energy.subs(t,at))-energy0)<2e-6
        assert max(abs(float(p.subs(t,at))) for p in momentum)<2e-7


def test_fit_overlay_and_normal_equations():
    engine=Engine()
    result=engine.execute('data={{0,1},{1,3},{2,5},{3,7}};f=Fit[data,{1,x},x];Show[ListPlot[data],Plot[f,{x,0,3}]]')
    assert engine.environment['f']==2*s.Symbol('x')+1
    assert len(result['traces'])==2
    assert result['traces'][0]['style']=='markers'
    assert result['traces'][1]['y'][0]==1 and result['traces'][1]['y'][-1]==7
