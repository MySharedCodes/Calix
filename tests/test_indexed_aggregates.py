import pytest
from backend.engine import Engine
from backend.syntax import InputError


def test_finite_indexed_aggregates_and_scope():
    engine = Engine()
    engine.execute('a={2,3,5};i=99')
    assert engine.execute('Sum[Part[a,i]^2,{i,1,3}]')['text'] == '38'
    assert engine.execute('Product[If[i==2,1,Part[a,i]],{i,1,3}]')['text'] == '10'
    assert engine.execute('i')['text'] == '99'
    assert engine.execute('Sum[If[i==j,1,0],{i,1,3},{j,1,3}]')['text'] == '3'
    assert engine.execute('Sum[Part[a,i],{i,1,0}]')['text'] == '0'
    assert engine.execute('Product[Part[a,i],{i,1,0}]')['text'] == '1'


def test_indexed_aggregates_reject_unbounded_or_undefined_data():
    engine = Engine()
    with pytest.raises(InputError):
        engine.execute('Sum[Part[a,i],{i,1,Infinity}]')
    with pytest.raises(InputError):
        engine.execute('Product[Part[a,i],{i,1,100001}]')
    with pytest.raises(InputError):
        engine.execute('Sum[Part[a,i],{i,1,2}]')


def test_symbolic_aggregate_path_is_preserved():
    assert Engine().execute('Sum[1/k^2,{k,1,Infinity}]')['text'] == '(1/6)*Pi^2'


def test_list_and_exact_matrix_results_share_array_arithmetic():
    engine = Engine()
    assert engine.execute('a={{1,2},{3,5}};a-Dot[a,IdentityMatrix[2]]')['text'] == '{{0, 0}, {0, 0}}'
    assert engine.execute('Inverse[a]+a')['text'] == '{{-4, 4}, {6, 4}}'


def test_rectangular_table_display():
    result = Engine().execute('TableForm[Table[{k,k^2},{k,1,3}]]')
    assert 'matrix' in result['latex']
    assert result['text'] == '{{1, 1}, {2, 4}, {3, 9}}'
    with pytest.raises(InputError):
        Engine().execute('TableForm[{{1,2},{3}}]')
