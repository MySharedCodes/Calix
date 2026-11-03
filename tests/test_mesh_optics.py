import sys
from pathlib import Path
import numpy as np
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import InputError,parse
from backend.components import pde_module

pde_module()
from calix_pde.language import Mesh,Elements
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))


def test_sort_mixed_exact_and_approximate_angles():
    e=Engine()
    actual=e.evaluate(parse('Sort[{{Pi/32,1},{-0.2,1},{0,1},{-Pi/32,1},{0.2,1},{-1/10,1}}]'))
    assert np.allclose(np.array(actual,float)[:,0],[-.2,-.1,-np.pi/32,0,np.pi/32,.2])
    actual=e.evaluate(parse('Sort[{1.5,-2,0.5,1/3,-1.2,0}]'))
    assert actual==[-2,s.Float('-1.2',16),0,s.Rational(1,3),s.Float('.5',16),s.Float('1.5',16)]


@pytest.mark.parametrize('points',[
    [[0,0],[1,1],[1,0],[0,1]],
    [[0,0],[1,0],[1,0],[0,1]],
    [[0,0],[1,0],[.2,.2],[0,1]]
])
def test_inverted_folded_and_degenerate_quads_rejected(points):
    with pytest.raises(InputError,match='Invalid quadrilateral mesh'):
        Mesh(points,Elements('QuadElement',[[1,2,3,4]]))


def test_consistent_clockwise_mesh_is_valid():
    Mesh([[0,0],[0,1],[1,1],[1,0]],Elements('QuadElement',[[1,2,3,4]]))
    with pytest.raises(InputError,match='Invalid quadrilateral mesh'):
        Mesh([[0,0],[1,0],[1,1],[0,1],[2,0],[2,1]],Elements('QuadElement',[[1,2,3,4],[2,3,6,5]]))


def test_default_gear_mesh_has_rounded_unequal_gears_and_quality_triangles():
    from gear_case import notebook
    e=Engine();e.execute(notebook(lambda c:None,lambda c:c)['cells'][1])
    for h,mesh in enumerate(e.environment['m']):
        assert mesh.elements.kind=='TriangleElement'
        p=np.array(mesh.points,float);f=np.array(mesh.elements.indices,int)-1;q=p[f]
        u=q[:,1]-q[:,0];v=q[:,2]-q[:,0];area=(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        assert np.all(area>0)
        side=np.sum((q-np.roll(q,1,axis=1))**2,axis=2)
        cosine=(side+np.roll(side,1,axis=1)-np.roll(side,-1,axis=1))/(2*np.sqrt(side*np.roll(side,1,axis=1)))
        assert cosine.max()<=np.cos(np.deg2rad(20))+1e-8
        assert area.max()<=.005*(1+1e-9)
        local=np.linalg.norm(q.mean(axis=1)-[1,0],axis=1)<.01
        assert area[local].max()<area.max()/100
        boundary=np.array(mesh.boundary[0].indices)-1
        expected=np.sum(p[boundary[:,0],0]*p[boundary[:,1],1]-p[boundary[:,1],0]*p[boundary[:,0],1])/2
        assert area.sum()==pytest.approx(expected,abs=1e-10)
        radius=np.linalg.norm(p-[3*h,0],axis=1)
        assert .35*(h+1)*np.cos(np.pi/96)-1e-12<=radius.min()<=.35*(h+1)+1e-12
        assert radius.max()==pytest.approx(h+1.1,abs=1e-12)


def test_oblique_fem_fresnel_energy_and_mesh_convergence():
    from quartz_case import notebook
    source=notebook(lambda c:None,lambda c:c)['cells']
    errors=[]
    for n in [64,96,128]:
        e=Engine();e.execute(source[1].replace('n=96;',f'n={n};'))
        e.execute(source[3])
        e.execute(source[5].split('c=Table[')[0])
        p=np.array(e.environment['p'],float);u=np.array(e.environment['u'],float)
        a=int(e.environment['a']);b=int(e.environment['b']);slope=float(e.environment['s'])
        k=float(e.environment['κ']);t=float(e.environment['τ'])
        r=float(e.environment['r']);trans=float(e.environment['t'])
        exact=((k-t)/(k+t))**2
        assert abs(r+trans-1)<1e-10
        assert np.allclose((u[::2]+1j*u[1::2]).reshape(a+1,b+1)[:,-1],
            np.exp(3j*slope)*(u[::2]+1j*u[1::2]).reshape(a+1,b+1)[:,0],atol=1e-12)
        q=np.array(e.environment['f'],float)
        assert np.isfinite(q).all()
        mesh=e.environment['m']
        assert len(np.unique(p,axis=0))==len(p)
        assert len(np.unique(p[p[:,0]==0,1]))==b+1
        errors.append(abs(r-exact))
    assert errors[1]<errors[0]*.6 and errors[2]<errors[1]*.7
    assert errors[2]<.002


def test_missing_module_message_is_deferred_and_named(monkeypatch,tmp_path):
    from backend import components
    monkeypatch.setattr(components,'ROOT',tmp_path)
    e=Engine()
    assert e.execute('1+1')['text']=='2'
    with pytest.raises(InputError,match='select PDE module'):
        e.execute('ToElementMesh[]')
