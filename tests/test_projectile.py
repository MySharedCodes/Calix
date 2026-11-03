import math
import json
import pickle
from pathlib import Path

import pytest
import sympy as s

from backend.engine import Engine
from backend.native import kernel
from backend.syntax import parse


@pytest.mark.parametrize('model,coefficient,unit', [('Linear',0.00504763605146416,'kg/s'),('Quadratic',0.000013049143921516,'kg/m')])
def test_calibration_and_independent_landing(model,coefficient,unit):
    scipy=pytest.importorskip('scipy.integrate')
    e=Engine()
    e.execute(f'm=650[gr];v=890[m/s];g=9.81[m/s^2];c={coefficient}[{unit}];')
    e.execute(f'q=ProjectileOptimum[c,m,v,g,"{model}"];')
    distance,angle,duration=e.environment['q']
    assert abs(float(distance.to('km').magnitude)-7)<1e-8
    mass=float(e.environment['m'].to('kg').magnitude)
    theta=float(angle.to('radian').magnitude)
    def rhs(t,u):
        z=coefficient/mass*(1 if model=='Linear' else math.hypot(u[2],u[3]))
        return [u[2],u[3],-z*u[2],-9.81-z*u[3]]
    def landing(t,u):return u[1]
    landing.direction=-1
    landing.terminal=True
    ref=scipy.solve_ivp(rhs,(0,300),[0,0,890*math.cos(theta),890*math.sin(theta)],events=landing,rtol=1e-11,atol=1e-10)
    assert abs(ref.y_events[0][0,0]-7000)<1e-4
    assert abs(ref.t_events[0][0]-float(duration.to('s').magnitude))<1e-5
    for a in range(1,90):
        r=kernel.projectile(coefficient,mass,890,9.81,1 if model=='Linear' else 2,math.radians(a))[0]
        assert r<=float(distance.magnitude)+1e-4


def test_quadratic_notebook_integrates_velocity_to_landing():
    e=Engine()
    notebook=json.loads(Path('frontend/src/starter.json').read_text(encoding='utf-8'))
    results=[e.execute(c['code']) for c in notebook['cells'] if c['mode']=='source']
    assert abs(float(e.environment['m'].to('kg').magnitude)-0.0421192915)<1e-12
    trace=results[-1]['plot']['traces'][0]
    assert abs(trace['x'][-1]-7000)<0.005
    assert abs(trace['y'][-1])<0.005
    assert all(y is not None and y>=-0.005 for y in trace['y'])
    for a in e.environment['r']:assert str(a.units)=='meter'


def test_projectile_vacuum_units_endpoints_and_tiny_angle():
    e=Engine()
    for c in ('0[kg/m]','0[g/cm]'):
        assert abs(float(e.execute(f'Magnitude[ProjectileMaxRange[{c},650[gr],890[m/s],9.81[m/s^2],"Quadratic"]]')['text'])-890**2/9.81)<1e-7
    for a in (0,math.pi/2):assert kernel.projectile(0.001,1,10,9.81,2,a)[0]==0
    assert kernel.projectile(0.001,1,10,9.81,2,1e-8)[0]>0
    for code in ('ProjectileMaxRange[1[kg/s],1[kg],10[m/s],9.81[m/s^2],"Quadratic"]',
                 'ProjectileMaxRange[-1[kg/m],1[kg],10[m/s],9.81[m/s^2],"Quadratic"]'):
        with pytest.raises(Exception):e.execute(code)


def test_unit_comparisons_integrals_and_bracketed_nsolve():
    e=Engine()
    assert e.execute('1[km]==1000[m]')['text']=='True'
    assert e.execute('1[m]<200[cm]')['text']=='True'
    assert e.execute('UnitConvert[Integrate[3[m/s],{t,0[min],2[min]}],"m"]')['text']=='360[m]'
    assert e.execute('Solve[c*1[kg/m]==2[g/cm],c]')['text']=='{1/5}'
    value=e.evaluate(parse('NSolve[Cos[x]==x,{x,0,1}]'))
    assert abs(float(value[0].rhs)-0.73908513321516)<1e-10
    with pytest.raises(ValueError):e.execute('NSolve[1/x==0,{x,-1,1}]')


def test_unit_state_roundtrip_between_calculation_cells():
    e=Engine()
    e.execute('m=650[gr];v=890[m/s];g=9.81[m/s^2];R=7[km];')
    e.environment=pickle.loads(pickle.dumps(e.environment))
    assert e.execute('UnitConvert[R+1[km],"m"]')['text']=='8000[m]'
    e.execute('p=NSolve[ProjectileMaxRange[k*1[kg/m],m,v,g,"Quadratic"]==R,{k,0,0.001}];')
    assert abs(float(e.environment['p'][0].rhs)-1.3049143921516e-5)<1e-12


def test_conic_fixed_point_exact_residuals():
    e=Engine()
    notebook=next(n for n in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if n['title'].startswith('高考数学：2022'))
    for c in notebook['cells']:
        if c['mode']=='source':e.execute(c['code'])
    p,y,h,n,z=[e.environment[a] for a in ('p_1','y_1','h','p_2','y_2')]
    assert s.simplify((h-n)*(-2-z)-(y-z)*(-n))==0
