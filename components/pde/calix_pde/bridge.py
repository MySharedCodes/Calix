"""3D tower solids + 2D plate/membrane deck + prestressed 1D trusses."""
import numpy as np
from scipy.sparse import block_diag, coo_matrix
from .linalg import solve as spsolve
from skfem import MeshTet, MeshTri, Basis, ElementTetP1, ElementTriP1, ElementTriMorley, ElementVector, BilinearForm, LinearForm, asm
from skfem.helpers import dd, ddot, trace, sym_grad, div
from skfem.models.elasticity import linear_elasticity, lame_parameters
from backend.syntax import InputError
from . import Solution, finite, count


def solve(dimensions, pressure, resolution):
    length=finite(dimensions[0],20,300,'Length [m]')
    width=finite(dimensions[1],3,30,'Width [m]')
    height=finite(dimensions[2],10,80,'Tower height [m]')
    q=finite(pressure,1,10000,'Incremental deck pressure [Pa]')
    n=count(resolution,2,6)
    e,nu,t=2.0e11,.3,.18
    et,nt=3.0e10,.2
    zdeck=height/2
    mesh=MeshTri.init_tensor(np.linspace(-length/2,length/2,8*n+1),np.linspace(-width/2,width/2,2*n+1))
    membrane=Basis(mesh,ElementVector(ElementTriP1()))
    plate=Basis(mesh,ElementTriMorley())
    lam=e*nu/(1-nu**2);mu=e/(2*(1+nu));d=e*t**3/(12*(1-nu**2))
    @BilinearForm
    def deck_membrane(u,v,w): return t*(2*mu*ddot(sym_grad(u),sym_grad(v))+lam*div(u)*div(v))
    @BilinearForm
    def deck_bending(u,v,w): return d*((1-nu)*ddot(dd(u),dd(v))+nu*trace(dd(u))*trace(dd(v)))
    @LinearForm
    def vertical_load(v,w): return -q*v
    blocks=[asm(deck_membrane,membrane),asm(deck_bending,plate)]
    forces=[np.zeros(membrane.N),asm(vertical_load,plate)]
    fixed=list(membrane.get_dofs(lambda x:np.isclose(np.abs(x[0]),length/2)).all())
    fixed.extend((membrane.N+plate.get_dofs(lambda x:np.isclose(np.abs(x[0]),length/2)).all()).tolist())
    # Morley vertex values provide exact transverse compatibility at cable nodes.
    deck_dofs=np.vstack([membrane.nodal_dofs,membrane.N+plate.nodal_dofs])
    towers=[];offset=membrane.N+plate.N
    top={}
    a=max(.8,height*.045)
    for xc in (-length/4,length/4):
        for yc in (-width/2,width/2):
            m=MeshTet.init_tensor(np.linspace(xc-a/2,xc+a/2,2*n+1),np.linspace(yc-a/2,yc+a/2,2*n+1),np.linspace(0,height,4*n+1))
            b=Basis(m,ElementVector(ElementTetP1()))
            blocks.append(asm(linear_elasticity(*lame_parameters(et,nt)),b));forces.append(np.zeros(b.N))
            fixed.extend((offset+b.get_dofs(lambda x:np.isclose(x[2],0)).all()).tolist())
            j=np.argmin(np.linalg.norm(m.p-np.array([xc,yc,height])[:,None],axis=0))
            top[(xc,yc)]=(offset+b.nodal_dofs[:,j]).tolist()
            towers.append((m,b,offset))
            offset+=b.N
    coordinates=[];mapping=[];segments=[];types=[];tensions=[]
    # The initial geometry and prestress define the reference equilibrium;
    # the solved load is an additional service load, not the dead-load form finding.
    sag=height*.25
    t0=2000*width*length**2/(32*sag)
    for side in (-1,1):
        row=[]
        for j,x in enumerate(np.linspace(-length/2,length/2,8*n+1)):
            y=side*width/2
            z=height-sag*(1-(x/(length/4))**2) if abs(x)<=length/4 else height-(height-zdeck)*(abs(x)-length/4)/(length/4)
            p=[float(x),float(y),float(z)]
            if j in (0,8*n): dofs=[-1,-1,-1]
            elif j in (2*n,6*n): dofs=top[(-length/4 if j==2*n else length/4,y)]
            else: dofs=list(range(offset,offset+3));offset+=3
            row.append(len(coordinates));coordinates.append(p);mapping.append(dofs)
            if j>0:
                segments.append([row[-2],row[-1]]);types.append('main');tensions.append(t0)
            if 0<j<8*n and j % n == 0:
                k=np.argmin(np.linalg.norm(mesh.p-np.array([x,y])[:,None],axis=0))
                pdeck=[float(x),float(y),zdeck]
                k2=len(coordinates);coordinates.append(pdeck);mapping.append(deck_dofs[:,k].tolist())
                segments.append([row[-1],k2]);types.append('hanger');tensions.append(2000*width*length/16)
    if offset>sum(b.shape[0] for b in blocks):
        blocks.append(coo_matrix((offset-sum(b.shape[0] for b in blocks),)*2));forces.append(np.zeros(blocks[-1].shape[0]))
    base=block_diag(blocks,format='csr');force=np.concatenate(forces)
    rr=[];cc=[];vv=[];lengths=[];directions=[]
    coordinates=np.array(coordinates);mapping=np.array(mapping)
    for (i,j),kind,tension in zip(segments,types,tensions):
        delta=coordinates[j]-coordinates[i];ell=np.linalg.norm(delta);axis=delta/ell
        area=.025 if kind=='main' else .003
        k=e*area/ell*np.outer(axis,axis)+tension/ell*(np.eye(3)-np.outer(axis,axis))
        local=np.block([[k,-k],[-k,k]])
        dofs=np.r_[mapping[i],mapping[j]]
        for a0 in range(6):
            for b0 in range(6):
                if dofs[a0]>=0 and dofs[b0]>=0: rr.append(dofs[a0]);cc.append(dofs[b0]);vv.append(local[a0,b0])
        lengths.append(ell);directions.append(axis)
    stiffness=base+coo_matrix((vv,(rr,cc)),shape=base.shape).tocsr()
    fixed=np.unique(fixed);free=np.setdiff1d(np.arange(offset),fixed)
    u=np.zeros(offset);u[free]=spsolve(stiffness[free][:,free],force[free])
    if not np.all(np.isfinite(u)): raise InputError('Bridge stiffness is singular')
    reaction=stiffness@u-force
    displacements=u[deck_dofs].T
    cu=np.zeros_like(coordinates)
    valid=mapping>=0;cu[valid]=u[mapping[valid]]
    tension_changes=[]
    for (i,j),kind,ell,axis in zip(segments,types,lengths,directions):
        tension_changes.append(e*(.025 if kind=='main' else .003)/ell*np.dot(cu[j]-cu[i],axis))
    total_tension=np.array(tensions)+tension_changes
    if np.min(total_tension)<=0: raise InputError('A cable loses tension; this linearized model is invalid for the requested load')
    # Independent force equilibrium includes tower base and cable anchor reactions.
    force_sum=np.zeros(3);reaction_sum=np.zeros(3)
    force_sum[:2]=np.sum(force[membrane.nodal_dofs],axis=1)
    force_sum[2]=np.sum(force[membrane.N+plate.nodal_dofs])
    reaction_sum[:2]=np.sum(reaction[membrane.nodal_dofs],axis=1)
    reaction_sum[2]=np.sum(reaction[membrane.N+plate.nodal_dofs])
    for m,b,o in towers: reaction_sum+=np.sum(reaction[o+b.nodal_dofs],axis=1)
    anchor_reaction=np.zeros(3)
    for (i,j),ell,axis,kind,tension in zip(segments,lengths,directions,types,tensions):
        area=.025 if kind=='main' else .003
        k=e*area/ell*np.outer(axis,axis)+tension/ell*(np.eye(3)-np.outer(axis,axis))
        f=k@(cu[i]-cu[j])
        if np.all(mapping[i]<0): anchor_reaction+=f
        if np.all(mapping[j]<0): anchor_reaction-=f
    balance=float(np.linalg.norm(reaction_sum+anchor_reaction+force_sum)/max(np.linalg.norm(force_sum),1))
    residual=float(np.linalg.norm(reaction[free])/np.linalg.norm(force[free]))
    stress=[]
    lt,mt=lame_parameters(et,nt)
    for m,b,o in towers:
        strain=sym_grad(b.interpolate(u[o:o+b.N])).mean(axis=-1)
        sigma=2*mt*strain+lt*np.einsum('iik->k',strain)[None,None,:]*np.eye(3)[:,:,None]
        dev=sigma-np.einsum('iik->k',sigma)[None,None,:]*np.eye(3)[:,:,None]/3
        stress.extend(np.sqrt(1.5*np.einsum('ijk,ijk->k',dev,dev)).tolist())
    data={'mesh':mesh,'deck':displacements,'towers':[(m,b.nodal_dofs,b.N,o) for m,b,o in towers],'u':u,'cables':coordinates,'cable_u':cu,'segments':segments,'types':types,'zdeck':zdeck,'q':q,'stresses':np.array(stress)}
    metrics={'3D tetrahedra':sum(m.nelements for m,_,_ in towers),'2D triangles':mesh.nelements,'1D trusses':len(segments),'DOF':offset,
             'deck min w [m]':float(displacements[:,2].min()),'tower max von Mises [Pa]':float(max(stress)),
             'max cable tension [N]':float(max(total_tension)),'min cable tension [N]':float(min(total_tension)),
             'relative residual':residual,'force balance relative error':balance,'strain energy [J]':float(.5*u@force)}
    return Solution('Bridge FEM',data,metrics)


