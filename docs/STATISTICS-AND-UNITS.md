# Statistics and Units (0.1.27)

Calix implements a documented Wolfram-style subset using SymPy, Pint, mpmath and the C++/Boost kernel. No Mathematica implementation or runtime is included.

## Statistics

Descriptive functions: `Mean`, `Median`, `Variance`, `StandardDeviation`, `Quantile`, `Quartiles`, `InterquartileRange`, `Total`, `Length`, `Sort`, `Counts`, `Commonest`, `GeometricMean`, `HarmonicMean`, `RootMeanSquare`, `MeanDeviation`, `CentralMoment`, `Skewness`, `Kurtosis`, `Standardize`.

- `Variance[data]` uses sample variance (denominator n-1); distribution variance uses the population formula.
- `Quantile[data,q]` uses the inverse empirical CDF: the ordered observation at ceil(n*q), clamped to the first observation at q=0. No interpolation is applied. `Quartiles` uses q={1/4,1/2,3/4}; the middle quartile may differ from the average-of-two `Median` on even samples.
- `Skewness` and `Kurtosis` use population central moments, without small-sample bias corrections. Kurtosis is not excess kurtosis.
- Constant samples are rejected where a statistic requires nonzero spread. Samples must contain finite real values, with at most 10000 observations.

Paired statistics: `Covariance`, `Correlation` (Pearson), `SpearmanRho` (average ranks for ties). Pair lengths must agree.

Least squares: `Fit[{{x1,y1},...},{1,x,x^2},x]`, up to 20 basis functions. Singular designs are rejected. Exact rational inputs preserve exact results; ill-conditioned floating-point fits can lose precision.

Distributions: `NormalDistribution[mean,sigma]`, `UniformDistribution[{lower,upper}]`, `ExponentialDistribution[rate]`, `BinomialDistribution[n,p]`, `PoissonDistribution[lambda]`, `StudentTDistribution[df]`, `ChiSquareDistribution[df]`.

Operations: `PDF[distribution,x]`, `CDF[distribution,x]`, `InverseCDF[distribution,q]`, and distribution `Mean`, `Variance`, `StandardDeviation`. Inverse CDF support follows SymPy; some distributions and parameter choices remain symbolic or unsupported.

Tests: `TTest[data,hypothesizedMean]` returns the two-sided one-sample Student t-test p-value (unknown population variance); the default hypothesized mean is zero. `ZTest[data,hypothesizedMean,populationSigma]` returns the two-sided one-sample normal z-test p-value with known positive population sigma. Both assume independent observations; the t-test assumes a normally distributed population for its exact small-sample interpretation. Two-sample tests, ANOVA, survival analysis, and a full Mathematica statistics compatibility layer are not included.

Plots: `Histogram[data,binCount]`, `ListPlot[data]`, `ListLinePlot[data]`. Lists of numbers use indices starting at 1; {x,y} pairs use their specified coordinates. Histogram bins have equal width; the rightmost endpoint belongs to the final bin.

## Unit Arithmetic

Quantities use suffixes such as `3[m]`, `9.81[m/s^2]`. Unit conversion preserves the requested target and displays brackets in both copied and typeset output: `UnitConvert[1[m],"cm"]` gives `100[cm]`.

Unit arithmetic is integrated into calculation cells. `[kg*m/s^2]` and `UnitSimplify["kg*m/s^2"]` produce `1[N]`. Quantity suffixes and arithmetic simplify compatible dimensions to named SI units or shorter products such as Pa*s and W/K. Simple units and prefixes are retained. Dimensional errors are rejected.

Pint's installed unit definitions, common prefixes and Chinese aliases supply 1,767 editor suggestions. Strings permit extra unit characters: `1["µm"]`, `1["m²"]`, `0["°C"]`; unquoted forms such as `1[牛顿]` also work. Assigned scalar and vector variables accept unit suffixes. Unassigned lowercase symbolic variables use a quoted unit, such as `x["m"]`, so bare `f[t]` keeps its function meaning. Unit expressions are case-sensitive and independent of notebook variable values. The catalog is generated with `scripts/create-unit-catalog.py` using the installed unit definitions.

Dimensional equivalence alone cannot infer the physical meaning of a quantity: N*m is rendered as J, although a torque can share that dimension. Use `UnitConvert[quantity,"N*m"]` to explicitly retain such a target representation. Offset temperatures obey Pint's affine-unit rules.

## ODE Solutions

The air-resistance notebook includes analytic linear drag followed by numerical quadratic drag. For numerical motion, `NDSolveValue` supports up to 16 dependent functions of first or second order, reduced to at most 32 first-order states, with all required initial conditions at the lower time bound. The C++ Boost Dormand-Prince solver advances states and their integrals together, using absolute and relative tolerances of 1e-10. Returned values use cubic Hermite interpolation at 1001 saved points. Interpolation error is separate from the adaptive solver tolerance; values outside the solved interval are rejected. Stored interpolation data is sampled before native batch evaluation of composite expressions such as energy.

`r=Integrate[v,{t,0,t}]` retrieves displacement integrals from that solution. This supports one integration from the solution's initial time, not arbitrary repeated or indefinite numerical integration. Scalar `NDSolve` and analytical `DSolveValue` retain their existing behavior.

Complete case notebooks are listed in Examples. Problem statements and model assumptions are in text cells; transformations, exact checks and numerical searches are in calculation cells. The current-loop example combines an analytic elliptic-integral field with native numerical motion. The hydrogen-like ion example computes and verifies analytic bound states using confluent hypergeometric functions and associated Laguerre polynomials.
