#include "cpu.h"
#include <immintrin.h>
#include <algorithm>
#include <cstring>

namespace {
struct alignas(64) TileConfiguration {
    uint8_t palette=1, start=0, reserved[14]{};
    uint16_t columns[16]{};
    uint8_t rows[16]{};
};
static_assert(sizeof(TileConfiguration)==64);
}

void calix_gemm_amx(const int8_t* a, const int8_t* b, int32_t* c, int m, int n, int k) {
    TileConfiguration config;
    config.columns[0]=64;config.rows[0]=16;
    config.columns[1]=64;config.rows[1]=16;
    config.columns[2]=64;config.rows[2]=16;
    _tile_loadconfig(&config);
    alignas(64) int8_t left[16][64],right[16][64];
    alignas(64) int32_t result[16][16];
    for (int i=0;i<m;i+=16) for (int j=0;j<n;j+=16) {
        _tile_zero(0);
        for (int h=0;h<k;h+=64) {
            std::memset(left,0,sizeof(left));std::memset(right,0,sizeof(right));
            for (int row=0;row<std::min(16,m-i);++row)
                std::memcpy(left[row],a+(i+row)*k+h,std::min(64,k-h));
            // AMX INT8 right-hand tiles use groups of four inner-dimension values.
            for (int l=0;l<std::min(64,k-h);++l) for (int col=0;col<std::min(16,n-j);++col)
                right[l/4][4*col+l%4]=b[(h+l)*n+j+col];
            _tile_loadd(1,left,64);_tile_loadd(2,right,64);
            _tile_dpbssd(0,1,2);
        }
        _tile_stored(0,result,64);
        for (int row=0;row<std::min(16,m-i);++row)
            std::memcpy(c+(i+row)*n+j,result[row],std::min(16,n-j)*sizeof(int32_t));
    }
    _tile_release();
}
