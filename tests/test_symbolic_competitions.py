import json
from pathlib import Path
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import InputError, parse


@pytest.mark.parametrize('code,expected',[
    ('Factor[x^10-x^8-5*x^6+x^4+8*x^2+4]', '(x^2-2)^2*(x^2+1)^3'),
    ('Cancel[(x^8-1)/(x^6+x^4+x^2+1)]', 'x^2-1'),
    ('Simplify[TrigExpand[Sin[3*x]*Cos[2*x]-Cos[3*x]*Sin[2*x]]]', 'Sin[x]'),
    ('Simplify[ComplexExpand[Exp[I*x]*(Cos[x]-I*Sin[x])]]', '1'),
    ('Factor[ComplexExpand[Conjugate[(x+I*y)^3]*(x+I*y)^3]]', '(x^2+y^2)^3'),
])
def test_symbolic_demonstration_identities(code, expected):
    assert s.simplify(Engine().evaluate(parse(code))-Engine().evaluate(parse(expected)))==0


def test_complex_expansion_real_default_and_series():
    engine=Engine();x,y=s.symbols('x y')
    assert engine.evaluate(parse('ComplexExpand[Re[(x+I*y)^2]]'))==x*x-y*y
    assert engine.evaluate(parse('ComplexExpand[Im[(x+I*y)^2]]'))==2*x*y
    series=engine.evaluate(parse('Series[Log[(1+x)/(1-x)]-2*x-2*x^3/3-2*x^5/5,{x,0,10}]'))
    assert s.expand(series.removeO()-2*x**7/7-2*x**9/9)==0
    for code in ('ComplexExpand[x,y]', 'TrigExpand[{x,y}]'):
        with pytest.raises(InputError):engine.execute(code)


def case(prefix):
    notebook=next(n for n in json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8')) if n['title'].startswith(prefix))
    engine=Engine()
    for cell in notebook['cells']:
        if cell['mode']!='markdown':engine.execute(cell['code'])
    return engine


def test_imo_exact_exhaustive_maximum():
    engine=case('IMO 1981')
    import math
    pairs=[]
    for m in range(1,1982):
        for sign in (-1,1):
            root=math.isqrt(5*m*m+4*sign)
            if root*root==5*m*m+4*sign and (m+root)%2==0:
                n=(m+root)//2
                if 1<=n<=1981:pairs.append([m,n])
    assert engine.environment['p_3']==pairs
    assert engine.environment['b_2']==5034507976
    assert engine.environment['w_1']==[[987,1597]]
    assert all(v==0 for v in engine.environment['r_10'])


def test_ipho_scattering_force_and_capture_cross_section():
    engine=case('IPhO 2011')
    r,Q,alpha,eps,mass,v0,b=s.symbols('r Q α ε m v_0 b')
    env=engine.environment
    assert s.simplify(env['r_5']+alpha*Q**2/(8*s.pi**2*eps**2*r**5))==0
    assert s.simplify(-s.diff(env['U'],r)-env['r_5'])==0
    assert s.simplify(env['c_11']**2-alpha*Q**2/(4*eps**2*mass*v0**2))==0
    assert s.simplify(env['c_9']**4-alpha*Q**2/(4*s.pi**2*eps**2*mass*v0**2))==0
    for impact in (2,3,4):
        closest=float(env['n_6'].subs(b,impact))
        assert abs(float(env['n_5'].subs({r:closest,b:impact}))-0.5)<1e-12
