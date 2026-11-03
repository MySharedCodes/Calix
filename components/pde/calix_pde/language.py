"""An explicit subset of Wolfram FEM's coefficient/matrix workflow.

Meshes and coefficient tensors are supplied by the notebook; there are no
bridge or airfoil identifiers in this assembler.
"""
from dataclasses import dataclass
import math
import numpy as np
import sympy as s
from scipy import sparse
from skfem import MeshQuad, MeshHex, MeshLine, MeshTri, Basis, ElementQuad1, ElementHex1, ElementLineP1, ElementTriP1, ElementVector, BilinearForm, LinearForm, asm
from backend.syntax import InputError
from .linalg import solve


def numeric(value):return np.asarray(value,dtype=float)


def format_array(value):
    if sparse.issparse(value):return f'SparseArray[{value.nnz} nonzero entries, {value.shape[0]} by {value.shape[1]}]'
    return value.tolist()


@dataclass
class Elements:
    kind:str
    indices:object
    markers:object=None

    def parts(self):return [self.indices] if self.markers is None else [self.indices,self.markers]


@dataclass
class Mesh:
    points:object
    elements:Elements
    boundary:object=None

    def __post_init__(self):
        if self.elements.kind=='TriangleElement':
            points=numeric(self.points);cells=np.asarray(self.elements.indices,dtype=int)-1
            if points.ndim!=2 or points.shape[1]!=2 or cells.ndim!=2 or cells.shape[1]!=3 or np.any(cells<0) or np.any(cells>=len(points)):
                raise InputError('TriangleElement requires planar coordinates and three valid indices per cell')
            q=points[cells];a=q[:,1]-q[:,0];b=q[:,2]-q[:,0];area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
            if not np.isfinite(q).all() or np.any(area*area[0]<=0) or np.any(np.abs(area)<1e-14*np.max(np.abs(q-q[:,:1]),axis=(1,2))**2):
                raise InputError('Invalid triangular mesh: degenerate or inconsistent element orientation')
            return
        if self.elements.kind!='QuadElement':return
        points=numeric(self.points);cells=np.asarray(self.elements.indices,dtype=int)-1
        if cells.ndim!=2 or cells.shape[1]!=4 or np.any(cells<0) or np.any(cells>=len(points)):
            raise InputError('QuadElement requires four valid node indices per cell')
        if points.ndim!=2 or points.shape[1]!=2:return
        vertices=points[cells]
        signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]])
        orientation=None
        for xi,eta in signs:
            derivative=np.c_[signs[:,0]*(1+signs[:,1]*eta),signs[:,1]*(1+signs[:,0]*xi)]/4
            jacobian=np.einsum('eai,aj->eij',vertices-vertices[:,:1,:],derivative)
            determinant=np.linalg.det(jacobian)
            if orientation is None:orientation=1 if determinant[0]>0 else -1
            scale=np.max(np.abs(jacobian),axis=(1,2))**2
            invalid=~np.isfinite(determinant)|(orientation*determinant<=1e-12*scale)
            if np.any(invalid):
                raise InputError(f'Invalid quadrilateral mesh: inverted, folded or degenerate cell {np.flatnonzero(invalid)[0]+1}; use consistent boundary winding')

    def summary(self):return f'ElementMesh[{self.elements.kind}, {len(self.points)} nodes]',r'\operatorname{ElementMesh}'

    def basis(self,components,order=2):
        cells=np.asarray(self.elements.indices,dtype=int)-1
        if np.any(cells<0) or np.any(cells>=len(self.points)):raise InputError('Mesh element indices are out of bounds')
        constructors={'TriangleElement':(MeshTri,ElementTriP1),'QuadElement':(MeshQuad,ElementQuad1),'HexahedronElement':(MeshHex,ElementHex1),'LineElement':(MeshLine,ElementLineP1)}
        cls,element=constructors[self.elements.kind]
        if self.elements.kind=='HexahedronElement':cells=cells[:,[6,2,5,7,1,3,4,0]]
        mesh=cls(numeric(self.points).T,cells.T)
        return Basis(mesh,ElementVector(element(),dim=components),intorder=order)

    def __call__(self,key):
        if key=='Coordinates':return self.points
        if key=='MeshElements':return [self.elements]
        if key=='BoundaryElements':
            if self.boundary is not None:return self.boundary
            cells=np.asarray(self.elements.indices,dtype=int)
            if self.elements.kind=='HexahedronElement':
                templates=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
                faces=np.vstack([cells[:,face] for face in templates])
                _,indices,counts=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
                return [Elements('QuadElement',faces[indices[counts==1]].tolist())]
            if self.elements.kind in ('QuadElement','TriangleElement'):
                edges=np.vstack([cells[:,pair] for pair in ([(0,1),(1,2),(2,0)] if self.elements.kind=='TriangleElement' else [(0,1),(1,2),(2,3),(3,0)])])
                _,indices,counts=np.unique(np.sort(edges,axis=1),axis=0,return_index=True,return_counts=True)
                return [Elements('LineElement',edges[indices[counts==1]].tolist())]
            raise InputError('Boundary extraction requires quadrilateral or hexahedral cells')
        if key=='Wireframe':
            cells=np.asarray(self.elements.indices,dtype=int)-1
            pairs={'TriangleElement':[(0,1),(1,2),(2,0)],'LineElement':[(0,1)],'QuadElement':[(0,1),(1,2),(2,3),(3,0)],'HexahedronElement':[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]}[self.elements.kind]
            edges=np.unique(np.sort(np.vstack([cells[:,pair] for pair in pairs]),axis=1),axis=0)
            points=numeric(self.points)
            if points.shape[1]==2:
                traces=[]
                for start in range(0,len(edges),3000):
                    x=[];y=[]
                    for i,j in edges[start:start+3000]:
                        x.extend([float(points[i,0]),float(points[j,0]),None]);y.extend([float(points[i,1]),float(points[j,1]),None])
                    traces.append({'x':x,'y':y,'name':'mesh','color':'#607d8b','width':0.7})
                return {'kind':'plot','plot_type':'curve','title':'ElementMesh','axes':['x','y'],'traces':traces,'options':{'equal_aspect':True,'legend':False}}
            return {'kind':'plot','plot_type':'geometry3d','title':'ElementMesh','axes':['x','y','z'],'primitives':[{'type':'line','points':points[edge].tolist(),'color':'#607d8b','label':''} for edge in edges],'options':{'wireframe':True}}
        raise InputError(f'Unsupported ElementMesh property {key}')


