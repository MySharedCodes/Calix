"""Bounded list iteration for parameter sweeps and finite searches."""
from itertools import accumulate, permutations
import math
import sympy as s
from .syntax import InputError

NOTHING = s.Symbol('Nothing')


def finite_aggregate(engine, name, nodes):
    """Evaluate bounded indexed expressions before combining scalar terms."""
    values = table(engine, nodes)
    def terms(value, depth):
        if depth:
            return [term for item in value for term in terms(item, depth - 1)]
        if isinstance(value, (list, dict)):
            raise InputError(f'{name} with indexed data currently requires scalar terms')
        return [value]
    values = terms(values, len(nodes) - 1)
    return (s.Add if name == 'Sum' else s.Mul)(*values)


def table(engine, nodes):
    if len(nodes) < 2:
        raise InputError('Table expects an expression and one or more iterators')
    previous = engine.environment.copy()
    count = 0

    def iterate(depth):
        nonlocal count
        if depth == len(nodes):
            count += 1
            if count > 100000:
                raise InputError('Table is limited to 100,000 evaluations')
            return engine.evaluate(nodes[0])
        spec = nodes[depth]
        if spec.kind != 'list' or len(spec.args) not in (2, 3, 4) or spec.args[0].kind != 'symbol':
            raise InputError('Use Table[expression,{i,upper}], {i,lower,upper,step} or {i,{values}}')
        name = spec.args[0].value
        bounds = [engine.evaluate(node) for node in spec.args[1:]]
        bounds = [s.sympify(value) if not isinstance(value,list) else value for value in bounds]
        if len(bounds) == 1 and isinstance(bounds[0], list):
            values = bounds[0]
        else:
            low, high, step = (s.Integer(1), bounds[0], s.Integer(1)) if len(bounds) == 1 else (*bounds, s.Integer(1)) if len(bounds) == 2 else bounds
            if any(not isinstance(value, s.Expr) or not value.is_number or value.is_real is not True or not value.is_finite for value in (low, high, step)) or step == 0:
                unresolved=set().union(*(value.free_symbols for value in (low,high,step) if isinstance(value,s.Basic)))
                if unresolved:raise InputError('Table bound is undefined: '+', '.join(sorted(map(str,unresolved)))+'. Run the preceding calculation cells first.')
                raise InputError('Table bounds and nonzero step must be finite real numbers')
            size = max(0, int(s.floor((high-low)/step)) + 1)
            if size > 100000:
                raise InputError('Table iterator exceeds 100,000 values')
            values = (low + i*step for i in range(size))
        result = []
        for value in values:
            engine.environment[name] = value
            item = iterate(depth + 1)
            if item is not NOTHING and not (isinstance(item,s.Symbol) and item==NOTHING):
                result.append(item)
        return result

    try:
        return iterate(1)
    finally:
        engine.environment = previous


def flatten(value, depth=math.inf):
    if not isinstance(value, list):
        raise InputError('Flatten expects a list')
    result = []
    for item in value:
        if item == NOTHING:
            continue
        if isinstance(item, list) and depth > 0:
            result.extend(flatten(item, depth - 1))
        else:
            result.append(item)
    return result


def list_call(name, args):
    if name == 'Flatten':
        level = args[1] if len(args) > 1 else s.oo
        if level != s.oo and (not level.is_Integer or level < 0):
            raise InputError('Flatten level must be a nonnegative integer')
        return flatten(args[0], math.inf if level == s.oo else int(level))
    if name == 'IntegerQ':
        return s.true if isinstance(args[0], s.Integer) else s.false
    if name == 'Mod':
        return s.Mod(*args)
    if not args or not isinstance(args[0], list):
        raise InputError(f'{name} expects a list')
    values = args[0]
    if name == 'Accumulate':
        return list(accumulate(values))
    if name == 'Count':
        return s.Integer(sum(item == args[1] for item in values))
    if name == 'Permutations':
        if len(values) > 8:
            raise InputError('Permutations is limited to eight elements')
        return [list(row) for row in dict.fromkeys(permutations(values))]
    if name == 'Intersection':
        if any(not isinstance(value, list) for value in args):
            raise InputError('Intersection expects lists')
        return sorted(set.intersection(*(set(value) for value in args)), key=s.default_sort_key)
    raise InputError(f'Unsupported list operation {name}')
