"""Add output labels while retaining the original calculation source and assignments."""
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.syntax import parse

NAMES = {
    'sweptArea': 'swept area', 'flux': 'magnetic flux', 'emf': 'induced EMF',
    'current': 'current', 'force': 'force', 'rest': 'equilibrium positions',
    'stiffness': 'stiffness / mass matrix', 'small': 'small-angle displacements',
    'motion': 'position functions', 'v': 'velocity, {x,y}', 'r': 'displacement, {x,y}',
    'uniform': 'uniform-field position, {x,y,z}', 'radial': 'radial wave function R(r)',
    'spherical': 'angular wave function Y(theta)', 'energy': 'energy',
    'regular': 'regular radial solution', 'residual': 'recurrence residual',
    'quantization': 'eta, quantization condition', 'levels': 'energy levels, n = 1...6',
    'bounds': '{infimum, supremum}', 'certificates': 'strict-bound positivity checks',
    'critical': 'stationary points', 'best': 'minimum m+n', 'winners': '{m,n,last three digits}',
    'total': 'alternating harmonic sum', 'p': 'numerator', 'q': 'denominator',
    'f': 'function', 'rec': 'recurrence solution', 'center': 'central magnetic field',
    'timeScale': 'cyclotron time scale', 'acceleration': 'initial accelerations',
    'com': 'center of mass', 'initialAcceleration': 'initial accelerations',
}
FUNCTIONS = {
    'Mean':'mean', 'Median':'median', 'Variance':'variance', 'StandardDeviation':'standard deviation',
    'Quartiles':'quartiles', 'Quantile':'quantiles', 'Counts':'frequency counts',
    'InterquartileRange':'interquartile range', 'Skewness':'skewness', 'Kurtosis':'kurtosis',
    'Standardize':'standardized observations', 'Histogram':'frequency histogram',
    'CDF':'cumulative probability', 'PDF':'probability density / mass', 'InverseCDF':'quantile',
    'Correlation':'Pearson correlation', 'Covariance':'covariance', 'SpearmanRho':'Spearman rank correlation',
    'TTest':'Student t-test p-value', 'ZTest':'z-test p-value', 'Fit':'fitted function',
    'D':'derivative', 'Integrate':'integral', 'NIntegrate':'numerical integral',
    'Solve':'equation solutions', 'SolveValues':'solution values', 'Reduce':'solution region',
    'DSolve':'ODE analytic solution', 'DSolveValue':'ODE analytic solution',
    'NDSolve':'ODE numerical solution', 'NDSolveValue':'ODE numerical solution',
    'RSolve':'recurrence solution', 'Minimize':'analytic minimum', 'Maximize':'analytic maximum',
    'FindMinimum':'numerical minimum', 'FindMaximum':'numerical maximum', 'FindRoot':'numerical root',
    'Sum':'sum', 'Product':'product', 'Det':'determinant', 'Dot':'matrix product',
    'Inverse':'inverse matrix', 'Transpose':'transposed matrix', 'Eigenvalues':'squared mode frequencies',
    'UnitConvert':'unit conversion', 'UnitSimplify':'simplified units',
    'Series':'power series', 'GCD':'greatest common divisor', 'IntegerLength':'decimal digits',
    'Plot':'function curves', 'Plot3D':'function surface', 'ContourPlot':'contours',
    'ParametricPlot':'parametric curve', 'ParametricPlot3D':'spatial parametric curve / surface',
    'ListPlot':'sampled values', 'Animate':'motion animation', 'Graphics3D':'spatial scene',
    'DensityPlot3D':'probability density cloud',
}

