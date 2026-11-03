import sys
from pathlib import Path

import numpy as np
import pytest
import sympy as sp

from backend.engine import Engine
from backend.syntax import parse
from backend.components import pde_module


@pytest.mark.parametrize('code,expected', [
    ('{1,2}+{3,4}', [4,6]),
    ('{{1,2},{3,4}}-{1,1}*{{1,1},{1,1}}', [[0,1],[2,3]]),
    ('{2,4}/2', [1,2]),
    ('{2,3}^2', [4,9]),
    ('Dot[{1,2},{3,4}]', 11),
    ('Dot[{{1,2},{3,4}},{2,3}]', [8,18]),
    ('Dot[{2,3},{{1,2},{3,4}}]', [11,16]),
    ('∫[Sin[x],x]', -sp.cos(sp.Symbol('x'))),
    ('∑[k^2,{k,1,3}]',14),
    ('𝒶=3;𝒶^2',9),
])
def test_exact_arithmetic_and_visible_characters(code,expected):
    assert Engine().evaluate(parse(code)) == expected


def test_native_numeric_interoperation():
    pde_module()
    e=Engine()
    e.environment['a']=np.array([1.,2.])
    assert np.allclose(e.evaluate(parse('{2,3}+a')), [3,5])
    assert np.allclose(e.evaluate(parse('a-{2,3}')), [-1,-1])
    assert float(e.evaluate(parse('Norm[a]'))) == pytest.approx(np.sqrt(5))
    assert float(e.evaluate(parse('Mean[a]'))) == pytest.approx(1.5)
    e.environment['b']=np.array([[1.,0.],[0.,2.]])
    result=e.evaluate(parse('ArrayFlatten[{{b,0},{0,b}}]'))
    assert np.allclose(result.toarray(),np.diag([1,2,1,2]))


@pytest.mark.parametrize('triangle',[False,True])
def test_authored_gear_constitutive_tensor_rigid_motion_and_strain_energy(triangle):
    pde_module()
    from calix_pde.language import Mesh,Elements,Data,assemble
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from gear_case import notebook
    source=notebook(lambda x:None,lambda x:x)['cells'][3]
    e=Engine()
    e.execute(source.split('k=Table[')[0])
    c=np.asarray(e.environment['c'],dtype=float)
    points=np.array([[0.,0.],[2.,.3],[2.4,1.4],[.4,1.1]])
    mesh=Mesh(points,Elements('TriangleElement' if triangle else 'QuadElement',[[1,2,3],[1,3,4]] if triangle else [[1,2,3,4]]))
    data=Data({'variables':{'DependentVariables':['u','v'],'Space':['x','y']},'coefficients':{'DiffusionCoefficients':c}})
    k=assemble(data,Data({'IntegrationOrder':2}),Data({'Space':mesh}))('StiffnessMatrix')
    for u in (np.tile([2.,3.],4),np.c_[-points[:,1],points[:,0]].ravel()):
        assert np.linalg.norm(k@u)<1e-12
    gradient=np.array([[.02,.03],[.01,-.01]])
    u=(points@gradient.T).ravel(); strain=(gradient+gradient.T)/2
    nu=.3; mu=1/(2*(1+nu)); lam=nu/(1-nu*nu)
    area=abs(np.linalg.det(np.stack([points[1]-points[0],points[3]-points[0]])))
    expected=area*(lam*np.trace(strain)**2+2*mu*np.sum(strain**2))
    assert float(u@k@u)==pytest.approx(expected,rel=1e-12)
