"""Symbolic dispatcher and the supported Wolfram-language subset."""
import json
import math
import time
from functools import reduce
import operator
import builtins
import pint
import sympy as s
from sympy.core.function import AppliedUndef
from .presentation import expression_latex, expression_text
from .syntax import InputError, Node, parse
from .units import quantity, unit_text, dimensionless, format_quantity, simplify_quantity, unit_label
from .native import kernel, NativeUnsupported
from . import statistics
from .interpolation import SampledFunction, SampledDerivative, interpolate, interpolate_derivative
from .linear_ode import normal_modes
from .ode_system import solve as solve_ode_system
from .iteration import table, list_call, NOTHING
from .graphics import graphics, frames as graphics_frames
from .components import pde_module


FUNCTIONS = {
    "Sin": s.sin, "Cos": s.cos, "Tan": s.tan, "ArcSin": s.asin, "ArcCos": s.acos,
    "ArcTan": s.atan, "Sinh": s.sinh, "Cosh": s.cosh, "Tanh": s.tanh,
    "Exp": s.exp, "Sqrt": s.sqrt, "Abs": s.Abs, "Re": s.re, "Im": s.im,
    "Conjugate": s.conjugate, "Floor": s.floor, "Ceiling": s.ceiling,
    "Gamma": s.gamma, "Beta": s.beta, "Erf": s.erf, "Erfc": s.erfc,
    "BesselJ": s.besselj, "BesselY": s.bessely, "BesselI": s.besseli, "BesselK": s.besselk,
    "AiryAi": s.airyai, "AiryBi": s.airybi, "EllipticK": s.elliptic_k,
    "EllipticE": s.elliptic_e, "Zeta": s.zeta, "PolyLog": s.polylog,
    "Pochhammer": s.rf, "LaguerreL": lambda *args: s.laguerre(*args) if len(args) == 2 else s.assoc_laguerre(*args),
    "LegendreP": lambda *args: s.legendre(*args) if len(args) == 2 else s.assoc_legendre(*args),
    "Factorial": s.factorial, "Binomial": s.binomial, "Sign": s.sign,
    "Min": s.Min, "Max": s.Max,
}
CONSTANTS = {"Pi": s.pi, "E": s.E, "I": s.I, "Infinity": s.oo,
             "EulerGamma": s.EulerGamma, "True": s.true, "False": s.false,
             "Reals": s.S.Reals, "Complexes": s.S.Complexes, "Integers": s.S.Integers, "Nothing": NOTHING}
PLOTS = {"Plot", "Plot1D", "Plot2D", "DensityPlot", "Plot3D", "ContourPlot", "ParametricPlot", "ParametricPlot3D"}


def symbol(name):
    if name.startswith("_") or "__" in name:
        raise InputError("Identifiers beginning with _ or containing __ are reserved")
    return s.Symbol(name)


def as_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("A finite real value is required")
    return result


def safe_float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


