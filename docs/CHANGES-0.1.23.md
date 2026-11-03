# Calix 0.1.23

Replace the serial Eigen SparseLU direct solver with oneMKL PARDISO, called
from C++ and loaded from the optional PDE module. The CPU Workers preference
sets the solver's thread-local limit. Small systems remain one-thread PARDISO.
There is no silent fallback to SparseLU when the runtime is missing.

Preserve symmetric equilibration, residual checks and iterative refinement.
Reject singular/perturbed factorization and nonfinite data. Update result
diagnostics to identify PARDISO and its assigned team size. Preserve complete
oneMKL and Intel OpenMP licenses, third-party notices and product-facing runtime
terms; CPU runtime DLLs stay outside the frozen core.

The full-gear stress overview uses the 95th percentile of recovered nodal stress
as its color maximum, with larger values saturated red. Actual peak outputs and
the contact-detail scale remain unchanged. This expands low and moderate stress
variations without altering solved values. Unmodified 0.1.21/0.1.22 gear source
cells are migrated; edited calculation sources are preserved.

Development-machine tests with an 8-physical-core budget compared the exact same
matrices and right-hand sides. Warm median wall times, including ABI conversion:

| Matrix | Eigen SparseLU, 1 thread | PARDISO, 1 thread | PARDISO, 8 threads |
| --- | ---: | ---: | ---: |
| Gear contact, 27112 unknowns | 95.5 ms | 107.4 ms | 57.0 ms |
| 3D Poisson, 10648 unknowns | 381.9 ms | 69.4 ms | 30.9 ms |

The 8-thread cases used about 7.5 CPU-seconds per wall-second during measured
calls. Gear solutions differed from SparseLU by approximately 4.4e-13 in relative
2-norm. These timings describe sparse solve calls, not the complete notebook;
mesh generation, interpreter overhead and stress postprocessing still contribute.

The traditional calculator now shares the notebook calculation editor in one
fixed cell. It supports inline mathematical formulas, Ctrl+Enter evaluation,
Alt+. cancellation, formula-preserving history recall and a searchable symbol
palette with Esc-alias-Esc tooltips. Mathematical keypad labels insert the same
integral, sum, product, root and other templates as notebook shortcuts. Saving
and adding cells are unavailable in this mode. Degree notation in mathematical
input is translated to executable radian expressions.

Preserve the Pi constant during mathematical-input conversion. The Greek
character catalog previously overwrote its mapping with capital Pi, causing
the definite integral of sin(x) from 0 to pi to remain 1-cos(capital Pi).
The same input now evaluates exactly to 2, covered by conversion and UI tests.
