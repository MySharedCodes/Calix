"""Exact list operations available without the optional PDE component."""
import sympy as s
from .syntax import InputError


FUNCTIONS={'Association','ConstantArray','IdentityMatrix','KroneckerDelta','Length','Range','Union','Complement','Norm','Dimensions','ArrayReshape'}


def call(name,args):
    if name=='Association':
        if len(args)==1 and isinstance(args[0],list):args=args[0]
        if any(not isinstance(item,tuple) or len(item)!=2 for item in args):raise InputError('Association expects rules')
        return dict(args)
    if name=='Length':
        if isinstance(args[0],s.Symbol):raise InputError(f'Length input is undefined: {args[0]}. Run the preceding calculation cells first.')
        try:return s.Integer(args[0].shape[0] if hasattr(args[0],'shape') else len(args[0]))
        except TypeError:raise InputError('Length requires a list, matrix or string') from None
    if name=='Dimensions':
        if hasattr(args[0],'shape'):return list(map(s.Integer,args[0].shape))
        shape=[];value=args[0]
        while isinstance(value,list):
            shape.append(s.Integer(len(value)))
            if not value:break
            if any(isinstance(v,list)!=isinstance(value[0],list) or isinstance(v,list) and len(v)!=len(value[0]) for v in value):break
            value=value[0]
        return shape
    if name=='IdentityMatrix':return s.eye(int(args[0])).tolist()
    if name=='KroneckerDelta':return s.KroneckerDelta(*args) if len(args)==2 else s.Integer(all(a==args[0] for a in args))
    if name=='Range':
        lo,hi,step=(s.Integer(1),args[0],s.Integer(1)) if len(args)==1 else (*args,s.Integer(1)) if len(args)==2 else args
        if step==0:raise InputError('Range step must be nonzero')
        count=max(0,int(s.floor((hi-lo)/step))+1)
        if count>200000:raise InputError('Range exceeds 200000 items')
        return [lo+i*step for i in range(count)]
    if name in ('ConstantArray','ArrayReshape'):
        shape=args[1] if isinstance(args[1],list) else [args[1]]
        shape=list(map(int,shape))
        if any(n<0 for n in shape) or s.prod(shape)>200000:raise InputError('Invalid or excessive array dimensions')
        def flatten(value):
            if isinstance(value,list):return [x for v in value for x in flatten(v)]
            return [value]
        source=args[0].tolist() if hasattr(args[0],'tolist') else args[0]
        values=iter([source]*int(s.prod(shape)) if name=='ConstantArray' else flatten(source))
        if name=='ArrayReshape' and len(flatten(source))!=s.prod(shape):raise InputError('ArrayReshape dimensions must match the number of elements')
        def build(d):return [build(d[1:]) for _ in range(d[0])] if d else next(values)
        return build(shape)
    if name in ('Union','Complement'):
        def freeze(v):return tuple(map(freeze,v)) if isinstance(v,list) else v
        def thaw(v):return list(map(thaw,v)) if isinstance(v,tuple) else v
        values=set(map(freeze,args[0]))
        for a in args[1:]:values=values.union(map(freeze,a)) if name=='Union' else values.difference(map(freeze,a))
        return list(map(thaw,sorted(values,key=s.default_sort_key)))
    if name=='Norm':
        if isinstance(args[0],list):return s.sqrt(s.Add(*(s.Abs(v)**2 for v in args[0])))
        if hasattr(args[0],'shape'):
            import numpy as np
            return s.Float(np.linalg.norm(np.asarray(args[0], dtype=complex)))
        return s.Abs(args[0])
    raise InputError(f'Unsupported array operation {name}')
