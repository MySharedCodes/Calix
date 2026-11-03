"""Scalar diffusion/wave method of lines and rectangular Poisson FEM."""
import numpy as np
import sympy as s
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator, LinearNDInterpolator
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh
from skfem import MeshTri, Basis, ElementTriP1, asm, condense, LinearForm
from skfem.models.poisson import laplace, mass
from backend.syntax import InputError
from . import Solution, finite, count
from .linalg import solve as sparse_solve


def prepare(fn, ranges, resolution):
    if not isinstance(fn, s.Function) or len(fn.args) != 2 or len(ranges) != 2:
        raise InputError('Numerical PDEs require one scalar u[x,y] and two rectangular coordinate ranges')
    n = count(resolution, 9, 101)
    grids = []
    for spec in ranges:
        if not isinstance(spec, list) or len(spec) != 3 or not isinstance(spec[0], s.Symbol):
            raise InputError('Use {coordinate,lower,upper}')
        low, high = [finite(v, -1e6, 1e6, 'Coordinate') for v in spec[1:]]
        if low >= high:
            raise InputError('Coordinate ranges must increase')
        grids.append(np.linspace(low, high, n))
    if tuple(spec[0] for spec in ranges) != fn.args:
        raise InputError('Coordinate ranges must follow the order in u[x,y]')
    return grids, n


def solve(equations, fn, ranges, resolution=41):
    grids, n = prepare(fn, ranges, resolution)
    x, y = fn.args
    equations = equations if isinstance(equations, list) else [equations]
    pdes = [eq for eq in equations if isinstance(eq, s.Equality) and eq.has(s.Derivative)]
    bcs = [eq for eq in equations if eq not in pdes]
    if len(pdes) != 1 or any(not isinstance(eq, s.Equality) for eq in bcs):
        raise InputError('Provide one PDE and explicit Dirichlet / initial value equations')
    residual = s.expand(pdes[0].lhs-pdes[0].rhs)
    xx, yy = s.diff(fn,x,2), s.diff(fn,y,2)
    ax, ay = residual.coeff(xx), residual.coeff(yy)
    if ax != 0 and s.simplify(ax-ay) == 0:
        source = s.simplify(residual-ax*(xx+yy))
        if source.has(fn, s.Derivative) or source.free_symbols-{x,y}:
            raise InputError('Poisson FEM requires a prescribed scalar source')
        # Explicit conditions on all four edges prevent an accidental underconstrained solve.
        expected = [fn.subs(x,grids[0][0]),fn.subs(x,grids[0][-1]),fn.subs(y,grids[1][0]),fn.subs(y,grids[1][-1])]
        match = lambda a,b: a.func == b.func and all(s.simplify(i-j)==0 for i,j in zip(a.args,b.args))
        if len(bcs) != 4 or any(sum(match(bc.lhs,e) for bc in bcs)!=1 for e in expected):
            raise InputError('Poisson FEM needs one value boundary condition on each rectangular edge')
        mesh = MeshTri.init_tensor(*grids)
        basis = Basis(mesh,ElementTriP1())
        f = s.lambdify((x,y),source/ax,'numpy')
        @LinearForm
        def load(v,w): return f(w.x[0],w.x[1])*v
        a, b = asm(laplace,basis), asm(load,basis)
        prescribed = np.zeros(basis.N)
        assigned = np.zeros(basis.N,dtype=bool)
        for bc,e in zip([next(bc for bc in bcs if match(bc.lhs,e)) for e in expected], expected):
            axis = 0 if e.args[0] != x else 1
            at = float(e.args[axis])
            indices = np.flatnonzero(np.isclose(mesh.p[axis],at))
            func = s.lambdify((x,y),bc.rhs,'numpy')
            values = np.broadcast_to(func(*mesh.p[:,indices]),(len(indices),))
            if np.any(assigned[indices] & ~np.isclose(prescribed[indices],values)):
                raise InputError('Dirichlet conditions disagree at a corner')
            prescribed[indices]=values; assigned[indices]=True
        fixed=np.flatnonzero(assigned)
        reduced,load,u,free=condense(a,b,x=prescribed,D=fixed)
        u[free]=sparse_solve(reduced,load)
        free=np.flatnonzero(~assigned)
        error=float(np.linalg.norm((a@u-b)[free])/max(np.linalg.norm(b[free]),1e-15))
        return Solution('Poisson FEM',{'mesh':mesh,'u':u,'grids':grids}, {'DOF':basis.N,'elements':mesh.nelements,'relative residual':error})
    yt=s.diff(fn,y)
    order = 1 if residual.coeff(yt)!=0 else 2
    time = yt if order==1 else yy
    if residual.coeff(time)==0 or ax==0:
        raise InputError('Supported numerical PDEs: rectangular Poisson, 1D heat and 1D wave')
    coefficient = s.simplify(-ax/residual.coeff(time))
    if s.simplify(residual-residual.coeff(time)*(time-coefficient*xx))!=0:
        raise InputError('Method of lines currently supports homogeneous constant-coefficient heat or wave equations')
    c=finite(coefficient,1e-12,1e6,'Diffusion / squared wave speed')
    left,right=fn.subs(x,grids[0][0]),fn.subs(x,grids[0][-1])
    initial=fn.subs(y,grids[1][0])
    match=lambda a,b: a.func==b.func and all(s.simplify(i-j)==0 for i,j in zip(a.args,b.args))
    lookup=lambda target: next((bc.rhs for bc in bcs if match(bc.lhs,target)),None)
    g,h,f=lookup(left),lookup(right),lookup(initial)
    if any(v is None for v in (g,h,f)) or len(bcs)!=3 or g.has(y) or h.has(y):
        raise InputError('Heat / wave needs two time-independent edge values and an initial profile; wave assumes zero initial velocity')
    z=np.broadcast_to(s.lambdify(x,f,'numpy')(grids[0]),(n,)).astype(float).copy()
    if not np.isclose(z[0],float(g)) or not np.isclose(z[-1],float(h)):
        raise InputError('Initial profile must agree with endpoint values')
    dx=grids[0][1]-grids[0][0]
    a=c/dx**2*diags([np.ones(n-3),-2*np.ones(n-2),np.ones(n-3)],[-1,0,1],format='csc')
    force=np.zeros(n-2);force[0]=c*float(g)/dx**2;force[-1]+=c*float(h)/dx**2
    if order==1:
        result=solve_ivp(lambda t,u:a@u+force,(grids[1][0],grids[1][-1]),z[1:-1],method='BDF',jac=a,t_eval=grids[1],rtol=1e-7,atol=1e-9)
    else:
        result=solve_ivp(lambda t,u:np.r_[u[n-2:],a@u[:n-2]+force],(grids[1][0],grids[1][-1]),np.r_[z[1:-1],np.zeros(n-2)],t_eval=grids[1],rtol=1e-7,atol=1e-9)
    if not result.success: raise InputError(result.message)
    u=np.vstack([np.full(n,float(g)),result.y[:n-2],np.full(n,float(h))]).T
    return Solution('Heat MOL' if order==1 else 'Wave MOL',{'grids':grids,'u':u}, {'spatial nodes':n,'time samples':n,'RHS evaluations':result.nfev,'min':float(u.min()),'max':float(u.max())})


