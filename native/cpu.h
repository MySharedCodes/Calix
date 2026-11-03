#pragma once
#include <cstdint>

using Gemm64 = void (*)(const double*, const double*, double*, int, int, int);
void calix_gemm_avx2(const double*, const double*, double*, int, int, int);
void calix_gemm_avx512(const double*, const double*, double*, int, int, int);
void calix_gemm_amx(const int8_t*, const int8_t*, int32_t*, int, int, int);
int calix_batch_avx2(const int32_t*, const double*, int, const double*, const double*, const double*, int, double*);
int calix_batch_avx512(const int32_t*, const double*, int, const double*, const double*, const double*, int, double*);
int calix_dispatch_batch(const int32_t*, const double*, int, const double*, const double*, const double*, int, double*);

#ifdef _WIN32
#define CALIX_CPU_API extern "C" __declspec(dllexport)
#else
#define CALIX_CPU_API extern "C" __attribute__((visibility("default")))
#endif

// Flags distinguish hardware capability from CPU + OS eligibility.
CALIX_CPU_API uint32_t calix_cpu_features();
CALIX_CPU_API int calix_simd_level();
CALIX_CPU_API int calix_dense_f64(const double*, const double*, double*, int, int, int, int);
CALIX_CPU_API int calix_dense_i8(const int8_t*, const int8_t*, int32_t*, int, int, int, int);
