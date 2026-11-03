# Get Started

This walkthrough uses Calix 0.1.28 on Windows x64. For installation and optional
components, see [installation (中文)](INSTALLATION.md). The packaged application
contains its calculation service; you do not need Mathematica, Python or Node.js
to use the installer. The public repository and license are still undecided;
the current [LICENSE](../LICENSE) applies.

## Create a Notebook

Wait for the engine status to become ready. Choose **New notebook** in the sidebar,
then edit the title. Paste these lines into a calculation cell and press
**Ctrl+Enter**:

```wolfram
1/3 + 1/6
N[Pi, 30]
UnitConvert[72[km/h], "m/s"]
```

The results are `1/2`, a 30-digit approximation to π and `20[m/s]`. Each new line
produces another result. A semicolon at the end of a line suppresses its output.
Exact fractions stay exact until you request a numerical approximation with `N`.

## Use Variables and Solve an Equation

Add a calculation cell with the toolbar button:

```wolfram
m = 2[kg];
v = 3[m/s];
1/2 m v^2
Solve[x^2-5*x+6 == 0, x]
```

The energy is `9[J]`; the roots are 2 and 3. Use `=` for an assignment and `==`
for an equation. Function names are case-sensitive; brackets `[]` hold arguments,
braces `{}` hold lists, and `^` means a power.

Units participate directly in arithmetic. Angles default to radians; `Sin[90°]`
uses degrees. Unit names are case-sensitive: `g` means grams and `gr` means grain.
Use `(x)[m]` or `Quantity[x,"m"]` for a symbolic quantity.

## Solve and Plot an ODE

```wolfram
DSolve[{y'[t]+2*y[t]==0, y[0]==3}, y[t], t]
Plot[3 Exp[-2 t], {t,0,3}]
```

The solution is $y(t)=3e^{-2t}$. Click a plot before using its wheel zoom; otherwise
the wheel scrolls the notebook. The plot toolbar offers reset and PNG export.

For a numerical initial-value solution, use:

```wolfram
u = NDSolveValue[{y'[t]==-y[t],y[0]==1}, y[t], {t,0,5}];
Plot[u[t], {t,0,5}]
```

The dependent argument is `y[t]`. Numerical solver values are defined only on the
solved interval. Native numerical solvers use double precision, independently of
the precision requested for symbolic `N`.

## Add Animation and Text

```wolfram
Animate[Plot[Sin[x-a], {x,0,2 Pi}], {a,0,2 Pi}]
```

Use the playback controls or timeline. Choose **Text cell** to add Markdown;
inline mathematics uses `$...$`, display mathematics uses `$$...$$`. Double-click
a text preview to edit it, then press Shift+Enter to preview.

The calculator panel has the same input editor in a single temporary cell.
Use notebooks when you want multiple cells or saved work.

## Enter Formulas

Ctrl+6 creates an exponent, Ctrl+2 a radical. For special symbols, press Esc,
type an abbreviation, then press Esc or Enter. Examples: `a` → α, `intt` → an
indefinite integral, `dint` → a definite integral, `sum` → a summation, `frac` →
a fraction, `pdiff` → a partial derivative, `mat` → a matrix. Fill every template
slot before evaluating. A symbol being available does not imply that every
mathematical structure involving it has a solver.

## Save and Continue

Ctrl+S saves a `.cixnb` file; Ctrl+Shift+S opens **Save as**. Files retain inputs
and outputs, not running kernel variables. On reopening, use **Run all** to rebuild
definitions. It resets the current session and evaluates from the top.

Alt+. cancels the active calculation and clears that session's variables.
After cancellation or timeout, rerun the definitions you need. F1 opens offline
help without executing any examples. Ctrl+wheel changes notebook zoom from
70% to 160%.

## Find Examples and Help

Full example notebooks open as separate documents. Function demonstrations insert
a calculation cell into the active notebook. Start with air resistance, elastic
pendulums or units. Numerical FEM examples require the optional **PDE module**.

Calix accepts a Wolfram-style subset, not arbitrary Mathematica programs.
`FindRoot[f,{x,a,b}]` requires a sign-changing bracket; `NSolve` approximates
finite symbolic solution sets. See [syntax reference](SUPPORTED-SYNTAX.md),
[statistics and units](STATISTICS-AND-UNITS.md), [PDE limits](PDE.md) and
[CLI/API](../API.md). The full [user guide](USER-GUIDE.md) and
[troubleshooting guide](TROUBLESHOOTING.md) are currently in Chinese.

For development or reproducible reports, read [Contributing](../CONTRIBUTING.md).
