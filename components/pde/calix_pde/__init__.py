"""Optional symbolic PDE, finite-element and steady-flow component."""
from dataclasses import dataclass, field
import math
import numpy as np
import sympy as s
from backend.syntax import InputError


@dataclass
class Solution:
    family: str
    data: dict = field(repr=False)
    metrics: dict = field(default_factory=dict)

    def summary(self):
        return f'{self.family} solution', r'\operatorname{' + self.family.replace(' ', r'\ ') + r'}'


NAMES = {'PDEInfo', 'PDEPlot', 'PDEValue', 'FEMBridgeSolve', 'WingFlowSolve', 'NDEigensystem'}


def finite(value, lower, upper, name):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise InputError(f'{name} must be numeric') from None
    if not math.isfinite(value) or not lower <= value <= upper:
        raise InputError(f'{name} must lie in [{lower}, {upper}]')
    return value


def count(value, lower, upper):
    number = finite(value, lower, upper, 'Mesh resolution')
    if not number.is_integer():
        raise InputError('Mesh resolution must be an integer')
    return int(number)


def analytic(equations, fn, variables):
    """Reduce inactive coordinates, or separate homogeneous heat/wave modes."""
    equations = equations if isinstance(equations, list) else [equations]
    if not isinstance(fn, s.Function) or len(fn.args) != 2 or len(variables) != 2:
        raise InputError('Symbolic PDE solving expects u[x,y] and {x,y}')
    differential = [eq for eq in equations if isinstance(eq, s.Equality) and eq.has(s.Derivative)]
    boundary = [eq for eq in equations if isinstance(eq, s.Equality) and not eq.has(s.Derivative)]
    if len(differential) != 1 or len(differential) + len(boundary) != len(equations):
        raise InputError('Symbolic PDE solving currently supports one scalar equation and value boundary conditions')
    eq = differential[0]
    active = {v for d in eq.atoms(s.Derivative) for v in d.variables if d.expr == fn}
    if len(active) == 1:
        var = next(iter(active))
        g = s.Function('CIXPDE')(var)
        ode = eq.xreplace({fn: g}).doit()
        solution = s.dsolve(ode, g).rhs
        constants = sorted(solution.free_symbols - eq.free_symbols, key=str)
        bcs = []
        for bc in boundary:
            if bc.lhs.func != fn.func or len(bc.lhs.args) != 2:
                raise InputError('Boundary conditions must use the dependent function on the left')
            substitutions = dict(zip(fn.args, bc.lhs.args))
            bcs.append(solution.subs(substitutions, simultaneous=True) - bc.rhs)
        if bcs:
            rules = s.solve(bcs, constants, dict=True)
            if len(rules) != 1:
                raise InputError('Boundary conditions do not determine a unique supported solution')
            solution = s.simplify(solution.subs(rules[0]))
        else:
            inactive = [v for v in variables if v != var]
            solution = solution.xreplace({c: s.Function(str(c))(*inactive) for c in constants})
        return s.Eq(fn, solution)
    if boundary:
        x, t = variables
        residual = s.expand(eq.lhs - eq.rhs)
        order = 1 if residual.has(s.diff(fn, t)) else 2
        time = s.diff(fn, t, order)
        second = s.diff(fn, x, 2)
        a = s.simplify(-residual.coeff(second) / residual.coeff(time))
        if s.simplify(residual - residual.coeff(time) * (time-a*second)) != 0 or a.has(x, t) or a == 0:
            raise InputError('Separation currently supports constant-coefficient homogeneous heat and wave equations')
        ends = [bc for bc in boundary if bc.lhs.func == fn.func and bc.lhs.args[1] == t and bc.rhs == 0]
        initial = [bc for bc in boundary if bc.lhs == fn.subs(t, 0)]
        if len(ends) != 2 or len(initial) != 1 or len(boundary) != 3:
            raise InputError('Provide u[0,t]==0, u[L,t]==0, u[x,0]==f[x]; wave separation assumes zero initial velocity')
        low, high = sorted([bc.lhs.args[0] for bc in ends], key=lambda v: float(v) if v.is_number else (0 if v == 0 else 1))
        if low != 0 or high.has(x, t):
            raise InputError('Separation expects an interval from 0 to L')
        terms, reconstruction = [], 0
        for n in range(1, 13):
            basis = s.sin(n*s.pi*x/high)
            coefficient = s.simplify(2/high*s.integrate(initial[0].rhs*basis, (x, 0, high)))
            reconstruction += coefficient*basis
            factor = s.exp(-a*(n*s.pi/high)**2*t) if order == 1 else s.cos(s.sqrt(a)*n*s.pi*t/high)
            if coefficient != 0:
                terms.append(coefficient*basis*factor)
        if s.trigsimp(s.expand_trig(reconstruction-initial[0].rhs)) != 0:
            n = s.Symbol('n', integer=True, positive=True)
            basis = s.sin(n*s.pi*x/high)
            coefficient = s.integrate(2/high*initial[0].rhs*basis, (x, 0, high))
            factor = s.exp(-a*(n*s.pi/high)**2*t) if order == 1 else s.cos(s.sqrt(a)*n*s.pi*t/high)
            return s.Eq(fn, s.Sum(coefficient*basis*factor, (n, 1, s.oo)))
        return s.Eq(fn, s.Add(*terms))
    try:
        return s.pdsolve(eq, fn)
    except NotImplementedError as exc:
        raise InputError('No analytical solution is available for this PDE in the current component') from exc


def numerical(equations, fn, ranges, resolution=41):
    from .scalar import solve
    return solve(equations, fn, ranges, resolution)


def dispatch(name, args):
    if name == 'FEMBridgeSolve':
        from .bridge import solve
        if len(args) != 3 or not isinstance(args[0], list) or len(args[0]) != 3:
            raise InputError('Use FEMBridgeSolve[{length,width,towerHeight},pressure,resolution] in SI units')
        return solve(*args)
    if name == 'WingFlowSolve':
        from .wing import solve
        if len(args) != 2 or not isinstance(args[0], list) or len(args[0]) != 2:
            raise InputError('Use WingFlowSolve[{ReynoldsNumber,angleInDegrees},resolution]')
        return solve(*args)
    if name == 'NDEigensystem':
        from .scalar import eigen
        return eigen(*args)
    if len(args) < 1 or not isinstance(args[0], Solution):
        raise InputError(f'{name} requires a PDE module solution')
    model = args[0]
    if name == 'PDEInfo' and len(args) == 1:
        return {'kind': 'group', 'items': [{'kind': 'labeled', 'label': key, 'value': s.Float(value) if isinstance(value, (float, np.floating)) else s.sympify(value)} for key, value in model.metrics.items()]}
    if name == 'PDEValue' and len(args) == 2:
        from .scalar import value
        return s.Float(value(model, args[1]))
    if name == 'PDEPlot' and len(args) == 2 and isinstance(args[1], str):
        if model.family == 'Bridge FEM':
            from .bridge import plot
        elif model.family == 'Wing RANS':
            from .wing import plot
        else:
            from .scalar import plot
        return plot(model, args[1])
    raise InputError(f'Invalid arguments for {name}')
