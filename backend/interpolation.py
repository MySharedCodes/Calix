"""Serializable cubic Hermite functions from native dense ODE output."""
from bisect import bisect_right
import math
import sympy as s
from .syntax import InputError


def interpolate(t, times, values, slopes):
    t = float(t)
    if not math.isfinite(t) or t < float(times[0]) - 1e-12 or t > float(times[-1]) + 1e-12:
        raise InputError("Interpolation argument is outside its solved interval")
    i = max(0, min(len(times) - 2, bisect_right(times, t) - 1))
    h = float(times[i + 1] - times[i]); u = (t - float(times[i])) / h
    return ((2*u**3-3*u**2+1)*float(values[i]) + (u**3-2*u**2+u)*h*float(slopes[i])
            + (-2*u**3+3*u**2)*float(values[i+1]) + (u**3-u**2)*h*float(slopes[i+1]))


def interpolate_derivative(t, times, values, slopes):
    interpolate(t, times, values, slopes)
    t = float(t)
    i = max(0, min(len(times)-2, bisect_right(times, t)-1))
    h = float(times[i+1]-times[i]); u = (t-float(times[i]))/h
    return ((6*u*u-6*u)*float(values[i])/h + (3*u*u-4*u+1)*float(slopes[i])
            + (-6*u*u+6*u)*float(values[i+1])/h + (3*u*u-2*u)*float(slopes[i+1]))


class _SampledExpression:
    @property
    def free_symbols(self):
        return self.args[0].free_symbols

    def _sympystr(self, printer):
        name = 'InterpolatingFunctionDerivative' if len(self.args) == 4 else 'InterpolatingFunction'
        return name + '(' + printer.doprint(self.args[0]) + ')'

    def _xreplace(self, rule):
        if all(isinstance(key, s.Symbol) for key in rule):
            time, changed = self.args[0]._xreplace(rule)
            return (self._at(time), True) if changed else (self, False)
        return super()._xreplace(rule)

    def _eval_subs(self, old, new):
        if isinstance(old, s.Symbol):
            return self._at(self.args[0].subs(old, new))

    def _at(self, time):
        if time.is_number:
            evaluator = interpolate_derivative if len(self.args) == 4 else interpolate
            return s.Float(evaluator(time, *self.args[1:4]))
        return self.func(time, *self.args[1:])


class SampledDerivative(_SampledExpression, s.Function):
    nargs = 4

    @classmethod
    def eval(cls, t, times, values, slopes):
        if t.is_number:
            return s.Float(interpolate_derivative(t, times, values, slopes))

    _imp_ = staticmethod(interpolate_derivative)

    def _eval_derivative(self, variable):
        return s.Derivative(self, variable, evaluate=False)

    def _latex(self, printer):
        return r"\operatorname{InterpolatingFunction}'(" + printer.doprint(self.args[0]) + ")"

    def _mcode(self, printer):
        return "InterpolatingFunctionDerivative[" + printer.doprint(self.args[0]) + "]"


class SampledFunction(_SampledExpression, s.Function):
    nargs = 6

    @classmethod
    def eval(cls, t, times, values, slopes, integrals, integral_slopes):
        if t.is_number:
            return s.Float(interpolate(t, times, values, slopes))

    @staticmethod
    def _imp_(t, times, values, slopes, integrals, integral_slopes):
        return interpolate(t, times, values, slopes)

    def _latex(self, printer):
        return r"\operatorname{InterpolatingFunction}_{[" + printer.doprint(self.args[1][0]) + "," + printer.doprint(self.args[1][-1]) + "]}(" + printer.doprint(self.args[0]) + ")"

    def _mcode(self, printer):
        return "InterpolatingFunction[{" + str(self.args[1][0]) + ", " + str(self.args[1][-1]) + "}][" + printer.doprint(self.args[0]) + "]"

    def _eval_derivative(self, variable):
        return s.diff(self.args[0], variable) * SampledDerivative(*self.args[:4])

    def integral(self, variable, lower, upper):
        t, times, values, slopes, integrals, integral_slopes = self.args
        if t != variable or not s.simplify(lower - times[0]).is_zero:
            raise InputError("Integrate numerical solutions from their initial time, using the solution's variable")
        if integrals == s.Tuple():
            raise InputError("Repeated integration of numerical solutions is not supported")
        return SampledFunction(upper, times, integrals, integral_slopes, s.Tuple(), s.Tuple())
