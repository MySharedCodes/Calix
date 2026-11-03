"""Native-sampled magnetic scenes and gravitational many-body demonstrations."""
import base64
import itertools
import math
import sympy as s
from .syntax import InputError
from .native import kernel
from .ode_system import solve


COLORS = ['#d9485f', '#168eaa', '#ce9922', '#6b65a8', '#459866']
CHARGE_COLORS = ['#d52b45', '#d77b00', '#a32897', '#1263c7', '#008f74', '#6948bd']


def finite(value):
    try:
        value = float(value)
        if math.isfinite(value):
            return value
    except (ValueError, TypeError, OverflowError):
        pass
    raise InputError('Scene parameters must be finite real numbers')


def nbody(masses, positions, velocities, interval):
    if not isinstance(masses, list) or not 2 <= len(masses) <= 5 or any(finite(m) <= 0 for m in masses):
        raise InputError('NBodySolve supports two to five positive masses, with G=1')
    count = len(masses)
    if not isinstance(positions, list) or len(positions) != count or not isinstance(velocities, list) or len(velocities) != count:
        raise InputError('Provide one position and velocity per mass')
    dimension = len(positions[0]) if isinstance(positions[0], list) else 0
    if dimension not in (2, 3) or any(not isinstance(row, list) or len(row) != dimension for row in positions+velocities):
        raise InputError('Use matching 2D or 3D position and velocity vectors')
    for row in positions+velocities:
        for value in row:
            finite(value)
    if not isinstance(interval, list) or len(interval) != 3 or not isinstance(interval[0], s.Symbol):
        raise InputError('NBodySolve range uses {t,lower,upper}')
    t, low, _ = interval
    q = [[s.Function(f'body{i+1}{axis}')(t) for axis in 'xyz'[:dimension]] for i in range(count)]
    equations = []
    for i in range(count):
        for axis in range(dimension):
            acceleration = 0
            for j in range(count):
                if i == j:
                    continue
                if all(positions[i][a] == positions[j][a] for a in range(dimension)):
                    raise InputError('Initial body positions must be distinct')
                distance2 = sum((q[j][a]-q[i][a])**2 for a in range(dimension))
                acceleration += masses[j]*(q[j][axis]-q[i][axis])/distance2**s.Rational(3,2)
            equations.extend([s.Eq(s.diff(q[i][axis],t,2),acceleration),
                              s.Eq(q[i][axis].subs(t,low),positions[i][axis]),
                              s.Eq(s.Subs(s.diff(q[i][axis],t),t,low),velocities[i][axis])])
    result = solve(equations, [value for row in q for value in row], interval)
    return [result[i*dimension:(i+1)*dimension] for i in range(count)]


def sample_motion(engine, motion, parameter, low, high, count=301):
    if not isinstance(motion, list) or not motion or any(not isinstance(row, list) or len(row) not in (2,3) for row in motion):
        raise InputError('Provide one 2D or 3D position function per body')
    times = [low+(high-low)*i/(count-1) for i in range(count)]
    paths = []
    for row in motion:
        columns = [engine.sample(s.sympify(expr),[parameter],[times]) for expr in row]
        if any(v is None for column in columns for v in column):
            raise InputError('Motion must remain finite throughout the plotted interval')
        if len(columns) == 2:
            columns.append([0.0]*count)
        paths.append([list(p) for p in zip(*columns)])
    return times, paths


def gravity_scene(engine, args):
    if len(args) != 3:
        raise InputError('Use NBodyPlot3D[positionFunctions,masses,{t,lower,upper}]')
    motion, masses, interval = args
    if not isinstance(masses,list) or not 2 <= len(masses) <= 5 or not isinstance(motion,list) or len(motion) != len(masses) or any(finite(m) <= 0 for m in masses):
        raise InputError('Provide two to five positive masses matching the motion')
    if not isinstance(interval,list) or len(interval)!=3 or not isinstance(interval[0],s.Symbol):
        raise InputError('Scene range uses {t,lower,upper}')
    t, low, high = interval[0], finite(interval[1]), finite(interval[2])
    if low >= high:
        raise InputError('Scene time bounds must increase')
    times, paths = sample_motion(engine,motion,t,low,high)
    extent = max(abs(value) for path in paths for point in path for value in point)*1.2+0.15
    total = sum(float(m) for m in masses)
    return {'kind':'plot','plot_type':'field3d','field_kind':'gravity','title':'NBodyPlot3D',
            'axes':['x','y','z'],'bounds':[[-extent,extent]]*3,'color_range':[-total*3.5,-total/(extent*1.3)],
            'masses':[float(m) for m in masses],'softening':0.12,'times':times,
            'paths':paths,'colors':COLORS[:len(masses)],
            'labels':[f'body {i+1}, m={float(m):g}' for i,m in enumerate(masses)]}


