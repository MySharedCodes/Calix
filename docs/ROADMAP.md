# Roadmap

Status: 0.1.28 engineering preview. This is a direction for development, not a
release schedule or a commitment to full Mathematica compatibility.

## Available

- Local notebook and calculator, shared inline formula editor, Markdown,
  multi-document workspace, saved outputs and stale-state handling.
- Exact and high-precision expressions, units, symbolic equations and calculus,
  statistics, fitting, native numerical roots, quadrature and ODE systems.
- Curves, surfaces, contours, parametric plots, animation and scientific scenes.
- Optional PDE examples, native element assembly and parallel sparse solution.
- CPU budget controls, selected SIMD kernels, CLI/JSONL/API and desktop handoff.
- Offline help, example catalog and documented language/model limits.
- Atomic notebook saves, on-disk recovery revisions and cell structure undo/redo.
- Independent arithmetic/numerical checks, bounded verification tiers and source
  provenance in packaged artifacts. Windows CI workflows are configured; remote
  execution awaits a repository.

See [supported syntax](SUPPORTED-SYNTAX.md) and [PDE scope](PDE.md) before choosing
a solver. Shipped features still need broader numerical and platform validation.

## Reliability First

- Reproduce clean Windows builds without private maintainer caches; automate
  core, optional-component and upgrade checks on clean machines.
- Expand independent verification of symbolic branches, units, conservation
  laws, contact stresses and mesh convergence.
- Improve conditional-solution reporting and errors for unsupported syntax.
- Test IME, keyboard navigation, formula editing and accessibility on more setups.
- Qualify recovery on clean Windows installations and real disk-space failures.

## Numerical and Language Work

- Evaluate stiff ODE solvers, event detection and more explicit error estimates.
- Improve adaptive plotting, singularity handling and user control of axes/styles.
- Extend solver coverage only with tests of domains, branches and precision.
- Improve unit-aware normalization for equations and lossless formula conversion.
- Extend the recorded source-engine performance baseline to packaged CLI and GUI
  startup, repeated use and representative FEM workloads.
- Run AVX-512 and AMX validation on matching hardware before claiming execution
  results there; current development hardware verifies AVX2.

## Public Distribution

- Decide application license and repository address after rights review.
- Audit source, assets, exact binary dependencies and third-party notices.
- Provide verified releases, hashes, private security reporting and contribution terms.
- Evaluate Windows signing and maintain current onboarding material.

[Release preparation](RELEASING.md) records the work required before publication.
No public release date has been selected.
