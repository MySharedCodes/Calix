"""Taylor-Hood steady incompressible RANS on a body-fitted NACA0012 grid.

Algebraic Prandtl mixing length with van Driest damping. This is an attached-flow
teaching model, not a separated-flow aerodynamic certification tool.
"""
import numpy as np
from scipy.sparse import bmat
from .linalg import solve as spsolve
from scipy.spatial import cKDTree
from scipy.interpolate import LinearNDInterpolator
from skfem import MeshQuad, Basis, FacetBasis, ElementQuad1, ElementQuad2, ElementVector, BilinearForm, asm, condense
from skfem.helpers import dot, ddot, grad, div, sym_grad, mul
from backend.syntax import InputError
from . import Solution, finite, count


def make_mesh(n):
    m=16*n;rings=2*n+12
    theta=np.arange(m)*2*np.pi/m
    x=(1+np.cos(theta))/2
    thickness=.6*(.2969*np.sqrt(x)-.126*x-.3516*x**2+.2843*x**3-.1036*x**4)
    surface=np.array([x,np.sign(np.sin(theta))*thickness])
    surface[1,0]=0;surface[1,m//2]=0
    outer=np.array([.5+6*np.cos(theta),6*np.sin(theta)])
    radii=np.r_[0,np.geomspace(.0015,1,rings-1)]
    points=np.hstack([surface*(1-r)+outer*r for r in radii])
    quadrilaterals=[]
    for k in range(rings-1):
        for j in range(m):
            a=k*m+j;b=k*m+(j+1)%m;c=(k+1)*m+j;d=(k+1)*m+(j+1)%m
            quadrilaterals.append([a,b,d,c])
    mesh=MeshQuad(points,np.array(quadrilaterals).T)
    return mesh,surface,m,rings


def solve(parameters,resolution,explicit_mesh=None,viscosity_function=None):
    re=finite(parameters[0],100,20000,'Chord Reynolds number')
    alpha=finite(parameters[1],-4,4,'Angle [degree]')*np.pi/180
    n=count(resolution,4,12)
    mesh,surface,m,rings=make_mesh(n) if explicit_mesh is None else explicit_mesh
    vb=Basis(mesh,ElementVector(ElementQuad2()),intorder=4)
    pb=Basis(mesh,ElementQuad1(),intorder=4)
    wall=mesh.boundary_facets()[np.all(mesh.facets[:,mesh.boundary_facets()]<m,axis=0)]
    outer=mesh.boundary_facets()[np.all(mesh.facets[:,mesh.boundary_facets()]>=(rings-1)*m,axis=0)]
    fixed=vb.get_dofs(facets=np.r_[wall,outer]).all()
    initial=np.zeros(vb.N+pb.N)
    uinf=np.array([np.cos(alpha),np.sin(alpha)])
    outd=vb.get_dofs(facets=outer)
    for i in range(2): initial[outd.all(['u^'+str(i+1)])]=uinf[i]
    pinned=vb.N+(rings-1)*m
    fixed=np.r_[fixed,pinned]
    @BilinearForm
    def divergence(u,q,w): return -q*div(u)
    b=asm(divergence,vb,pb)
    @BilinearForm
    def viscous(u,v,w): return 2*w.nu*ddot(sym_grad(u),sym_grad(v))
    @BilinearForm
    def advective(u,v,w):
        conv=mul(grad(u),w.wind)
        return dot(conv,v)+w.tau*dot(conv,mul(grad(v),w.wind))
    wallpoints=np.hstack([surface*(1-t)+np.roll(surface,-1,axis=1)*t for t in np.linspace(0,1,9)])
    coords=vb.global_coordinates()
    distance=cKDTree(wallpoints.T).query(coords.reshape(2,-1).T)[0].reshape(coords.shape[1:])
    u=initial[:vb.N].copy();pressure=np.zeros(pb.N);history=[]
    # Continuation makes the low-order initial field useful at moderate Reynolds number.
    stages=sorted(set([min(re,200),min(re,1000),re]))
    converged=False;final_matrix=None
    for current_re in stages:
        nu=1/current_re
        for iteration in range(80):
            field=vb.interpolate(u)
            strain=np.sqrt(np.maximum(2*ddot(sym_grad(field),sym_grad(field)),0))
            # Wall friction estimate sqrt(nu*|du/dn|) supplies the damping scale.
            friction=np.sqrt(nu*np.maximum(strain,0))
            length=np.minimum(.41*distance,.09)*(1-np.exp(-distance*friction/(26*nu)))
            nut=length**2*strain if viscosity_function is None else viscosity_function(field,distance,nu)-nu
            if not np.all(np.isfinite(nut)) or np.min(nut)<-1e-12:raise InputError('The supplied viscosity must be finite and nonnegative')
            speed=np.sqrt(np.sum(field**2,axis=0))
            h=vb.default_parameters()['h']
            tau=1/np.sqrt((2*speed/h)**2+(4*(nu+nut)/h**2)**2+1e-20)
            a=asm(viscous,vb,nu=nu+nut)+asm(advective,vb,wind=field,tau=tau)
            matrix=bmat([[a,b.T],[b,None]],format='csr')
            rhs=np.zeros(matrix.shape[0])
            reduced,load,x,free=condense(matrix,rhs,x=initial.copy(),D=fixed)
            x[free]=spsolve(reduced,load)
            change=np.linalg.norm(x[:vb.N]-u)/max(np.linalg.norm(x[:vb.N]),1e-12)
            if not np.isfinite(change) or np.max(np.abs(x))>1e8: raise InputError('Steady wing iteration diverged; reduce Reynolds number or incidence')
            relaxation=.65
            u=(1-relaxation)*u+relaxation*x[:vb.N]
            pressure=(1-relaxation)*pressure+relaxation*x[vb.N:]
            if current_re==re: history.append(float(change))
            if change<2e-5:
                if current_re==re: converged=True;final_matrix=matrix
                break
    if not converged:
        raise InputError(f'Steady RANS did not converge (relative update {history[-1]:.3g}); use Re <= 5000 or refine the mesh')
    # Weak divergence is tested in the pressure space independently of the update.
    weak_div=float(np.linalg.norm(b@u)/max(np.linalg.norm(u),1e-12))
    field=vb.interpolate(u)
    strain=np.sqrt(np.maximum(2*ddot(sym_grad(field),sym_grad(field)),0))
    nu=1/re;friction=np.sqrt(nu*strain)
    length=np.minimum(.41*distance,.09)*(1-np.exp(-distance*friction/(26*nu)))
    nut=length**2*strain if viscosity_function is None else viscosity_function(field,distance,nu)-nu
    # Integrated stress on the actual airfoil facets, including molecular wall shear.
    fb=FacetBasis(mesh,vb.elem,facets=wall,intorder=4)
    fp=FacetBasis(mesh,ElementQuad1(),facets=wall,intorder=4)
    uf=fb.interpolate(u);pf=fp.interpolate(pressure)
    sigma=2*nu*sym_grad(uf)-np.eye(2)[:,:,None,None]*pf
    # Fluid outward normal points into the wing; reverse the fluid traction.
    traction=-np.einsum('ijab,jab->iab',sigma,fb.normals)
    force=np.sum(traction*fb.dx[None,:,:],axis=(1,2))
    drag=float(2*force@uinf);lift=float(2*force@np.array([-uinf[1],uinf[0]]))
    flux=float(np.sum(np.einsum('iab,iab->ab',FacetBasis(mesh,vb.elem,facets=outer,intorder=4).interpolate(u),FacetBasis(mesh,vb.elem,facets=outer,intorder=4).normals)*FacetBasis(mesh,vb.elem,facets=outer,intorder=4).dx))
    data={'mesh':mesh,'u':u,'p':pressure,'surface':surface,'history':np.array(history),'nut':nut.mean(axis=-1),'velocity':u[vb.nodal_dofs], 're':re}
    metrics={'Re':re,'angle [degree]':alpha*180/np.pi,'quadrilaterals':mesh.nelements,'DOF':vb.N+pb.N,
             'iterations':len(history),'relative update':history[-1],'weak divergence':weak_div,'net outer flux':flux,
             'C_L':lift,'C_D':drag,'max eddy viscosity / nu':float(np.max(nut)/nu)}
    return Solution('Wing RANS',data,metrics)


def plot(model,kind):
    if kind not in ('Mesh','Velocity','Pressure','Streamlines','Convergence'): raise InputError('Wing PDEPlot supports "Mesh", "Velocity", "Pressure", "Streamlines", "Convergence"')
    a=model.data;mesh=a['mesh'];surface=a['surface']
    options={'equal_aspect':True,'x_range':[-.6,2],'range':[-.7,.7]}
    if kind=='Convergence':
        return {'kind':'plot','plot_type':'curve','title':'RANS relative update','axes':['iteration','relative update'],'traces':[{'x':list(range(1,len(a['history'])+1)),'y':a['history'].tolist(),'name':'Picard update'}]}
    if kind=='Mesh':
        x=[];y=[]
        for i,j in mesh.facets.T:
            x.extend([float(mesh.p[0,i]),float(mesh.p[0,j]),None]);y.extend([float(mesh.p[1,i]),float(mesh.p[1,j]),None])
        return {'kind':'plot','plot_type':'curve','title':'NACA0012 body-fitted mesh','axes':['x/c','y/c'],'traces':[{'x':x,'y':y,'name':'P2/P1 mesh'}],'options':options}
    if kind=='Streamlines':
        uv=LinearNDInterpolator(mesh.p.T,a['velocity'].T)
        traces=[]
        for y in np.linspace(-.45,.45,13):
            p=np.array([-.55,y]);points=[]
            for k in range(550):
                velocity=uv(p).ravel()
                if not np.all(np.isfinite(velocity)) or np.linalg.norm(velocity)<1e-6:break
                points.append(p.copy());step=.007*velocity/max(np.linalg.norm(velocity),.1)
                mid=uv(p+step/2).ravel()
                if not np.all(np.isfinite(mid)):break
                p+=.007*mid/max(np.linalg.norm(mid),.1)
                if p[0]>2 or abs(p[1])>.8:break
            if len(points)>1:
                points=np.array(points);traces.append({'x':points[:,0].tolist(),'y':points[:,1].tolist(),'name':f'y/c={y:.2f}'})
        traces.append({'x':np.r_[surface[0],surface[0,0]].tolist(),'y':np.r_[surface[1],surface[1,0]].tolist(),'name':'NACA0012'})
        return {'kind':'plot','plot_type':'curve','title':'Mean streamlines','axes':['x/c','y/c'],'traces':traces,'options':{**options,'legend':False}}
    x=np.linspace(-.6,2,141);y=np.linspace(-.7,.7,101);xx,yy=np.meshgrid(x,y)
    value=np.sqrt(np.sum(a['velocity']**2,axis=0)) if kind=='Velocity' else 2*a['p']
    z=LinearNDInterpolator(mesh.p.T,value)(xx,yy)
    # Mask the closed NACA profile; Delaunay interpolation alone fills its hole.
    xc=np.clip(xx,0,1);th=.6*(.2969*np.sqrt(xc)-.126*xc-.3516*xc**2+.2843*xc**3-.1036*xc**4)
    z[(xx>=0)&(xx<=1)&(np.abs(yy)<=th)]=np.nan
    return {'kind':'plot','plot_type':'density','title':'|u|/U' if kind=='Velocity' else 'C_p (reference at pinned far-field node)','axes':['x/c','y/c'],'x':x.tolist(),'y':y.tolist(),'z':[[float(v) if np.isfinite(v) else None for v in row] for row in z],'options':options}
