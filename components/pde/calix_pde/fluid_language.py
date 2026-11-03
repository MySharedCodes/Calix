"""Wolfram-style fluid component on an explicitly supplied quadrilateral mesh."""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
import sympy as s
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree
from backend.syntax import InputError
from .language import Data,Mesh


@dataclass
class Polygon:
    points:object
    def summary(self):return 'Polygon',r'\operatorname{Polygon}'


@dataclass
class Fluid:
    fields:object
    coordinates:object
    parameters:dict

    def equation(self,rhs):
        if rhs!=[0,0,0]:raise InputError('The current fluid component requires zero body force and incompressible continuity')
        return self


@dataclass
class Boundary:
    equation:object
    predicate:object


@dataclass
class Domain:
    coordinates:object
    mesh:Mesh


class Distance(s.Function):
    nargs=3
    @staticmethod
    def _imp_(x,y,points):
        return distance_tree(tuple(points)).query(np.c_[np.asarray(x).ravel(),np.asarray(y).ravel()])[0].reshape(np.shape(x))


@lru_cache(maxsize=12)
def distance_tree(points):
    p=np.asarray(points,dtype=float)
    # Sample each polygon edge densely to approximate the wall distance.
    q=np.vstack([p*(1-t)+np.roll(p,-1,axis=0)*t for t in np.linspace(0,1,9)])
    return cKDTree(q)


@lru_cache(maxsize=12)
def interpolator(points,values):return LinearNDInterpolator(np.asarray(points,dtype=float),np.asarray(values,dtype=float))


def inside_polygon(x,y,polygon):
    x=np.asarray(x);y=np.asarray(y);inside=np.zeros(np.broadcast_shapes(x.shape,y.shape),dtype=bool)
    points=np.asarray(polygon,dtype=float)
    for a,b in zip(points,np.roll(points,-1,axis=0)):
        if a[1]==b[1]:continue
        inside^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
    return inside


class SpatialSample(s.Function):
    nargs=5

    def _latex(self,printer):return r'\operatorname{InterpolatingFunction}('+','.join(printer.doprint(a) for a in self.args[:2])+')'

    def sample(self,x,y):
        points,values,polygon=self.args[2:]
        x,y=np.broadcast_arrays(np.asarray(x,dtype=float),np.asarray(y,dtype=float))
        result=np.asarray(interpolator(points,values)(x,y))
        return np.where(inside_polygon(x,y,polygon),np.nan,result)


@dataclass
class Field:
    points:object
    values:object
    polygon:object
    mesh:Mesh
    def summary(self):return 'InterpolatingFunction',r'\operatorname{InterpolatingFunction}'
    def __call__(self,*args):
        if len(args)==1 and isinstance(args[0],str):
            if args[0]=='ValuesOnGrid':return self.values
            if args[0]=='ElementMesh':return self.mesh
            raise InputError('Unsupported InterpolatingFunction property')
        if len(args)!=2:raise InputError('A 2D interpolating function requires two coordinates')
        if all(getattr(a,'is_number',False) for a in args):
            expr=SpatialSample(*args,self.points,self.values,self.polygon)
            return s.Float(float(expr.sample(float(args[0]),float(args[1]))))
        return SpatialSample(*args,self.points,self.values,self.polygon)


def call(engine,name,nodes):
    args=[engine.evaluate(n) for n in nodes]
    if name=='Polygon':return Polygon(args[0])
    if name=='RegionDistance':
        if len(args)!=2 or not isinstance(args[0],Polygon) or len(args[1])!=2:raise InputError('Use RegionDistance[Polygon[wallPoints],{x,y}]')
        return Distance(*args[1],s.Tuple(*[s.Tuple(*p) for p in args[0].points]))
    if name=='FluidFlowPDEComponent':
        if len(args)!=2 or not isinstance(args[1],(dict,Data)):raise InputError('FluidFlowPDEComponent requires variables and an Association of material parameters')
        return Fluid(args[0][0],args[0][1],args[1] if isinstance(args[1],dict) else args[1].values)
    if name=='DirichletCondition':return Boundary(*args)
    if name=='Element':return Domain(*args)
    raise InputError(f'Unsupported fluid expression {name}')


