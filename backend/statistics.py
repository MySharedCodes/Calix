"""Common Wolfram-style statistics backed by SymPy and exact sample formulas."""
import math
from collections import Counter
import sympy as s
import sympy.stats as stats
import mpmath
from .syntax import InputError

DISTRIBUTIONS = {"NormalDistribution": (stats.Normal, 2), "UniformDistribution": (stats.Uniform, 2),
                 "ExponentialDistribution": (stats.Exponential, 1), "BinomialDistribution": (stats.Binomial, 2),
                 "PoissonDistribution": (stats.Poisson, 1), "StudentTDistribution": (stats.StudentT, 1),
                 "ChiSquareDistribution": (stats.ChiSquared, 1)}
NAMES = set(DISTRIBUTIONS) | {"Mean", "Median", "Variance", "StandardDeviation", "Total", "Length", "Sort",
    "Quantile", "Quartiles", "InterquartileRange", "GeometricMean", "HarmonicMean", "RootMeanSquare",
    "MeanDeviation", "CentralMoment", "Skewness", "Kurtosis", "Covariance", "Correlation", "SpearmanRho",
    "Counts", "Commonest", "PDF", "CDF", "InverseCDF", "Standardize", "Fit", "Histogram", "ListPlot", "ListLinePlot", "TTest", "ZTest"}


def sample(value, minimum=1):
    if (type(value).__module__ or '').startswith('numpy') and getattr(value,'ndim',0)==1:
        value=value.tolist()
    if not isinstance(value, list) or not minimum <= len(value) <= 10000:
        raise InputError(f"Expected a list of {minimum} to 10000 real numbers")
    value = [s.sympify(x) for x in value]
    if any(not isinstance(x, s.Expr) or x.is_real is not True or x.is_finite is not True for x in value):
        raise InputError("Statistics require finite real numbers")
    return value


def mean(xs):
    if xs and isinstance(xs[0],list):
        if any(not isinstance(row,list) or len(row)!=len(xs[0]) for row in xs):raise InputError('Mean requires matching row dimensions')
        return [mean(list(column)) for column in zip(*xs)]
    if any(isinstance(x, float) for x in xs) and all(isinstance(x, (int, float)) and math.isfinite(x)
            and (not isinstance(x, int) or abs(x) <= 2**53) for x in xs):
        return math.fsum(xs) / len(xs)
    return s.Add(*xs) / len(xs)


def variance(xs):
    sample(xs, 2)
    return sum((x - mean(xs)) ** 2 for x in xs) / (len(xs) - 1)


def quantile(xs, q):
    if q.is_number is not True or not 0 <= q <= 1:
        raise InputError("Quantile probability must be between 0 and 1")
    return sorted(xs, key=float)[max(0, math.ceil(len(xs) * q) - 1)]


def ranks(xs):
    ordered = sorted(xs, key=float)
    return [s.Rational(ordered.index(x) + len(xs) - ordered[::-1].index(x) + 1, 2) for x in xs]


