"""Typed C ABI bridge; symbolic expressions are compiled once per batch."""
import ctypes as ct
import math
import os
from pathlib import Path
import sys
from array import array
from functools import lru_cache
import sympy as s


class NativeUnsupported(ValueError):
    pass

ROOT_CALLBACK = ct.CFUNCTYPE(ct.c_double, ct.c_double)


class NativeKernel:
    def __init__(self):
        root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
        candidates = [root / "calix_native.dll", root / "native/build/Release/calix_native.dll"]
        explicit = os.environ.get("CALIX_NATIVE_DLL")
        if explicit:
            candidates.insert(0, Path(explicit))
        path = next((p for p in candidates if p.exists()), None)
        self.lib = ct.CDLL(str(path)) if path else None
        self.execution={}
        self.thread_limit=1
        self.sparse_runtime_loaded=False
        self.sparse_directories=[]
        if not self.lib:
            return
        ip, dp = ct.POINTER(ct.c_int32), ct.POINTER(ct.c_double)
        self.lib.calix_cpu_features.restype=ct.c_uint32
        self.lib.calix_simd_level.restype=ct.c_int
        self.lib.calix_set_threads.argtypes=[ct.c_int]
        self.lib.calix_set_threads.restype=ct.c_int
        self.lib.calix_last_threads.restype=ct.c_int
        self.lib.calix_dense_f64.argtypes=[dp,dp,dp]+[ct.c_int]*4
        self.lib.calix_dense_f64.restype=ct.c_int
        self.lib.calix_dense_i8.argtypes=[ct.POINTER(ct.c_int8),ct.POINTER(ct.c_int8),ip]+[ct.c_int]*4
        self.lib.calix_dense_i8.restype=ct.c_int
        self.lib.calix_sparse_solve.argtypes=[ct.c_int,ct.c_int,ip,ip,dp,dp,dp,dp]
        self.lib.calix_sparse_solve.restype=ct.c_int
        self.lib.calix_load_sparse_runtime.argtypes=[ct.c_wchar_p]
        self.lib.calix_load_sparse_runtime.restype=ct.c_int
        self.lib.calix_fem_elements.argtypes=[ct.c_int]*5+[dp,ip]+[dp]*7
        self.lib.calix_fem_elements.restype=ct.c_int
        self.lib.calix_projectile.argtypes = [ct.c_double]*4+[ct.c_int,ct.c_double,ct.c_int,dp]
        self.lib.calix_projectile.restype = ct.c_int
        self.lib.calix_callback_root.argtypes = [ROOT_CALLBACK,ct.c_double,ct.c_double,dp]
        self.lib.calix_callback_root.restype = ct.c_int
        self.lib.calix_batch.argtypes = [ip, dp, ct.c_int, dp, dp, dp, ct.c_int, dp]
        self.lib.calix_batch_variables.argtypes = [ip, dp, ct.c_int, dp, ct.c_int, ct.c_int, dp]
        self.lib.calix_batch_variables.restype = ct.c_int
        self.lib.calix_root.argtypes = [ip, dp, ct.c_int, ct.c_double, ct.c_double, ct.c_double, dp]
        self.lib.calix_integrate.argtypes = [ip, dp, ct.c_int, ct.c_double, ct.c_double, ct.c_double, dp, dp]
        self.lib.calix_ode.argtypes = [ip, dp, ct.c_int, ct.c_double, ct.c_double, ct.c_double, ct.c_int, ct.c_double, dp, dp]
        self.lib.calix_extremum.argtypes = [ip, dp, ct.c_int, ct.c_double, ct.c_double, ct.c_int, dp, dp]
        self.lib.calix_extremum.restype = ct.c_int
        self.lib.calix_ode_pair.argtypes = [ip, dp, ct.c_int, ip, dp, ct.c_int,
                                          ct.c_double, ct.c_double, ct.c_double, ct.c_double,
                                          ct.c_int, ct.c_double, dp]
        self.lib.calix_ode_pair.restype = ct.c_int
        self.lib.calix_ode_system.argtypes = [ip, dp, ip, ct.c_int, ct.c_double, ct.c_double,
                                            dp, ct.c_int, ct.c_double, dp]
        self.lib.calix_ode_system.restype = ct.c_int
        for name in ("calix_batch", "calix_root", "calix_integrate", "calix_ode"):
            getattr(self.lib, name).restype = ct.c_int

    @property
    def available(self):
        return self.lib is not None

    def cpu_features(self):
        if not self.available:return {'selected':'scalar','native':False}
        flags=self.lib.calix_cpu_features()
        return {'selected':('scalar','avx2','avx512')[self.lib.calix_simd_level()],
                'avx2_hardware':bool(flags&1),'avx2_enabled':bool(flags&2),
                'avx512_hardware':bool(flags&4),'avx512_enabled':bool(flags&8),
                'amx_int8_hardware':bool(flags&16),'amx_os_enabled':bool(flags&32),
                'compiled':['scalar','avx2','avx512','amx-int8']}

    def configure_threads(self,count):
        self.thread_limit=int(count)
        if self.available and self.lib.calix_set_threads(self.thread_limit)<0:
            raise ValueError('Invalid native thread limit')

    def reset_execution(self):
        self.execution={'thread_limit':self.thread_limit,'threads_used':1,'operations':{}}

    def record_execution(self,operation,path,threads=1):
        if not self.execution:self.reset_execution()
        self.execution['threads_used']=max(self.execution['threads_used'],threads)
        record=self.execution['operations'].setdefault(operation,{'calls':0,'threads_used':1,'path':path})
        record['calls']+=1
        record['threads_used']=max(record['threads_used'],threads)
        record['path']=path

    def dense_dot(self,left,right,integer=False,mode=-1):
        m,k,n=len(left),len(left[0]),len(right[0])
        if len(right)!=k or any(len(row)!=k for row in left) or any(len(row)!=n for row in right):
            raise ValueError('Dot matrix dimensions do not match')
        if integer:
            values=[int(v) for row in left for v in row]+[int(v) for row in right for v in row]
            if any(v < -128 or v > 127 for v in values):raise ValueError('AMX integer input must fit signed INT8')
        scalar,out_type=(ct.c_int8,ct.c_int32) if integer else (ct.c_double,ct.c_double)
        a=(scalar*(m*k))(*(int(v) if integer else float(v) for row in left for v in row))
        b=(scalar*(k*n))(*(int(v) if integer else float(v) for row in right for v in row))
        out=(out_type*(m*n))()
        status=(self.lib.calix_dense_i8 if integer else self.lib.calix_dense_f64)(a,b,out,m,n,k,mode)
        if status<0:raise NativeUnsupported(f'Native matrix path unavailable or invalid ({status})')
        self.record_execution('matrix_product',('scalar','avx2','avx512','amx-int8')[status],self.lib.calix_last_threads() if not integer else 1)
        return [[out[i*n+j] for j in range(n)] for i in range(m)],('scalar','avx2','avx512','amx-int8')[status]

    def sparse_solve(self,matrix,rhs):
        import numpy as np
        if not self.sparse_runtime_loaded:
            from .components import ROOT
            folder=ROOT/'pde/native'
            runtime=folder/'mkl_rt.2.dll'
            if not runtime.is_file():
                raise ValueError('Parallel sparse solver is missing. Reinstall Calix and select PDE module.')
            directory=os.add_dll_directory(str(folder.resolve()))
            status=self.lib.calix_load_sparse_runtime(str(runtime.resolve()))
            if status:
                directory.close()
                raise ValueError('Parallel sparse solver runtime could not be loaded. Reinstall PDE module.')
            self.sparse_directories.append(directory)
            self.sparse_runtime_loaded=True
        a=matrix.tocoo()
        row=np.ascontiguousarray(a.row,dtype=np.int32)
        col=np.ascontiguousarray(a.col,dtype=np.int32)
        data=np.ascontiguousarray(a.data,dtype=np.float64)
        b=np.ascontiguousarray(rhs,dtype=np.float64)
        if matrix.shape!=(len(b),len(b)):raise ValueError('LinearSolve requires a square matrix and matching vector')
        out=np.empty_like(b);residual=ct.c_double()
        status=self.lib.calix_sparse_solve(len(b),len(data),row.ctypes.data_as(ct.POINTER(ct.c_int32)),col.ctypes.data_as(ct.POINTER(ct.c_int32)),data.ctypes.data_as(ct.POINTER(ct.c_double)),b.ctypes.data_as(ct.POINTER(ct.c_double)),out.ctypes.data_as(ct.POINTER(ct.c_double)),ct.byref(residual))
        if status:raise ValueError(f'C++ oneMKL PARDISO sparse solve failed ({status}); check constraints and conditioning')
        self.record_execution('sparse_solve','oneMKL PARDISO',self.lib.calix_last_threads())
        return out

    def fem_elements(self,points,cells,fields,order,coefficients):
        import numpy as np
        if not self.available:raise NativeUnsupported('The C++ finite-element kernel is not built')
        points=np.ascontiguousarray(points,dtype=np.float64)
        cells=np.ascontiguousarray(cells,dtype=np.int32)
        dimension=points.shape[1];local=cells.shape[1]*fields
        matrix=np.empty((len(cells),local,local));force=np.empty((len(cells),local))
        arrays=[np.ascontiguousarray(c,dtype=np.float64) for c in coefficients]+[matrix,force]
        triangular=dimension==2 and cells.shape[1]==3
        function=self.lib.calix_fem_triangles if triangular else self.lib.calix_fem_elements
        function.argtypes=[ct.c_int]*(4 if triangular else 5)+[ct.POINTER(ct.c_double),ct.POINTER(ct.c_int32)]+[ct.POINTER(ct.c_double)]*7
        function.restype=ct.c_int
        status=function(*([fields,len(points),len(cells),order] if triangular else [dimension,fields,len(points),len(cells),order]),
            points.ctypes.data_as(ct.POINTER(ct.c_double)),cells.ctypes.data_as(ct.POINTER(ct.c_int32)),
            *[a.ctypes.data_as(ct.POINTER(ct.c_double)) for a in arrays])
        if status:raise ValueError(f'C++ element integration failed ({status}); check mesh Jacobians and coefficients')
        self.record_execution('fem_assembly','C++ triangles' if triangular else 'C++ quadrilateral/hexahedral',self.lib.calix_last_threads())
        return matrix,force

    def compile(self, expr, variables):
        return self._compile(s.sympify(expr), tuple(variables))

    @lru_cache(maxsize=256)
    def _compile(self, expr, variables):
        if not self.available:
            raise NativeUnsupported("Native kernel is not built")
        ops, args = [], []
        functions = {s.sin: 20, s.cos: 21, s.tan: 22, s.exp: 23, s.log: 24,
                     s.Abs: 26, s.asin: 27, s.acos: 28, s.atan: 29, s.sinh: 30,
                     s.cosh: 31, s.tanh: 32, s.erf: 33, s.gamma: 34, s.floor: 35, s.ceiling: 36,
                     s.elliptic_k: 37, s.elliptic_e: 38}

        def emit(op, value=0):
            ops.append(op)
            args.append(value)

        def visit(e):
            if e in variables:
                index = variables.index(e)
                emit(index + 1 if index < 3 else 100 + index)
            elif e.is_number:
                try:
                    value = float(e)
                except (ValueError, TypeError):
                    raise NativeUnsupported("Real numerical expressions required") from None
                if not math.isfinite(value):
                    raise NativeUnsupported("Nonfinite numeric constant")
                emit(0, value)
            elif e.func in (s.Add, s.Mul):
                visit(e.args[0])
                for term in e.args[1:]:
                    visit(term)
                    emit(10 if e.func == s.Add else 12)
            elif e.func == s.Pow:
                visit(e.base)
                visit(e.exp)
                emit(14)
            elif e.func in functions:
                visit(e.args[0])
                emit(functions[e.func])
            else:
                raise NativeUnsupported(f"Native evaluation does not support {e.func}")

        visit(s.sympify(expr))
        if len(ops) > 4096:
            raise NativeUnsupported("Native expression instruction limit exceeded")
        return (ct.c_int32 * len(ops))(*ops), (ct.c_double * len(args))(*args), len(ops)

    def batch(self, expr, variables, coordinates):
        code = self.compile(expr, variables)
        count = len(coordinates[0])
        if len(variables) > 3:
            if len(variables) > 33 or len(coordinates) != len(variables) or any(len(column) != count for column in coordinates):
                raise NativeUnsupported('Native batch evaluation supports up to 33 coordinate columns')
            buffer = array('d', (value for row in zip(*coordinates) for value in row))
            inputs = (ct.c_double * len(buffer)).from_buffer(buffer)
            output = (ct.c_double * count)()
            status = self.lib.calix_batch_variables(*code, inputs, len(variables), count, output)
            if status: raise ValueError(f'Native batch evaluation failed ({status})')
            return list(output)
        buffers = [array("d", v) for v in coordinates]
        arrays = [(ct.c_double * count).from_buffer(v) for v in buffers]
        arrays += [None] * (3 - len(arrays))
        out = (ct.c_double * count)()
        status = self.lib.calix_batch(*code, *arrays, count, out)
        if status:
            raise ValueError(f"Native evaluation failed ({status})")
        return list(out)

    def root(self, expr, var, lo, hi, tolerance=1e-12):
        code = self.compile(expr, [var])
        result = ct.c_double()
        status = self.lib.calix_root(*code, lo, hi, tolerance, ct.byref(result))
        if status:
            raise ValueError("Root solving failed: provide a continuous real function and a sign-changing bracket")
        residual = self.batch(expr, [var], [[result.value]])[0]
        if not math.isfinite(residual) or abs(residual) > 1e-7:
            raise ValueError("Candidate root failed residual verification; possible discontinuity or poor scaling")
        return result.value

    @lru_cache(maxsize=2048)
    def projectile(self, coefficient, mass, speed, gravity, model, angle=0., optimize=False):
        output=(ct.c_double*3)()
        status=self.lib.calix_projectile(coefficient,mass,speed,gravity,model,angle,int(optimize),output)
        if status: raise ValueError('Projectile landing / angular optimization failed or exceeded its step limit')
        return tuple(output)

    def callback_root(self, function, lower, upper):
        failures=[]
        def call(x):
            try: return float(function(x))
            except Exception as exc:
                failures.append(exc)
                return math.nan
        callback=ROOT_CALLBACK(call)
        result=ct.c_double()
        status=self.lib.calix_callback_root(callback,lower,upper,ct.byref(result))
        if failures: raise ValueError(str(failures[0])) from failures[0]
        if status: raise ValueError('NSolve bracket needs finite values and opposite endpoint signs')
        residual=call(result.value)
        if not math.isfinite(residual) or abs(residual)>1e-6: raise ValueError('NSolve candidate failed residual verification')
        return result.value

    def extremum(self, expr, var, lo, hi, maximize=False):
        code = self.compile(expr, [var])
        location, value = ct.c_double(), ct.c_double()
        status = self.lib.calix_extremum(*code, lo, hi, int(maximize), ct.byref(location), ct.byref(value))
        if status:
            raise ValueError("Bounded Brent optimization failed; use a continuous finite real unimodal objective")
        return value.value, location.value

    def integrate(self, expr, var, lo, hi, tolerance=1e-10):
        code = self.compile(expr, [var])
        result, error = ct.c_double(), ct.c_double()
        status = self.lib.calix_integrate(*code, lo, hi, tolerance, ct.byref(result), ct.byref(error))
        if status:
            raise ValueError("Native quadrature failed: check bounds and singularities")
        if error.value > tolerance * max(1, abs(result.value)) * 10:
            raise ValueError("Quadrature did not meet the requested error tolerance")
        return result.value, error.value

    def ode(self, expr, time, state, lo, hi, initial, points=501):
        code = self.compile(expr, [time, state])
        ts, ys = (ct.c_double * points)(), (ct.c_double * points)()
        status = self.lib.calix_ode(*code, lo, hi, initial, points, 1e-9, ts, ys)
        if status:
            raise ValueError("Native ODE integration failed or exceeded its step limit")
        return list(ts), list(ys)

    def ode_pair(self, expressions, variables, lo, hi, initial, points=501):
        codes = [self.compile(expr, variables) for expr in expressions]
        output = (ct.c_double * (points * 8))()
        status = self.lib.calix_ode_pair(*codes[0], *codes[1], lo, hi, *initial, points, 1e-10, output)
        if status:
            raise ValueError("Coupled native ODE integration failed or exceeded its step limit")
        times = [lo + (hi - lo) * i / (points - 1) for i in range(points)]
        return times, [[output[i * 8 + j] for i in range(points)] for j in range(8)]

    def ode_system(self, expressions, variables, lo, hi, initial, points=1001):
        dimension = len(expressions)
        if not 1 <= dimension <= 32 or len(initial) != dimension or len(variables) != dimension + 1:
            raise ValueError('ODE systems support one to 32 first-order states')
        codes = [self.compile(expr, variables) for expr in expressions]
        ops, args, offsets = [], [], [0]
        for code_ops, code_args, size in codes:
            ops.extend(code_ops); args.extend(code_args); offsets.append(len(ops))
        output = (ct.c_double * (points*4*dimension))()
        status = self.lib.calix_ode_system((ct.c_int32*len(ops))(*ops), (ct.c_double*len(args))(*args),
            (ct.c_int32*len(offsets))(*offsets), dimension, lo, hi, (ct.c_double*dimension)(*initial), points, 1e-10, output)
        if status:
            raise ValueError('Native ODE system integration failed or exceeded its step limit')
        times = [lo+(hi-lo)*i/(points-1) for i in range(points)]
        return times, [[output[i*4*dimension+j] for i in range(points)] for j in range(4*dimension)]


kernel = NativeKernel()
