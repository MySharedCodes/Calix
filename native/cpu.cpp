#include "cpu.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <intrin.h>
#include <immintrin.h>
#include <windows.h>
#include "parallel.h"

namespace {
uint32_t detect() {
    int r[4]{};
    __cpuid(r, 0);
    if (r[0] < 7) return 0;
    __cpuidex(r, 1, 0);
    const bool xsave = (r[2] & (1 << 27)) && (r[2] & (1 << 28));
    const bool fma = (r[2] & (1 << 12)) != 0;
    const uint64_t state = xsave ? _xgetbv(0) : 0;
    __cpuidex(r, 7, 0);
    uint32_t flags = 0;
    if (r[1] & (1 << 5)) flags |= 1;
    if ((flags & 1) && fma && (state & 6) == 6) flags |= 2;
    const uint32_t zmm = (1u << 16) | (1u << 17) | (1u << 30) | (1u << 31);
    if ((static_cast<uint32_t>(r[1]) & zmm) == zmm) flags |= 4;
    if ((flags & 4) && (flags & 2) && (state & 0xe6) == 0xe6) flags |= 8;
    if ((r[3] & (1 << 24)) && (r[3] & (1 << 25))) flags |= 16;
    if ((flags & 16) && (state & 0x60000) == 0x60000 &&
        (GetEnabledXStateFeatures() & 0x60000) == 0x60000) flags |= 32;
    return flags;
}

void scalar(const double* a, const double* b, double* c, int m, int n, int k) {
    for (int i = 0; i < m; ++i) for (int j = 0; j < n; ++j) {
        double sum = 0;
        for (int h = 0; h < k; ++h) sum += a[i*k+h]*b[h*n+j];
        c[i*n+j] = sum;
    }
}

int requested_level(int mode) {
    const int available = calix_simd_level();
    if (mode == -1) return available;
    if (mode < 0 || mode > 2 || mode > available) return -1;
    return mode;
}

bool amx_enabled() {
    if (!(calix_cpu_features() & 16)) return false;
    using EnableFeatures = BOOL (WINAPI*)(DWORD64);
    const auto enable = reinterpret_cast<EnableFeatures>(GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "EnableProcessOptionalXStateFeatures"));
    if (enable && !enable(0x60000)) return false;
    return (detect() & 32) != 0;
}

int guarded_amx(const int8_t* a, const int8_t* b, int32_t* c, int m, int n, int k) {
    __try {
        calix_gemm_amx(a, b, c, m, n, k);
        return 3;
    } __except (GetExceptionCode() == EXCEPTION_ILLEGAL_INSTRUCTION ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) {
        return -4;
    }
}

bool dimensions(int m, int n, int k) {
    return m > 0 && n > 0 && k > 0 && m <= 4096 && n <= 4096 && k <= 65536 &&
        int64_t(m)*k <= 16000000 && int64_t(k)*n <= 16000000 && int64_t(m)*n <= 16000000;
}

bool capped(const char* name) {
    char value[16]{};
    return GetEnvironmentVariableA("CALIX_SIMD",value,sizeof(value))>0 && std::strcmp(value,name)==0;
}
}

uint32_t calix_cpu_features() {
    static const uint32_t flags = detect();
    return flags;
}

int calix_simd_level() {
    const auto flags = calix_cpu_features();
    if (capped("scalar")) return 0;
    if ((flags & 8) && !capped("avx2")) return 2;
    return (flags & 2) ? 1 : 0;
}

int calix_dispatch_batch(const int32_t* ops, const double* args, int n,
    const double* x, const double* y, const double* z, int count, double* out) {
    const int level = calix_simd_level();
    if (level == 2 && count >= 32) return calix_batch_avx512(ops,args,n,x,y,z,count,out);
    if (level >= 1 && count >= 16) return calix_batch_avx2(ops,args,n,x,y,z,count,out);
    return 0;
}

int calix_dense_f64(const double* a, const double* b, double* c, int m, int n, int k, int mode) {
    if (!a || !b || !c || !dimensions(m,n,k)) return -1;
    const int level = requested_level(mode);
    if (level < 0) return -4;
    const Gemm64 function = level == 2 ? calix_gemm_avx512 : level == 1 ? calix_gemm_avx2 : scalar;
    const int status=calix_parallel_for(m,std::max(1,32768/std::max(1,n*k)),[&](int i) {
        function(a+i*k,b,c+i*n,1,n,k);
        return 0;
    });
    if(status)return status;
    return level;
}

int calix_dense_i8(const int8_t* a, const int8_t* b, int32_t* c, int m, int n, int k, int mode) {
    if (!a || !b || !c || !dimensions(m,n,k) || (mode != -1 && mode != 0 && mode != 3)) return -1;
    const bool wants_amx = mode == 3 || (mode == -1 && int64_t(m)*n*k >= 32768 &&
        !capped("scalar"));
    if (wants_amx && amx_enabled()) {
        const int status = guarded_amx(a,b,c,m,n,k);
        if (status == 3) return status;
        if (mode == 3) return status;
    } else if (mode == 3) return -4;
    for (int i=0;i<m;++i) for (int j=0;j<n;++j) {
        int32_t sum=0;
        for (int h=0;h<k;++h) sum += int32_t(a[i*k+h])*int32_t(b[h*n+j]);
        c[i*n+j]=sum;
    }
    return 0;
}
