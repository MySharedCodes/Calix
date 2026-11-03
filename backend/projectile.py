"""Unit-aware projectile ranges, angular envelopes and native event integration."""
import math
import pint
import sympy as s
from .syntax import InputError
from .units import quantity, dimensionless
from .native import kernel


class DragRange(s.Function):
    nargs=7

    @classmethod
    def eval(cls, coefficient, mass, speed, gravity, model, angle, maximum):
        args=(coefficient,mass,speed,gravity,model,angle,maximum)
        if all(a.is_number for a in args):
            return s.Float(kernel.projectile(*[float(a) for a in args[:4]],int(model),float(angle),bool(maximum))[0])

    @staticmethod
    def _imp_(*args):
        return kernel.projectile(*[float(a) for a in args[:4]],int(args[4]),float(args[5]),bool(args[6]))[0]

    def _latex(self, printer):
        return (r'R_{\max}' if self.args[-1] else 'R')+'('+printer.doprint(self.args[0])+')'


def si(value,unit):
    if not isinstance(value,pint.Quantity): raise InputError(f'Projectile inputs must carry units compatible with {unit}')
    return s.sympify(value.to(unit).magnitude)


def parameters(args):
    if len(args)<5 or args[-1] not in ('Linear','Quadratic'):
        raise InputError('Use ProjectileMaxRange[coefficient,mass,speed,gravity,"Linear"|"Quadratic"]')
    model=1 if args[-1]=='Linear' else 2
    c=si(args[0],'kg/s' if model==1 else 'kg/m')
    m,v,g=[si(value,unit) for value,unit in zip(args[1:4],('kg','m/s','m/s^2'))]
    for value in (m,v,g):
        if not value.is_number or not math.isfinite(float(value)) or float(value)<=0:
            raise InputError('Mass, initial speed and gravity must be finite positive quantities')
    if c.is_number and (not math.isfinite(float(c)) or float(c)<0): raise InputError('Drag coefficient must be finite and nonnegative')
    return c,m,v,g,model


def dispatch(name,args):
    if name=='ProjectileVelocity':
        if len(args)!=7 or not isinstance(args[5],list) or len(args[5])!=3:
            raise InputError('Use ProjectileVelocity[c,m,v,g,angle,{t,0[s],T},"Linear"|"Quadratic"]')
        c,m,v,g,model=parameters(args)
        t,lower,upper=args[5]
        if not isinstance(t,s.Symbol) or si(lower,'s')!=0 or not c.is_number:
            raise InputError('ProjectileVelocity requires a numerical coefficient and a time interval starting at 0[s]')
        end=si(upper,'s')
        if not end.is_number or not 0<float(end)<=10000: raise InputError('Flight duration must be positive and at most 10000[s]')
        angle=dimensionless(args[4],angle=True)
        if not angle.is_number or not 0<float(angle)<math.pi/2: raise InputError('Launch angle must be between 0 and 90 degrees')
        if model==1:
            z=c/m
            if z==0: values=[v*s.cos(angle),v*s.sin(angle)-g*t]
            else: values=[v*s.cos(angle)*s.exp(-z*t),(v*s.sin(angle)+g/z)*s.exp(-z*t)-g/z]
        else:
            from .ode_system import solve
            vx,vy=s.Function('V1')(t),s.Function('V2')(t)
            drag=c/m*s.sqrt(vx**2+vy**2)
            values=solve([s.Eq(s.diff(vx,t),-drag*vx),s.Eq(s.diff(vy,t),-g-drag*vy),
                          s.Eq(vx.subs(t,0),v*s.cos(angle)),s.Eq(vy.subs(t,0),v*s.sin(angle))], [vx,vy], [t,s.Integer(0),end])
        return [quantity(value,'m/s') for value in values]
    expected=6 if name=='ProjectileRange' else 5
    if len(args)!=expected: raise InputError(f'{name} expects {expected} arguments')
    c,m,v,g,model=parameters(args)
    angle=dimensionless(args[4],angle=True) if name=='ProjectileRange' else s.Integer(0)
    if name=='ProjectileOptimum':
        if not c.is_number: raise InputError('ProjectileOptimum requires a numerical drag coefficient')
        distance,angle,duration=kernel.projectile(float(c),float(m),float(v),float(g),model,optimize=True)
        return [quantity(s.Float(distance),'m'),quantity(s.Float(angle*180/math.pi),'degree'),quantity(s.Float(duration),'s')]
    return quantity(DragRange(c,m,v,g,s.Integer(model),angle,s.Integer(name=='ProjectileMaxRange')),'m')
