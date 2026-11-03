import json
import pickle
from pathlib import Path

import numpy as np
import pytest
import sympy as s

from backend.engine import Engine
from backend.syntax import InputError, parse
from backend.components import pde_module


def evaluate(code): return Engine().evaluate(parse(code))


def test_laminar_exact_pde_and_boundary_residuals():
    y=s.Symbol('y')
    u=evaluate('DSolveValue[{D[u[x,y],{y,2}]==-6,u[x,0]==0,u[x,1]==0},u[x,y],{x,y}]')
    assert s.simplify(s.diff(u,y,2)+6)==0
    assert u.subs(y,0)==u.subs(y,1)==0
    assert s.integrate(u,(y,0,1))==s.Rational(1,2)


@pytest.mark.parametrize('time_derivative, factor', [('t',s.exp(-s.pi**2*s.Symbol('t'))), ('{t,2}',s.cos(s.pi*s.Symbol('t')))])
def test_separated_analytical_modes(time_derivative,factor):
    u=evaluate(f'DSolveValue[{{D[u[x,t],{time_derivative}]==D[u[x,t],{{x,2}}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]}},u[x,t],{{x,t}}]')
    assert s.simplify(u-factor*s.sin(s.pi*s.Symbol('x')))==0


def poisson(n):
    return evaluate(f'NDSolveValue[{{Laplacian[u[x,y],{{x,y}}]==-2*Pi^2*Sin[Pi*x]*Sin[Pi*y],u[0,y]==0,u[1,y]==0,u[x,0]==0,u[x,1]==0}},u[x,y],{{x,0,1}},{{y,0,1}},{n}]')


def test_manufactured_poisson_convergence():
    module=pde_module()
    errors=[abs(float(module.dispatch('PDEValue',[poisson(n),[.5,.5]]))-1) for n in (11,21,41)]
    assert errors[1]<errors[0]/3 and errors[2]<errors[1]/3
    assert poisson(21).metrics['relative residual']<1e-10


@pytest.mark.parametrize('derivative,t,expected',[('t',.1,np.exp(-np.pi**2*.1)),('{t,2}',.2,np.cos(np.pi*.2))])
def test_heat_and_wave_against_exact_modes(derivative,t,expected):
    u=evaluate(f'NDSolveValue[{{D[u[x,t],{derivative}]==D[u[x,t],{{x,2}}],u[0,t]==0,u[1,t]==0,u[x,0]==Sin[Pi*x]}},u[x,t],{{x,0,1}},{{t,0,1}},81]')
    result=pde_module().dispatch('PDEValue',[u,[.5,t]])
    assert abs(float(result)-expected)<2e-4


def test_laplace_eigenvalues_against_square_spectrum():
    values=np.array([float(x) for x in evaluate('NDEigensystem[-Laplacian[u[x,y],{x,y}],u[x,y],{x,0,1},{y,0,1},3]')])
    assert np.max(np.abs(values/np.array([2,5,5])/np.pi**2-1))<.015


def test_reject_underconstrained_or_inconsistent_boundary_data():
    with pytest.raises(InputError,match='each rectangular edge'):
        evaluate('NDSolveValue[{Laplacian[u[x,y],{x,y}]==0,u[0,y]==0},u[x,y],{x,0,1},{y,0,1}]')
    with pytest.raises(InputError,match='corner'):
        evaluate('NDSolveValue[{Laplacian[u[x,y],{x,y}]==0,u[0,y]==1,u[1,y]==0,u[x,0]==0,u[x,1]==0},u[x,y],{x,0,1},{y,0,1}]')


@pytest.fixture(scope='module')
def bridge(): return pde_module().dispatch('FEMBridgeSolve',[[80,10,24],1000,2])


def test_bridge_dimensions_equilibrium_and_linearity(bridge):
    assert pickle.loads(pickle.dumps(bridge)).metrics==bridge.metrics
    m=bridge.metrics
    assert m['3D tetrahedra']>0 and m['2D triangles']>0 and m['1D trusses']>0
    assert m['relative residual']<1e-8
    assert m['force balance relative error']<1e-8
    assert m['deck min w [m]']<0 and m['min cable tension [N]']>0
    other=pde_module().dispatch('FEMBridgeSolve',[[80,10,24],2000,2])
    assert abs(other.metrics['deck min w [m]']/m['deck min w [m]']-2)<1e-9
    assert abs(other.metrics['strain energy [J]']/m['strain energy [J]']-4)<1e-9


def test_bridge_mesh_preserves_physical_hangers(bridge):
    finer=pde_module().dispatch('FEMBridgeSolve',[[80,10,24],1000,3])
    assert bridge.data['types'].count('hanger')==finer.data['types'].count('hanger')==14
    for kind in ('Mesh','Displacement','Stress'):
        p=pde_module().dispatch('PDEPlot',[bridge,kind])
        assert 100<len(p['primitives'])<16000
        assert all(np.all(np.isfinite(x['points'])) for x in p['primitives'])


def test_wing_symmetry_mass_conservation_and_mesh():
    module=pde_module()
    u=module.dispatch('WingFlowSolve',[[20000,0],4])
    assert abs(u.metrics['C_L'])<.003
    assert u.metrics['C_D']>0
    assert u.metrics['relative update']<2e-5
    assert u.metrics['weak divergence']<1e-10
    assert abs(u.metrics['net outer flux'])<1e-10
    assert u.metrics['max eddy viscosity / nu']>0
    for kind in ('Mesh','Velocity','Pressure','Streamlines','Convergence'):
        p=module.dispatch('PDEPlot',[u,kind])
        assert p['kind']=='plot'
        json.dumps(p,allow_nan=False)
    assert pickle.loads(pickle.dumps(u)).metrics==u.metrics


def test_optional_component_absence(monkeypatch,tmp_path):
    from backend import components
    monkeypatch.setattr(components,'ROOT',tmp_path)
    assert not any(components.capabilities().values())
    with pytest.raises(InputError,match='not installed'):evaluate('FEMBridgeSolve[{80,10,24},1000,2]')
    assert evaluate('1+1')==2