def plot(model,kind):
    if kind not in ('Mesh','Displacement','Stress'): raise InputError('Bridge PDEPlot supports "Mesh", "Displacement", "Stress"')
    a=model.data;mesh=a['mesh'];u=a['u'];primitives=[]
    scale=0 if kind=='Mesh' else min(100,2/max(np.max(np.abs(a['deck'])),1e-10))
    def line(points,color,label=''): primitives.append({'type':'line','points':np.asarray(points).tolist(),'color':color,'label':label})
    deck=np.c_[mesh.p.T,np.full(mesh.nvertices,a['zdeck'])]+scale*a['deck']
    values=np.abs(a['deck'][:,2]);maximum=max(values.max(),1e-12)
    color=lambda v:'#%02x%02x%02x'%(int(35+210*v),int(165-90*v),int(190-130*v))
    # Every edge belongs to the actual mixed-dimensional FE mesh.
    for i,j in mesh.facets.T: line(deck[[i,j]],color(float(max(values[i],values[j])/maximum)), '2D deck' if len(primitives)==0 else '')
    if kind!='Mesh':
        for tri in mesh.t.T:
            primitives.append({'type':'triangle','points':deck[tri].tolist(),'color':color(float(np.mean(values[tri])/maximum)),'label':''})
    stress_offset=0
    for m,nodal_dofs,size,o in a['towers']:
        p=m.p.T+scale*u[o+nodal_dofs].T
        boundary=m.facets[:,m.boundary_facets()]
        edges=np.unique(np.sort(np.hstack([boundary[[0,1]],boundary[[1,2]],boundary[[2,0]]]),axis=0),axis=1)
        for j,edge in enumerate(edges.T):
            line(p[edge], '#526b8d','3D towers' if j==0 else '')
        if kind!='Mesh':
            st=a['stresses'][stress_offset:stress_offset+m.nelements]
            for j,tri in enumerate(boundary.T):
                adjacent=m.f2t[0,m.boundary_facets()[j]]
                primitives.append({'type':'triangle','points':p[tri].tolist(),'color':color(float(st[adjacent]/max(a['stresses'].max(),1e-12))) if kind=='Stress' else '#7393ad','label':''})
        stress_offset+=m.nelements
    cp=a['cables']+scale*a['cable_u']
    for j,(i,k) in enumerate(a['segments']): line(cp[[i,k]],'#b46042' if a['types'][j]=='main' else '#5c8c65','1D cables' if j==0 else '')
    return {'kind':'plot','plot_type':'geometry3d','title':f'Bridge {kind}; deformation scale = {scale:.3g}', 'axes':['x [m]','y [m]','z [m]'],'primitives':primitives}
