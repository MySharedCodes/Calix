# Supported Syntax In 0.1.27

## Input And Sessions

Source cells accept a restricted Wolfram-style language, not arbitrary Wolfram programs. Function calls use square brackets, lists use braces, `==` constructs equations, `=` assigns a simple variable, and semicolons sequence expressions. A trailing semicolon suppresses expression output. Multiplication may be explicit or implicit. `^` is right associative, and exponentiation binds more tightly than unary minus.

Top-level newline-separated expressions produce separate results in order, up to 40 visible results per cell. Assignments are available to subsequent lines; add `;` to hide an intermediate assignment. Newlines within brackets do not separate results. A trailing operator continues the expression on the next line; a leading `*`, `/`, or `^` also continues the preceding line. Leading `+` and `-` begin a separate signed expression. Use parentheses for an expression spanning multiple lines when in doubt. `Column` is still supported for existing notebooks but is not needed for multiline output.

Both Unicode pi/infinity and `\[Pi]` / `\[Infinity]` are accepted. Selected named Greek letters are supported. Strings use JSON-compatible escapes. User function definitions, patterns, delayed assignments, packages, file commands and process commands are not implemented.

Greek characters can be entered directly or with their supported named forms, such as `α` and `\[Alpha]`. Numerical subscript identifiers `x₁`, `m₁₂` normalize to `x_1`, `m_12`; string literals and quoted unit names are not changed. The editor's Esc abbreviation input opens with Esc and commits with Esc or Enter. `a`, `b`, `g`, `q`, `p` and `w` insert α, β, γ, θ, π and ω. Uppercase short aliases insert uppercase Greek letters. `inf`, `deg`, `ii`, `ee`, `<=`, `>=`, `!=` and `->` enter common constants and operators. Unknown abbreviations remain editable.

`intt` opens an indefinite integral, `dint` a definite integral, `sum` a sum, `prod` a product, and `lim` a limit. `sqrt`, `frac`, `sup` and `sub` open radical, fraction, exponent and numerical subscript templates. Templates remain inline as typeset mathematics; fill the slots, move with Tab, and press Ctrl+Enter to evaluate. Incomplete formulas are rejected. `pdiff` inserts a partial derivative, `mat` a matrix and `sc` a calligraphic-letter template. The calculator uses the same editor. These shortcuts implement a common Mathematica-style subset; displaying a character does not establish solver support for every structure containing it.

`Clear[x]` removes a variable. Notebook and calculator use separate sessions. Bound differentiation, integration, solve and plot variables are local to those operations. Editing or reordering cells marks downstream outputs stale. Run All resets the session before evaluating from the top. Files restore inputs and outputs, but session variables are rebuilt by running cells. Loaded results are marked stale and never execute automatically.

Ctrl+Enter evaluates a calculation cell; Alt+. cancels the current calculation. Ctrl+S saves; Ctrl+O opens. Formula input accepts Ctrl+6 for a superscript and Ctrl+2 for a radical. It supports common scalar arithmetic and elementary functions; unsupported structures should be entered directly in the calculation cell.

## Examples

```text
1/3 + Sqrt[2]
N[Pi, 80]
Sum[1/n^2, {n, 1, Infinity}]
Product[k, {k, 1, 10}]
HypergeometricPFQ[{1, 1}, {2}, z]
N[Hypergeometric2F1[1/2, 1/2, 1, 1/2], 40]
Assuming[x > 0, Simplify[Sqrt[x^2]]]
D[x^3 y^2, {x, 2}, y]
Integrate[Exp[-x^2], x]
Integrate[Exp[-a x], {x, 0, Infinity}]
Limit[Sin[x]/x, x -> 0]
Series[Exp[x], {x, 0, 5}]
Normal[Series[Exp[x], {x, 0, 5}]]
ReplaceAll[x^2+y, {x -> 2, y -> 3}]
Solve[x^2 == 2, x]
Solve[x^2 == -1, x, Reals]
Solve[{x+y == 3, x-y == 1}, {x,y}]
RSolve[{a[n+1] == 2 a[n]+1, a[0] == 0}, a[n], n]
DSolve[{y'[x] == -2 y[x], y[0] == 1}, y[x], x]
FindRoot[Cos[x]-x, {x, 0, 1}]
NIntegrate[Exp[-x^2], {x, -3, 3}]
NDSolve[{y'[t] == -y[t], y[0] == 1}, y, {t, 0, 10}]
```