@dataclass
class Data:
    values:dict

    def summary(self):return 'FiniteElementData',r'\operatorname{FiniteElementData}'
    def __call__(self,key):
        if key not in self.values:raise InputError(f'Unknown finite-element property {key}')
        return self.values[key]


def rules(items):
    if not all(isinstance(item,tuple) and len(item)==2 for item in items):raise InputError('Expected option rules')
    return {key:value for key,value in items}


def assemble(coeff,method,solution):
    from backend.native import kernel
    v=coeff.values['variables'];mesh=solution.values['Space']
    if not isinstance(mesh,Mesh):raise InputError('SolutionData Space must contain an ElementMesh')
    n=len(v['DependentVariables']);d=len(v['Space']);p=coeff.values['coefficients']
    order=method.values.get('IntegrationOrder',2)
    if order not in (1,2,3,4):raise InputError('IntegrationOrder must be from 1 to 4')
    c=numeric(p.get('DiffusionCoefficients',np.zeros((n,n,d,d))))
    a=numeric(p.get('ReactionCoefficients',np.zeros((n,n))))
    alpha=numeric(p.get('ConservativeConvectionCoefficients',np.zeros((n,n,d))))
    beta=numeric(p.get('ConvectionCoefficients',np.zeros((n,n,d))))
    f=numeric(p.get('LoadCoefficients',np.zeros(n)))
    if c.shape!=(n,n,d,d) or a.shape!=(n,n) or alpha.shape!=(n,n,d) or beta.shape!=(n,n,d) or f.shape!=(n,):
        raise InputError('Coefficient tensors must match dependent-variable and coordinate dimensions')
    if not all(np.all(np.isfinite(t)) for t in (c,a,alpha,beta,f)):raise InputError('Finite coefficient tensors are required')
    if mesh.elements.kind not in ('TriangleElement','QuadElement','HexahedronElement') or d not in (2,3):
        raise InputError('Coefficient FEM requires planar triangles/quadrilaterals or 3D hexahedra')
    if p.keys()-{'DiffusionCoefficients','ReactionCoefficients','ConservativeConvectionCoefficients','ConvectionCoefficients','LoadCoefficients'}:
        raise InputError('Unsupported coefficient type')
    points=numeric(mesh.points);cells=np.asarray(mesh.elements.indices,dtype=np.int32)-1
    if points.shape[1]!=d:raise InputError('Mesh and coefficient dimensions differ')
    local,load=kernel.fem_elements(points,cells,n,int(order),(c,a,alpha,beta,f))
    indices=(cells[:,:,None]*n+np.arange(n)).reshape(len(cells),-1)
    rows=np.broadcast_to(indices[:,:,None],local.shape).ravel()
    columns=np.broadcast_to(indices[:,None,:],local.shape).ravel()
    matrix=sparse.coo_matrix((local.ravel(),(rows,columns)),shape=(len(points)*n,)*2).tocsr()
    matrix.eliminate_zeros()
    vector=np.bincount(indices.ravel(),weights=load.ravel(),minlength=len(points)*n)
    return Data({'StiffnessMatrix':matrix,'LoadVector':vector,'ElementMesh':mesh})


