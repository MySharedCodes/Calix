"""Exact normal modes for constant-coefficient second-order initial value systems."""
import sympy as s
from sympy.solvers.solveset import NonlinearError


def normal_modes(equations, functions, time, initial):
    if not isinstance(functions, list) or not 1 <= len(functions) <= 8:
        return None
    if any(not isinstance(fn, s.Function) or fn.args != (time,) for fn in functions):
        return None
    n = len(functions)
    if len(equations) != n:
        return None
    derivatives = [s.diff(fn, time, 2) for fn in functions] + [s.diff(fn, time) for fn in functions] + functions
    try:
        coefficients, forcing = s.linear_eq_to_matrix([eq.lhs - eq.rhs for eq in equations], derivatives)
    except (NonlinearError, ValueError):
        return None
    if coefficients.has(time) or forcing.has(time) or coefficients[:, n:2*n] != s.zeros(n):
        return None
    times = {key.args[0] for key in initial if isinstance(key, s.Function) and key.func in {fn.func for fn in functions}}
    if len(times) != 1:
        return None
    start = times.pop()
    position_keys = [fn.subs(time, start) for fn in functions]
    velocity_keys = [s.Subs(s.diff(fn, time), time, start) for fn in functions]
    if any(key not in initial for key in position_keys + velocity_keys):
        return None
    try:
        mass = coefficients[:, :n]
        stiffness = mass.inv() * coefficients[:, 2*n:]
        acceleration = mass.inv() * forcing
        eigenvectors = stiffness.eigenvects()
        if sum(len(vectors) for _, _, vectors in eigenvectors) != n:
            return None
        if any(value.is_nonnegative is not True for value, _, _ in eigenvectors):
            return None
        vectors = s.Matrix.hstack(*(vector for _, _, basis in eigenvectors for vector in basis))
        inverse = vectors.inv()
        positions = (inverse * s.Matrix([initial[key] for key in position_keys])).applyfunc(s.simplify)
        velocities = (inverse * s.Matrix([initial[key] for key in velocity_keys])).applyfunc(s.simplify)
        force = (inverse * acceleration).applyfunc(s.simplify)
    except (ValueError, NotImplementedError, ZeroDivisionError, s.matrices.exceptions.NonInvertibleMatrixError):
        return None
    elapsed = time - start
    modes = []
    for index, value in enumerate(value for value, _, basis in eigenvectors for _ in basis):
        if value == 0:
            modes.append(positions[index] + velocities[index]*elapsed + force[index]*elapsed**2/2)
        else:
            omega = s.sqrt(value)
            modes.append(positions[index]*s.cos(omega*elapsed) + velocities[index]*s.sin(omega*elapsed)/omega
                         + force[index]*(1-s.cos(omega*elapsed))/value)
    result = vectors * s.Matrix(modes)
    def compact(expr):
        expanded = s.expand(expr)
        return s.collect(expanded, sorted(expanded.atoms(s.sin, s.cos), key=str), func=s.simplify)
    return [s.Eq(fn, compact(expr)) for fn, expr in zip(functions, result)]
