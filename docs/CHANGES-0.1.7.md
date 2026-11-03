# Calix 0.1.7

- Ctrl+Enter evaluates the focused calculation cell. Alt+. cancels running notebook calculations, including Run all, through the existing worker cancellation path. Shift+Enter remains available.
- The projectile example uses the same directory row layout as every other complete notebook, in both interface languages.
- Replaced the 1988 and 2009 IMO notebooks with IMO 1979 Problem 1 (an exact alternating harmonic sum) and IMO 1978 Problem 1 (last digits of powers). The latter computes the minimum exponent sum and checks that its finite search includes every potentially smaller sum.
- Gaokao Mathematics In[1] describes its derivative, stationary point, monotonicity intervals, stationary value and plot. Its global bounds use exact limiting values and rational positive-coefficient certificates on a covering of the positive domain. The result is strict bounds 1 < f < 2 with infimum 1 and supremum 2; neither endpoint is attained. Computations and transformations are in calculation cells.
- Elastic double pendulum: keeps the small-amplitude analytic model, adds a separate nonlinear initial condition with spring angles 60 and -45 degrees, and animates only the large-amplitude numerical solution. Curve comparisons use separate plots, since initial conditions differ.
- Five-ball chain: replaces the five-position plot and gap plot with bottom-ball, second-from-bottom and free-fall displacements measured from their respective initial positions, plus differences from free fall. Exact motion, initial accelerations and animation remain.
- Adds a planar equal-mass three-body example with Newtonian gravity, numerical trajectories, energy/momentum/angular-momentum diagnostics, and three moving bodies over the trajectories. G=1 and dimensionless initial data are stated in the notebook.
- Explicit ODE forces remain factored when already isolated, avoiding expression expansion before native compilation. Integration and composite sampled evaluation continue to run in C++.
- Adds exact Numerator, Denominator, CoefficientList, IntegerLength, PowerMod and GCD; Reduce supports a single real variable with assigned parameters. CoefficientList is limited to 100,000 entries. PlotLegends accepts one short text label per ordinary 2D curve.
- No new dependencies. Existing edited notebooks are preserved; revised cases use a new example identity.