def part(value,indices):
    if isinstance(value,np.matrix) and 1 in value.shape:value=np.asarray(value).ravel()
    selectors=[]
    for i in indices:
        if i==s.Symbol('All'):selectors.append(slice(None))
        elif isinstance(i,list):selectors.append(np.asarray(i,dtype=int)-1)
        else:selectors.append(int(i)-1 if int(i)>0 else int(i))
    if sparse.issparse(value):
        if len(selectors)==2:
            if all(isinstance(i,int) for i in selectors):return value[selectors[0],selectors[1]]
            return value[selectors[0],:][:,selectors[1]]
        return value[selectors[0],:]
    if len(selectors)==2 and all(isinstance(i,np.ndarray) for i in selectors):return value[np.ix_(*selectors)]
    return value[tuple(selectors)]


def call(engine,name,nodes):
    if name=='ToElementMesh' and nodes and nodes[0].kind=='call':
        from .meshing import to_mesh
        return to_mesh(engine,nodes)
    args=[engine.evaluate(node) for node in nodes]
    if name=='BoundaryMeshRegion':
        from .meshing import BoundaryRegion
        if len(args)!=2 or not isinstance(args[1],list) or len(args[1])!=1 or not isinstance(args[1][0],Elements) or args[1][0].kind!='LineElement':
            raise InputError('BoundaryMeshRegion requires coordinates and one LineElement boundary')
        return BoundaryRegion(args[0],args[1][0].indices)
    if name in ('TriangleElement','QuadElement','HexahedronElement','LineElement'):
        if len(args) not in (1,2):raise InputError(f'{name} requires connectivity and optional element markers')
        return Elements(name,*args)
    if name=='ToElementMesh':
        p=rules(args)
        if set(p)-{'Coordinates','MeshElements','BoundaryElements'}:raise InputError('Explicit mesh requires Coordinates and MeshElements')
        if len(p['MeshElements'])!=1 or not isinstance(p['MeshElements'][0],Elements):raise InputError('Provide one element type per mesh')
        mesh=Mesh(p['Coordinates'],p['MeshElements'][0],p.get('BoundaryElements'))
        points=numeric(mesh.points);cells=np.asarray(mesh.elements.indices,dtype=int)
        expected={'TriangleElement':3,'LineElement':2,'QuadElement':4,'HexahedronElement':8}[mesh.elements.kind]
        if points.ndim!=2 or cells.ndim!=2 or cells.shape[1]!=expected or np.any(cells<1) or np.any(cells>len(points)) or not np.all(np.isfinite(points)):
            raise InputError('Invalid explicit finite-element coordinates or connectivity')
        return mesh
    if name in ('NDSolve`VariableData','NDSolve`SolutionData'):
        result={}
        for names,values in args:
            if len(names)!=len(values):raise InputError('VariableData / SolutionData field lengths differ')
            result.update(zip(names,values))
        return Data(result)
    if name=='InitializePDECoefficients':
        return Data({'variables':args[0].values,'coefficients':rules(args[2:])})
    if name=='InitializePDEMethodData':return Data(rules(args[2:]))
    if name=='DiscretizePDE':return assemble(*args)
    if name=='SparseArray':
        entries,shape=args[:2];row=[];col=[];data=[]
        for index,value in entries:
            row.append(int(index[0])-1);col.append(int(index[1])-1);data.append(float(value))
        if len(set(zip(row,col)))!=len(row):raise InputError('SparseArray rules must have unique indices')
        shape=tuple(int(i) for i in shape)
        if any(r<0 or r>=shape[0] or c<0 or c>=shape[1] for r,c in zip(row,col)):raise InputError('SparseArray index outside its dimensions')
        return sparse.csr_matrix((data,(row,col)),shape=shape)
    if name=='LinearSolve':
        matrix=args[0] if sparse.issparse(args[0]) else sparse.csr_matrix(numeric(args[0]))
        return solve(matrix,numeric(args[1]))
    if name=='Nearest':
        from scipy.spatial import cKDTree
        points,key=args[0]
        if key!='Index':raise InputError('Supported form: Nearest[points->"Index",point]')
        cache=getattr(engine,'_nearest_cache',{})
        if id(points) not in cache:
            if len(cache)>=8:cache.clear()
            cache[id(points)]=(points,cKDTree(numeric(points)))
            engine._nearest_cache=cache
        return [s.Integer(cache[id(points)][1].query(numeric(args[1]))[1]+1)]
    if name=='ArrayReshape':return numeric(args[0]).reshape(tuple(map(int,args[1]))).tolist()
    if name=='ArrayFlatten':
        blocks = [[None if isinstance(value, (int, float, s.Number)) and value == 0 else value
                   for value in row] for row in args[0]]
        return sparse.bmat(blocks,format='csr')
    if name=='ConstantArray':return np.full(tuple(map(int,args[1])) if isinstance(args[1],list) else (int(args[1]),),float(args[0])).tolist()
    if name=='IdentityMatrix':return s.eye(int(args[0])).tolist()
    if name=='KroneckerDelta':return s.Integer(int(all(a==args[0] for a in args)))
    if name=='Length':return s.Integer(args[0].shape[0] if hasattr(args[0],'shape') else len(args[0]))
    if name=='Dimensions':return list(map(s.Integer,args[0].shape if hasattr(args[0],'shape') else np.shape(args[0])))
    if name=='Range':
        lo,hi,step=(1,args[0],1) if len(args)==1 else (*args,1) if len(args)==2 else args
        count=max(0,int(s.floor((hi-lo)/step))+1)
        if count>200000:raise InputError('Range exceeds 200000 items')
        return [lo+i*step for i in range(count)]
    if name in ('Union','Complement'):
        make=lambda value:tuple(map(make,value)) if isinstance(value,list) else value
        values=set(make(v) for v in args[0])
        for arg in args[1:]:
            values=values.union(make(v) for v in arg) if name=='Union' else values.difference(make(v) for v in arg)
        undo=lambda v:list(map(undo,v)) if isinstance(v,tuple) else v
        return [undo(v) for v in sorted(values,key=s.default_sort_key)]
    if name=='Norm':return s.Float(np.linalg.norm(numeric(args[0])))
    if name=='Association':return Data(rules(args))
    raise InputError(f'Unsupported finite-element operation {name}')
