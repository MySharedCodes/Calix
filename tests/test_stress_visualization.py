import json
import sys
from pathlib import Path

import numpy as np
import pytest

from backend.engine import Engine
from backend.syntax import InputError, parse


@pytest.mark.parametrize('strain', [0, 0.00001])
def test_authored_stress_recovers_affine_fields_and_rigid_translation(strain):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from bridge_case import notebook

    e = Engine()
    e.execute('''p={{0,0},{2,0},{2,1},{0,1}};f={{1,2,3,4}};
    e=200000000000;v=3/10;t=18/100;
    p₅=Table[{Part[j,1],Part[j,2],1},{j,p}];
    p₂=Table[Table[{Part[j,1]+4*b,Part[j,2],Part[j,3]},
      {j,{{0,0,0},{2,0,0},{2,1,0},{0,1,0},{0,0,3},{2,0,3},{2,1,3},{0,1,3}}}],{b,1,4}];
    f₂={{1,2,3,4,5,6,7,8}};
    m₂=Table[ToElementMesh["Coordinates"->j,"MeshElements"->{HexahedronElement[f₂]}],{j,p₂}];
    t₁=SparseArray[Table[{i,i}->1,{i,1,20}],{20,20}];
    p₃={{{0,0,0},{1,0,0}}};a₁={100};l={{{0,0,3},{1,0,3}}};''')
    e.execute(f'α={strain};')
    e.execute('''u=Flatten[Table[{1+α*Part[j,1],2,3,0,0},{j,p}]];
    u₂=Table[Table[{1+α*Part[j,1],2-α/5*Part[j,2],3-α/5*Part[j,3]},
      {j,Part[p₂,b]}],{b,1,4}];''')
    source = notebook(lambda code: None, lambda code: code)['cells'][-1]
    output = e.execute(source)
    expected = 2e11 * strain / (1 - .3**2) * np.sqrt(1 - .3 + .3**2)
    assert np.allclose(e.environment['s_1'], expected, atol=1e-3)
    assert np.allclose(e.environment['s_2'], 3e10 * strain, atol=1e-3)
    cloud = output['items'][-1]
    triangles = [p for p in cloud['primitives'] if p['type'] == 'triangle']
    assert len(triangles) == 50
    assert cloud['scalar_legend']['range'][1] > 0
    assert all(len(p['colors']) == 3 for p in triangles)
    json.dumps(output, allow_nan=False)


def test_mesh_boundary_omits_internal_faces():
    e = Engine()
    result = e.evaluate(parse('''m=ToElementMesh["Coordinates"->{{0,0,0},{1,0,0},{1,1,0},{0,1,0},
    {0,0,1},{1,0,1},{1,1,1},{0,1,1},{2,0,0},{2,1,0},{2,0,1},{2,1,1}},
    "MeshElements"->{HexahedronElement[{{1,2,3,4,5,6,7,8},{2,9,10,3,6,11,12,7}}]}];
    Part[Part[m["BoundaryElements"],1],1]'''))
    assert len(result) == 10
    assert {2, 3, 6, 7} not in [set(face) for face in result]
    assert len({tuple(sorted(face)) for face in result}) == 10


def test_color_interpolation_and_geometry_table_scope():
    e = Engine()
    assert e.execute('ColorData["TemperatureMap"][0]')['text'] == '#2448a6'
    assert e.execute('ColorData["TemperatureMap"][1]')['text'] == '#c73d38'
    e.execute('i=99;')
    plot = e.execute('''Graphics3D[{Table[GraphicsComplex[{{i,0,0},{i,1,0},{i,0,1}},
      Polygon[{1,2,3}],VertexColors->{"#ff0000","#00ff00","#0000ff"}],{i,{1,3}}]}]''')
    assert len(plot['primitives']) == 2
    assert plot['primitives'][1]['points'][0] == [3, 0, 0]
    assert e.execute('i')['text'] == '99'


@pytest.mark.parametrize('code', [
    'BarLegend[{"TemperatureMap",2}]',
    'BarLegend[{"TemperatureMap",{0,0}}]',
    'BarLegend[{"TemperatureMap",{0,Infinity}}]',
    'Legended[1,BarLegend[{"TemperatureMap",{0,1}}]]',
    'Graphics3D[{GraphicsComplex[{{0,0,0}},Polygon[{1,2,3}]]}]',
    'Graphics3D[{GraphicsComplex[{{0,0,0}},Point[{0,0,0}],VertexColors->{"red"}]}]',
    'Graphics3D[{Table[Point[{i,0,0}],{i,1,48001}]}]',
    'Graphics3D[{Table[Point[{i,0,0}],{i,1,3,0}]}]',
])
def test_invalid_scalar_graphics(code):
    with pytest.raises(InputError):
        Engine().execute(code)


def test_density_overlay_keeps_field_and_streamlines():
    e = Engine()
    result = e.execute('Show[DensityPlot[x+y,{x,0,1},{y,0,1}],StreamPlot[{1,x},{x,0,1},{y,0,1}]]')
    assert result['plot_type'] == 'density'
    assert len(result['z']) > 10 and len(result['traces']) > 5
    assert result['options']['equal_aspect']
    assert all(len(t['x']) == len(t['y']) > 2 for t in result['traces'])
    json.dumps(result, allow_nan=False)


def test_extrema_accept_native_numeric_arrays_and_nested_lists():
    e = Engine()
    e.environment['a'] = np.array([[2., -1.], [5., 3.]])
    assert e.execute('Min[a]')['text'] == '-1.00000000000000'
    assert e.execute('Max[a]')['text'] == '5.00000000000000'
    assert e.execute('Max[{{1,4},{2,3}},0]')['text'] == '4'
