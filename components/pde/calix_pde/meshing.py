"""Conforming Delaunay refinement using SciPy's BSD-licensed Qhull backend."""
from dataclasses import dataclass
import numpy as np
import sympy as s
from scipy.spatial import Delaunay,cKDTree
from backend.syntax import InputError


@dataclass
class BoundaryRegion:
    points:object
    edges:object


def inside(points,boundary,edges):
    result=np.zeros(len(points),bool)
    # Ray crossings with an even/odd rule support multiple loops and holes.
    for lo in range(0,len(edges),128):
        a=boundary[edges[lo:lo+128,0]];b=boundary[edges[lo:lo+128,1]]
        x=points[:,0,None];y=points[:,1,None]
        cross=((a[:,1]>y)!=(b[:,1]>y)) & (x<(b[:,0]-a[:,0])*(y-a[:,1])/np.where(b[:,1]!=a[:,1],b[:,1]-a[:,1],1)+a[:,0])
        result^=(np.count_nonzero(cross,axis=1)%2).astype(bool)
    return result


def refinement(engine,node):
    if node.kind!='call' or node.args[0].value!='Function' or len(node.args)!=3 or node.args[1].kind!='list' or len(node.args[1].args)!=2:
        raise InputError('Use MeshRefinementFunction -> Function[{vertices,area}, predicate]')
    variables=s.symbols('cx0 cy0 cx1 cy1 cx2 cy2 area',real=True)
    previous=engine.environment.copy()
    try:
        names=[arg.value for arg in node.args[1].args]
        engine.environment[names[0]]=[list(variables[i:i+2]) for i in range(0,6,2)]
        engine.environment[names[1]]=variables[-1]
        predicate=engine.evaluate(node.args[2])
    finally:engine.environment=previous
    if not isinstance(predicate,(s.logic.boolalg.Boolean,bool)):raise InputError('Mesh refinement function must return a Boolean predicate')
    if getattr(predicate,'free_symbols',set())-set(variables):raise InputError('Unresolved symbols in mesh refinement function')
    compiled=s.lambdify(variables,predicate,'numpy',cse=True)
    def evaluate(triangles,areas):
        values=triangles.reshape(len(triangles),6).T
        return np.broadcast_to(np.asarray(compiled(*values,areas),dtype=bool),areas.shape)
    return evaluate


