# Calix 0.1.16

- Colored themes now give the upper-left Calix mark a matching pink, ocean-blue or forest-green fill. White and black retain the original mark.
- Pink wallpaper replaces the stars with original, lightly drawn cats, rabbits and bears. The artwork is bundled with the optional theme component and needs no network requests.
- The air-resistance notebook now takes 650[gr] (grain), 890[m/s] and 7[km] directly. Separate linear and quadratic drag coefficients are inferred from the maximum landing range over launch angles.
- C++ Boost.Odeint integrates the flight; a downward ground event ends the flight; a coarse angular scan and bounded Brent search find the best launch angle; TOMS748 calibrates the coefficient.
- Linear velocity and displacement retain exponential analytical expressions after numerical calibration. Quadratic velocity is numerical, with displacement obtained from its integral. Both sections include time plots and a trajectory animation ending at landing.
- Added a conic notebook based on the 2022 Paper B ellipse problem: solve the ellipse, determine secant slopes, verify the fixed point exactly, check vertical secants, and draw a valid configuration. Calculation variables use single letters or subscripts; visible outputs have labels.

## Extended calculation functions

```
ProjectileRange[c,m,v,g,angle,"Linear"|"Quadratic"]
ProjectileMaxRange[c,m,v,g,"Linear"|"Quadratic"]
ProjectileOptimum[c,m,v,g,"Linear"|"Quadratic"]
ProjectileVelocity[c,m,v,g,angle,{t,0[s],T},"Linear"|"Quadratic"]
```

Inputs require compatible units. Coefficients have units kg/s for the linear law and kg/m for the quadratic law. Optimum returns {maximum range, launch angle in degrees, flight time}. Velocity expressions use the numeric time coordinate in seconds, with output units m/s; integrate them with bounds in seconds. The model assumes constant gravity, constant drag, level ground, and no wind.

The Calix extension `NSolve[equation,{x,lower,upper}]` finds one real root in a finite sign-changing bracket. This interval syntax is an extension, not a claim of exact Wolfram Language compatibility. It rejects nonfinite evaluations and verifies the result's residual. It does not enumerate every root.

For an unknown unit-bearing coefficient, use `k*1[kg/m]`; the bare unassigned expression `k[kg/m]` is interpreted as a function call. Definite integration supports unit-bearing bounds and quantity-valued integrands. Unit-aware comparisons normalize compatible quantities before forming the symbolic equation.

## Licenses

No new runtime dependencies were added. The numerical core continues to use Boost under the Boost Software License, symbolic calculations use SymPy, and unit conversion uses Pint. The new theme drawings are original project artwork. Existing third-party notices remain included. See LICENSE-REVIEW.md for the dependency assessment and outstanding legal review limits.