def dispatch(name, args):
    if name in DISTRIBUTIONS:
        factory, count = DISTRIBUTIONS[name]
        params = args[0] if name == "UniformDistribution" and len(args) == 1 and isinstance(args[0], list) else args
        if len(params) != count:
            raise InputError(f"{name} expects {count} parameters")
        try:
            factory("calixDistribution", *params)
        except (ValueError, TypeError) as exc:
            raise InputError(str(exc)) from None
        return s.Tuple(s.Symbol(name), *params)
    if name in ("PDF", "CDF", "InverseCDF") or (name in ("Mean", "Variance", "StandardDeviation") and args and isinstance(args[0], s.Tuple)):
        distribution = args[0]
        if not isinstance(distribution, s.Tuple) or str(distribution[0]) not in DISTRIBUTIONS:
            raise InputError("Expected a supported probability distribution")
        factory = DISTRIBUTIONS[str(distribution[0])][0]
        rv = factory("calixDistribution", *distribution[1:])
        if name in ("Mean", "Variance", "StandardDeviation"):
            return stats.E(rv) if name == "Mean" else s.sqrt(stats.variance(rv)) if name == "StandardDeviation" else stats.variance(rv)
        if len(args) != 2:
            raise InputError(f"{name} expects a distribution and a value")
        if name == "InverseCDF":
            if args[1].is_number and not 0 <= args[1] <= 1:
                raise InputError("InverseCDF probability must be between 0 and 1")
            return stats.quantile(rv)(args[1])
        function = stats.density(rv) if name == "PDF" else stats.cdf(rv)
        if isinstance(function, dict):
            if name == "PDF":
                return sum(probability * s.Piecewise((1, s.Eq(args[1], point)), (0, True)) for point, probability in function.items())
            # SymPy's finite CDF maps each support point to its cumulative probability.
            if args[1].is_number:
                eligible = [point for point in function if point <= args[1]]
                return function[max(eligible)] if eligible else s.Integer(0)
            ordered = sorted(function, reverse=True)
            return s.Piecewise(*[(function[point], args[1] >= point) for point in ordered], (0, True))
        return function(args[1])
    if name == "Fit":
        if len(args) != 3 or not isinstance(args[1], list) or not isinstance(args[2], s.Symbol):
            raise InputError("Use Fit[{{x1,y1},...},{1,x},x]")
        data, basis, var = args
        if not isinstance(data, list) or not 2 <= len(data) <= 10000 or len(basis) > 20:
            raise InputError("Fit needs 2 to 10000 observations and at most 20 basis functions")
        for point in data:
            sample(point, 2)
            if len(point) != 2:
                raise InputError("Fit needs {x,y} pairs")
        if any(not isinstance(b, s.Expr) or b.free_symbols - {var} for b in basis):
            raise InputError("Fit basis must depend only on its specified variable")
        matrix = s.Matrix([[b.subs(var, x) for b in basis] for x, _ in data])
        try:
            coefficients = (matrix.T * matrix).inv() * matrix.T * s.Matrix([y for _, y in data])
        except Exception:
            raise InputError("Fit basis is singular for these observations") from None
        return s.expand(sum(c * b for c, b in zip(coefficients, basis)))
    if name in ("ListPlot", "ListLinePlot", "Histogram"):
        return data_plot(name, args)
    if not args:
        raise InputError(f"{name} needs data")
    if name in ('Length', 'Total', 'Sort'):
        if not isinstance(args[0], list):
            raise InputError(f'{name} expects a list')
        if name == 'Length': return s.Integer(len(args[0]))
        if name == 'Total': return sum(args[0], s.Integer(0))
        def order(value):
            if isinstance(value, list):return (1, tuple(order(v) for v in value))
            if isinstance(value, (int, float, s.Expr)) and s.sympify(value).is_number and s.sympify(value).is_real:
                return (0, s.sympify(value))
            return (2, s.default_sort_key(value))
        return sorted(args[0], key=order)
    if name=='Mean' and isinstance(args[0],list) and args[0] and isinstance(args[0][0],list):
        return mean(args[0])
    xs = sample(args[0])
    if name in ("TTest", "ZTest"):
        sample(xs, 2)
        if (name == "TTest" and len(args) not in (1, 2)) or (name == "ZTest" and len(args) != 3):
            raise InputError("Use TTest[data, hypothesizedMean] or ZTest[data, hypothesizedMean, populationSigma]")
        center = args[1] if len(args) > 1 else s.Integer(0)
        sample([center])
        spread = variance(xs) if name == "TTest" else args[2] ** 2
        if name == "ZTest": sample([args[2]])
        if spread <= 0 or (name == "ZTest" and args[2] <= 0):
            raise InputError("Hypothesis testing requires a positive standard deviation")
        statistic = float((mean(xs) - center) / s.sqrt(spread / len(xs)))
        if name == "ZTest":
            return s.Float(math.erfc(abs(statistic) / math.sqrt(2)))
        df = len(xs) - 1
        return s.Float(mpmath.betainc(df / 2, 0.5, 0, df / (df + statistic**2), regularized=True))
    if name == "Mean": return mean(xs)
    if name == "Median":
        ordered = sorted(xs, key=float); n = len(xs)
        return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    if name == "Variance": return variance(xs)
    if name == "StandardDeviation": return s.sqrt(variance(xs))
    if name == "Quantile":
        if len(args) != 2: raise InputError("Quantile[data,q] needs two arguments")
        return [quantile(xs, q) for q in args[1]] if isinstance(args[1], list) else quantile(xs, args[1])
    if name == "Quartiles": return [quantile(xs, s.Rational(i, 4)) for i in (1, 2, 3)]
    if name == "InterquartileRange": return quantile(xs, s.Rational(3, 4)) - quantile(xs, s.Rational(1, 4))
    if name in ("GeometricMean", "HarmonicMean"):
        if any(x <= 0 for x in xs): raise InputError(f"{name} requires positive data")
        return s.prod(xs) ** s.Rational(1, len(xs)) if name == "GeometricMean" else len(xs) / sum(1 / x for x in xs)
    if name == "RootMeanSquare": return s.sqrt(mean([x * x for x in xs]))
    if name == "MeanDeviation": return mean([abs(x - mean(xs)) for x in xs])
    if name == "CentralMoment":
        if len(args) != 2 or args[1].is_Integer is not True or not 0 <= args[1] <= 100:
            raise InputError("CentralMoment order must be an integer from 0 to 100")
        return mean([(x - mean(xs)) ** args[1] for x in xs])
    if name in ("Skewness", "Kurtosis", "Standardize"):
        if all(x == xs[0] for x in xs): raise InputError("This statistic is undefined for constant data")
        if name == "Standardize": return [(x - mean(xs)) / s.sqrt(variance(xs)) for x in xs]
        order = 3 if name == "Skewness" else 4
        return mean([(x - mean(xs)) ** order for x in xs]) / mean([(x - mean(xs)) ** 2 for x in xs]) ** s.Rational(order, 2)
    if name in ("Covariance", "Correlation", "SpearmanRho"):
        if len(args) != 2: raise InputError(f"{name} needs two samples")
        ys = sample(args[1], 2); sample(xs, 2)
        if len(xs) != len(ys): raise InputError("Paired samples must have equal length")
        if name == "SpearmanRho": xs, ys = ranks(xs), ranks(ys)
        covariance = sum((x - mean(xs)) * (y - mean(ys)) for x, y in zip(xs, ys)) / (len(xs) - 1)
        if name == "Covariance": return covariance
        spread = variance(xs) * variance(ys)
        if spread == 0: raise InputError("Correlation is undefined for constant data")
        return s.simplify(covariance / s.sqrt(spread))
    if name == "Counts": return {key: s.Integer(count) for key, count in Counter(xs).items()}
    if name == "Commonest":
        counts = Counter(xs); largest = max(counts.values())
        return [x for x, count in counts.items() if count == largest]
    raise InputError(f"Unsupported statistic: {name}")