def to_mesh(engine,nodes):
    from .language import Mesh,Elements
    region=engine.evaluate(nodes[0])
    if not isinstance(region,BoundaryRegion):raise InputError('Expected a BoundaryMeshRegion')
    maximum=.01;predicate=None
    for option in nodes[1:]:
        if option.kind!='binary' or option.value!='->':raise InputError('ToElementMesh requires option rules')
        key=str(engine.evaluate(option.args[0]))
        if key=='MaxCellMeasure':maximum=float(engine.evaluate(option.args[1]))
        elif key=='MeshRefinementFunction':predicate=refinement(engine,option.args[1])
        elif key=='MeshOrder':
            if engine.evaluate(option.args[1])!=1:raise InputError('Triangular meshing currently supports MeshOrder -> 1')
        else:raise InputError(f'Unsupported triangular meshing option {key}')
    if not np.isfinite(maximum) or maximum<=0:raise InputError('MaxCellMeasure must be finite and positive')
    points=np.asarray(region.points,float);edges=np.asarray(region.edges,int)-1
    if points.ndim!=2 or points.shape[1]!=2 or edges.ndim!=2 or edges.shape[1]!=2 or not np.isfinite(points).all() or edges.min()<0 or edges.max()>=len(points):
        raise InputError('BoundaryMeshRegion requires finite planar coordinates and valid edges')
    if len(np.unique(points,axis=0))!=len(points):raise InputError('Boundary mesh contains duplicate coordinates')
    if not np.all(np.bincount(edges.ravel(),minlength=len(points))==2):raise InputError('Boundary edges must form closed loops')
    boundary=points.copy();boundary_edges=edges.copy()
    spacing=np.sqrt(2*maximum)
    x=np.arange(points[:,0].min()+spacing/2,points[:,0].max(),spacing)
    y=np.arange(points[:,1].min()+spacing/2,points[:,1].max(),spacing*np.sqrt(3)/2)
    seeds=np.array([[v+(i%2)*spacing/2,w] for i,w in enumerate(y) for v in x]).reshape(-1,2)
    seeds=seeds[inside(seeds,boundary,boundary_edges)]
    near=np.zeros(len(seeds),bool)
    for start in range(0,len(edges),128):
        a=points[edges[start:start+128,0]];delta=points[edges[start:start+128,1]]-a
        offset=seeds[:,None,:]-a
        projection=np.clip(np.sum(offset*delta,axis=2)/np.sum(delta*delta,axis=1),0,1)
        near|=np.any(np.linalg.norm(offset-projection[:,:,None]*delta,axis=2)<spacing*1e-6,axis=1)
    seeds=seeds[~near]
    points=np.vstack([points,seeds])
    for iteration in range(80):
        if len(points)>45000:raise InputError('Triangular refinement exceeds 45000 nodes; increase the requested cell sizes')
        triangulation=Delaunay(points)
        cells=triangulation.simplices
        all_edges=np.sort(np.vstack([cells[:,[0,1]],cells[:,[1,2]],cells[:,[2,0]]]),axis=1)
        present=set(map(tuple,all_edges))
        missing=np.array([tuple(sorted(edge)) not in present for edge in edges])
        if missing.any():
            split=edges[missing];mid=(points[split[:,0]]+points[split[:,1]])/2
            indices=np.arange(len(points),len(points)+len(mid))
            edges=np.vstack([edges[~missing],np.c_[split[:,0],indices],np.c_[indices,split[:,1]]])
            points=np.vstack([points,mid]);continue
        vertices=points[cells];centers=vertices.mean(axis=1)
        cells=cells[inside(centers,boundary,boundary_edges)]
        vertices=points[cells];centers=vertices.mean(axis=1)
        u=vertices[:,1]-vertices[:,0];v=vertices[:,2]-vertices[:,0]
        areas=np.abs(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
        valid=areas>1e-13*np.maximum(np.sum(u*u,axis=1),np.sum(v*v,axis=1))
        cells=cells[valid];vertices=vertices[valid];areas=areas[valid]
        bad=areas>maximum*(1+1e-9)
        if predicate is not None:bad|=predicate(vertices,areas)
        squared=np.sum((vertices-np.roll(vertices,1,axis=1))**2,axis=2)
        cosine=(squared+np.roll(squared,1,axis=1)-np.roll(squared,-1,axis=1))/(2*np.sqrt(squared*np.roll(squared,1,axis=1)))
        bad|=np.max(cosine,axis=1)>np.cos(np.deg2rad(20))
        if not bad.any():break
        vertices=vertices[bad]
        u=vertices[:,1]-vertices[:,0];v=vertices[:,2]-vertices[:,0]
        determinant=2*(u[:,0]*v[:,1]-u[:,1]*v[:,0])
        uu=np.sum(u*u,axis=1);vv=np.sum(v*v,axis=1)
        added=vertices[:,0]+np.c_[(uu*v[:,1]-vv*u[:,1])/determinant,(u[:,0]*vv-v[:,0]*uu)/determinant]
        outside=~inside(added,boundary,boundary_edges)
        boundary_lookup={tuple(sorted(edge)):i for i,edge in enumerate(edges)}
        forced=set()
        for triangle in cells[bad][outside]:
            for pair in ((0,1),(1,2),(2,0)):
                key=tuple(sorted(triangle[list(pair)]))
                if key in boundary_lookup:forced.add(boundary_lookup[key])
        added=np.unique(added,axis=0)
        distance=cKDTree(points).query(added)[0]
        added=added[distance>1e-9];distance=distance[distance>1e-9]
        tree=cKDTree(added);blocked=np.zeros(len(added),bool);selected=[]
        for index in np.argsort(-distance):
            if blocked[index]:continue
            selected.append(index)
            blocked[tree.query_ball_point(added[index],.8*distance[index])]=True
        added=added[selected]
        midpoint=(points[edges[:,0]]+points[edges[:,1]])/2
        radius=np.linalg.norm(points[edges[:,0]]-points[edges[:,1]],axis=1)/2
        encroached=np.array([len(hits)>0 for hits in cKDTree(added).query_ball_point(midpoint,radius*(1+1e-9))])
        if forced:encroached[list(forced)]=True
        if encroached.any():
            split=edges[encroached];mid=midpoint[encroached]
            indices=np.arange(len(points),len(points)+len(mid))
            edges=np.vstack([edges[~encroached],np.c_[split[:,0],indices],np.c_[indices,split[:,1]]])
            points=np.vstack([points,mid]);continue
        added=added[inside(added,boundary,boundary_edges)]
        added=np.unique(added,axis=0)
        distance=cKDTree(points).query(added)[0]
        added=added[distance>1e-10]
        if not len(added):raise InputError('Mesh refinement stalled before reaching the requested cell size')
        points=np.vstack([points,added])
    else:raise InputError('Triangular refinement did not converge')
    used=np.unique(cells);remap=np.full(len(points),-1,int);remap[used]=np.arange(len(used))
    cells=remap[cells];points=points[used];edges=remap[edges]
    if np.any(edges<0):raise InputError('Boundary nodes were lost during triangulation')
    # Exact agreement between recovered constraints and the final boundary is essential.
    pairs=np.sort(np.vstack([cells[:,[0,1]],cells[:,[1,2]],cells[:,[2,0]]]),axis=1)
    unique,counts=np.unique(pairs,axis=0,return_counts=True)
    if set(map(tuple,unique[counts==1]))!=set(map(tuple,np.sort(edges,axis=1))):raise InputError('Triangulation failed to preserve the complete boundary')
    return Mesh(points.tolist(),Elements('TriangleElement',(cells+1).tolist()),[Elements('LineElement',(edges+1).tolist())])