def solve(equations,unknowns,domain):
    from .wing import solve as flow
    equations=equations if isinstance(equations,list) else [equations]
    components=[e for e in equations if isinstance(e,Fluid)]
    boundaries=[e for e in equations if isinstance(e,Boundary)]
    if len(components)!=1 or len(components)+len(boundaries)!=len(equations):raise InputError('Provide one FluidFlowPDEComponent and DirichletCondition boundary equations')
    component=components[0];mesh=domain.mesh
    if not isinstance(mesh,Mesh) or mesh.elements.kind!='QuadElement':raise InputError('The fluid component currently requires a structured annular quadrilateral mesh')
    if len(component.fields)!=3 or tuple(component.coordinates)!=tuple(domain.coordinates):raise InputError('Use {u[x,y],v[x,y],p[x,y]} with matching domain coordinates')
    params=component.parameters
    if set(params)-{'MassDensity','DynamicViscosity'}:raise InputError('Unsupported fluid material parameter')
    rho=s.sympify(params.get('MassDensity',1));mu=s.sympify(params['DynamicViscosity'])
    if not rho.is_number or float(rho)<=0:raise InputError('MassDensity must be a positive constant')
    x,y=component.coordinates;u,v,p=component.fields
    distances=list(mu.atoms(Distance))
    if len(distances)!=1:raise InputError('Supply one wall-distance expression in the algebraic viscosity')
    wallpoints=np.asarray(distances[0].args[2],dtype=float)
    points=np.asarray(mesh.points,dtype=float)
    m=len(wallpoints)
    if len(points)%m:raise InputError('Annular mesh must have the same number of nodes on each ring')
    rings=len(points)//m
    if not np.allclose(points[:m],wallpoints):raise InputError('First mesh ring must equal the specified wall polygon')
    expected={tuple(sorted((k*m+j,k*m+(j+1)%m,(k+1)*m+(j+1)%m,(k+1)*m+j))) for k in range(rings-1) for j in range(m)}
    actual={tuple(sorted(np.asarray(cell,dtype=int)-1)) for cell in mesh.elements.indices}
    if actual!=expected:raise InputError('Quad connectivity must cover the annular rings without missing or overlapping cells')
    if not mesh.boundary or len(mesh.boundary)!=1 or mesh.boundary[0].kind!='LineElement':raise InputError('Provide wall and outer boundary LineElement markers')
    boundary=mesh.boundary[0]
    if boundary.markers is None or len(boundary.indices)!=len(boundary.markers):raise InputError('Each boundary edge needs a marker')
    expected_edges={(tuple(sorted((j,(j+1)%m))),1) for j in range(m)}|{(tuple(sorted(((rings-1)*m+j,(rings-1)*m+(j+1)%m))),2) for j in range(m)}
    actual_edges={(tuple(sorted(np.asarray(edge,dtype=int)-1)),int(mark)) for edge,mark in zip(boundary.indices,boundary.markers)}
    if actual_edges!=expected_edges:raise InputError('Boundary marker 1 must describe the wall and marker 2 the outer ring')
    marker=s.Symbol('ElementMarker')
    prescribed={}
    if len(boundaries)!=5:raise InputError('Provide four wall/far-field velocity conditions and one pressure reference')
    for bc in boundaries:
        if not isinstance(bc.equation,s.Equality):raise InputError('Boundary conditions require scalar equalities')
        eq=bc.equation
        key=(eq.lhs,bc.predicate)
        if key in prescribed:raise InputError('Duplicate or conflicting fluid boundary condition')
        prescribed[key]=eq.rhs
    wall=[prescribed.get((field,s.Eq(marker,1))) for field in (u,v)]
    far=[prescribed.get((field,s.Eq(marker,2))) for field in (u,v)]
    if wall!=[0,0] or any(a is None or not getattr(a,'is_number',False) for a in far):raise InputError('Specify no slip on marker 1 and constant far-field velocity on marker 2')
    if not any(b.equation==s.Eq(p,0) and b.predicate==s.And(s.Eq(x,s.Rational(str(points[-m,0]))),s.Eq(y,s.Rational(str(points[-m,1])))) for b in boundaries):
        raise InputError('Pin p=0 at the first outer-ring node')
    speed=float(s.sqrt(far[0]**2+far[1]**2))
    if abs(speed-1)>1e-10:raise InputError('This steady-flow implementation uses unit nondimensional far-field speed')
    gu,gv,guy,gvx,d=s.symbols('_gu _gv _guy _gvx _d')
    constitutive=mu.xreplace({s.diff(u,x):gu,s.diff(v,y):gv,s.diff(u,y):guy,s.diff(v,x):gvx,distances[0]:d})/rho
    if constitutive.has(u,v,p) or constitutive.free_symbols-{gu,gv,guy,gvx,d}:raise InputError('Viscosity may depend on velocity gradients and wall distance only')
    laminar=float(constitutive.subs({gu:0,gv:0,guy:0,gvx:0,d:0}))
    if not 1/20000<=laminar<=.01:raise InputError('Supported nondimensional molecular viscosity is 1/20000 to 1/100')
    # NumPy's reduce implementation of symbolic Min/Max needs broadcast inputs.
    expression=constitutive.replace(s.Min,lambda *a:s.Function('_minimum')(*a)).replace(s.Max,lambda *a:s.Function('_maximum')(*a))
    fn=s.lambdify((gu,gv,guy,gvx,d),expression,[{'_minimum':lambda a,b:np.minimum(a,b),'_maximum':lambda a,b:np.maximum(a,b)},'numpy'])
    def viscosity(field,distance,current_nu):
        value=np.asarray(fn(field.grad[0,0],field.grad[1,1],field.grad[0,1],field.grad[1,0],distance),dtype=float)
        # Continue only the molecular viscosity; the authored turbulent term is retained.
        return value-laminar+current_nu
    base=mesh.basis(1).mesh
    alpha=np.degrees(np.arctan2(float(far[1]),float(far[0])))
    result=flow([1/laminar,alpha],4,(base,wallpoints.T,m,rings),viscosity)
    coords=s.Tuple(*[s.Tuple(*row) for row in points]);polygon=s.Tuple(*[s.Tuple(*row) for row in wallpoints])
    fields=[Field(coords,s.Tuple(*values),polygon,mesh) for values in [*result.data['velocity'],result.data['p']]]
    names=[field.func.__name__ for field in component.fields]
    if sorted(str(u) for u in unknowns)!=sorted(names):raise InputError('Request the velocity and pressure variables declared in FluidFlowPDEComponent')
    return [fields[names.index(str(u))] for u in unknowns]