class Engine:
    def __init__(self):
        self.environment = {}
        self.assumptions = s.true
        self.route = "SymPy"

    def execute(self, source):
        start = time.perf_counter()
        self.route = "SymPy"
        kernel.reset_execution()
        result = self.evaluate(parse(source))
        elapsed = (time.perf_counter() - start) * 1000
        return {**self.format_result(result, elapsed),'execution':kernel.execution}

    def format_result(self, result, elapsed=0):
        if isinstance(result, dict) and result.get('kind') == 'labeled':
            return {**self.format_result(result['value'], elapsed), 'label': result['label']}
        if isinstance(result, dict) and result.get("kind") == "group":
            return {**result, "items": [self.format_result(item) for item in result["items"]],
                    "elapsed_ms": round(elapsed, 2), "engine": self.route}
        if isinstance(result, dict) and result.get("kind") in ("plot", "animation"):
            return {**result, "elapsed_ms": round(elapsed, 2), "engine": self.route}
        if (type(result).__module__ or '').startswith(('numpy','scipy')):
            from calix_pde.language import format_array
            return self.format_result(format_array(result),elapsed)
        if (type(result).__module__ or '').startswith(('calix_pde','backend.lattice')) and hasattr(result, 'summary'):
            text, latex = result.summary()
            text = next((key for key,value in self.environment.items() if value is result), text)
            return {'kind':'expression','text':text,'latex':latex,'elapsed_ms':round(elapsed,2),'engine':self.route}
        if isinstance(result, pint.Quantity):
            text, latex = format_quantity(result)
        elif isinstance(result, list):
            if any(isinstance(item,dict) and item.get('kind') in ('plot','animation','labeled','group') for item in result):
                return self.format_result({'kind':'group','items':result},elapsed)
            parts = [self.format_result(item) for item in result]
            text = '{'+', '.join(part['text'] for part in parts)+'}'
            latex = r'\left\{'+', '.join(part['latex'] for part in parts)+r'\right\}'
        elif result is None:
            text, latex = "Null", ""
        elif isinstance(result, str):
            text, latex = result, s.latex(result)
        else:
            latex = expression_latex(result)
            try:
                text = expression_text(result)
            except (TypeError, NotImplementedError, AttributeError):
                text = str(result)
        unresolved = isinstance(result, s.Basic) and result.has(s.Integral, s.Sum, s.Product, s.Derivative)
        if isinstance(result, list):
            unresolved = any(part.get('unresolved', False) for part in parts)
        expression = result.rhs if isinstance(result, s.Equality) else result
        symbolic_functions = sorted({str(fn.func) for fn in expression.atoms(AppliedUndef)}) if isinstance(expression, s.Basic) else []
        if isinstance(result, list):
            symbolic_functions = sorted({name for part in parts for name in part.get('symbolic_functions', [])})
        # A named symbolic function is legal input, but its display is not evidence of a solver result.
        status = 'unevaluated' if unresolved else 'symbolic' if symbolic_functions else 'evaluated'
        return {"kind": "expression", "text": text, "latex": latex,
                "elapsed_ms": round(elapsed, 2), "engine": self.route,
                "unresolved": bool(unresolved), "evaluation_status": status,
                "symbolic_functions": symbolic_functions, "variables": sorted(self.environment)}

    def evaluate(self, node):
        kind, value, children = node.kind, node.value, node.args
        if kind == "number":
            return s.Float(value, 16) if any(c in value for c in ".eE") else s.Integer(value)
        if kind == "string":
            return value
        if kind == "symbol":
            if value in CONSTANTS:
                return CONSTANTS[value]
            if value in self.environment:
                return self.environment[value]
            return symbol(value)
        if kind == "group":
            return self.evaluate(children[0])
        if kind == "null":
            return None
        if kind == "list":
            return [self.evaluate(child) for child in children]
        if kind == "sequence":
            result = None
            for child in children:
                result = self.evaluate(child)
            return result
        if kind == 'program':
            outputs = []
            for child in children:
                result = self.evaluate(child)
                if result is not None:
                    outputs.append(result)
                if len(outputs) > 40:
                    raise InputError('A calculation cell supports up to 40 visible results')
            if not outputs:
                return None
            return outputs[0] if len(outputs) == 1 else {'kind': 'group', 'items': outputs}
        if kind == "unary":
            result = self.evaluate(children[0])
            return -result if value == "-" else result
        if kind == "postfix":
            if value == "°":
                return self.evaluate(children[0]) * s.pi / 180
            if value == "!":
                return s.factorial(self.evaluate(children[0]))
            raise InputError("Derivative notation must be followed by an argument, for example y'[x]")
        if kind == "binary":
            if value == "=":
                lhs = children[0]
                if lhs.kind != "symbol" or lhs.value in CONSTANTS or lhs.value in FUNCTIONS:
                    raise InputError("Assignment requires an unreserved variable name")
                result = self.evaluate(children[1])
                self.environment[lhs.value] = result
                return result
            a, b = (self.evaluate(c) for c in children)
            if value=='==' and hasattr(a,'equation') and callable(a.equation):return a.equation(b)
            if (type(a).__module__ or '').startswith(('numpy','scipy')) and isinstance(b,s.Number):b=float(b)
            if (type(b).__module__ or '').startswith(('numpy','scipy')) and isinstance(a,s.Number):a=float(a)
            if value in ('==','!=','<','>','<=','>=') and (isinstance(a,pint.Quantity) or isinstance(b,pint.Quantity)):
                difference = a-b
                a,b = s.sympify(difference.magnitude), s.Integer(0)
            operations = {"+": operator.add, "-": operator.sub, "*": operator.mul,
                          "/": operator.truediv, "^": operator.pow, "==": s.Eq,
                          "!=": s.Ne, "<": s.Lt, ">": s.Gt, "<=": s.Le, ">=": s.Ge,
                          "&&": s.And, "||": s.Or, "->": lambda x, y: (x, y)}
            if value in ('+', '-', '*', '/', '^') and any((type(item).__module__ or '').startswith('numpy') for item in (a, b)):
                import numpy as np
                if isinstance(a, list):a = np.asarray(a, dtype=float)
                if isinstance(b, list):b = np.asarray(b, dtype=float)
                return operations[value](a, b)
            if value in ('+', '-', '*', '/', '^') and (isinstance(a, list) or isinstance(b, list)):
                def threaded(left, right):
                    if isinstance(left, list) and isinstance(right, list):
                        if len(left) != len(right):
                            raise InputError('List arithmetic requires matching dimensions')
                        return [threaded(x, y) for x, y in zip(left, right)]
                    if isinstance(left, list):return [threaded(x, right) for x in left]
                    if isinstance(right, list):return [threaded(left, y) for y in right]
                    return operations[value](left, right)
                return threaded(a, b)
            result = operations[value](a, b)
            return simplify_quantity(result) if isinstance(result, pint.Quantity) else result
        if kind == "call":
            target, *arguments = children
            if target.kind=='symbol' and target.value in self.environment and callable(self.environment[target.value]):
                return self.environment[target.value](*[self.evaluate(a) for a in arguments])
            if target.kind == "postfix" and target.value == "'":
                order = 0
                while target.kind == "postfix" and target.value == "'":
                    order += 1
                    target = target.args[0]
                if target.kind != "symbol" or len(arguments) != 1:
                    raise InputError("Use y'[x] or y''[x] for function derivatives")
                x = self.evaluate(arguments[0])
                if isinstance(x, s.Symbol):
                    return s.diff(s.Function(target.value)(x), x, order)
                variable = s.Dummy("argument")
                return s.Subs(s.diff(s.Function(target.value)(variable), variable, order), variable, x)
            if target.kind != "symbol":
                candidate=self.evaluate(target)
                if callable(candidate):return candidate(*[self.evaluate(a) for a in arguments])
                if len(arguments) != 1:
                    raise InputError("A unit suffix requires exactly one unit expression")
                result = quantity(candidate, unit_text(arguments[0]))
                return simplify_quantity(result)
            name = target.value
            if isinstance(self.environment.get(name), (SampledFunction, SampledDerivative)):
                if len(arguments) != 1:
                    raise InputError('An interpolating function takes one argument')
                return self.environment[name]._at(self.evaluate(arguments[0]))
            if len(arguments) == 1 and ((name in self.environment and isinstance(self.environment[name], (s.Expr, pint.Quantity, list))) or (name[0].islower() and arguments[0].kind == 'string')):
                unit = unit_text(arguments[0])
                def attach(value):
                    return [attach(item) for item in value] if isinstance(value, list) else simplify_quantity(quantity(value, unit))
                return attach(self.environment.get(name, symbol(name)))
            if name in PLOTS:
                return self.plot(name, arguments)
            return self.call(name, arguments)
        raise InputError(f"Unsupported expression {kind}")

    def scoped(self, nodes, variables):
        previous = self.environment.copy()
        try:
            for var in variables:
                self.environment.pop(str(var), None)
            return [self.evaluate(node) for node in nodes]
        finally:
            self.environment = previous

    def call(self, name, nodes):
        if name=='Block':
            if len(nodes)!=2 or nodes[0].kind!='list':raise InputError('Use Block[{local symbols}, expression]')
            if any(node.kind!='symbol' for node in nodes[0].args):raise InputError('Block local declarations must be symbols')
            names=[node.value for node in nodes[0].args]
            previous={key:self.environment[key] for key in names if key in self.environment}
            try:
                for key in names:self.environment.pop(key,None)
                return self.evaluate(nodes[1])
            finally:
                for key in names:self.environment.pop(key,None)
                self.environment.update(previous)
        if name=='LatticeGaugeSimulation':
            from .lattice import simulate
            self.route='C++ / SU(3) Wilson gauge action, Metropolis'
            return simulate([self.evaluate(node) for node in nodes])
        from . import arrayops
        if name in arrayops.FUNCTIONS:
            return arrayops.call(name,[self.evaluate(node) for node in nodes])
        if name in ('FluidFlowPDEComponent','DirichletCondition','Element','Polygon','RegionDistance'):
            pde_module()
            from calix_pde.fluid_language import call
            return call(self,name,nodes)
        if name=='StreamPlot':
            pde_module()
            from calix_pde.fluid_language import streamplot
            return streamplot(self,nodes)
        if name=='NDSolveValue' and len(nodes)>=3 and nodes[2].kind=='call' and nodes[2].args[0].value=='Element':
            pde_module()
            from calix_pde.fluid_language import solve
            coordinates=nodes[2].args[1]
            bound=[symbol(n.value) for n in [*coordinates.args,*nodes[1].args] if n.kind=='symbol']
            args=self.scoped(nodes,bound)
            if len(args)>3:raise InputError('Additional fluid NDSolve options are not supported yet')
            self.route='C++ / oneMKL PARDISO; quadrilateral Q2/Q1 finite elements'
            return solve(*args)
        if name in ('ToElementMesh','BoundaryMeshRegion','TriangleElement','QuadElement','HexahedronElement','LineElement','NDSolve`VariableData','NDSolve`SolutionData','InitializePDECoefficients','InitializePDEMethodData','DiscretizePDE','SparseArray','LinearSolve','Nearest','ArrayFlatten','Association'):
            pde_module()
            from calix_pde.language import call
            self.route='C++ / oneMKL PARDISO + finite-element assembly'
            return call(self,name,nodes)
        if name in ('ProjectileRange','ProjectileMaxRange','ProjectileOptimum','ProjectileVelocity'):
            from .projectile import dispatch
            self.route='C++ / Boost projectile event integration and angular Brent'
            variables=[symbol(nodes[5].args[0].value)] if name=='ProjectileVelocity' and len(nodes)==7 and nodes[5].kind=='list' and nodes[5].args and nodes[5].args[0].kind=='symbol' else []
            result=dispatch(name,self.scoped(nodes,variables))
            if name=='ProjectileVelocity' and nodes[-1].value=='Linear': self.route='Exact exponential linear-drag solution'
            return result
        if name in ('PDEInfo','PDEPlot','PDEValue','FEMBridgeSolve','WingFlowSolve','NDEigensystem'):
            module = pde_module()
            variables = []
            if name == 'NDEigensystem':
                variables = [symbol(node.args[0].value) for node in nodes[2:4] if node.kind == 'list' and node.args and node.args[0].kind == 'symbol']
            args = self.scoped(nodes, variables)
            self.route = 'PDE / scikit-fem + C++ oneMKL PARDISO / native ARPACK'
            return module.dispatch(name, args)
        if name in ('Laplacian', 'Grad', 'Div'):
            if len(nodes) != 2 or nodes[1].kind != 'list' or any(n.kind != 'symbol' for n in nodes[1].args):
                raise InputError(f'Use {name}[expression,{{x,y,...}}]')
            variables = [symbol(n.value) for n in nodes[1].args]
            expr, variables = self.scoped(nodes, variables)
            if name == 'Grad': return [s.diff(expr,var) for var in variables]
            if name == 'Div':
                if not isinstance(expr,list) or len(expr)!=len(variables): raise InputError('Div needs one vector component per coordinate')
                return s.Add(*(s.diff(e,var) for e,var in zip(expr,variables)))
            return s.Add(*(s.diff(expr,var,2) for var in variables))
        if name in ('NBodySolve','NBodyPlot3D','MagneticFieldPlot3D'):
            from .field_scenes import nbody, gravity_scene, magnetic_scene
            if name == 'NBodySolve' and len(nodes) != 4:
                raise InputError('Use NBodySolve[masses,positions,velocities,{t,lower,upper}]')
            variables=[]
            if nodes and nodes[-1].kind=='list' and nodes[-1].args and nodes[-1].args[0].kind=='symbol':
                variables=[symbol(nodes[-1].args[0].value)]
            args=self.scoped(nodes,variables)
            self.route='C++ / Dormand-Prince many-body ODE'
            return nbody(*args) if name=='NBodySolve' else gravity_scene(self,args) if name=='NBodyPlot3D' else magnetic_scene(self,args)
        if name == 'Labeled':
            if len(nodes) != 2:
                raise InputError('Labeled expects an expression and a text label')
            label = self.evaluate(nodes[1])
            if not isinstance(label, str) or not 1 <= len(label) <= 240:
                raise InputError('A label must contain 1 to 240 characters')
            return {'kind': 'labeled', 'value': self.evaluate(nodes[0]), 'label': label}
        if name in ('ColorData','BarLegend','Legended'):
            from .scientific3d import decoration
            return decoration(self,name,nodes)
        if name in ('DensityPlot3D', 'Graphics3D'):
            from .scientific3d import volume, graphics3d
            return (volume if name == 'DensityPlot3D' else graphics3d)(self, nodes)
        if name == "Animate":
            return self.animate(nodes)
        if name == 'Graphics':
            return self.graphics(nodes)
        if name == 'Table':
            return table(self, nodes)
        if name == 'If':
            if len(nodes) not in (2, 3):
                raise InputError('If expects a condition, a true branch and an optional false branch')
            condition = self.evaluate(nodes[0])
            if condition not in (s.true, s.false):
                raise InputError('If condition must evaluate to True or False')
            return self.evaluate(nodes[1] if condition == s.true else nodes[2]) if condition == s.true or len(nodes) == 3 else None
        if name == "DSolveValue":
            solution = self.call("DSolve", nodes)
            equations = solution if isinstance(solution, list) else [solution]
            functions = self.evaluate(nodes[1])
            requested = functions if isinstance(functions, list) else [functions]
            rules = {eq.lhs: eq.rhs for eq in equations}
            values = [rules[fn] for fn in requested]
            return values if nodes[1].kind == "list" else values[0]
        if name == "Clear":
            for node in nodes:
                if node.kind != "symbol":
                    raise InputError("Clear expects variable names")
                self.environment.pop(node.value, None)
            return None
        if name == "Assuming":
            if len(nodes) != 2:
                raise InputError("Assuming[condition, expression] expects two arguments")
            old = self.assumptions
            try:
                condition = self.evaluate(nodes[0])
                def predicates(c):
                    if c.func == s.And:
                        return s.And(*(predicates(a) for a in c.args))
                    if isinstance(c, (s.StrictGreaterThan, s.GreaterThan)) and c.rhs == 0:
                        return s.Q.positive(c.lhs) if isinstance(c, s.StrictGreaterThan) else s.Q.nonnegative(c.lhs)
                    if isinstance(c, (s.StrictLessThan, s.LessThan)) and c.rhs == 0:
                        return s.Q.negative(c.lhs) if isinstance(c, s.StrictLessThan) else s.Q.nonpositive(c.lhs)
                    return c
                self.assumptions = s.And(old, predicates(condition))
                with s.assuming(self.assumptions):
                    return s.refine(self.evaluate(nodes[1]), self.assumptions)
            finally:
                self.assumptions = old
        if name in ("D", "Integrate", "Sum", "Product", "Limit", "Series", "NIntegrate", "FindRoot", "Solve", "SolveValues", "NSolve", "Reduce", "CoefficientList", "DSolve", "RSolve", "NDSolve", "NDSolveValue", "Minimize", "Maximize", "FindMinimum", "FindMaximum", "Fit"):
            bound = []
            for node in nodes[1:]:
                if node.kind == "symbol" and node.value not in CONSTANTS:
                    bound.append(symbol(node.value))
                elif node.kind == "list" and node.args:
                    first = node.args[0]
                    if first.kind == "symbol":
                        bound.append(symbol(first.value))
                    if name in ("Solve", "NSolve", "SolveValues", "CoefficientList", "DSolve", "DSolveValue"):
                        bound.extend(symbol(n.value) for n in node.args if n.kind == "symbol")
            args = self.scoped(nodes, bound)
        else:
            args = [self.evaluate(node) for node in nodes]
        if name=='Total' and args and isinstance(args[0],list) and args[0] and (type(args[0][0]).__module__ or '').startswith(('numpy','scipy')):
            return reduce(operator.add,args[0])
        if name in statistics.NAMES:
            return statistics.dispatch(name, args)
        if name in ('Flatten', 'IntegerQ', 'Mod', 'Accumulate', 'Count', 'Permutations', 'Intersection'):
            return list_call(name, args)
        if name == 'Join':
            if any(not isinstance(value, list) for value in args):
                raise InputError('Join expects lists')
            return [item for value in args for item in value]
        if name == "Column":
            if len(args) != 1 or not isinstance(args[0], list) or not 1 <= len(args[0]) <= 40:
                raise InputError("Column expects a list of 1 to 40 results")
            return {"kind": "group", "items": args[0]}
        if name == 'Show':
            if len(args)>=2 and isinstance(args[0],dict) and args[0].get('plot_type')=='density' and all(isinstance(a,dict) and a.get('plot_type')=='curve' for a in args[1:]):
                traces=[trace for a in args[1:] for trace in a['traces']]
                if len(traces)>20:raise InputError('Show supports at most 20 overlay traces')
                return {**args[0],'title':'Show','traces':traces,'options':{**args[0].get('options',{}),'equal_aspect':True,'legend':False}}
            if 2<=len(args)<=10 and all(isinstance(a,dict) and a.get('plot_type')=='geometry3d' for a in args):
                primitives=[p for a in args for p in a['primitives']]
                if len(primitives)>48000:raise InputError('Show supports at most 48,000 spatial primitives')
                return {**args[0],'title':'Show','primitives':primitives}
            if not 2 <= len(args) <= 10 or any(not isinstance(a,dict) or a.get('plot_type')!='curve' for a in args):
                raise InputError('Show supports two to ten 2D curve or data plots')
            traces=[trace for plot in args for trace in plot['traces']]
            if len(traces)>20:
                raise InputError('Show supports at most 20 traces')
            return {**args[0],'title':'Show','traces':traces}
        if name in ("Part", "First", "Last"):
            if args and hasattr(args[0],'parts'):
                args[0]=args[0].parts()
            if args and (type(args[0]).__module__ or '').startswith(('numpy','scipy')):
                from calix_pde.language import part
                return part(args[0],args[1:] if name=='Part' else [1 if name=='First' else -1])
            if not args or not isinstance(args[0], (list, s.MatrixBase)):
                raise InputError(f"{name} expects a list")
            value = args[0].tolist() if isinstance(args[0], s.MatrixBase) else args[0]
            indices = [s.Integer(1)] if name == 'First' else [s.Integer(-1)] if name == 'Last' else args[1:]
            if not indices:
                raise InputError('Part expects one or more indices')
            for raw in indices:
                if not isinstance(raw, (int,s.Integer)) or isinstance(raw,bool) or not isinstance(value, list):
                    raise InputError('Part indices must be integers into lists')
                index = int(raw)
                if index == 0 or not -len(value) <= index <= len(value):
                    raise InputError('List index is out of range')
                value = value[index-1 if index > 0 else index]
            return value
        if name in FUNCTIONS:
            if name in ('Min', 'Max'):
                def extrema_items(values):
                    for value in values:
                        if hasattr(value, 'tolist'):
                            value = value.tolist()
                        if isinstance(value, list):
                            yield from extrema_items(value)
                        else:
                            yield value
                args = list(extrema_items(args))
                if args and all(isinstance(a, (int, float, s.Number)) and s.sympify(a).is_extended_real is True for a in args):
                    return s.sympify((builtins.min if name == 'Min' else builtins.max)(args))
            if name == "Factorial" and args and args[0].is_Integer and args[0] > 100000:
                raise InputError("Exact factorial is limited to 100,000; use a smaller argument")
            if name in ("Sin", "Cos", "Tan"):
                args = [dimensionless(a, angle=True) for a in args]
            else:
                args = [dimensionless(a) for a in args]
            if name == 'ArcTan' and len(args) == 2:
                return s.atan2(args[1],args[0])
            return FUNCTIONS[name](*args)
        if name == "Log":
            values = [dimensionless(a) for a in args]
            return s.log(values[0]) if len(values) == 1 else s.log(values[1], values[0])
        if name == "N":
            digits = int(args[1]) if len(args) > 1 else 16
            if digits < 2 or digits > 1000:
                raise InputError("Precision must be between 2 and 1000 digits")
            if isinstance(args[0], pint.Quantity):
                return quantity(s.N(args[0].magnitude, digits), args[0].units)
            def approximate(value):
                return [approximate(item) for item in value] if isinstance(value, list) else s.N(value, digits)
            return approximate(args[0])
        if name in ("Simplify", "FullSimplify"):
            def simplify(value):
                return [simplify(item) for item in value] if isinstance(value, list) else s.refine(s.simplify(value), self.assumptions)
            return simplify(args[0])
        if name == "Expand":
            return s.expand(*args)
        if name=='PowerExpand':return s.powsimp(s.expand_power_base(s.expand(args[0]),force=True),force=True)
        if name=='Coefficient':return s.expand(args[0]).coeff(args[1],int(args[2]) if len(args)>2 else 1)
        if name == "Factor":
            return s.factor(*args)
        if name in ('TrigExpand', 'ComplexExpand'):
            if len(args) != 1 or not isinstance(args[0], s.Expr):
                raise InputError(f'{name} expects one scalar expression')
            if name == 'TrigExpand':
                return s.expand_trig(args[0])
            real_variables = {var: s.Dummy(str(var), real=True) for var in args[0].free_symbols}
            expanded = s.expand_complex(args[0].xreplace(real_variables))
            return expanded.xreplace({value: key for key, value in real_variables.items()})
        if name == "Together":
            return s.together(*args)
        if name == "Cancel":
            return s.cancel(*args)
        if name in ('Numerator', 'Denominator'):
            if len(args) != 1 or not isinstance(args[0], s.Expr):
                raise InputError(f'{name} expects one scalar expression')
            return s.fraction(args[0])[0 if name == 'Numerator' else 1]
        if name == 'CoefficientList':
            if len(args) != 2:
                raise InputError('Use CoefficientList[polynomial, variable or {variables}]')
            variables = args[1] if isinstance(args[1], list) else [args[1]]
            if not variables or any(not isinstance(var, s.Symbol) for var in variables) or len(set(variables)) != len(variables):
                raise InputError('CoefficientList requires distinct variables')
            try:
                polynomial = s.Poly(args[0], *variables)
            except s.PolynomialError:
                raise InputError('CoefficientList requires a polynomial in the requested variables') from None
            degrees = [max(0, int(degree)) if degree != -s.oo else 0 for degree in polynomial.degree_list()]
            if math.prod(degree+1 for degree in degrees) > 100000:
                raise InputError('CoefficientList is limited to 100,000 coefficients')
            def coefficients(powers):
                if len(powers) == len(variables):
                    return polynomial.coeff_monomial(tuple(powers))
                return [coefficients(powers+[power]) for power in range(degrees[len(powers)]+1)]
            return coefficients([])
        if name in ('PowerMod', 'IntegerLength', 'GCD'):
            if any(not isinstance(value, s.Integer) for value in args):
                raise InputError(f'{name} requires integer arguments')
            if name == 'PowerMod':
                if len(args) != 3 or args[1] < 0 or args[2] <= 0:
                    raise InputError('Use PowerMod[integer, nonnegative exponent, positive modulus]')
                return s.Integer(pow(int(args[0]), int(args[1]), int(args[2])))
            if name == 'GCD':
                if not args:
                    raise InputError('GCD requires integer arguments')
                return s.Integer(math.gcd(*(int(value) for value in args)))
            if len(args) not in (1, 2) or (len(args) == 2 and args[1] < 2):
                raise InputError('Use IntegerLength[integer, optional base >= 2]')
            number, base = abs(int(args[0])), int(args[1]) if len(args) == 2 else 10
            digits = 1
            while number >= base:
                number //= base
                digits += 1
            return s.Integer(digits)
        if name == 'Reduce':
            if len(args) not in (2, 3) or not isinstance(args[1], s.Symbol) or (len(args) == 3 and args[2] != s.S.Reals):
                raise InputError('Reduce currently supports one real variable: Reduce[conditions, x, Reals]')
            conditions = args[0] if isinstance(args[0], list) else list(args[0].args) if isinstance(args[0], s.And) else [args[0]]
            if any(condition.free_symbols - {args[1]} for condition in conditions):
                raise InputError('Assign all parameters before using one-variable Reduce')
            try:
                return s.reduce_inequalities(conditions, args[1])
            except (NotImplementedError, ValueError, TypeError):
                raise InputError('Reduce could not determine this real inequality exactly') from None
        if name == "D":
            return s.diff(args[0], *[tuple(a) if isinstance(a, list) else a for a in args[1:]])
        if name == "Integrate":
            limits = [tuple(a) if isinstance(a, list) else a for a in args[1:]]
            integration_unit=None
            if len(limits)==1 and isinstance(limits[0],tuple) and len(limits[0])==3:
                var,lower,upper=limits[0]
                integration_unit=next((a.units for a in (lower,upper) if isinstance(a,pint.Quantity)),None)
                if integration_unit is not None:
                    limits=[(var,*[s.sympify(a.to(integration_unit).magnitude) if isinstance(a,pint.Quantity) else a for a in (lower,upper)])]
            def integral(expr):
                if isinstance(expr,pint.Quantity):
                    return simplify_quantity(quantity(integral(expr.magnitude),expr.units*(integration_unit or quantity(1,'').units)))
                if isinstance(expr, SampledFunction):
                    if len(limits) != 1 or not isinstance(limits[0], tuple) or len(limits[0]) != 3:
                        raise InputError("Numerical solutions require Integrate[v,{t,initialTime,endTime}]")
                    return expr.integral(*limits[0])
                return s.integrate(expr, *limits)
            return [integral(expr) for expr in args[0]] if isinstance(args[0], list) else integral(args[0])
        if name in ("Sum", "Product"):
            return (s.summation if name == "Sum" else s.product)(args[0], *[tuple(a) for a in args[1:]])
        if name == "Limit":
            if len(args) != 2 or not isinstance(args[1], tuple):
                raise InputError("Use Limit[expression, x -> value]")
            return s.limit(args[0], *args[1])
        if name == "Series":
            x, at, order = args[1]
            return s.series(args[0], x, at, int(order) + 1)
        if name == "Normal":
            return args[0].removeO() if hasattr(args[0], "removeO") else args[0]
        if name in ("Solve", "NSolve", "SolveValues"):
            equations, variables = args[:2]
            if name=='NSolve' and isinstance(variables,list) and len(variables)==3 and isinstance(variables[0],s.Symbol) and all(getattr(v,'is_number',False) for v in variables[1:]):
                from .projectile import DragRange
                expr=equations.lhs-equations.rhs if isinstance(equations,s.Equality) else equations
                var,lo,hi=variables
                if not isinstance(expr,s.Expr) or expr.free_symbols-{var}: raise InputError('Bracketed NSolve requires one real variable with assigned parameters')
                fn=s.lambdify(var,expr,modules=[{'DragRange':DragRange._imp_},'math'])
                self.route='C++ / Boost TOMS 748 bracketed NSolve'
                return [s.Eq(var,s.Float(kernel.callback_root(fn,float(lo),float(hi)))),]
            domain = args[2] if len(args) > 2 else s.S.Complexes
            if domain not in (s.S.Complexes, s.S.Reals, s.S.Integers):
                raise InputError("Supported domains: Reals, Complexes, Integers")
            if name != 'SolveValues' and not isinstance(equations, list) and not isinstance(variables, list):
                result = s.solveset(equations, variables, domain=domain)
                if name == "NSolve":
                    if not isinstance(result, s.FiniteSet):
                        raise InputError("NSolve currently supports finite solution sets; use FindRoot with a bracket")
                    return [s.N(x) for x in result]
                return result
            if domain != s.S.Complexes:
                raise InputError("Domain restrictions for systems are not implemented yet")
            result = s.solve(equations, variables, dict=True)
            if name == 'SolveValues':
                requested = variables if isinstance(variables, list) else [variables]
                if any(any(var not in row for var in requested) for row in result):
                    raise InputError('SolveValues requires determined values for every requested variable')
                return [[row[var] for var in requested] for row in result] if isinstance(variables, list) else [row[variables] for row in result]
            return [{k: s.N(v) for k, v in sol.items()} for sol in result] if name == "NSolve" else result
        if name == "FindRoot":
            expr = args[0].lhs - args[0].rhs if isinstance(args[0], s.Equality) else args[0]
            if not isinstance(args[1], list) or len(args[1]) != 3:
                raise InputError("Use FindRoot[f[x], {x, lower, upper}] with a sign-changing bracket")
            var, lo, hi = args[1]
            self.route = "C++ / Boost TOMS 748"
            return s.Float(kernel.root(expr, var, as_float(lo), as_float(hi)))
        if name == "NIntegrate":
            if len(args) != 2 or len(args[1]) != 3:
                raise InputError("Use NIntegrate[f[x], {x, finiteLower, finiteUpper}]")
            var, lo, hi = args[1]
            self.route = "C++ / Boost Gauss-Kronrod 61"
            value, _ = kernel.integrate(args[0], var, as_float(lo), as_float(hi))
            return s.Float(value)
        if name in ("Minimize", "Maximize", "FindMinimum", "FindMaximum"):
            if len(args) != 2:
                raise InputError(f"Use {name}[expression, {{variable, lower, upper}}]")
            objective, spec = args
            bounded = isinstance(spec, list) and len(spec) == 3
            if not bounded and not isinstance(spec, s.Symbol):
                raise InputError("Optimization expects a variable or {variable, lower, upper}")
            var = spec[0] if bounded else spec
            if not isinstance(var, s.Symbol) or objective.free_symbols - {var}:
                raise InputError("Optimization currently supports one real variable with assigned parameters")
            maximize = name in ("Maximize", "FindMaximum")
            if name.startswith("Find"):
                if not bounded:
                    raise InputError("Numerical extrema require finite bounds and a continuous unimodal objective")
                value, at = kernel.extremum(objective, var, as_float(spec[1]), as_float(spec[2]), maximize)
                self.route = "C++ / Boost bounded Brent"
                return [s.Float(value), {var: s.Float(at)}]
            domain = s.Interval(spec[1], spec[2]) if bounded else s.S.Reals
            if bounded and not spec[1] < spec[2]:
                raise InputError("Optimization bounds must increase")
            value = (s.maximum if maximize else s.minimum)(objective, var, domain)
            locations = s.solveset(objective - value, var, domain=domain) if value.is_finite else s.EmptySet
            at = next(iter(locations)) if isinstance(locations, s.FiniteSet) and locations else None
            if objective == value:
                at = spec[1] if bounded else s.Integer(0)
            return [value, {var: at} if at is not None else {}]
        if name == "DSolve":
            if len(args) == 3 and isinstance(args[2], list):
                self.route = 'PDE / SymPy analytical separation'
                return pde_module().analytic(*args)
            equations = args[0] if isinstance(args[0], list) else [args[0]]
            differential, initial = [], {}
            for eq in equations:
                if isinstance(eq, s.Equality) and isinstance(eq.lhs, s.Subs):
                    if len(eq.lhs.variables) != 1 or len(args) < 3:
                        raise InputError("Derivative initial conditions require a single independent variable")
                    var = args[2]
                    derivative = eq.lhs.expr.xreplace({eq.lhs.variables[0]: var})
                    initial[s.Subs(derivative, var, eq.lhs.point[0])] = eq.rhs
                elif isinstance(eq, s.Equality) and (eq.lhs.has(s.Derivative) or eq.rhs.has(s.Derivative)):
                    differential.append(eq)
                elif isinstance(eq, s.Equality):
                    initial[eq.lhs] = eq.rhs
                else:
                    raise InputError("DSolve requires differential equations and optional initial conditions")
            if not differential:
                raise InputError("No differential equation found")
            modal = normal_modes(differential, args[1], args[2], initial) if len(args) == 3 else None
            if modal is not None:
                self.route = 'SymPy / exact normal modes'
                return modal
            return s.dsolve(differential[0] if len(differential) == 1 else differential,
                            args[1], ics=initial or None)
        if name == "RSolve":
            equations = args[0] if isinstance(args[0], list) else [args[0]]
            fn, n = args[1:3]
            recurrence, initial = None, {}
            for eq in equations:
                if not isinstance(eq, s.Equality):
                    raise InputError("RSolve requires equations")
                if eq.lhs.func == fn.func and len(eq.lhs.args) == 1 and eq.lhs.args[0].is_number:
                    initial[eq.lhs] = eq.rhs
                else:
                    recurrence = eq.lhs - eq.rhs
            if recurrence is None:
                raise InputError("No recurrence equation found")
            result = s.rsolve(recurrence, fn, initial or None)
            if result is None:
                raise InputError("The symbolic backend could not solve this recurrence")
            return s.Eq(fn, result)
        if name == "NDSolveValue":
            if len(args) in (4, 5):
                self.route = 'PDE / scikit-fem + native SciPy method of lines'
                return pde_module().numerical(args[0], args[1], args[2:4], args[4] if len(args) == 5 else 41)
            if len(args) != 3:
                raise InputError('Use NDSolveValue[equations,functions,{t,lower,upper}]')
            result = solve_ode_system(*args)
            self.route = 'C++ / Boost system Dormand-Prince 5(4)'
            return result
        if name == "NDSolve":
            if len(args) in (4, 5):
                model = self.call('NDSolveValue', nodes)
                return pde_module().dispatch('PDEPlot', [model, 'Solution'])
            equations, fn, interval = args
            t, lo, hi = interval
            dep = s.Function(str(fn))(t) if isinstance(fn, s.Symbol) else fn
            equations = equations if isinstance(equations, list) else [equations]
            differential = next((eq for eq in equations if eq.has(s.Derivative)), None)
            if differential is None:
                raise InputError("NDSolve needs a first-order differential equation")
            rhs = s.solve(differential, s.diff(dep, t))
            if len(rhs) != 1 or rhs[0].has(s.Derivative):
                raise InputError("Native NDSolve currently supports explicit scalar first-order ODEs")
            initial = next((eq.rhs for eq in equations if isinstance(eq, s.Equality) and eq.lhs == dep.subs(t, lo)), None)
            if initial is None:
                raise InputError("Provide an initial condition at the interval's lower bound")
            state = s.Dummy("state")
            xs, ys = kernel.ode(rhs[0].subs(dep, state), t, state, as_float(lo), as_float(hi), as_float(initial))
            self.route = "C++ / Boost Dormand-Prince 5(4)"
            return {"kind": "plot", "plot_type": "curve", "title": "NDSolve", "traces": [{"x": xs, "y": ys, "name": str(dep)}], "axes": [str(t), str(dep)]}
        if name == "Hypergeometric0F1":
            return s.hyper([], [args[0]], args[1])
        if name == "Hypergeometric1F1":
            return s.hyper([args[0]], [args[1]], args[2])
        if name == "Hypergeometric2F1":
            return s.hyper(args[:2], [args[2]], args[3])
        if name == "HypergeometricPFQ":
            return s.hyper(*args)
        if name == 'FunctionExpand':
            return s.hyperexpand(args[0])
        if name == "Quantity":
            return simplify_quantity(quantity(*args))
        if name == "UnitConvert":
            if not isinstance(args[0], pint.Quantity) or not isinstance(args[1], str):
                raise InputError('Use UnitConvert[3[m], "cm"]')
            return args[0].to(quantity(1, args[1]).units)
        if name == "UnitSimplify":
            if len(args) != 1:
                raise InputError('Use UnitSimplify["kg*m/s^2"] or UnitSimplify[quantity]')
            return simplify_quantity(quantity(s.Integer(1), args[0]) if isinstance(args[0], str) else args[0])
        if name == "Magnitude":
            return args[0].magnitude if isinstance(args[0], pint.Quantity) else args[0]
        if name == "ReplaceAll":
            if isinstance(args[1],list) and args[1] and all(isinstance(rule,dict) for rule in args[1]):
                def apply(value,mapping):
                    return [apply(v,mapping) for v in value] if isinstance(value,list) else value.xreplace(mapping)
                return [apply(args[0],mapping) for mapping in args[1]]
            rules = list(args[1].items()) if isinstance(args[1],dict) else args[1] if isinstance(args[1], list) else [args[1]]
            rules = [(rule.lhs, rule.rhs) if isinstance(rule, s.Equality) else rule for rule in rules]
            def replace(value):
                if isinstance(value, list):
                    return [replace(item) for item in value]
                try:
                    return value.xreplace(dict(rules))
                except ValueError:
                    return value.subs(dict(rules), simultaneous=True)
            return replace(args[0])
        if name == "Det":
            if (type(args[0]).__module__ or '').startswith('numpy'):
                import numpy as np
                return s.Float(np.linalg.det(args[0]))
            return s.Matrix(args[0]).det()
        if name == "Inverse":
            if (type(args[0]).__module__ or '').startswith('numpy'):
                import numpy as np
                try:
                    return np.linalg.inv(args[0])
                except np.linalg.LinAlgError as exc:
                    raise InputError('Matrix is singular or not square') from exc
            return s.Matrix(args[0]).inv()
        if name == "Eigenvalues":
            return s.Matrix(args[0]).eigenvals()
        if name == "Transpose":
            if (type(args[0]).__module__ or '').startswith(('numpy','scipy')):return args[0].T
            from .dense import machine_matrix
            packed = machine_matrix(args[0])
            if packed is not None:
                return packed.T
            return s.Matrix(args[0]).T
        if name == "Dot":
            if any((type(a).__module__ or '').startswith(('numpy','scipy')) for a in args):
                import numpy as np
                from scipy import sparse
                use_sparse=any(sparse.issparse(a) for a in args)
                def convert(a):
                    if isinstance(a,list):a=np.asarray(a,dtype=float)
                    return sparse.csr_matrix(a) if use_sparse and isinstance(a,np.ndarray) and a.ndim==2 else a
                result=convert(args[0])
                for value in args[1:]:
                    result=result@convert(value)
                return result
            from .dense import product
            if any(isinstance(a, list) and a and not isinstance(a[0], list) for a in args):
                current = args[0]
                for other in args[1:]:
                    left_vector = isinstance(current, list) and (not current or not isinstance(current[0], list))
                    right_vector = isinstance(other, list) and (not other or not isinstance(other[0], list))
                    left = s.Matrix([current]) if left_vector else s.Matrix(current)
                    right = s.Matrix(other)
                    value = left @ right
                    current = value[0] if left_vector and right_vector else list(value) if left_vector or right_vector else value
                return current
            matrices=[s.Matrix(a) for a in args]
            result=matrices[0]
            for matrix in matrices[1:]:
                accelerated=product(result,matrix)
                if accelerated is None:result=result@matrix
                else:
                    result,path=accelerated
                    self.route=f'C++ / {path} matrix product'
            return result
        if name in ("Import", "Export", "Run", "Get", "Put", "ToExpression"):
            raise InputError(f"{name} is not available in calculation expressions")
        if name in self.environment or name in CONSTANTS:
            raise InputError(f"{name} is not a callable function")
        symbol(name)
        return s.Function(name)(*args)

    def graphics(self, nodes):
        return graphics(self, nodes)

    def animate(self, nodes):
        if not nodes or len(nodes) > 2:
            raise InputError("Use Animate[ParametricPlot[...]] or Animate[Plot[...], {parameter, lower, upper}]")
        plot_node = nodes[0]
        if plot_node.kind != "call" or plot_node.args[0].kind != "symbol" or plot_node.args[0].value not in PLOTS | {'Graphics'}:
            raise InputError("Animate requires a plotting expression")
        if len(nodes) == 1:
            if plot_node.args[0].value != "ParametricPlot":
                raise InputError("Trajectory animation requires a two-dimensional ParametricPlot")
            result = self.evaluate(plot_node)
            interval = plot_node.args[2]
            parameter, lower, upper = interval.args
            bounds = [self.evaluate(bound) for bound in (lower, upper)]
            unit = next((b.units for b in bounds if isinstance(b, pint.Quantity)), None)
            lo, hi = [as_float(b.to(unit).magnitude) if isinstance(b, pint.Quantity) else as_float(b) for b in bounds]
            count = len(result["traces"][0]["x"])
            values = [lo + (hi - lo) * i / (count - 1) for i in range(count)]
            return {"kind": "animation", "animation_type": "trajectory", "plot": result,
                    "values": values, "parameter": f"{parameter.value} [{unit:~}]" if unit else parameter.value}
        interval = nodes[1]
        if interval.kind != "list" or len(interval.args) != 3 or interval.args[0].kind != "symbol":
            raise InputError("Animation range uses {parameter, lower, upper}")
        parameter = interval.args[0].value
        lo, hi = [as_float(self.evaluate(bound)) for bound in interval.args[1:]]
        if not lo < hi:
            raise InputError("Animation bounds must be increasing finite real values")
        if plot_node.args[0].value not in ("Plot", "Plot1D", "ParametricPlot", 'Graphics', 'Plot3D'):
            raise InputError("Frame animation supports Plot, ParametricPlot, Plot3D and Graphics")
        # Bound frame count and sampling so playback requires no repeated solver calls.
        count = 41 if plot_node.args[0].value == 'Plot3D' else 201
        sampled = plot_node if plot_node.args[0].value == 'Graphics' else Node("call", args=(*plot_node.args, Node("binary", "->", (Node("symbol", "PlotPoints"), Node("number", str(count))))))
        previous = self.environment.copy()
        frames, values = [], [lo + (hi - lo) * i / 60 for i in range(61)]
        try:
            if plot_node.args[0].value == 'Graphics':
                self.environment[parameter] = symbol(parameter)
                frames = graphics_frames(self, plot_node.args[1:], symbol(parameter), values)
            else:
                for value in values:
                    self.environment[parameter] = s.Float(value)
                    frames.append(self.evaluate(sampled))
        finally:
            self.environment = previous
        return {"kind": "animation", "animation_type": "frames", "plot": frames[0],
                "frames": frames, "values": values, "parameter": parameter}

    def sample(self, expr, variables, coordinates):
        spatial=[a for a in expr.atoms(s.Function) if a.func.__name__=='SpatialSample']
        if spatial:
            import numpy as np
            replacements=[s.Dummy('field') for _ in spatial]
            columns=[a.sample(*[np.asarray(c) for c in coordinates[:2]]) for a in spatial]
            fn=s.lambdify([*variables,*replacements],expr.xreplace(dict(zip(spatial,replacements))),'numpy')
            with np.errstate(all='ignore'):values=np.broadcast_to(fn(*coordinates,*columns),(len(coordinates[0]),))
            self.route='C++ / Eigen FEM; interpolated field evaluation'
            return [safe_float(v) for v in values]
        interpolated = sorted(expr.atoms(SampledFunction, SampledDerivative), key=str)
        if interpolated:
            placeholders = [s.Dummy(f'interpolation{i}') for i in range(len(interpolated))]
            columns = []
            for function in interpolated:
                times, values, slopes = ([float(value) for value in column] for column in function.args[1:4])
                parameters = self.sample(function.args[0], variables, coordinates)
                evaluator = interpolate_derivative if isinstance(function, SampledDerivative) else interpolate
                columns.append([evaluator(value, times, values, slopes) for value in parameters])
            expression = expr.xreplace(dict(zip(interpolated, placeholders)))
            try:
                values = kernel.batch(expression, [*variables, *placeholders], [*coordinates, *columns])
                self.route = 'C++ / interpolated batch evaluator'
                return [safe_float(value) for value in values]
            except NativeUnsupported:
                evaluator = s.lambdify([*variables, *placeholders], expression, modules='mpmath', cse=True)
                return [safe_float(evaluator(*row)) for row in zip(*coordinates, *columns)]
        try:
            values = kernel.batch(expr, variables, coordinates)
            self.route = "C++ / batch evaluator"
            return [safe_float(v) for v in values]
        except NativeUnsupported:
            remaining = expr.free_symbols - set(variables)
            if remaining:
                raise InputError("Assign numeric values to: " + ", ".join(map(str, remaining)))
            fn = s.lambdify(variables, expr, modules="mpmath", cse=True)
            result = []
            for point in zip(*coordinates):
                try:
                    result.append(safe_float(fn(*point)))
                except (ValueError, ZeroDivisionError, OverflowError, TypeError):
                    result.append(None)
            self.route = "mpmath / sampled evaluation"
            return result

    def plot(self, name, nodes):
        ranges, options = [], {}
        range_units = []
        for node in nodes[1:]:
            if node.kind == "binary" and node.value == "->" and node.args[0].kind == "symbol":
                options[node.args[0].value] = self.evaluate(node.args[1])
            elif node.kind == "list" and len(node.args) == 3 and node.args[0].kind == "symbol":
                bounds = [self.evaluate(v) for v in node.args[1:]]
                unit = next((b.units for b in bounds if isinstance(b, pint.Quantity)), None)
                numeric = [as_float(b.to(unit).magnitude) if isinstance(b, pint.Quantity) else as_float(b) for b in bounds]
                range_units.append(unit)
                ranges.append((symbol(node.args[0].value), *numeric))
            else:
                raise InputError("Plot ranges use {variable, lower, upper}")
        allowed = {"PlotPoints", "PlotRange", "PlotLegends", "BoxRatios"}
        unknown = set(options) - allowed
        if unknown:
            raise InputError("Unsupported plot option: " + ", ".join(sorted(unknown)))
        expected = 2 if name in ("Plot2D", "DensityPlot", "Plot3D", "ContourPlot") else 1
        if name == "ParametricPlot3D" and len(ranges) == 2:
            expected = 2
        if len(ranges) != expected:
            raise InputError(f"{name} requires {expected} variable range(s)")
        if any(not lo < hi for _, lo, hi in ranges):
            raise InputError("Plot bounds must be increasing finite real values")
        variables = [r[0] for r in ranges]
        previous = self.environment.copy()
        try:
            for var, unit in zip(variables, range_units):
                self.environment[str(var)] = quantity(var, unit) if unit is not None else var
            expression = self.evaluate(nodes[0])
        finally:
            self.environment = previous
        def axis_label(label, unit):
            return f"{label} [{unit_label(unit)}]" if unit is not None else label
        labels = [axis_label(str(var), unit) for var, unit in zip(variables, range_units)]
        base = {"kind": "plot", "title": name, "axes": labels, "options": {}}
        if 'BoxRatios' in options:
            ratios = options['BoxRatios']
            if name not in ('Plot3D', 'ParametricPlot3D') or not isinstance(ratios, list) or len(ratios) != 3 or any(as_float(value) <= 0 for value in ratios):
                raise InputError('BoxRatios requires three positive finite ratios for a 3D plot')
            base['options']['box_ratios'] = [as_float(value) for value in ratios]
        if "PlotRange" in options:
            plot_range = options["PlotRange"]
            if isinstance(plot_range, list) and len(plot_range) == 2:
                base["options"]["range"] = [as_float(x) for x in plot_range]
            else:
                raise InputError("This preview supports PlotRange -> {minimum, maximum}")
        if len(ranges) == 1:
            count = min(4001, max(101, int(options.get("PlotPoints", 801))))
            _, lo, hi = ranges[0]
            xs = [lo + (hi-lo)*i/(count-1) for i in range(count)]
            if name.startswith("Parametric"):
                dim = 3 if name == "ParametricPlot3D" else 2
                if not isinstance(expression, list) or len(expression) != dim:
                    raise InputError(f"{name} expects {dim} coordinate expressions")
                labels = [axis_label(label, e.units if isinstance(e, pint.Quantity) else None) for label, e in zip("xyz", expression)]
                expression = [s.sympify(e.magnitude) if isinstance(e, pint.Quantity) else e for e in expression]
                coords = [self.sample(e, variables, [xs]) for e in expression]
                trace = {axis: values for axis, values in zip("xyz", coords)}
                return {**base, "plot_type": "curve3d" if dim == 3 else "curve", "traces": [{**trace, "name": str(expression)}], "axes": labels}
            expressions = expression if isinstance(expression, list) else [expression]
            legends = options.get('PlotLegends')
            if legends is not None and (not isinstance(legends, list) or len(legends) != len(expressions) or any(not isinstance(label, str) or len(label) > 100 for label in legends)):
                raise InputError('PlotLegends requires one text label per curve (up to 100 characters each)')
            yunit = next((e.units for e in expressions if isinstance(e, pint.Quantity)), None)
            if yunit is not None:
                expressions = [s.sympify(e.to(yunit).magnitude) if isinstance(e, pint.Quantity) else dimensionless(quantity(e, "").to(yunit)) for e in expressions]
                base["axes"] = [labels[0], axis_label("y", yunit)]
            traces = []
            for curve_index, expr in enumerate(expressions):
                ys = self.sample(expr, variables, [xs])
                midpoints = [(xs[i]+xs[i+1])/2 for i in range(count-1)]
                mids = self.sample(expr, variables, [midpoints])
                clean_x, clean_y = [], []
                for i, (x, y) in enumerate(zip(xs, ys)):
                    clean_x.append(x)
                    clean_y.append(y)
                    if i < count-1 and y is not None and ys[i+1] is not None:
                        next_y, mid = ys[i+1], mids[i]
                        scale = max(1, abs(y), abs(next_y))
                        if mid is None or abs(mid-(y+next_y)/2) > 0.6*scale:
                            clean_x.append((x+xs[i+1])/2)
                            clean_y.append(None)
                traces.append({"x": clean_x, "y": clean_y, "name": legends[curve_index] if legends is not None else str(expr)})
            return {**base, "plot_type": "curve", "traces": traces}
        count = min(141, max(21, int(options.get("PlotPoints", 65))))
        axes = [[lo+(hi-lo)*i/(count-1) for i in range(count)] for _, lo, hi in ranges]
        xx = [x for y in axes[1] for x in axes[0]]
        yy = [y for y in axes[1] for x in axes[0]]
        if name == "ParametricPlot3D":
            if not isinstance(expression, list) or len(expression) != 3:
                raise InputError("A parametric surface needs three coordinate expressions")
            labels = [axis_label(label, e.units if isinstance(e, pint.Quantity) else None) for label, e in zip("xyz", expression)]
            expression = [s.sympify(e.magnitude) if isinstance(e, pint.Quantity) else e for e in expression]
            coords = [self.sample(e, variables, [xx, yy]) for e in expression]
            return {**base, "plot_type": "parametric_surface", "size": count,
                    "coordinates": coords, "axes": labels}
        if isinstance(expression, pint.Quantity):
            base["axes"] = [*labels, axis_label("z", expression.units)]
            expression = s.sympify(expression.magnitude)
        values = self.sample(expression, variables, [xx, yy])
        rows = [values[i*count:(i+1)*count] for i in range(count)]
        kind = "surface" if name == "Plot3D" else "contour" if name == "ContourPlot" else "density"
        return {**base, "plot_type": kind, "x": axes[0], "y": axes[1], "z": rows}
