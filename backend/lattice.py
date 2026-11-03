"""Small periodic SU(3) pure-gauge ensembles evaluated by the C++ kernel."""
import ctypes as ct
from dataclasses import dataclass
import math
import sympy as s
from .native import kernel
from .syntax import InputError


@dataclass
class GaugeData:
    history:list
    measurements:list
    diagnostics:list

    def __call__(self,key):
        values={'History':self.history,'Measurements':self.measurements,'Diagnostics':self.diagnostics}
        if key not in values:raise InputError('Use History, Measurements or Diagnostics')
        return values[key]

    def summary(self):
        return f'LatticeGaugeData[{len(self.measurements)} measurements]',r'\operatorname{LatticeGaugeData}'


def simulate(args):
    if len(args)!=2 or not isinstance(args[0],list) or len(args[0])!=4:
        raise InputError('Use LatticeGaugeSimulation[{L,L,L,L}, Association[options]]')
    dimensions=args[0]
    if any(not isinstance(v,(int,s.Integer)) for v in dimensions) or len(set(dimensions))!=1:
        raise InputError('This simulation requires four equal integer lattice lengths')
    options=args[1]
    if not isinstance(options,dict):raise InputError('Simulation options require an Association')
    allowed={'Beta','ThermalizationSweeps','Measurements','SweepsBetweenMeasurements','ProposalSize','RandomSeed'}
    if options.keys()-allowed:raise InputError('Unknown lattice gauge simulation option')
    def integer(name,default):
        value=options.get(name,default)
        if not isinstance(value,(int,s.Integer)):raise InputError(f'{name} must be an integer')
        return int(value)
    length=int(dimensions[0]);beta=float(options.get('Beta',5.7))
    warm=integer('ThermalizationSweeps',200);samples=integer('Measurements',120)
    interval=integer('SweepsBetweenMeasurements',5);seed=integer('RandomSeed',20261030)
    step=float(options.get('ProposalSize',.3))
    total=warm+samples*interval
    if not 2<=length<=6 or not 0<=beta<=100 or not math.isfinite(beta) or warm<0 or samples<2 or interval<1 or total>10000 or not 0<step<=math.pi or not 0<=seed<2**64:
        raise InputError('Require 2<=L<=6, 0<=Beta<=100, nonnegative warmup, at least 2 measurements, positive interval, at most 10000 sweeps, and 0<ProposalSize<=Pi')
    if not kernel.available:raise InputError('LatticeGaugeSimulation requires the Calix C++ kernel')
    dp=ct.POINTER(ct.c_double)
    function=kernel.lib.calix_lattice_su3
    function.argtypes=[ct.c_int,ct.c_double,ct.c_int,ct.c_int,ct.c_int,ct.c_double,ct.c_uint64,dp,dp,dp]
    function.restype=ct.c_int
    history=(ct.c_double*(total*3))();measured=(ct.c_double*(samples*4))();diagnostics=(ct.c_double*3)()
    status=function(length,beta,warm,samples,interval,step,seed,history,measured,diagnostics)
    if status:raise InputError(f'C++ SU(3) simulation failed ({status})')
    return GaugeData([list(history[i:i+3]) for i in range(0,len(history),3)],
                     [list(measured[i:i+4]) for i in range(0,len(measured),4)],list(diagnostics))
