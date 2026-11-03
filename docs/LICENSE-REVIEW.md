# License Review For The Engineering Preview

Calix application code is proprietary. This document records engineering selection decisions, not a legal opinion or a warranty of compliance for future releases.

## Selected Components

- MIT/ISC: React, MathLive, CodeMirror, Cortex Compute Engine (math-input parsing only), KaTeX, Three.js, Plotly.js, Lucide, fflate (lossless workspace compression) and their relevant dependencies.
- MIT/Apache dual-licensed: Tauri and supported Rust dependency paths.
- BSD: SymPy, mpmath, Pint, Boost-adjacent Python service dependencies where applicable.
- Boost Software License 1.0: native Boost.Math and Boost.Odeint.
- PSF: embedded CPython, plus its bundled component notices.
- PyInstaller: build tooling and its bootloader exception permit distribution of non-free applications. The PyInstaller exception is essential to this packaging decision and its COPYING text is included.
- NSIS: the installer explicitly selects zlib compression and carries NSIS's COPYING text. The unused LZMA compression path has CPL terms, so it is excluded from the selected installer stub.

No GMP, MPFR, FLINT, GSL, GiNaC, Maxima, Mathics, Wolfram Engine or FFTW is selected. SymEngine and SUNDIALS remain future candidates.

## Optional PDE Component In 0.1.15

The optional PDE component selects unmodified scikit-fem 11.0.0 (BSD-3-Clause), NumPy 2.2.6 and SciPy 1.15.3 (BSD-3-Clause with bundled-component notices). It is installed as a separate directory, excluded from the frozen core. In 0.1.17, structural Q1 quad/hex integration and local matrices run in C++, using Eigen 3.4.0. Since 0.1.23 the sparse direct solver uses oneMKL PARDISO instead of Eigen SparseLU. The wing's Q2/Q1 assembly and nonlinear iteration remain in Python/scikit-fem. Dense numerical kernels use the wheel's native OpenBLAS/LAPACK binaries; rectangular Laplacian eigenproblems use native ARPACK. These terms permit a proprietary application with attribution and preservation of supplied notices. No GPL-only FEM or CFD engine is linked into Calix.

### Parallel Sparse Runtime In 0.1.23

CPU-only oneMKL 2025.3.1 is dynamically loaded from the optional PDE directory by Calix's C++ solver. Its unmodified DLLs carry the Intel Simplified Software License (October 2022), which allows binary redistribution with notices and prohibits reverse engineering/modification of those proprietary binaries. Intel OpenMP 2025.3.3 carries the Intel End User License Agreement for Developer Tools (August 2024), not a plain BSD/MIT license. Its distribution conditions include incorporation into the product, a reverse-engineering prohibition for Intel redistributables, passing through Intel's liability limitations, and the other accompanying conditions. `docs/licenses/INTEL-RUNTIME-TERMS.txt` supplies those product-facing terms; complete original licenses and bundled third-party statements are copied into both the optional runtime and installed notices. Intel endorsement/certification is not claimed.

This selection is for a local desktop product. The Intel OpenMP license's SaaS/service-bureau restriction means a hosted offering needs a separate license decision. Only the CPU DLLs listed by hash in `components/pde/native/manifest.json` are shipped: no MPI, cluster, SYCL, GPU, TBB-threading or offload binaries are included. License-only dependency records remain in the notice inventory for completeness. No Intel binaries are modified, disassembled or merged into Calix source. MPL-covered Eigen files remain separate unmodified headers; their file-level source obligations do not apply to the proprietary runtime.

The Windows NumPy/SciPy wheels include OpenBLAS and LAPACK (BSD terms) and GCC runtime portions under GPL-3.0 **with the GCC Runtime Library Exception 3.1**. This is a material exception: eligible compiled combinations may be conveyed under terms chosen by the distributor, including proprietary terms. Calix does not modify these runtimes; retain the complete wheel license texts, including COPYING.RUNTIME, and do not classify these binaries as plain BSD. The NumPy wheel also carries a Microsoft VC runtime DLL; preserve applicable Microsoft redistribution terms. This selection does not authorize using unrelated GPL numerical libraries.

Theme patterns are original code-native SVG tiles authored for Calix. The optional language data is Calix-authored. No external cartoon artwork or Wolfram code/assets is included. Mathematica is a syntax and feature reference only; this release implements a documented subset, not Mathematica v13 compatibility.

## MPL Transitive Components

Eigen 3.4.0 is compiled from unmodified headers with `EIGEN_MPL2_ONLY`, excluding its non-MPL optional modules. MPL-2.0 permits the proprietary larger work while retaining source and license rights for covered files. The installer includes `notices/mpl-sources/eigen-3.4.0.zip`, the exact upstream source archive used for the build, plus COPYING.MPL2 and COPYING.README. The archive includes unused optional upstream modules under their original licenses; those modules are not compiled into Calix. Calix's own FEM and ABI files contain application code and are not modifications to Eigen files.

The Tauri dependency graph includes MPL-2.0 components: `option-ext`, `cssparser`, `cssparser-macros`, `dtoa-short`, and `selectors`. `option-ext` is on the runtime path; several parser components are on the build/procedural-macro path. MPL is file-level copyleft and permits a larger proprietary work, subject to its obligations for covered files. The dependency files are unmodified.

To preserve source availability without exposing Calix's application code, the package contains the exact original crate archives for these MPL components under `notices/mpl-sources/`, together with the MPL license text. Crate archives are gzip tar files and contain the corresponding component source. The application license does not restrict rights granted by third-party licenses.

This is an explicit exception to the preference for permissive-only dependencies, because these particular file-level terms fit a proprietary application. GPL-only mathematics engines remain excluded.

## Notices And Remaining Release Work

`scripts/notices.py` collects package versions, license identifiers and actual license files from installed JavaScript, Python and Windows-target Rust dependency graphs. Some included records describe build dependencies, so the notice set is conservative and is not a binary reachability proof. The upstream license supplements cover archives that omit their root license text. Font assets are copied from the MathLive/KaTeX distributions; preserve their component notices and recheck their upstream asset provenance before a public release.

`release/notices/components.json` records the component inventory. Python lock snapshots, npm and Cargo lockfiles, and release hashes identify the tested artifacts. Before external commercial distribution, review the exact installer and compiler runtime assets, confirm every asset's licensing, document WebView2 and installer bootstrap terms, supply the final EULA and verify trademark wording. Public release remains a separate milestone.
