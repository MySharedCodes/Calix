"""Bounded volume sampling and spatial primitives for scientific notebooks."""
import base64
import itertools
import math
from dataclasses import dataclass
import sympy as s
from .syntax import InputError


def number(value):
    try:
        result = float(value)
        if math.isfinite(result):
            return result
    except (ValueError, TypeError, OverflowError):
        pass
    raise InputError('Graphics3D requires finite real coordinates')


TEMPERATURE=['#2448a6','#2389cf','#22b6b0','#a2d46f','#f4da53','#ed913b','#c73d38']


@dataclass
class Palette:
    name:str

    def __call__(self,value):
        t=max(0,min(1,number(value)))*(len(TEMPERATURE)-1)
        i=min(int(t),len(TEMPERATURE)-2);fraction=t-i
        a,b=TEMPERATURE[i:i+2]
        rgb=[round(int(a[j:j+2],16)*(1-fraction)+int(b[j:j+2],16)*fraction) for j in (1,3,5)]
        return '#'+''.join(f'{c:02x}' for c in rgb)


@dataclass
class Legend:
    bounds:list
    label:str


def decoration(engine,name,nodes):
    args=[engine.evaluate(node) for node in nodes]
    if name=='ColorData':
        if args!=['TemperatureMap']:raise InputError('Supported ColorData palette: TemperatureMap')
        return Palette(args[0])
    if name=='BarLegend':
        if not args or not isinstance(args[0],list) or len(args[0])!=2 or args[0][0]!='TemperatureMap':
            raise InputError('Use BarLegend[{"TemperatureMap",{minimum,maximum}},LegendLabel->"label"]')
        if not isinstance(args[0][1],list):raise InputError('BarLegend range must be a two-item list')
        bounds=[number(v) for v in args[0][1]]
        if len(bounds)!=2 or bounds[0]>=bounds[1]:raise InputError('BarLegend range must increase')
        label=''
        for option in args[1:]:
            if not isinstance(option,tuple) or str(option[0])!='LegendLabel' or not isinstance(option[1],str):raise InputError('Unsupported BarLegend option')
            label=option[1]
        if len(label)>160:raise InputError('BarLegend label is too long')
        return Legend(bounds,label)
    if len(args)!=2 or not isinstance(args[0],dict) or args[0].get('kind')!='plot' or not isinstance(args[1],Legend):
        raise InputError('Legended requires a plot and BarLegend')
    return {**args[0],'scalar_legend':{'range':args[1].bounds,'label':args[1].label,'colors':TEMPERATURE}}


def volume(engine, nodes):
    if len(nodes) not in (4, 5):
        raise InputError('Use DensityPlot3D[density,{x,min,max},{y,min,max},{z,min,max},PlotPoints->49]')
    ranges = []
    for node in nodes[1:4]:
        if node.kind != 'list' or len(node.args) != 3 or node.args[0].kind != 'symbol':
            raise InputError('DensityPlot3D needs three coordinate ranges')
        low, high = (number(engine.evaluate(n)) for n in node.args[1:])
        if low >= high:
            raise InputError('Volume bounds must be increasing')
        ranges.append((s.Symbol(node.args[0].value), low, high))
    if len({r[0] for r in ranges}) != 3:
        raise InputError('Volume coordinates must be distinct')
    count = 49
    if len(nodes) == 5:
        option = nodes[4]
        if option.kind != 'binary' or option.value != '->' or option.args[0].value != 'PlotPoints':
            raise InputError('DensityPlot3D supports PlotPoints only')
        raw = engine.evaluate(option.args[1])
        if not isinstance(raw, s.Integer) or not 17 <= raw <= 65:
            raise InputError('Volume PlotPoints must be an integer from 17 to 65')
        count = int(raw)
    variables = [r[0] for r in ranges]
    density = engine.scoped([nodes[0]], variables)[0]
    if not isinstance(density, s.Expr):
        raise InputError('Volume density must be a scalar expression')
    axes = [[lo+(hi-lo)*i/(count-1) for i in range(count)] for _, lo, hi in ranges]
    # Three.js 3D textures store x fastest, followed by y and then z.
    points = list(itertools.product(axes[2], axes[1], axes[0]))
    coordinates = [[p[i] for p in points] for i in (2, 1, 0)]
    values = engine.sample(density, variables, coordinates)
    if any(v is None or v < -1e-12 for v in values):
        raise InputError('Probability density must be finite and nonnegative throughout the sampled volume')
    maximum = max(values)
    if maximum <= 0:
        raise InputError('Probability density is zero throughout the sampled volume')
    # Square-root encoding retains low-density tails with a compact byte texture.
    encoded = bytes(round(255*math.sqrt(max(0, v)/maximum)) for v in values)
    return {'kind': 'plot', 'plot_type': 'volume', 'title': 'DensityPlot3D',
            'axes': [str(v) for v in variables], 'size': count,
            'volume': base64.b64encode(encoded).decode('ascii'), 'density_max': maximum,
            'bounds': [[lo, hi] for _, lo, hi in ranges]}


