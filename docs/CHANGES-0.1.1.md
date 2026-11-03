# Calix 0.1.1

- Notebook content zoom: Ctrl+mouse wheel, 5% steps, bounded to 70%-160%, persisted locally. The percentage button resets to 100%. Navigation and toolbars do not zoom.
- The traditional calculator panel replaces the scientific calculator label. Three button pages provide basic arithmetic, functions and solvers. RAD/DEG state is removed. A postfix degree button inserts `°`; unmarked trigonometric arguments use radians. Examples: `Sin[30°]`, `Cos[(45+45)°]`.
- Markdown cells support editing, preview, GFM tables/lists and inline/display mathematics. Raw HTML is not enabled. Cells are saved as text and skipped during computation.
- First-run notebook: a two-dimensional projectile with linear drag. A symbolic ODE system yields velocities; those results are used directly in definite integrals for displacement, then two time plots and a parametric trajectory. The worked example includes assumptions, SI units, initial conditions and symbolic consistency checks.
- Existing autosaves are preserved. The physical notebook is available from the example library and as `examples/00-projectile-with-linear-drag.calix`.
- Explicit numerical calculations offer ten randomly selected examples, ranging from `1+1` through exact arithmetic, complex numbers, finite/infinite sums, products and hypergeometric functions. Symbolic categories each offer several examples. Consecutive clicks avoid an immediate repeat when multiple variants exist.
- The backend accepts degree postfixes, list-valued numerical approximation and replacement rules returned as equations from DSolve. These additions are tested against the worked physics problem.
