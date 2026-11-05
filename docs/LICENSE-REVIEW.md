# License Review For The Engineering Preview

Calix-owned source, documentation and examples are licensed under GNU GPL version 3 only (`GPL-3.0-only`), as selected on 2026-11-04. See [LICENSE](../LICENSE) for the complete terms and [licensing and signing status](LICENSING.md) for the current release state. This document records component selection and distribution constraints; third-party components retain their own licenses.

## GPLv3 Transition

The existing installers were built under the previous proprietary application declaration. They have not been rebuilt or signed as part of this change. The old selection criterion of allowing a proprietary application is no longer sufficient for a GPL release.

The optional Intel oneMKL / OpenMP runtime is dynamically loaded into Calix's process and carries restrictions absent from GPLv3. Compatibility of this combined distribution has not been established. Separate directories, optional installation and retaining notices do not settle that issue. No Intel linking exception is granted by the Calix application license. Before publishing a combined binary, replace the solver/runtime with a GPLv3-compatible alternative or obtain and document sufficient distribution rights. The release checker records this as pending while staged Intel runtime DLLs remain present.

GPL binary releases must provide the corresponding source required by GPLv3 section 6, including the matching application revision and necessary build/install scripts, together with applicable dependency source and notices. Shipping Eigen's archive alone does not fulfill the application's source obligations.

## Selected Components

- MIT/ISC: React, MathLive, CodeMirror, Cortex Compute Engine (math-input parsing only), KaTeX, Three.js, Plotly.js, Lucide, fflate (lossless workspace compression), Tiptap / ProseMirror (text editing), unified / remark / rehype (Markdown parsing and sanitizing) and their relevant dependencies. Only the MIT-licensed Tiptap packages are selected; no paid Tiptap service or proprietary extension is used.
- MIT/Apache dual-licensed: Tauri and supported Rust dependency paths.
- BSD: SymPy, mpmath, Pint, Boost-adjacent Python service dependencies where applicable.
- Boost Software License 1.0: native Boost.Math and Boost.Odeint.
- PSF: embedded CPython, plus its bundled component notices.
- PyInstaller: build tooling and its bootloader exception; preserve its complete COPYING text and exception when packaging the application.
- NSIS: the installer explicitly selects zlib compression and carries NSIS's COPYING text. The unused LZMA compression path has CPL terms, so it is excluded from the selected installer stub.

No GMP, MPFR, FLINT, GSL, GiNaC, Maxima, Mathics, Wolfram Engine or FFTW is selected. SymEngine and SUNDIALS remain future candidates.

## Optional PDE Component In 0.1.15

The optional PDE component selects unmodified scikit-fem 11.0.0 (BSD-3-Clause), NumPy 2.2.6 and SciPy 1.15.3 (BSD-3-Clause with bundled-component notices). It is installed as a separate directory, excluded from the frozen core. In 0.1.17, structural Q1 quad/hex integration and local matrices run in C++, using Eigen 3.4.0. Since 0.1.23 the sparse direct solver uses oneMKL PARDISO instead of Eigen SparseLU. The wing's Q2/Q1 assembly and nonlinear iteration remain in Python/scikit-fem. Dense numerical kernels use the wheel's native OpenBLAS/LAPACK binaries; rectangular Laplacian eigenproblems use native ARPACK. Preserve the complete component and bundled-runtime notices. Intel runtime compatibility is a separate unresolved distribution issue described above.

### Parallel Sparse Runtime In 0.1.23

CPU-only oneMKL 2025.3.1 is dynamically loaded from the optional PDE directory by Calix's C++ solver. Its unmodified DLLs carry the Intel Simplified Software License (October 2022), which allows binary redistribution with notices and prohibits reverse engineering/modification of those proprietary binaries. Intel OpenMP 2025.3.3 carries the Intel End User License Agreement for Developer Tools (August 2024), not a plain BSD/MIT license. Its distribution conditions include incorporation into the product, a reverse-engineering prohibition for Intel redistributables, passing through Intel's liability limitations, and the other accompanying conditions. `docs/licenses/INTEL-RUNTIME-TERMS.txt` supplies those product-facing terms; complete original licenses and bundled third-party statements are copied into both the optional runtime and installed notices. Intel endorsement/certification is not claimed.

