import json
import base64
import math
from pathlib import Path
import mpmath as mp
import pytest
import sympy as s
from backend.engine import Engine
from backend.units import registry
from backend.native import kernel
from backend.syntax import InputError


@pytest.mark.parametrize('code, expected', [
    ('[kg*m/s^2]', '1[N]'), ('[N]*[m]', '1[J]'),
    ('2[牛顿]*3[米]', '6[J]'), ('3["牛顿"]*2["米"]', '6[J]'),
    ('UnitConvert[1["µm"],"nm"]', '1000[nm]'),
    ('UnitConvert[1["μA"],"nA"]', '1000[nA]'),
    ('UnitConvert[1["m²"],"cm²"]', '10000[cm^2]'),
    ('UnitConvert[1["m·s⁻²"],"m/s^2"]', '1[m / s^2]'),
    ('UnitConvert[1[Ω],"ohm"]', '1[Ω]'),
    ('UnitConvert[0["°C"],"K"]', '5463/20[K]'),
    ('UnitConvert[32[degF],"degC"]', '0[°C]'),
    ('v=72;UnitConvert[v[km/h],"m/s"]', '20[m / s]'),
    ('v=3;v["m/s"]', '3[m / s]'), ('x["m"]', 'x[m]'),
    ('a={1,2};a[cm]', '{1[cm], 2[cm]}'),
    ('1[kg/(m*s)]', '1[Pa · s]'), ('1[kg*m^2/(s^3*K)]', '1[W / K]'),
    ('1[V]*1[A]', '1[W]'), ('2[kg]*3[m/s^2]', '6[N]'),
    ('1[cm]/1[m]', '1/100'), ('1[mm]+1[m]', '1001[mm]'),
    ('UnitConvert[1[电子伏特],"eV"]', '1[eV]'),
])
def test_integrated_units(code, expected):
    assert Engine().execute(code)['text'] == expected


def test_unit_catalog_and_invalid_input():
    catalog=json.loads(Path('frontend/src/unit-catalog.json').read_text(encoding='utf-8'))
    names={row['label'] for row in catalog}
    assert len(names) >= 1700
    for name in ('mT','nF','GHz','eV','微米','英寸','µm','kPa','mL','hartree'):
        assert name in names
    engine=Engine()
    for code in ('1["imaginary_unit_xyz"]', '1[m]+1[s]', '1["m/s"]["s"]+1[m^2]'):
        with pytest.raises((InputError, ValueError, TypeError)):
            engine.execute(code)
    assert 'f[t]' in engine.execute('f[t]')['text']
    assert engine.execute('UnitSimplify["N*m"]')['text']=='1[J]'
    assert engine.execute('Sin[90[deg]]')['text']=='1'


def case(prefix):
    notebook=next(row for row in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if row['title'].startswith(prefix))
    engine=Engine()
    results=[engine.execute(cell['code']) for cell in notebook['cells'] if cell['mode']=='source']
    return engine,results


def test_native_elliptic_parameter_convention():
    t=s.Symbol('t')
    for function in (s.elliptic_k,s.elliptic_e):
        values=kernel.batch(function(t),[t],[[0,0.2,0.8,0.99]])
        assert max(abs(value-float(function(at))) for value,at in zip(values,[0,0.2,0.8,0.99]))<1e-12


def test_coil_field_against_biot_savart_and_motion():
    engine,results=case('电流线圈')
    x,y,z,t=s.symbols('x y z t')
    field=engine.environment['B_1']
    # Direct line quadrature provides an independent check of the elliptic field formula.
    for px,py,pz in ((0.3,0,0.3),(0.5,0.2,-0.4),(1.5,0,0.2)):
        def component(i):
            def integrand(phi):
                dx,dy=px-mp.cos(phi),py-mp.sin(phi)
                return sum(((pz-h)*mp.cos(phi),(pz-h)*mp.sin(phi),1-px*mp.cos(phi)-py*mp.sin(phi))[i]/(2*mp.pi*(dx*dx+dy*dy+(pz-h)**2)**1.5) for h in (-0.7,0,0.7))/float(engine.environment['n_4'])
            return float(mp.quad(integrand,[0,mp.pi,2*mp.pi]))
        expected=[component(i) for i in range(3)]
        actual=[float(expr.subs({x:px,y:py,z:pz})) for expr in field]
        assert max(abs(a-b) for a,b in zip(actual,expected))<1e-10
    motions=engine.environment['m_2']
    starts=engine.environment['s_13'];velocities=engine.environment['v_4']
    assert len(motions)==6 and len({tuple(v) for v in starts})==6 and len({tuple(v) for v in velocities})==6
    times=[20*i/100 for i in range(101)]
    for k,(motion,speed2) in enumerate(zip(motions,engine.environment['s_11'])):
        assert max(abs(float(expr.subs(t,0))-float(starts[k][i])) for i,expr in enumerate(motion))<1e-12
        expected=sum(float(v)**2 for v in velocities[k])
        assert max(abs(v-expected) for v in engine.sample(speed2,[t],[times]))<2e-7
    scene=results[3]
    assert scene['plot_type']=='field3d' and scene['field_kind']=='magnetic'
    assert scene['coils']==[-0.7,0,0.7] and len(scene['paths'])==6
    assert len(scene['field_lines'])==48
    assert len(set(scene['colors']))==6 and len(set(scene['labels']))==6
    assert all(('+1e' if k<3 else '-1e') in label for k,label in enumerate(scene['labels']))
    assert len({tuple(path[0]) for path in scene['paths']})==6
    for path in scene['paths']:
        assert all(math.hypot(math.hypot(*p[:2])-1,p[2]-offset)>0.05 for p in path for offset in scene['coils'])
    assert all(math.isfinite(v) for line in scene['field_lines'] for point in line for v in point)
    assert abs(float(engine.environment['c_2'].to('mT').magnitude)-2*math.pi*float(engine.environment['n_4']))<1e-10


def test_hydrogen_analytic_eigenstate_and_probability():
    engine,results=case('类氢离子')
    assert results[1]['items'][-1]['text']=='-1/2*z^2/n^2'
    assert results[2]['items'][1]['text']=='{1, 1, 1, 1, 1, 1}'
    assert results[2]['items'][2]['text']=='{0, 0, 0, 0, 0, 0}'
    assert all(not radial.has(s.Float,s.Derivative,s.Integral) for radial in engine.environment['a'])
    densities=engine.environment['b']
    x,y,z=s.symbols('x y z')
    assert len(densities)==6
    assert s.simplify(densities[0]-8/s.pi*s.exp(-4*s.sqrt(x*x+y*y+z*z)))==0
    assert s.simplify(densities[1].subs({x:1,y:0,z:0}))==0  # 2s radial node.
    assert densities[2].subs(z,0)==0 and densities[4].subs(z,0)==0
    assert s.simplify(densities[5].subs({x:s.sqrt(2),y:0,z:1}))==0
    clouds=results[-1]['items'][1:]
    assert len(clouds)==6 and all(g['plot_type']=='volume' for g in clouds)
    assert len({g['volume'] for g in clouds})==6
    for graph in clouds:
        data=base64.b64decode(graph['volume'],validate=True)
        assert len(data)==graph['size']**3 and max(data)==255 and min(data)==0
        assert graph['density_max']>0 and graph['label']
