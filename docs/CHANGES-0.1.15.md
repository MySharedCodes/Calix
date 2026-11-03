# Calix 0.1.15

- Expression outputs have a copy-to-input button beside clipboard copy. It
  creates a calculation cell immediately below the originating cell, including
  individual outputs inside labeled or grouped results, and focuses that input.
- Five persisted interface styles: white, black, pink, ocean and forest. Colored
  styles carry original restrained pattern tiles. Editors and 2D/3D plot surfaces
  follow the selected style.
- Optional PDE component: symbolic PDE reduction/separation, rectangular scalar
  Poisson FEM, heat/wave method of lines, rectangular Laplacian eigensolutions,
  and Cartesian differential operators. See `PDE.md` for exact supported syntax
  and limits. Full Mathematica v13 functionality is not implemented.
- Two engineering notebooks with equations, material properties, geometry,
  boundary conditions, mesh/solver details, diagnostics and refinement:
  mixed-dimensional suspension bridge FEM and steady NACA0012 wing-section flow.
- Bridge towers use 3D tetrahedra, the deck uses 2D membrane/Morley plate triangles,
  and prestressed cables/hangers use 1D trusses. The model solves incremental
  service load about an assumed prestressed state, without nonlinear form finding.
- Wing flow uses body-fitted Taylor-Hood elements and a damped algebraic
  mixing-length turbulence closure for attached-flow instruction. Lift/drag
  remain mesh-sensitive and have no experimental calibration.
- NSIS components page separately selects PDE/FEM/Flow, extra languages and
  themes. Deselecting a component removes its managed files on upgrade; core
  mathematics remains available. Silent component switches are documented in
  `PDE.md`. User notebooks and preferences are retained.
- The extra language dictionaries and theme artwork are external resources,
  excluded from the core frontend bundle. Numerical PDE libraries are outside
  the frozen core service. Added library notices include OpenBLAS/LAPACK and
  the GCC Runtime Library Exception supplied by the Windows wheels.

The Windows installer is unsigned. This is an engineering preview, with numerical
and model limitations recorded in the notebooks and `PDE.md`.