This runtime selection predates the GPLv3 transition. The Intel OpenMP license also has a SaaS/service-bureau restriction. Only the CPU DLLs listed by hash in `components/pde/native/manifest.json` were selected: no MPI, cluster, SYCL, GPU, TBB-threading or offload binaries. License-only dependency records remain in the notice inventory for completeness. No Intel binaries are modified, disassembled or merged into Calix source. MPL-covered Eigen files remain separate unmodified headers. These facts do not establish GPL compatibility for the Intel runtime.

The Windows NumPy/SciPy wheels include OpenBLAS and LAPACK (BSD terms) and GCC runtime portions under GPL-3.0 **with the GCC Runtime Library Exception 3.1**. Preserve the exception and verify its eligibility conditions; do not classify these binaries as plain BSD. Calix does not modify these runtimes; retain the complete wheel license texts, including COPYING.RUNTIME. The NumPy wheel also carries a Microsoft VC runtime DLL; preserve applicable Microsoft redistribution terms. System-library and runtime exceptions must be assessed for the actual build and cannot be assumed for arbitrary bundled libraries.

Theme patterns are original code-native SVG tiles authored for Calix. The optional language data is Calix-authored. No external cartoon artwork or Wolfram code/assets is included. Mathematica is a syntax and feature reference only; this release implements a documented subset, not Mathematica v13 compatibility.

## MPL Transitive Components

Eigen 3.4.0 is compiled from unmodified headers with `EIGEN_MPL2_ONLY`, excluding its non-MPL optional modules. Preserve MPL-2.0 rights and source for covered files, and verify the covered files are eligible for GPLv3 combination under MPL section 3.3, including the absence of an applicable Incompatible With Secondary Licenses notice. The installer includes `notices/mpl-sources/eigen-3.4.0.zip`, the exact upstream source archive used for the build, plus COPYING.MPL2 and COPYING.README. The archive includes unused optional upstream modules under their original licenses; those modules are not compiled into Calix. Calix's own FEM and ABI files contain application code and are not modifications to Eigen files.

The Tauri dependency graph includes MPL-2.0 components: `option-ext`, `cssparser`, `cssparser-macros`, `dtoa-short`, and `selectors`. `option-ext` is on the runtime path; several parser components are on the build/procedural-macro path. The dependency files are unmodified. Preserve their MPL obligations and check secondary-license eligibility for the actual covered files used in the GPLv3 combination.

The package contains the exact original crate archives for these MPL components under `notices/mpl-sources/`, together with the MPL license text. Crate archives are gzip tar files and contain the corresponding component source. Calix's GPL corresponding source must also be supplied. The application license does not restrict rights granted independently by third-party licenses.

Earlier component choices favored permissive licenses to support a proprietary application. Future choices must instead be checked against GPL-3.0-only and the intended distribution; this license change does not itself add or replace any mathematics engine.

## Notices And Remaining Release Work

`scripts/notices.py` collects package versions, license identifiers and actual license files from installed JavaScript, Python and Windows-target Rust dependency graphs. Some included records describe build dependencies, so the notice set is conservative and is not a binary reachability proof. The upstream license supplements cover archives that omit their root license text. Font assets are copied from the MathLive/KaTeX distributions; preserve their component notices and recheck their upstream asset provenance before a public release.

`release/notices/components.json` records the component inventory. Python lock snapshots, npm and Cargo lockfiles, and release hashes identify the tested artifacts. Before public distribution, resolve the Intel runtime issue, review the exact installer and compiler runtime assets, confirm asset rights, document WebView2 and installer bootstrap terms, supply corresponding source, and verify trademark wording. Do not add an application EULA that restricts GPL rights. Public release remains a separate milestone.
