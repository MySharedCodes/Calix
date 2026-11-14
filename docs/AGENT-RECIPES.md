# Calix task recipes

Read only the section needed. Commands and delivery are in
[AGENTS.md](../AGENTS.md) and [AI-CONTROL.md](../AI-CONTROL.md).
Each Wolfram block is independent and executable as one calculation cell.
Replace inputs rather than assuming full Mathematica compatibility.

## Algebra and complex numbers

```wolfram
Factor[x^6-1]
Simplify[(x^2-1)/(x-1)]
N[Pi,50]
ComplexExpand[(1+I)^6]
```

Keep fractions for exact work. Cancellation does not remove original domain
restrictions: the fraction still requires x != 1. `FullSimplify` currently shares
the `Simplify` implementation.

## Sums, products, statistics and fits

```wolfram
Sum[k^6,{k,1,500}]
Product[k,{k,1,10}]
Mean[{2,3,5,7,11}]
Fit[{{0,1},{1,3},{2,5}},{1,x},x]
```

`Fit` takes explicit data, basis expressions and a variable. Use
[statistics and units](STATISTICS-AND-UNITS.md) for additional supported forms.

## Equations and roots

```wolfram
Solve[{x+y==3,x*y==2},{x,y}]
Solve[x^2+1==0,x,Reals]
FindRoot[Cos[x]-x,{x,0,1}]
```

`FindRoot` requires two real sign-changing bracket endpoints, not a single guess.
Check discontinuities. `Solve` supports a domain argument for scalar equations,
not general systems; check real/integer constraints on system solutions yourself.
`NSolve` approximates finite symbolic solution sets; it is not an exhaustive
general numerical equation solver.

## Calculus and ODEs

```wolfram
D[Exp[-x^2]*Sin[x],x]
Integrate[Exp[-x^2],{x,-Infinity,Infinity}]
Normal[Series[Sin[x]/x,{x,0,8}]]
DSolve[{y''[t]+3*y'[t]+2*y[t]==Exp[-t],y[0]==0,y'[0]==1},y[t],t]
```

`DSolve` and `NDSolve` return different representations. Use the closest
[documented form](SUPPORTED-SYNTAX.md), not assumed Mathematica options or
replacement-rule output formats. FEM has a narrower [PDE scope](PDE.md).

## Matrices and indexed data

```wolfram
Block[{a,b},a={{4,1},{1,3}};b={1,2};{Det[a],Inverse[a],Dot[Inverse[a],b],Dot[a,Inverse[a]]}]
Block[{a,i},a={2,3,5};Sum[Part[a,i]^2,{i,1,3}]]
```

Use `Dot` for matrix multiplication and `Part[a,i,j]` for entries. Retain original
lists for data operations: `TableForm`/`MatrixForm` return exact matrices and have
limited formatting support. Newlines produce outputs without `Column`.

## Units and angles

```wolfram
UnitConvert[650[gr],"g"]
UnitConvert[650[gr]*(890[m/s])^2/2,"J"]
UnitConvert[3[m]+20[cm],"cm"]
Sin[90°]
```

`gr` is grain, `g` is gram. Bare angles are radians. Use `(x)[m]` or
`Quantity[x,"m"]` to attach a unit to a symbolic value; `x[m]` is a function call.
Arbitrary unit-bearing symbolic equation solving is not guaranteed.

## Reuse expressions instead of defining functions

```wolfram
Block[{f,x},f=x^3-2*x-1;{ReplaceAll[f,x->2],ReplaceAll[D[f,x],x->2],Table[ReplaceAll[f,x->k],{k,0,3}]}]
```

No `f[x_]:=...`, patterns, `/@`, slot functions `#...&`, or arbitrary packages.
Use expressions, `ReplaceAll`, `Table` and `Part`. Avoid `(* ... *)` comments in
calculation input; put explanations in text cells or `Labeled[value,"description"]`.
`Block[{...},...]` localizes temporary variables. Also use a new session per task.

## Plots and animation

```wolfram
Plot[{Sin[x],Cos[x]},{x,0,2*Pi}]
ParametricPlot[{Cos[t],Sin[t]},{t,0,2*Pi}]
Animate[Plot[Sin[x-a],{x,0,2*Pi}],{a,0,2*Pi}]
```

General `Manipulate` is unsupported; use supported `Animate` forms. `Plot2D`
means density plotting. Full JSON contains plot data, not a PNG; `--open-ui`
provides the interactive view. See supported options in the syntax reference.

## Recovery

| Observation | Next action |
| --- | --- |
| `ok:true`, but `unresolved:true` | Inspect function/form; simplify input or report unsupported work |
| Symbolic answer still has variables | Keep it symbolic or substitute requested data and use `N` |
| Exit 1 / engine error | Read `error`, fix syntax/domain; use a new session to avoid partial state |
| Timeout/cancel | Restore definitions in a fresh/cleared session |
| Missing PDE module | Report/install it only if this task requires it |
| Runtime missing | Use a complete installation; source launchers need the documented `.venv` |
| Calculation succeeds, UI fails | Keep outputs; select the desktop path and `open-ui --notebook PATH` |
| No contents in an older GUI | Use a supporting build; headings belong in `mode:"markdown"` cells |

For equations check substitution/residuals and the requested solution domain;
for approximate answers check precision and method assumptions. Do not assert
an unevaluated expression as a completed answer.
