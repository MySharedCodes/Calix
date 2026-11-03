# Calix 0.1.4

- Example buttons append calculation cells to the current notebook. Complete worked examples append their text and calculation cells while retaining the current title and session.
- Explicit numerical examples contain ten rows. Each row draws from four alternatives and avoids its previous selection, including matrix multiplication, determinants, inverses and transposes.
- UnitConvert output includes square brackets in typeset and plain output. Compound unit arithmetic simplifies to common derived units, with an independent sidebar unit calculator. Unit arithmetic and conversion examples each show five results.
- Statistics includes descriptive measures, quantiles, correlations, average-rank Spearman correlation, least-squares fitting, seven common distributions, PDF/CDF/inverse CDF operations, one-sample two-sided t/z tests, histograms and data plots. Four example groups cover these workflows.
- The starter problem uses quadratic vector drag: -c*sqrt(vx^2+vy^2)*(vx,vy). A new C++ Boost coupled Dormand-Prince solver integrates velocities and displacement together. In[2] is r=Integrate[v,{t,0,t}]. Two displacement-time curves and a trajectory animation use the same numerical solution.
- Three worked challenge examples: 2016 Gaokao Physics Paper III Problem 25's final part; 2008 Jiangxi Mathematics Problem 22; IMO 1988 Problem 6. Each includes source references, independently written derivations and executable verification.
- Fixed Pint Fraction-exponent formatting in compound units on Python 3.12, and finite-distribution CDF handling.

No new third-party dependencies were added. Statistics uses the existing SymPy/mpmath stack; native ODE solving uses Boost under its existing license. This is a supported subset rather than complete Mathematica compatibility.
