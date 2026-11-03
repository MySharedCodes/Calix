import ctypes as ct
import numpy as np
import pytest
from backend.engine import Engine
from backend.syntax import InputError,parse
from backend.native import kernel


def test_block_restores_locals_on_success_and_error():
    e=Engine();e.execute('a=3;b=7;Block[{a,c},a=5;c=2;a*c]')
    assert e.environment=={'a':3,'b':7}
    assert e.execute('Block[{a},Block[{a},a=9;a]+a]')['text']=='a + 9'
    with pytest.raises(InputError):e.execute('Block[{a,c},a=19;c=2;Part[{},1]]')
    assert e.environment=={'a':3,'b':7}


def test_block_returns_plots_without_leaking_local_results():
    e=Engine()
    result=e.execute('Block[{p,q},p=Labeled[Plot[x^2,{x,0,1}],"curve"];q=7;{p,q}]')
    assert result['kind']=='group' and result['items'][0]['kind']=='plot'
    assert result['items'][0]['label']=='curve' and result['items'][1]['text']=='7'
    assert e.environment=={}


def test_length_reports_missing_dependency():
    with pytest.raises(InputError,match='Length input is undefined: c'):
        Engine().execute('Length[c]')


@pytest.mark.parametrize('triangle',[True,False])
def test_native_assembly_uses_eight_threads_and_matches_serial(triangle):
    if triangle:p=np.array([[0.,0.],[2.,.1],[.3,1.3]]);cell=[0,1,2]
    else:p=np.array([[0.,0.],[2.,.1],[2.3,1.4],[.3,1.3]]);cell=[0,1,2,3]
    cells=np.tile(cell,(4096,1));rng=np.random.default_rng(17)
    coeff=tuple(rng.normal(size=shape) for shape in [(2,2,2,2),(2,2),(2,2,2),(2,2,2),(2,)])
    try:
        kernel.configure_threads(1);a,f=kernel.fem_elements(p,cells,2,2,coeff)
        assert kernel.lib.calix_last_threads()==1
        kernel.configure_threads(8);b,g=kernel.fem_elements(p,cells,2,2,coeff)
        assert kernel.lib.calix_last_threads()==8
        assert np.array_equal(a,b) and np.array_equal(f,g)
    finally:kernel.configure_threads(1)


def test_matrix_actual_simd_path_and_threads():
    rng=np.random.default_rng(38);a=rng.normal(size=(128,128));b=rng.normal(size=(128,128))
    try:
        kernel.configure_threads(8);kernel.reset_execution()
        actual,path=kernel.dense_dot(a.tolist(),b.tolist())
        assert path==kernel.cpu_features()['selected']
        assert kernel.execution['operations']['matrix_product']['threads_used']==8
        assert np.allclose(actual,a@b,atol=1e-12,rtol=1e-12)
    finally:kernel.configure_threads(1)


def test_settings_reach_calculation_process_and_affinity():
    from fastapi.testclient import TestClient
    from backend.service import create_app
    from backend.hardware import physical_cores
    count=min(8,physical_cores())
    with TestClient(create_app('runtime-test')) as client:
        headers={'X-Calix-Token':'runtime-test'}
        for threads in (count,1,count):
            assert client.post('/api/settings',headers=headers,json={'max_workers':threads}).status_code==200
            result=client.post('/api/evaluate',headers=headers,json={'session':'runtime','code':'a=Table[N[1/(i+j),15],{i,1,128},{j,1,128}];Dot[a,a]'}).json()
            assert result['ok'],result
            execution=result['result']['execution']
            assert execution['thread_limit']==execution['threads_used']==threads
            if execution['affinity']:assert execution['affinity']['physical_cores']==threads
