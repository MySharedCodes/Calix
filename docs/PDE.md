# PDE module, Version 0.1.27

The component is optional. The ordinary calculator, units and ODE workflows
remain available without it. Missing components produce an installation message.

## Explicit Finite Elements

The bridge notebook supplies coordinates, element connectivity, coefficient
tensors, DOF projections, loads and constraints. It uses existing Wolfram names:
`ToElementMesh`, `QuadElement`, `HexahedronElement`, `LineElement`,
``NDSolve`VariableData``, ``NDSolve`SolutionData``, `InitializePDECoefficients`,
`InitializePDEMethodData`, `DiscretizePDE`, `SparseArray`, and `LinearSolve`.
The names containing a backtick denote Wolfram contexts.

This release supports one explicit element family per mesh and constant real
diffusion, reaction, conservative-convection, convection and load tensors.
Coordinates and tensors must agree in dimension. Structural assembly accepts
Q1 quadrilaterals in 2D and Q1 hexahedra in 3D, with interleaved nodal fields.
`IntegrationOrder` 1 uses one Gauss point per element; 2/3 use two points per
coordinate; 4 uses three. The bridge explicitly combines reduced and full
integration for transverse shear. C++ computes Jacobians, quadrature, coefficient
contractions and local matrices; Python constructs the global sparse storage.
oneMKL PARDISO performs parallel sparse factorization through the C++ interface,
with symmetric equilibration and iterative refinement. Full real unsymmetric
CSR storage also accommodates symmetric, indefinite and saddle systems. The
thread-local limit follows CPU Workers; inputs below 512 rows use one thread
to avoid scheduling overhead. A failed factorization, perturbed singular pivot,
nonfinite result or excessive residual is an error. The optional PDE module
includes the unmodified CPU runtime and its distribution licenses.

The default bridge grid has 1024 deck quadrilaterals, 2048 tower hexahedra and
142 prestressed trusses. The 14 physical hangers stay fixed under refinement.
The deck is a membrane plus Reissner-Mindlin plate; the towers are 3D linear
elastic solids. Shared translations couple coincident nodes through Boolean
projection matrices. The model solves an added load about an assumed tensioned
equilibrium; it does not perform cable form finding or nonlinear slackening.
Tower point connections do not resolve connection stresses. The notebook reports
linear residual, vertical force balance, strain energy, displacement and minimum
total cable tension. Refinement n=8 to n=12 changes maximum deflection by about
0.56% for the supplied load; this does not establish structural design adequacy.

## Steady Fluid Component

The wing notebook uses `FluidFlowPDEComponent`, `DirichletCondition`,
`NDSolveValue`, `Element`, `RegionDistance`, `Polygon`, `DensityPlot` and
`StreamPlot`. The dynamic viscosity is an authored expression of wall distance
and velocity gradients, evaluated during iteration. It is not a model-name switch.

Supported scope: a structured annular quadrilateral grid, one closed wall,
constant positive density, zero body force, two velocity components and pressure,
no slip on marker 1, constant unit far-field velocity on marker 2 and one pressure
reference at the first outer node. The mesh and boundary connectivity are checked.
Reynolds number is 100-20000 and incidence is within four degrees. The current
algebraic-viscosity path requires a wall-distance term. Other boundary conditions
or additional options are rejected. This is not a general nonlinear PDE interface.

The default grid has 3456 body-fitted quadrilaterals, 128 nodes per ring and 28
rings. Velocity is Q2 and pressure Q1 (Taylor-Hood). Python/scikit-fem assembles
the nonlinear Picard systems; each sparse solve uses the C++ oneMKL PARDISO interface. Molecular
viscosity continuation and SUPG streamline stabilization are used. Iteration must
converge below the relative-update threshold. Pressure-space divergence and flux
are independently checked in tests. Plot fields interpolate FE vertex values;
the plotting interpolation is not the full Q2 basis evaluator.

Prandtl mixing length with van Driest damping is a simplified algebraic closure.
It has no turbulence transport equation, natural-transition prediction, separation
model or experimental calibration. It does not predict stall. Refinement and
iteration convergence cannot validate the closure against physical measurements.

## Stress And Flow Postprocessing

The bridge ends with an undeformed stress cloud, including all four towers,
deck, main cables and hangers. Tower von Mises stress is recovered from the
cell-centre displacement gradient and 3D isotropic elasticity. Deck values are
the larger in-plane von Mises stresses at its upper/lower surfaces, combining
membrane and bending terms. Transverse shear is not included in this surface
quantity. Adjacent cell-centre scalar values are averaged at nodes; this smooths
local peaks and is not an equilibrated stress recovery estimator. Cable colors
represent total axial stress, including the initial tension. Other components
show incremental stress. The common scale is MPa.

`GraphicsComplex` supports indexed convex `Polygon` faces and `VertexColors`.
`ColorData["TemperatureMap"]` provides Calix's interpolated seven-stop palette;
`BarLegend` and `Legended` attach a scalar color scale. The wing combines
`DensityPlot` and `StreamPlot` with `Show` to overlay streamlines on speed.

## Other Supported PDEs

- `DSolve` / `DSolveValue`: scalar first-order PDEs supported by SymPy pdsolve;
  equations with one active derivative coordinate reduce to ODEs, including fully
  developed laminar flow. Homogeneous heat/wave equations on an interval use
  sine separation with zero endpoint values. Wave separation assumes zero initial
  velocity. Finite sine profiles yield exact expressions; other profiles may yield
  Fourier series when coefficients can be integrated.
- Rectangular 2D Poisson: scalar P1 triangular FEM, prescribed source and a value
  condition on every edge, with consistent corner data. Sparse solution uses Eigen.
- Homogeneous 1D heat/wave: centered spatial differences and native SciPy time
  integration, fixed endpoints and an initial profile. Wave initial velocity is zero.
- `NDEigensystem`: rectangular negative Laplacian with homogeneous Dirichlet
  data, P1 stiffness/mass matrices and native ARPACK; 1-12 modes.
- `Grad`, `Div`, `Laplacian`: symbolic Cartesian differential operators.

Legacy `FEMBridgeSolve`, `WingFlowSolve`, `PDEValue`, `PDEInfo` and `PDEPlot`
remain for old saved notebooks. The new bridge and wing examples do not use them.
General CAD import, arbitrary nonlinear PDE systems, general 3D CFD, SST/SA
turbulence transport and full Mathematica v13 compatibility are not implemented.

## Runtime And Packaging

Fresh installations default to the Windows physical-core count, obtained from
`GetLogicalProcessorInformationEx`; logical SMT threads are reported separately.
Existing saved worker preferences are preserved. `CALIX_MAX_WORKERS=8` sets the
debug default to eight on machines with at least eight cores. General BLAS/OpenMP
work defaults to one thread; supported native operations use the selected thread
budget explicitly. The worker cap bounds concurrent calculations and native
thread limits. PARDISO uses that budget above its small-system threshold; this
does not imply full CPU occupancy during all phases. Cancellable process
isolation applies to all calculations, with a 180-second per-cell limit.

The optional directory carries NumPy, SciPy and scikit-fem outside the frozen
core. Eigen headers are compiled into the native DLL; the exact upstream source
archive and license texts are included under notices. `EIGEN_MPL2_ONLY` excludes
non-MPL optional code. See LICENSE-REVIEW.md for license details.

Installer switches: `/PDE=0|1`, `/LANGUAGES=0|1`, `/THEMES=0|1`. Existing
choices, notebooks and preferences are retained on upgrade.