Exact and high-precision symbolic operations use SymPy/mpmath. Supported precision is 2-1000 decimal digits. Native roots, quadrature, ODEs and standard plot sampling use IEEE-754 doubles. `FindRoot` requires a real sign-changing bracket, unlike Mathematica's usual starting-value form. `NSolve` currently approximates finite symbolic solution sets; it is not an exhaustive general numerical equation solver.

Symbolic function families include elementary trigonometric, exponential and logarithmic functions; Gamma/Beta; Erf/Erfc; Bessel J/Y/I/K; Airy Ai/Bi; elliptic K/E; Zeta/PolyLog; and hypergeometric 0F1/1F1/2F1/PFQ. Simplification is delegated to the installed engine, so not every identity or analytic continuation is reduced automatically. `FullSimplify` currently shares the `Simplify` implementation.

## Units

```text
3[m] + 20[cm]
10[m/s] * 2[s]
(a+b)[m]
Quantity[x, "m"]
UnitConvert[1[bar], "Pa"]
UnitConvert[0[degC], "K"]
UnitConvert[10[delta_degC], "delta_degF"]
Sin[90[deg]]
```

Pint supplies unit definitions, dimension checking and affine temperature rules. Unit scale factors use exact fractions. A symbol followed by brackets, such as `f[x]`, is a function call; use `(x)[m]` or `Quantity[x,"m"]` to attach a unit to a symbolic value. A numeric or parenthesized expression followed by brackets is a unit suffix. Unknown units and incompatible dimensions are rejected. Do not rely on arbitrary unit-bearing symbolic equation solving in this preview; automatic nondimensionalization is a later milestone.

Angles default to radians. Use the keypad's degree symbol, for example `Sin[90°]`, or an explicit degree unit such as `Sin[90[deg]]`. Units display in square brackets; products use a centered dot and division uses `/`. Input still accepts `*`, for example `1[kg/(m*s)]`. `gr` means grain; grams use `g`.

## Plotting

```text
Plot[{Sin[x], Cos[x]}, {x,-Pi,Pi}]
Plot1D[1/x, {x,-2,2}, PlotRange -> {-5,5}]
Plot2D[Sin[x y], {x,-3,3}, {y,-3,3}]
DensityPlot[Sin[x y], {x,-3,3}, {y,-3,3}]
ContourPlot[x^2-y^2, {x,-3,3}, {y,-3,3}]
Plot3D[Sin[x] Cos[y], {x,-Pi,Pi}, {y,-Pi,Pi}]
ParametricPlot[{Cos[3 t], Sin[2 t]}, {t,0,2 Pi}]
ParametricPlot3D[{Cos[t], Sin[t], t/4}, {t,0,6 Pi}]
ParametricPlot3D[{(2+Cos[v]) Cos[u], (2+Cos[v]) Sin[u], Sin[v]}, {u,0,2 Pi}, {v,0,2 Pi}]
Plot[3[m/s]*t, {t,0[s],2[s]}]
```

`Plot2D` means a density plot in Calix. `PlotPoints` is supported, capped at 4001 points for curves and 141 per grid axis. Curves currently use regular sampling plus midpoint discontinuity checks; fully adaptive refinement and difficult singularity detection remain pending. All renderers use real-valued samples; invalid or complex samples become gaps. Unit-bearing plot ranges and expressions produce axis unit labels. Multiple curves on one axis must have compatible dimensions.

2D plots support pan/zoom, reset and PNG export. 3D plots support orbit/zoom, reset and PNG export. Click a plot before using wheel interaction; otherwise the wheel scrolls the document. `Animate[Plot[Sin[x-a],{x,0,2 Pi}],{a,0,2 Pi}]` provides playback and a timeline. General `Manipulate`, arbitrary Mathematica plot options, 3D contours and SVG export are not implemented. See the shipped examples for the supported animation forms.

## Resource Limits And Recovery

Each calculation defaults to a 180-second deadline; the API accepts 0.01–3600 seconds. A cancellation or timeout terminates its worker and clears that session's variables. Windows service processes belong to a kill-on-close job, with a 1.5 GiB per-process memory cap. A service stores up to 128 sessions; the Workers setting separately bounds concurrent calculation processes and participating native threads. The input cap is 24,000 characters; notebook files allow 1–200 cells and are capped at 10 MB. Calix does not automatically replay state after an interrupted calculation. See [CPU execution](CPU-ACCELERATION.md) for threading and SIMD limits, and [PDE](PDE.md) for the optional module.
