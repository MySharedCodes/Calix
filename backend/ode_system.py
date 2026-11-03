"""Reduce explicit first- and second-order initial value equations for the native solver."""
import sympy as s
from .syntax import InputError
from .native import kernel
from .interpolation import SampledFunction


def solve(equations, functions, interval):
    if not isinstance(interval, list) or len(interval) != 3:
        raise InputError('Use NDSolveValue[equations,functions,{t,lower,upper}]')
    time, low, high = interval
    if not isinstance(time, s.Symbol) or not float(low) < float(high):
        raise InputError('ODE interval must have an independent variable and increasing finite bounds')
    scalar = not isinstance(functions, list)
    functions = [functions] if scalar else functions
    if not 1 <= len(functions) <= 16 or len(set(functions)) != len(functions):
        raise InputError('Provide one to 16 distinct dependent functions')
    if any(not isinstance(fn, s.Function) or fn.args != (time,) for fn in functions):
        raise InputError('List dependent functions as {x1[t],y1[t],x2[t],y2[t]}')
    if not isinstance(equations, list) or any(not isinstance(eq, s.Equality) for eq in equations):
        raise InputError('Provide a list of differential equations and initial conditions')
    differential, initial = [], {}
    for eq in equations:
        if isinstance(eq.lhs, s.Subs):
            if len(eq.lhs.variables) != 1:
                raise InputError('Initial conditions need a single independent variable')
            derivative = eq.lhs.expr.xreplace({eq.lhs.variables[0]: time})
            key = s.Subs(derivative, time, eq.lhs.point[0])
            initial[key] = eq.rhs
        elif eq.has(s.Derivative):
            differential.append(eq)
        else:
            initial[eq.lhs] = eq.rhs
    orders = []
    for fn in functions:
        derivatives = [derivative for eq in differential for derivative in eq.atoms(s.Derivative) if derivative.expr == fn]
        if not derivatives or any(set(derivative.variables) != {time} for derivative in derivatives):
            raise InputError('Each function needs an ODE in the specified independent variable')
        order = max(len(derivative.variables) for derivative in derivatives)
        if order > 2:
            raise InputError('NDSolveValue supports first- and second-order ODE systems')
        orders.append(order)
    highest = [s.diff(fn, time, order) for fn, order in zip(functions, orders)]
    if len(differential) != len(functions):
        raise InputError('Provide exactly one differential equation per dependent function')
    # Keep explicitly isolated forces factored; a general solve can expand coupled radicals dramatically.
    explicit = {eq.lhs: eq.rhs for eq in differential if eq.lhs in highest and not eq.rhs.has(*highest)}
    solved = [explicit] if len(explicit) == len(highest) else s.solve(differential, highest, dict=True, simplify=False)
    if len(solved) != 1 or any(derivative not in solved[0] for derivative in highest):
        raise InputError('Could not isolate the highest derivatives')
    terms = [s.diff(fn, time, order) for fn, maximum in zip(functions, orders) for order in range(maximum)]
    states = [s.Dummy(f'state{i}') for i in range(len(terms))]
    mapping = dict(zip(terms, states))
    values, rhs = [], []
    for term in terms:
        key = term.subs(time, low) if not isinstance(term, s.Derivative) else s.Subs(term, time, low)
        if key not in initial:
            raise InputError('Provide every initial position and required velocity at the interval lower bound')
        value = initial[key]
        if not value.is_number or value.is_real is not True or value.is_finite is not True:
            raise InputError('ODE initial values must be finite real numbers')
        values.append(float(value))
        derivative = s.diff(term, time)
        rhs.append(solved[0].get(derivative, derivative).xreplace(mapping))
    if any(expr.has(s.Derivative) or expr.free_symbols - {time, *states} for expr in rhs):
        raise InputError('Assign all ODE parameters and include all coupled dependent functions')
    times, columns = kernel.ode_system(rhs, [time, *states], float(low), float(high), values)
    times = s.Tuple(*times)
    dimension = len(terms)
    result = []
    index = 0
    for order in orders:
        result.append(SampledFunction(time, times, s.Tuple(*columns[index]), s.Tuple(*columns[index+2*dimension]),
                                      s.Tuple(*columns[index+dimension]), s.Tuple(*columns[index])))
        index += order
    return result[0] if scalar else result
