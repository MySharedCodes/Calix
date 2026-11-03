import numpy as np
import pytest
import sympy as s
from backend.engine import Engine
from backend.syntax import parse,InputError


def test_two_argument_arctangent_quadrants():
    e=Engine()
    for x,y,angle in [(1,1,s.pi/4),(-1,1,3*s.pi/4),(-1,-1,-3*s.pi/4),(1,-1,-s.pi/4)]:
        assert e.evaluate(parse(f'ArcTan[{x},{y}]'))==angle


def test_undefined_iterator_names_and_numeric_mesh_indices():
    e=Engine()
    with pytest.raises(InputError,match='undefined: b'):
        e.execute('Table[i,{i,0,b}]')
    e.environment['p']=[[2,3],[4,5]];e.environment['i']=1
    assert e.evaluate(parse('Part[p,i,2]'))==3
    e.environment['b']=np.float64(2)
    assert e.evaluate(parse('Table[i,{i,0,b}]'))==[0,1,2]
    assert e.evaluate(parse('Mean[{{1,2},{3,4}}]'))==[2,3]


def test_unstructured_mesh_preserves_hole_and_refines_selected_area():
    from backend.components import pde_module
    pde_module()
    e=Engine()
    e.execute('m=ToElementMesh[BoundaryMeshRegion[{{0,0},{2,0},{2,2},{0,2},{0.8,0.8},{0.8,1.2},{1.2,1.2},{1.2,0.8}},{LineElement[{{1,2},{2,3},{3,4},{4,1},{5,6},{6,7},{7,8},{8,5}}]}],MaxCellMeasure->0.08,MeshRefinementFunction->Function[{v,a},Part[Mean[v],1]<0.5&&a>0.005],MeshOrder->1];')
    m=e.environment['m'];p=np.asarray(m.points,float);f=np.asarray(m.elements.indices)-1;q=p[f]
    u=q[:,1]-q[:,0];v=q[:,2]-q[:,0];a=np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
    assert a.sum()==pytest.approx(3.84,abs=1e-12)
    assert a.max()<=.08*(1+1e-9)
    assert a[q.mean(axis=1)[:,0]<.5].max()<=.005*(1+1e-9)
    assert not np.any(np.all((q.mean(axis=1)>.8)&(q.mean(axis=1)<1.2),axis=1))
    e.execute('m=ToElementMesh[BoundaryMeshRegion[{{0,0},{1,0},{0,1}},{LineElement[{{1,2},{2,3},{3,1}}]}],MaxCellMeasure->100]')
    assert len(e.environment['m'].elements.indices)==1


def test_gear_bore_constraints_include_refined_boundary_midpoints():
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
    from gear_case import notebook
    source=notebook(lambda c:None,lambda c:c)['cells'][4]
    e=Engine()
    e.environment.update(p=[[[1,0],[.35,0],[0,.35],[.175,.175]],[[5,0],[3.7,0],[3,.7],[3.35,.35]]],l=[[[1,1],[2,4],[4,3],[3,2]],[[1,1],[2,4],[4,3],[3,2]]],e=4)
    e.execute(source[source.index('d₁='):source.index('\nd=Flatten')])
    assert e.environment['d_1']==[2,3,4]
    assert e.environment['d_2']==[6,7,8]


def test_plotrange_clips_faces_and_interpolates_colors():
    result=Engine().execute('Graphics3D[{GraphicsComplex[{{-1,0,0},{1,0,0},{0,2,0}},Polygon[{1,2,3}],VertexColors->{"#000000","#ff0000","#0000ff"}],Line[{{-2,0,0},{2,0,0}}]},PlotRange->{{0,1},{0,1},{-1,1}}]')
    triangles=[p for p in result['primitives'] if p['type']=='triangle']
    area=0
    for triangle in triangles:
        p=np.array(triangle['points']);assert np.all(p[:,:2]>=-1e-12) and np.all(p[:,:2]<=1+1e-12)
        area+=np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))/2
    assert area==pytest.approx(.75)
    assert result['primitives'][-1]['points']==[[0,0,0],[1,0,0]]
    colors=[color for t in triangles for p,color in zip(t['points'],t['colors']) if np.allclose(p,[0,0,0])]
    assert colors and set(colors)=={'#800000'}
    with pytest.raises(InputError,match='three coordinate intervals'):
        Engine().execute('Graphics3D[{Point[{0,0,0}]},PlotRange->{{0,1}}]')
