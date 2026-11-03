"""Two-dimensional line and point primitives rendered through the existing plot view."""
import math
from .syntax import InputError


def geometry(engine, nodes):
    if len(nodes) != 1 or nodes[0].kind != 'list' or not 1 <= len(nodes[0].args) <= 20:
        raise InputError('Use Graphics[{Line[points],Point[points]}]')
    shapes = []
    for primitive in nodes[0].args:
        if primitive.kind != 'call' or primitive.args[0].kind != 'symbol' or primitive.args[0].value not in ('Line', 'Point') or len(primitive.args) != 2:
            raise InputError('Graphics supports Line and Point primitives')
        name = primitive.args[0].value
        points = engine.evaluate(primitive.args[1])
        if name == 'Point' and isinstance(points, list) and len(points) == 2 and not isinstance(points[0], list):
            points = [points]
        if not isinstance(points, list) or not (2 if name == 'Line' else 1) <= len(points) <= 2000:
            raise InputError('Graphics requires nonempty coordinate lists (at least two points for Line)')
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise InputError('Each point must contain two coordinates')
        shapes.append((name, points))
    return shapes


def graphics(engine, nodes):
    traces = []
    for name, points in geometry(engine, nodes):
        coordinates = []
        for point in points:
            try:
                pair = [float(value) for value in point]
            except (TypeError, ValueError, OverflowError):
                raise InputError('Graphics coordinates must be finite real numbers') from None
            if any(not math.isfinite(value) for value in pair):
                raise InputError('Graphics coordinates must be finite real numbers')
            coordinates.append(pair)
        traces.append({'x': [p[0] for p in coordinates], 'y': [p[1] for p in coordinates], 'name': name,
                       'style': 'markers' if name == 'Point' else 'lines'})
    return {'kind': 'plot', 'plot_type': 'curve', 'title': 'Graphics', 'axes': ['x', 'y'],
            'options': {'equal_aspect': True, 'legend': False}, 'traces': traces}


def frames(engine, nodes, parameter, values):
    import sympy as s
    shapes = geometry(engine, nodes)
    sampled = []
    for name, points in shapes:
        x = [engine.sample(s.sympify(point[0]), [parameter], [values]) for point in points]
        y = [engine.sample(s.sympify(point[1]), [parameter], [values]) for point in points]
        if any(value is None for column in x+y for value in column):
            raise InputError('Animation coordinates must stay finite over the animation interval')
        sampled.append((name, x, y))
    return [{'kind': 'plot', 'plot_type': 'curve', 'title': 'Graphics', 'axes': ['x', 'y'],
             'options': {'equal_aspect': True, 'legend': False},
             'traces': [{'name': name, 'style': 'markers' if name == 'Point' else 'lines',
                         'x': [column[i] for column in x], 'y': [column[i] for column in y]} for name, x, y in sampled]}
            for i in range(len(values))]