# Labels follow output order within each calculation cell in the authored cases.
CASE_LABELS = {
    '空气阻力': [
        ['velocity, {x,y} [m/s]'], ['displacement, {x,y} [m]'],
        ['displacement,x versus time [m]', 'displacement,y versus time [m]'], ['trajectory, {x,y} [m]'],
    ],
    '高考物理': [
        ['swept area', 'magnetic flux', 'induced EMF', 'current', 'required external force'],
        ['force unit', 'external force [N]', 'magnetic flux versus time [Wb]'],
    ],
    '高考数学': [
        ['f8 derivative', 'stationary x values', 'increasing region', 'decreasing region', 'stationary function values', 'f8 versus x'],
        ['{infimum, supremum}', 'strict-bound positivity checks', 'f versus log(a), log(x)'],
    ],
    'IMO 1979': [
        ['alternating harmonic sum, 30 digits', 'decimal digits, {numerator,denominator}', 'GCD of numerator and denominator', 'remainders modulo 1979, {numerator,denominator}', 'exact numerator / 1979'],
    ],
    'IMO 1978': [
        ['minimum m+n', '{m,n,last three digits}', 'search covers every smaller sum', '1978^n modulo 1000'],
    ],
    '弹性双摆': [
        ['equilibrium positions, {x1,y1,x2,y2} [m]', 'stiffness / mass matrix [1/s^2]', 'squared mode frequencies [1/s^2]'],
        [], ['large-angle position functions, {x1,y1,x2,y2} [m]'],
        ['small-angle horizontal displacements [m]', 'large-angle horizontal displacements [m]', 'total energy drift [J]'],
        ['large-angle motion, coordinates [m]'],
    ],
    '五球': [
        ['initial positions, balls 1...5 [m]'], [],
        ['initial accelerations, balls 1...5 [m/s^2]', 'center of mass position [m]', 'bottom ball position series [m]'],
        ['bottom two balls and free-fall displacements [m]', 'displacement differences from free fall [m]'],
        ['spring chain, positions relative to center of mass [m]'],
    ],
    '多天体': [
        ['position functions, {x1,y1,x2,y2,x3,y3}'],
        ['total energy drift', 'total momentum, {x,y}', 'total angular momentum'],
        ['gravitational potential versus planar position'],
    ],
    '电流线圈': [
        ['axial magnetic field, Bz(z) / B0', 'central magnetic field B0', 'time scale, mp / (e B0)', 'velocity scale, R / time scale'],
        [], ['nonuniform-field position functions, {x,y,z} / R'],
        ['', 'height comparison, z / R', 'speed squared drift, normalized units'],
    ],
    '类氢': [
        ['regular radial solution', 'hypergeometric recurrence residual', 'hypergeometric power series', 'eta, quantization condition', 'energy levels, n=1...6 [Hartree]'],
        ['normalized radial wave function', 'normalized angular wave function', 'energy [Hartree]', 'energy [eV]'], [], [],
    ],
}


def split(source, separator):
    """Split separators outside strings and balanced WL argument/list groups."""
    depth, start, pieces = 0, 0, []
    for match in re.finditer(r'"(?:[^"\\]|\\.)*"|[\[\]{}();,]', source):
        token = match.group()
        if token in ('[', '{', '('):
            depth += 1
        elif token in (']', '}', ')'):
            depth -= 1
        elif token == separator and depth == 0:
            pieces.append(source[start:match.start()])
            start = match.end()
    pieces.append(source[start:])
    return pieces


def description(expression):
    compact = ' '.join(expression.split())
    node = parse(expression)
    if node.kind == 'symbol':
        return NAMES.get(node.value, node.value)
    if node.kind == 'call' and node.args[0].kind == 'symbol':
        head = node.args[0].value
        if head in ('N', 'Simplify', 'Factor', 'Expand', 'FunctionExpand'):
            inner = expression[expression.index('[')+1:-1]
            return description(split(inner, ',')[0])
        if head == 'Part' and node.args[1].kind == 'symbol' and node.args[1].value in ('v','r','uniform','motion','small'):
            name = node.args[1].value
            index = node.args[2].value
            axis = {'1':'x','2':'y','3':'z'}.get(index,index)
            return ('velocity' if name == 'v' else 'displacement' if name in ('r','small') else 'position')+', '+axis
        if head in FUNCTIONS:
            return FUNCTIONS[head]+': '+compact[:140]
    return 'value: '+compact[:210]


def labeled(expression, label=None):
    expression = expression.strip()
    if expression.startswith('Labeled['):
        return expression
    return 'Labeled['+expression+', '+json.dumps(label or description(expression),ensure_ascii=False)+']'


def annotate(source, labels=None):
    labels = labels or []
    statements = split(source, ';')
    expression = statements[-1].strip()
    if not expression or expression.startswith('Labeled['):
        return source
    if expression.startswith('Column[') and expression.endswith(']'):
        inside = expression[7:-1].strip()
        if inside.startswith('{') and inside.endswith('}'):
            result = 'Column[{\n'+',\n'.join('  '+labeled(part, labels[i] if i<len(labels) else None) for i,part in enumerate(split(inside[1:-1],',')))+'\n}]'
        else:
            result = labeled(expression)
    else:
        node = parse(expression)
        if node.kind == 'binary' and node.value == '=':
            result = expression+';\n'+labeled(node.args[0].value, labels[0] if labels else None)
        else:
            result = labeled(expression, labels[0] if labels else None)
    return ';'.join(statements[:-1])+(';' if len(statements)>1 else '')+'\n'+result if len(statements)>1 else result


def annotate_notebook(notebook):
    labels = next((v for k,v in CASE_LABELS.items() if notebook['title'].startswith(k)), [])
    index = 0
    for cell in notebook['cells']:
        if cell['mode'] != 'markdown':
            cell['code'] = annotate(cell['code'], labels[index] if index<len(labels) else None)
            index += 1
    return notebook