def streamplot(engine,nodes):
    from scipy.integrate import solve_ivp
    from scipy.interpolate import RegularGridInterpolator
    if len(nodes)!=3:raise InputError('Use StreamPlot[{u[x,y],v[x,y]},{x,x0,x1},{y,y0,y1}]')
    specs=[engine.evaluate(n) for n in nodes[1:]]
    variables=[spec[0] for spec in specs]
    expressions=engine.scoped([nodes[0]],variables)[0]
    if len(expressions)!=2:raise InputError('StreamPlot requires a two-component vector field')
    axes=[np.linspace(float(spec[1]),float(spec[2]),101) for spec in specs]
    if any(a[0]>=a[-1] for a in axes):raise InputError('StreamPlot ranges must increase')
    xx,yy=np.meshgrid(*axes)
    values=[np.array(engine.sample(e,variables,[xx.ravel(),yy.ravel()]),dtype=float).reshape(xx.shape) for e in expressions]
    field=RegularGridInterpolator((axes[1],axes[0]),np.stack(values,axis=-1),bounds_error=False,fill_value=np.nan)
    length=axes[0][-1]-axes[0][0]
    def rhs(t,p):
        value=field([[p[1],p[0]]])[0]
        if not np.all(np.isfinite(value)):return np.zeros(2)
        return value/max(np.linalg.norm(value),1e-10)
    def exit(t,p):return min(p[0]-axes[0][0]+1e-8,axes[0][-1]-p[0],p[1]-axes[1][0],axes[1][-1]-p[1])
    exit.terminal=True;exit.direction=-1
    traces=[]
    for y in np.linspace(axes[1][0]*.9,axes[1][-1]*.9,13):
        result=solve_ivp(rhs,(0,3*length),[axes[0][0]+1e-7,y],events=exit,max_step=length/300,rtol=1e-6,atol=1e-8)
        traces.append({'x':result.y[0].tolist(),'y':result.y[1].tolist(),'name':f'y={y:.2f}'})
    return {'kind':'plot','plot_type':'curve','title':'StreamPlot','axes':[str(v) for v in variables],'traces':traces,'options':{'equal_aspect':True,'legend':False}}