def data_plot(name, args):
    if not args: raise InputError(f"{name} requires a data list")
    data = args[0]
    if name in ('ListPlot','ListLinePlot') and isinstance(data,list) and data and isinstance(data[0],list) and data[0] and isinstance(data[0][0],list):
        plots=[data_plot(name,[series]) for series in data]
        labels=next((rule[1] for rule in args[1:] if isinstance(rule,tuple) and str(rule[0])=='PlotLegends'),None)
        if labels is not None and (not isinstance(labels,list) or len(labels)!=len(plots)):raise InputError('PlotLegends must match the number of data series')
        traces=[plot['traces'][0] for plot in plots]
        for i,trace in enumerate(traces):trace['name']=str(labels[i]) if labels is not None else str(i+1)
        return {**plots[0],'traces':traces}
    style = "markers" if name == "ListPlot" else "lines"
    if name == "Histogram":
        xs = [float(x) for x in sample(data)]
        bins = args[1] if len(args) > 1 else s.Integer(max(1, math.ceil(math.sqrt(len(xs)))))
        if not isinstance(bins, s.Integer) or not 1 <= bins <= 200:
            raise InputError("Histogram bin count must be an integer from 1 to 200")
        bins = int(bins); lo, hi = min(xs), max(xs)
        if lo == hi: lo -= 0.5; hi += 0.5
        width = (hi - lo) / bins; counts = [0] * bins
        for x in xs: counts[min(bins - 1, int((x - lo) / width))] += 1
        xvalues, yvalues = [lo + (i + 0.5) * width for i in range(bins)], counts
        style = "bars"
    elif isinstance(data, list) and data and isinstance(data[0], list):
        for point in data:
            sample(point, 2)
            if len(point) != 2: raise InputError("Expected {x,y} pairs")
        if len(data) > 10000: raise InputError("At most 10000 observations are allowed")
        xvalues, yvalues = zip(*data)
    else:
        sample(data); xvalues, yvalues = range(1, len(data) + 1), data
    return {"kind": "plot", "plot_type": "curve", "title": name, "axes": ["value" if name == "Histogram" else "x", "count" if name == "Histogram" else "y"],
            "traces": [{"x": [float(x) for x in xvalues], "y": [float(y) for y in yvalues], "name": name, "style": style}]}
