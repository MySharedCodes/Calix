import ctypes as ct
import numpy as np
import pytest
from backend.engine import Engine
from backend.native import kernel
from backend.lattice import simulate
from backend.syntax import InputError


def run(beta=5.7,seed=7,**options):
    return simulate([[3]*4,{'Beta':beta,'ThermalizationSweeps':80,'Measurements':120,
        'SweepsBetweenMeasurements':3,'ProposalSize':.7,'RandomSeed':seed,**options}])


def test_su3_reproducibility_gauge_invariance_and_temperature():
    a=run();b=run()
    assert a==b
    assert max(a.diagnostics)<1e-11
    assert all(0<=row[2]<=1 for row in a.history)
    cold=run(beta=20);hot=run(beta=0,ProposalSize=2.5)
    assert np.mean(cold.measurements,axis=0)[0]>.85
    assert abs(np.mean(hot.measurements,axis=0)[0])<.025
    assert np.mean(a.measurements,axis=0)[0]>.4


def test_staple_action_matches_independent_full_plaquette_change():
    from scipy.linalg import expm
    l=3;rng=np.random.default_rng(31)
    raw=rng.normal(size=(l,l,l,l,4,3,3))+1j*rng.normal(size=(l,l,l,l,4,3,3))
    h=(raw+raw.swapaxes(-1,-2).conj())/2
    h-=np.trace(h,axis1=-2,axis2=-1)[...,None,None]*np.eye(3)/3
    links=np.array([expm(1j*a) for a in h.reshape(-1,3,3)]).reshape(h.shape)
    def independent(u):
        total=0
        for x in np.ndindex((l,)*4):
            for mu in range(4):
                for nu in range(mu+1,4):
                    a=list(x);b=list(x);a[mu]=(a[mu]+1)%l;b[nu]=(b[nu]+1)%l
                    total+=np.trace(u[x+(mu,)]@u[tuple(a)+(nu,)]@u[tuple(b)+(mu,)].conj().T@u[x+(nu,)].conj().T).real/3
        return total/(6*l**4)
    function=kernel.lib.calix_lattice_observe;dp=ct.POINTER(ct.c_double)
    function.argtypes=[ct.c_int,dp,ct.c_int,ct.c_int,dp,dp];function.restype=ct.c_int
    def native(u):
        # C++ site indexing has coordinate zero varying fastest.
        values=np.ascontiguousarray(u.transpose(3,2,1,0,4,5,6),dtype=np.complex128)
        p=ct.c_double();staple=np.empty((3,3),complex)
        assert function(l,values.ctypes.data_as(dp),0,1,ct.byref(p),staple.ctypes.data_as(dp))==0
        return p.value,staple
    before=independent(links);p,staple=native(links)
    assert p==pytest.approx(before,abs=1e-14)
    old=links[0,0,0,0,1].copy();new=expm(.2j*h[0,0,0,0,0])@old
    links[0,0,0,0,1]=new;after=independent(links)
    assert (after-before)*6*l**4==pytest.approx(np.trace((new-old)@staple).real/3,abs=1e-13)


def test_simulation_runs_without_pde_component(monkeypatch,tmp_path):
    from backend import components
    monkeypatch.setattr(components,'ROOT',tmp_path)
    out=Engine().execute('u=LatticeGaugeSimulation[{2,2,2,2},Association["ThermalizationSweeps"->0,"Measurements"->2,"SweepsBetweenMeasurements"->1]];u["Diagnostics"]')
    assert '10^' in out['latex'] or 'e-' in out['text']
    with pytest.raises(InputError):simulate([[2]*4,{'Measurements':2.5}])


def test_multiseries_listlineplot_and_formula_lists():
    e=Engine()
    out=e.execute('ListLinePlot[{{{1,2},{2,3}},{{1,4},{2,5}}},PlotLegends->{"a","b"}]')
    assert [t['name'] for t in out['traces']]==['a','b']
    assert out['traces'][1]['y']==[4,5]
    assert e.execute('Table[Plot[i*x,{x,0,1}],{i,1,2}]')['kind']=='group'
