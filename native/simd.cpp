#include "cpu.h"
#include <immintrin.h>
#include <array>
#include <cmath>

#if CALIX_SIMD_WIDTH == 8
using Vec = __m512d;
#define SIMD_NAME(name) name##_avx512
#define V(name) _mm512_##name##_pd
#else
using Vec = __m256d;
#define SIMD_NAME(name) name##_avx2
#define V(name) _mm256_##name##_pd
#endif

void SIMD_NAME(calix_gemm)(const double* a, const double* b, double* c, int m, int n, int k) {
    constexpr int w = CALIX_SIMD_WIDTH;
    for (int i=0;i<m;++i) {
        int j=0;
        for (;j+w<=n;j+=w) {
            Vec sum = V(setzero)();
            for (int h=0;h<k;++h) sum=V(add)(sum,V(mul)(V(set1)(a[i*k+h]),V(loadu)(b+h*n+j)));
            V(storeu)(c+i*n+j,sum);
        }
        for (;j<n;++j) {
            double sum=0;
            for (int h=0;h<k;++h) sum+=a[i*k+h]*b[h*n+j];
            c[i*n+j]=sum;
        }
    }
}

int SIMD_NAME(calix_batch)(const int32_t* ops, const double* args, int n,
    const double* x, const double* y, const double* z, int count, double* output) {
    int depth=0;
    for (int i=0;i<n;++i) {
        const int op=ops[i];
        if (op>=0 && op<=3) { if (++depth>512) return 0; }
        else if (op>=10 && op<=14) {
            if (depth<2) return 0;
            --depth;
            if (op==14 && (i==0 || ops[i-1]!=0 || !std::isfinite(args[i-1]) ||
                (args[i-1]!=.5 && args[i-1]!=-.5 && (std::floor(args[i-1])!=args[i-1] || std::abs(args[i-1])>32)))) return 0;
        } else if ((op==15 || op==25 || op==26) && depth>=1) {}
        else return 0;
    }
    if (depth!=1) return 0;
    std::array<Vec,512> stack;
    constexpr int w=CALIX_SIMD_WIDTH;
    const int processed=count-count%w;
    for (int row=0;row<processed;row+=w) {
        int top=0;
        for (int i=0;i<n;++i) {
            const int op=ops[i];
            if (op==0) stack[top++]=V(set1)(args[i]);
            else if (op<=3) {
                const double* data=op==1?x:op==2?y:z;
                stack[top++]=data?V(loadu)(data+row):V(setzero)();
            } else if (op>=10 && op<=14) {
                const Vec b=stack[--top];Vec& a=stack[top-1];
                if (op==10) a=V(add)(a,b);
                else if (op==11) a=V(sub)(a,b);
                else if (op==12) a=V(mul)(a,b);
                else if (op==13) a=V(div)(a,b);
                else {
                    const double exponent=args[i-1];
                    if (exponent==.5 || exponent==-.5) {
                        a=V(sqrt)(a);
                        if (exponent<0) a=V(div)(V(set1)(1),a);
                    } else {
                        int power=static_cast<int>(std::abs(exponent));Vec result=V(set1)(1),base=a;
                        while (power) { if (power&1) result=V(mul)(result,base);power>>=1;if (power)base=V(mul)(base,base); }
                        a=exponent<0?V(div)(V(set1)(1),result):result;
                    }
                }
            } else if (op==15) stack[top-1]=V(sub)(V(setzero)(),stack[top-1]);
            else if (op==25) stack[top-1]=V(sqrt)(stack[top-1]);
            else stack[top-1]=V(andnot)(V(set1)(-0.0),stack[top-1]);
        }
        V(storeu)(output+row,stack[0]);
    }
    return processed;
}