def eigen(*args):
    if len(args)!=5: raise InputError('Use NDEigensystem[-Laplacian[u[x,y],{x,y}],u[x,y],{x,0,L},{y,0,H},count] with homogeneous Dirichlet boundaries')
    expr,fn,xr,yr,k=args
    grids,n=prepare(fn,[xr,yr],31)
    if s.simplify(expr+s.diff(fn,fn.args[0],2)+s.diff(fn,fn.args[1],2))!=0: raise InputError('NDEigensystem currently supports the negative Laplacian on rectangles')
    k=count(k,1,12)
    mesh=MeshTri.init_tensor(*grids);b=Basis(mesh,ElementTriP1())
    a,m=asm(laplace,b),asm(mass,b)
    _,_,_,free=condense(a,np.zeros(b.N),D=b.get_dofs())
    values,vectors=eigsh(a[free][:,free],k=k,M=m[free][:,free],sigma=0,which='LM')
    return [s.Float(v) for v in sorted(values)]


def value(model,coordinates):
    if not isinstance(coordinates,list) or len(coordinates)!=2: raise InputError('PDEValue needs {x,y}')
    p=np.array([float(v) for v in coordinates])
    grids=model.data.get('grids')
    if grids is None or any(v<g[0] or v>g[-1] for v,g in zip(p,grids)): raise InputError('Point is outside the solved scalar PDE domain')
    if 'mesh' in model.data:
        v=LinearNDInterpolator(model.data['mesh'].p.T,model.data['u'])(p)
    else: v=RegularGridInterpolator((grids[1],grids[0]),model.data['u'])(p[::-1][None,:])
    return float(np.asarray(v).ravel()[0])


def plot(model,kind):
    if kind not in ('Solution','Mesh'): raise InputError('Scalar PDEPlot supports "Solution" and "Mesh"')
    data=model.data;grids=data['grids']
    if 'mesh' in data:
        mesh=data['mesh']
        if kind=='Mesh':
            points=mesh.p[:,mesh.facets].transpose(2,1,0)
            xs=[];ys=[]
            for edge in points: xs.extend([*edge[:,0],None]);ys.extend([*edge[:,1],None])
            return {'kind':'plot','plot_type':'curve','title':'PDE mesh','axes':['x','y'],'traces':[{'x':xs,'y':ys,'name':'P1 triangles'}],'options':{'equal_aspect':True}}
        xx,yy=np.meshgrid(*grids);z=LinearNDInterpolator(mesh.p.T,data['u'])(xx,yy)
    else: z=data['u']
    return {'kind':'plot','plot_type':'density','title':model.family,'axes':['x','t' if 'MOL' in model.family else 'y'],'x':grids[0].tolist(),'y':grids[1].tolist(),'z':z.tolist()}