def graphics3d(engine, nodes):
    if not nodes or nodes[0].kind != 'list' or not 1 <= len(nodes[0].args) <= 200:
        raise InputError('Use Graphics3D[{Style[Line[points],"#color","label"],Arrow[{start,end}],Point[point]}]')
    bounds=None
    for node in nodes[1:]:
        if node.kind!='binary' or node.value!='->' or node.args[0].value!='PlotRange':raise InputError('Graphics3D supports the PlotRange option')
        bounds=engine.evaluate(node.args[1])
        if not isinstance(bounds,list) or len(bounds)!=3 or any(not isinstance(row,list) or len(row)!=2 for row in bounds):raise InputError('Graphics3D PlotRange requires three coordinate intervals')
        bounds=[[number(v) for v in row] for row in bounds]
        if any(lo>=hi for lo,hi in bounds):raise InputError('PlotRange lower bounds must be less than upper bounds')
    primitives = []

    def append(value):
        primitives.append(value)
        if len(primitives)>48000:raise InputError('Graphics3D supports at most 48,000 primitives')

    def primitive(node, color='#087e80', label='',coordinates=None,vertex_colors=None):
        if node.kind == 'list':
            for item in node.args:
                primitive(item, color, label,coordinates,vertex_colors)
            return
        if node.kind != 'call' or node.args[0].kind != 'symbol':
            raise InputError('Graphics3D expects Line, Arrow or Point primitives')
        name = node.args[0].value
        args = node.args[1:]
        if name == 'Table' and len(args)>=2:
            previous = engine.environment.copy()
            count=0
            def iterate(depth):
                nonlocal count
                if depth==len(args):
                    count+=1
                    if count>48000:raise InputError('Graphics3D Table exceeds 48,000 items')
                    primitive(args[0],color,label,coordinates,vertex_colors)
                    return
                iterator=args[depth]
                if iterator.kind!='list' or len(iterator.args) not in (2,3,4) or iterator.args[0].kind!='symbol':raise InputError('Invalid Graphics3D Table iterator')
                bounds=[engine.evaluate(n) for n in iterator.args[1:]]
                if len(bounds)==1 and isinstance(bounds[0],list):values=bounds[0]
                else:
                    low,high,step=(1,bounds[0],1) if len(bounds)==1 else (*bounds,1) if len(bounds)==2 else bounds
                    if not all(number(v).is_integer() for v in (low,high,step)) or step==0:raise InputError('Graphics3D numeric iterators require integers and nonzero step')
                    values=range(int(low),int(high)+(1 if step>0 else -1),int(step))
                if len(values)>48000:raise InputError('Graphics3D Table exceeds 48,000 items')
                for value in values:
                    engine.environment[iterator.args[0].value]=s.Integer(value) if isinstance(value,int) else value
                    iterate(depth+1)
            try:
                iterate(1)
            finally:
                engine.environment = previous
            return
        if name == 'Style' and len(args) in (2, 3):
            color = engine.evaluate(args[1])
            label = engine.evaluate(args[2]) if len(args) == 3 else ''
            if not isinstance(color, str) or len(color) != 7 or color[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]):
                raise InputError('3D colors use #rrggbb')
            if not isinstance(label, str) or len(label) > 120:
                raise InputError('3D labels must be text of at most 120 characters')
            primitive(args[0], color, label,coordinates,vertex_colors)
            return
        if name=='GraphicsComplex':
            if len(args) not in (2,3):raise InputError('GraphicsComplex requires coordinates, primitives and optional VertexColors')
            points=engine.evaluate(args[0]);colors=None
            if not isinstance(points,list) or not 1<=len(points)<=20000 or any(not isinstance(p,list) or len(p)!=3 for p in points):raise InputError('GraphicsComplex requires a list of 3D coordinates')
            points=[[number(v) for v in p] for p in points]
            if len(args)==3:
                rule=engine.evaluate(args[2])
                if not isinstance(rule,tuple) or str(rule[0])!='VertexColors':raise InputError('GraphicsComplex supports VertexColors only')
                colors=rule[1]
                if not isinstance(colors,list) or len(colors)!=len(points) or any(not valid_color(c) for c in colors):raise InputError('VertexColors must provide a #rrggbb color for every vertex')
            primitive(args[1],color,label,points,colors)
            return
        if name not in ('Line', 'Arrow', 'Point','Polygon') or len(args) != 1:
            raise InputError('Graphics3D supports Line, Arrow, Point, Polygon, GraphicsComplex and Style')
        points = engine.evaluate(args[0])
        if name=='Polygon':
            faces=points if coordinates is not None and points and isinstance(points[0],list) else [points]
            for face in faces:
                if not isinstance(face,list) or not 3<=len(face)<=32:raise InputError('Polygon requires 3 to 32 vertices')
                colors=None
                if coordinates is not None:
                    if any(not isinstance(i,(int,s.Integer)) or isinstance(i,bool) or i<1 or i>len(coordinates) for i in face):raise InputError('GraphicsComplex polygon index is outside its coordinate list')
                    if vertex_colors is not None:colors=[vertex_colors[int(i)-1] for i in face]
                    face=[coordinates[int(i)-1] for i in face]
                if any(not isinstance(p,list) or len(p)!=3 for p in face):raise InputError('Polygon vertices must be 3D points')
                for i in range(1,len(face)-1):
                    triangle={'type':'triangle','points':[[number(v) for v in face[j]] for j in (0,i,i+1)],'color':color,'label':label}
                    if colors is not None:triangle['colors']=[colors[j] for j in (0,i,i+1)]
                    append(triangle)
            return
        if name == 'Point' and isinstance(points, list) and len(points) == 3 and not isinstance(points[0], list):
            points = [points]
        if not isinstance(points, list) or not 1 <= len(points) <= 4000 or (name == 'Line' and len(points) < 2) or (name == 'Arrow' and len(points) != 2):
            raise InputError('Invalid number of 3D primitive coordinates')
        if any(not isinstance(p, list) or len(p) != 3 for p in points):
            raise InputError('Each 3D point requires three coordinates')
        append({'type': name.lower(), 'points': [[number(v) for v in p] for p in points], 'color': color, 'label': label})

    for node in nodes[0].args:
        primitive(node)
    if bounds is not None:primitives=clip_geometry(primitives,bounds)
    if not primitives:raise InputError('No geometry lies within PlotRange')
    return {'kind': 'plot', 'plot_type': 'geometry3d', 'title': 'Graphics3D',
            'axes': ['x', 'y', 'z'], 'primitives': primitives,'options':{'wireframe':any(p['type']=='triangle' for p in primitives)}}


