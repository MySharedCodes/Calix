# CPU Acceleration

Calix's Windows x64 DLL contains separately compiled baseline, AVX2, AVX-512
and AMX-INT8 code. No global `/arch:AVX2` or `/arch:AVX512` requirement is imposed
on the executable or generic solvers. CPUID checks include OSXSAVE, XGETBV and
the required register-state masks before an instruction-specific entry is used.
The AVX-512 build requires F, DQ, BW and VL. Unsupported processors keep the
baseline path. `CALIX_SIMD=scalar` disables automatic SIMD selection;
`CALIX_SIMD=avx2` caps floating-point dispatch at AVX2.

## Supported Operations

- Double-precision dense matrix multiplication: C++ scalar, AVX2 and AVX-512.
  `Dot` selects the native implementation for real machine-precision matrices
  with at least 32768 multiply-add terms. For example,
  `a=Table[N[1/(i+j),15],{i,1,32},{j,1,32}]; Dot[a,a]`.
  Exact rationals, symbolic values, complex numbers and higher-precision floats
  retain the symbolic path. Calix's existing 16-digit default `N` values have
  56-bit internal precision, so they are conservatively kept on that path too.
- Batched expression sampling: constants, x/y/z, arithmetic, absolute value,
  square root, and bounded constant integer powers / half-powers. This benefits
  compatible plot sampling. Transcendental functions or unsupported bytecode
  use the original scalar evaluator. Vector tails are evaluated safely.
- Exact signed INT8 matrix multiplication: AMX tile packing, INT32 accumulation.
  Matrices whose integer entries fit [-128,127] are eligible. The inner dimension
  is limited to 65536, so the worst possible accumulation fits signed INT32.
  Nonmultiples of tile dimensions are zero-padded and copied back within bounds.
  Without AMX, these products use scalar C++ with the same exact integer result.

AMX is not a double-precision floating-point accelerator. No FP64 scientific
calculation is silently converted to BF16 or INT8. BF16/FP16 AMX products are
not exposed in this release. Eigen's sparse factorization and finite-element
assembly remain separate kernels; this update does not claim that every solver
runs AVX-512 or AMX. Optional NumPy/SciPy wheels also perform their own CPU dispatch.

## AMX Operating-System Support

The INT8 kernel requires AMX-TILE and AMX-INT8 hardware bits plus enabled tile
configuration/data state. When available, Windows
`EnableProcessOptionalXStateFeatures` is called before use. An illegal-instruction
guard catches an OS denial; automatic dispatch falls back, while an explicit
native test request reports that the path is unavailable. Health diagnostics
distinguish hardware capability and OS state.

## Verification

The development machine is an Intel Core i9-13900HX. It supports AVX2 and does
not expose AVX-512 or AMX. AVX2 is tested against independent NumPy results,
including unaligned tails, plus scalar comparisons. The AVX-512 and AMX code
is compiled and checked for the corresponding instructions, but has not been
executed on matching hardware in this release. Such a machine is still required
for final numerical/performance validation of those two paths. Unsupported
forced-path requests are tested to fail without executing the instructions.

`/api/health` reports `cpu_features`, including compiled paths, CPU/OS flags and
the selected floating-point path. All debugging uses 8 Workers. The worker cap
and vector width are independent settings.

## CPU Budget And Actual Execution (0.1.22)

The preference now controls the native thread limit as well as the maximum
number of simultaneous calculation processes. On Windows, each calculation
process is confined to the same selected physical-core masks (processor group
0); the UI process is unaffected. Multiple concurrent calculations share this
CPU budget. A topology/affinity result is returned with execution diagnostics.

Native dense FP64 matrix products partition independent rows across threads.
Triangle, quadrilateral and hexahedral element integration partitions independent
elements. Small inputs stay serial to avoid thread startup costs. The matrix
SIMD path remains independently selected by CPU and OS capability checks.

Each calculation returns `execution.thread_limit`, `threads_used` and operation
records with path, call count and actual thread count. Results show this metadata
when native matrix products, element assembly or sparse solves were performed.
Since 0.1.23 sparse direct solves use `oneMKL PARDISO`, with its thread-local
limit set from CPU Workers. The runtime's dynamic thread reduction is disabled;
small systems below 512 rows are explicitly assigned one thread. Operation
metadata reports the solver's assigned team limit, not a guarantee of full CPU
occupancy during every phase. Benchmark CPU time divided by wall time verifies
parallel participation separately. Symbolic evaluation, most notebook loops,
mesh generation and stress postprocessing are not automatically parallelized.
An 8-core limit does not imply that every phase can occupy all 8 cores.

The core DLL loads the CPU-only runtime from the optional PDE directory. Missing
runtime files produce an installation error; no silent SparseLU fallback remains.
PARDISO handles all real sparse direct solves through full unsymmetric CSR,
including symmetric indefinite saddle systems. Its CPU instruction dispatch
belongs to oneMKL and is independent of Calix's own dense/plot SIMD dispatch.
