import ctypes as ct
import json
import os
import subprocess
import sys

import numpy as np
import pytest
import sympy as s

from backend.engine import Engine
from backend.native import kernel, NativeUnsupported


@pytest.mark.parametrize('shape',[(1,1,1),(3,5,7),(17,19,65),(32,32,32),(5,9,1)])
def test_double_matrix_paths_and_unaligned_tails(shape):
    m,n,k=shape
    rng=np.random.default_rng(51)
    a=rng.normal(size=(m,k));b=rng.normal(size=(k,n))
    available=kernel.lib.calix_simd_level()
    for level in range(available+1):
        result,path=kernel.dense_dot(a.tolist(),b.tolist(),mode=level)
        assert path==('scalar','avx2','avx512')[level]
        assert np.allclose(result,a@b,rtol=1e-12,atol=1e-12)
    if available<2:
        with pytest.raises(NativeUnsupported):kernel.dense_dot(a.tolist(),b.tolist(),mode=2)


@pytest.mark.parametrize('shape',[(1,1,1),(17,19,65),(32,32,67)])
def test_exact_int8_signed_products_and_padding(shape):
    m,n,k=shape
    rng=np.random.default_rng(17)
    a=rng.integers(-128,128,size=(m,k));b=rng.integers(-128,128,size=(k,n))
    reference=a.astype(np.int64)@b.astype(np.int64)
    result,_=kernel.dense_dot(a.tolist(),b.tolist(),integer=True)
    assert np.array_equal(result,reference)
    try:
        tiled,path=kernel.dense_dot(a.tolist(),b.tolist(),integer=True,mode=3)
    except NativeUnsupported:
        if kernel.cpu_features().get('amx_int8_hardware'):
            pytest.skip('AMX hardware exists but OS tile state is not enabled')
    else:
        assert path=='amx-int8' and np.array_equal(tiled,reference)


def test_int8_bound_accumulation_and_invalid_input():
    result,_=kernel.dense_dot([[-128]*65536],[[-128] for _ in range(65536)],integer=True,mode=0)
    assert result==[[1073741824]]
    with pytest.raises(ValueError):kernel.dense_dot([[128]],[[1]],integer=True)
    with pytest.raises(ValueError):kernel.dense_dot([[1,2]],[[1,2]])


@pytest.mark.parametrize('expression',['x**3-2*x+1','sqrt(x+3)','abs(x)/(x*x+1)','x**-3','sin(x)+exp(x)','x**s.Rational(1,2)'])
def test_vector_expression_sampling_matches_scalar_reference(expression):
    x=s.Symbol('x');expr=eval(expression,{'x':x,'sqrt':s.sqrt,'abs':s.Abs,'sin':s.sin,'exp':s.exp,'s':s})
    points=np.linspace(.05,2,67).tolist()
    result=kernel.batch(expr,[x],[points])
    reference=s.lambdify(x,expr,'numpy')(np.array(points))
    assert np.allclose(result,reference,rtol=1e-13,atol=1e-13)


def test_scalar_override_is_process_local_and_never_enables_unsupported_isa():
    command='from backend.native import kernel; import json; print(json.dumps(kernel.cpu_features()))'
    env={**os.environ,'CALIX_SIMD':'scalar'}
    data=json.loads(subprocess.check_output([sys.executable,'-c',command],env=env,text=True))
    assert data['selected']=='scalar'
    assert set(data['compiled'])=={'scalar','avx2','avx512','amx-int8'}


def test_wolfram_dot_preserves_exact_and_high_precision_values():
    e=Engine()
    result=e.execute('a=Table[N[1/(i+j),15],{i,1,32},{j,1,32}];Dot[a,a]')
    assert result['engine'].startswith('C++ /')
    assert e.execute('Dot[{{1/3,0},{0,1/3}},{{3,0},{0,3}}]')['text']=='{{1, 0}, {0, 1}}'
    exact=e.execute('a=Table[1/3,{i,1,32},{j,1,32}];Dot[a,a]')
    assert '32/9' in exact['text'] and exact['engine']=='SymPy'
    high=e.execute('a=Table[N[1/3,40],{i,1,32},{j,1,32}];Dot[a,a]')
    assert high['engine']=='SymPy'