def clip_geometry(primitives,bounds):
    result=[]
    for item in primitives:
        if item['type']!='triangle':
            if item['type']=='point':
                points=[p for p in item['points'] if all(lo<=p[axis]<=hi for axis,(lo,hi) in enumerate(bounds))]
                if points:result.append({**item,'points':points})
                continue
            for a,b in zip(item['points'],item['points'][1:]):
                enter,leave=0.,1.
                for axis,(lo,hi) in enumerate(bounds):
                    delta=b[axis]-a[axis]
                    if delta==0:
                        if not lo<=a[axis]<=hi:leave=-1;break
                    else:
                        t0,t1=sorted(((lo-a[axis])/delta,(hi-a[axis])/delta))
                        enter=max(enter,t0);leave=min(leave,t1)
                if enter<=leave:
                    result.append({**item,'points':[[x+t*(y-x) for x,y in zip(a,b)] for t in (enter,leave)]})
            continue
        colors=item.get('colors',[item['color']]*3)
        polygon=[(list(p),[int(color[i:i+2],16) for i in (1,3,5)]) for p,color in zip(item['points'],colors)]
        # Sutherland-Hodgman clipping preserves the interpolated vertex field.
        for axis,(lo,hi) in enumerate(bounds):
            for limit,sign in ((lo,1),(hi,-1)):
                clipped=[]
                for previous,current in zip(polygon[-1:]+polygon[:-1],polygon):
                    a,ac=previous;b,bc=current
                    ain=sign*(a[axis]-limit)>=0;bin=sign*(b[axis]-limit)>=0
                    if ain!=bin:
                        t=(limit-a[axis])/(b[axis]-a[axis])
                        clipped.append(([x+t*(y-x) for x,y in zip(a,b)],[x+t*(y-x) for x,y in zip(ac,bc)]))
                    if bin:clipped.append(current)
                polygon=clipped
                if not polygon:break
            if not polygon:break
        for i in range(1,len(polygon)-1):
            vertices=[polygon[j] for j in (0,i,i+1)]
            result.append({**item,'points':[v[0] for v in vertices],'colors':['#'+''.join(f'{max(0,min(255,round(c))):02x}' for c in v[1]) for v in vertices]})
            if len(result)>48000:raise InputError('Clipped graphics exceed 48,000 primitives')
    return result


def valid_color(color):return isinstance(color,str) and len(color)==7 and color[0]=='#' and all(c in '0123456789abcdefABCDEF' for c in color[1:])
