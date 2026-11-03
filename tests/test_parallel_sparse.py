import numpy as np
import pytest
import subprocess
import sys
from scipy import sparse
from backend.native import kernel


@pytest.mark.parametrize('kind',['spd','saddle','unsymmetric','scaled'])
def test_pardiso_parallel_systems_against_known_solution(kind):
    rng=np.random.default_rng(34);n=1024
    a=sparse.diags([-np.ones(n-1),4*np.ones(n),-np.ones(n-1)],[-1,0,1],format='csr')
    if kind=='saddle':
        a=sparse.bmat([[a,sparse.eye(n)],[sparse.eye(n),None]],format='csr')
    elif kind=='unsymmetric':a=a+sparse.diags([.6*np.ones(n-2)],[2])
    elif kind=='scaled':
        scale=sparse.diags(np.geomspace(1e-4,1e4,n));a=scale@a@scale
    x=rng.normal(size=a.shape[0]);b=a@x
    try:
        for threads in (1,8,1):
            kernel.configure_threads(threads);kernel.reset_execution();actual=kernel.sparse_solve(a,b)
            assert np.allclose(actual,x,rtol=1e-6,atol=1e-7)
            operation=kernel.execution['operations']['sparse_solve']
            assert operation['path']=='oneMKL PARDISO' and operation['threads_used']==threads
            assert np.linalg.norm(a@actual-b)/np.linalg.norm(b)<1e-10
    finally:kernel.configure_threads(1)


@pytest.mark.parametrize('matrix,rhs',[
    ([[1.,1.],[1.,1.]],[1.,1.]),
    ([[1.,0.],[0.,0.]],[1.,0.]),
    ([[1.,0.],[0.,1.]],[1.,float('nan')]),
])
def test_pardiso_rejects_rank_deficiency_and_nonfinite_data(matrix,rhs):
    with pytest.raises(ValueError):kernel.sparse_solve(sparse.csr_matrix(matrix),np.array(rhs))


def test_pardiso_sums_duplicates_and_accepts_unsorted_sparse_input():
    a=sparse.coo_matrix(([1.,2.,1.,2.,3.],([1,0,0,1,0],[0,1,0,1,0])),shape=(2,2))
    x=np.array([.3,-.8]);assert np.allclose(kernel.sparse_solve(a,a@x),x)


def test_missing_parallel_runtime_reports_installation_error(tmp_path):
    code='from pathlib import Path;from backend import components;from backend.native import kernel;from scipy import sparse;import numpy as np;components.ROOT=Path('+repr(str(tmp_path))+');kernel.sparse_solve(sparse.eye(2),np.ones(2))'
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert result.returncode!=0 and 'Reinstall Calix and select PDE module' in result.stderr


def test_service_passes_worker_limit_to_pardiso():
    from fastapi.testclient import TestClient
    from backend.service import create_app
    from backend.hardware import physical_cores
    count=min(8,physical_cores())
    code='n=600;a=SparseArray[Join[Table[{i,i}->4,{i,1,n}],Table[{i,i+1}->-1,{i,1,n-1}],Table[{i+1,i}->-1,{i,1,n-1}]],{n,n}];b=ConstantArray[1,n];x=LinearSolve[a,b];Norm[Dot[a,x]-b]'
    with TestClient(create_app('sparse-test')) as client:
        headers={'X-Calix-Token':'sparse-test'}
        for threads in (count,1,count):
            assert client.post('/api/settings',headers=headers,json={'max_workers':threads}).status_code==200
            result=client.post('/api/evaluate',headers=headers,json={'session':'sparse','code':code}).json()
            assert result['ok'],result
            operation=result['result']['execution']['operations']['sparse_solve']
            assert operation['path']=='oneMKL PARDISO' and operation['threads_used']==threads
            assert float(result['result']['text'])<1e-10
