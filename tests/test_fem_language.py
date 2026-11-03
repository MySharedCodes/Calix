import json
import sys
from pathlib import Path

import numpy as np
import pytest
import sympy as s
from scipy import sparse
from skfem import BilinearForm, LinearForm, asm

from backend.engine import Engine
from backend.native import kernel
from backend.syntax import parse
from backend.components import pde_module

pde_module()
from calix_pde.language import Mesh, Elements, Data, assemble


@pytest.mark.parametrize('dimension',[2,3,'triangle'])
def test_cpp_element_integrals_against_independent_assembler(dimension):
    points=np.array([[0,0],[2,.3],[2.4,1.4],[.4,1.1]])
    triangle=dimension=='triangle'
    if triangle:dimension=2;points=points[:3]
    if dimension==3:
        points=np.vstack([np.c_[points,np.zeros(4)],np.c_[points+[.2,.1],np.full(4,1.3)]])
    mesh=Mesh(points,Elements('TriangleElement' if triangle else 'QuadElement' if dimension==2 else 'HexahedronElement',[list(range(1,len(points)+1))]))
    rng=np.random.default_rng(17)
    c=rng.normal(size=(2,2,dimension,dimension));a=rng.normal(size=(2,2))
    alpha=rng.normal(size=(2,2,dimension));beta=rng.normal(size=(2,2,dimension));f=np.array([2.,-3.])
    coeff=Data({'variables':{'DependentVariables':['u','v'],'Space':list(range(dimension))},'coefficients':{
        'DiffusionCoefficients':c,'ReactionCoefficients':a,'ConservativeConvectionCoefficients':alpha,'ConvectionCoefficients':beta,'LoadCoefficients':f}})
    result=assemble(coeff,Data({'IntegrationOrder':2}),Data({'Space':mesh}))
    @BilinearForm
    def form(u,w,ctx):
        return np.einsum('ijab,ja...,ib...->...',c,u.grad,w.grad)+np.einsum('ij,j...,i...->...',a,u,w)+np.einsum('ijb,j...,ib...->...',alpha,u,w.grad)+np.einsum('ija,ja...,i...->...',beta,u.grad,w)
    @LinearForm
    def load(w,ctx):return np.einsum('i,i...->...',f,w)
    basis=mesh.basis(2)
    assert np.allclose(result('StiffnessMatrix').toarray(),asm(form,basis).toarray(),rtol=1e-12,atol=1e-12)
    assert np.allclose(result('LoadVector'),asm(load,basis),rtol=1e-12,atol=1e-12)


def test_reduced_integration_is_actually_one_point():
    points=np.array([[0,0],[1,0],[1,1],[0,1]])
    coefficients=(np.zeros((1,1,2,2)),np.ones((1,1)),np.zeros((1,1,2)),np.zeros((1,1,2)),np.ones(1))
    reduced,load=kernel.fem_elements(points,[[0,1,2,3]],1,1,coefficients)
    full,_=kernel.fem_elements(points,[[0,1,2,3]],1,2,coefficients)
    assert np.linalg.matrix_rank(reduced[0])==1
    assert np.linalg.matrix_rank(full[0])==4
    assert np.isclose(reduced.sum(),1) and np.isclose(full.sum(),1) and np.isclose(load.sum(),1)


def test_cpp_sparse_saddle_system_and_singular_rejection():
    a=np.array([[4.,1.,1.],[1.,3.,-2.],[1.,-2.,0.]])
    b=np.array([1.,2.,3.])
    assert np.allclose(kernel.sparse_solve(sparse.csr_matrix(a),b),np.linalg.solve(a,b))
    with pytest.raises(ValueError,match='constraints'):
        kernel.sparse_solve(sparse.csr_matrix([[1.,1.],[1.,1.]]),np.ones(2))


def test_basic_arrays_do_not_require_pde(monkeypatch,tmp_path):
    from backend import components
    monkeypatch.setattr(components,'ROOT',tmp_path)
    e=Engine()
    assert e.evaluate(parse('Length[Range[3]]'))==3
    assert e.evaluate(parse('Norm[{3,4}]'))==5
    assert e.evaluate(parse('Dimensions[ConstantArray[1,{2,3}]]'))==[2,3]
    assert e.evaluate(parse('ArrayReshape[Range[4],{2,2}]'))==[[1,2],[3,4]]
    assert e.evaluate(parse('Union[{3,1,2},{2,4}]'))==[1,2,3,4]


def test_physical_core_default_and_debug_override(monkeypatch):
    import backend.hardware as hardware
    monkeypatch.setattr(hardware,'physical_cores',lambda:24)
    monkeypatch.delenv('CALIX_MAX_WORKERS',raising=False)
    assert hardware.default_workers()==24
    monkeypatch.setenv('CALIX_MAX_WORKERS','8')
    assert hardware.default_workers()==8
    monkeypatch.setenv('CALIX_MAX_WORKERS','128')
    assert hardware.default_workers()==24


def test_hydrogen_states_are_computed_from_equation():
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'scripts'))
    from hydrogen_case import notebook
    case=notebook(lambda code:None,lambda code:code)
    e=Engine();outputs=[e.execute(cell) for cell in case['cells'] if cell]
    assert outputs[2]['items'][1]['text']=='{1, 1, 1, 1, 1, 1}'
    assert outputs[2]['items'][2]['text']=='{0, 0, 0, 0, 0, 0}'
    assert outputs[3]['items'][0]['text']=='{1, q, q^2 - 1/3}'
    assert len([o for o in outputs[3]['items'] if o.get('plot_type')=='volume'])==6
    assert 'LaguerreL' not in ''.join(cell for cell in case['cells'] if cell)
    assert 'LegendreP' not in ''.join(cell for cell in case['cells'] if cell)
    json.dumps(outputs,allow_nan=False)


def test_standard_function_cases_have_no_model_shortcuts():
    root=Path(__file__).resolve().parents[1]
    cases=json.loads((root/'frontend/src/example-notebooks.json').read_text(encoding='utf-8'))
    for case in cases:
        if case.get('component')=='pde':
            source='\n'.join(c['code'] for c in case['cells'] if c['mode']=='source')
            assert 'FEMBridgeSolve' not in source and 'WingFlowSolve' not in source and 'PDEPlot' not in source
            assert 'ToElementMesh' in source and any(name in source for name in ('QuadElement','BoundaryMeshRegion'))