def magnetic_scene(engine, args):
    if len(args) not in (5,6):
        raise InputError('Use MagneticFieldPlot3D[field,{x,y,z},coilOffsets,particleMotions,optionalCharges,{t,lower,upper}]')
    field, variables, offsets, motion = args[:4]
    interval = args[-1]
    charges = args[4] if len(args)==6 else None
    if not isinstance(field,list) or len(field)!=3 or not isinstance(variables,list) or len(variables)!=3 or len(set(variables))!=3 or any(not isinstance(v,s.Symbol) for v in variables):
        raise InputError('Provide a 3D magnetic field and three distinct coordinate variables')
    if not isinstance(offsets,list) or not 1 <= len(offsets) <= 8:
        raise InputError('Provide one to eight equal-current, unit-radius coaxial coil offsets')
    offsets = [finite(v) for v in offsets]
    if not isinstance(interval,list) or len(interval)!=3 or not isinstance(interval[0],s.Symbol):
        raise InputError('Scene range uses {t,lower,upper}')
    t,low,high = interval[0],finite(interval[1]),finite(interval[2])
    if low >= high or not isinstance(motion,list) or not 2 <= len(motion) <= 6:
        raise InputError('Provide two to six charged-particle paths and increasing time bounds')
    if charges is not None and (not isinstance(charges,list) or len(charges)!=len(motion) or any(finite(q)==0 for q in charges)):
        raise InputError('Provide one finite nonzero charge in units of e per particle')
    times,paths = sample_motion(engine,motion,t,low,high)
    extent = max(2.1,max(abs(v) for path in paths for p in path for v in p)*1.1)
    paths = [[[round(v,6) for v in point] for point in path] for path in paths]
    bounds = [[-extent,extent]]*3
    count = 41
    grid = [-extent+2*extent*i/(count-1) for i in range(count)]
    points = list(itertools.product(grid,grid,grid))  # z,y,x order for the texture.
    valid, coordinates = [], [[],[],[]]
    for index,(z,y,x) in enumerate(points):
        rho = math.hypot(x,y)
        if rho < 1e-8 or any(math.hypot(rho-1,z-h)<0.075 for h in offsets):
            continue
        valid.append(index)
        for column,value in zip(coordinates,(x,y,z)):
            column.append(value)
    columns = [engine.sample(expr,variables,coordinates) for expr in field]
    magnitudes = [0.0]*len(points)
    for j,index in enumerate(valid):
        values = [column[j] for column in columns]
        if any(v is None for v in values):
            raise InputError('Magnetic field is nonfinite away from the excluded wire region')
        magnitudes[index] = math.sqrt(sum(v*v for v in values))
    normalization = sum((1+h*h)**-1.5 for h in offsets)
    for index,(z,y,x) in enumerate(points):
        if math.hypot(x,y)<1e-8:
            magnitudes[index]=sum((1+(z-h)**2)**-1.5 for h in offsets)/normalization
    maximum = 3.0
    encoded = bytes(round(255*min(1,math.log1p(v)/math.log1p(maximum))) for v in magnitudes)
    parameter=s.Dummy('arc')
    norm=s.sqrt(sum(component**2 for component in field))
    lines=[]
    for radius in (0.25,0.5,0.75,1.3):
        for angle in (2*math.pi*i/12 for i in range(12)):
            seed=[radius*math.cos(angle),radius*math.sin(angle),0.0]
            halves=[]
            for direction in (-1,1):
                _,columns=kernel.ode_system([direction*v/norm for v in field],[parameter,*variables],0,9,seed,points=121)
                half=[]
                for point in zip(*columns[:3]):
                    if any(abs(v)>extent for v in point) or any(math.hypot(math.hypot(*point[:2])-1,point[2]-h)<0.075 for h in offsets):
                        break
                    half.append([round(v,6) for v in point])
                halves.append(half)
            line=list(reversed(halves[0]))+halves[1][1:]
            if len(line)>1:
                lines.append(line)
    engine.route='C++ / field sampling and field-line ODE'
    return {'kind':'plot','plot_type':'field3d','field_kind':'magnetic','title':'MagneticFieldPlot3D',
            'axes':['x / R','y / R','z / R'],'bounds':bounds,'color_range':[0,maximum],
            'size':count,'volume':base64.b64encode(encoded).decode('ascii'),'coils':offsets,
            'field_lines':lines,'times':times,'paths':paths,'colors':CHARGE_COLORS[:len(motion)],
            'labels':[f'particle {i+1}'+(f', q={float(charges[i]):+g}e' if charges is not None else '') for i in range(len(motion))],
            'wire_mask':0.075}
