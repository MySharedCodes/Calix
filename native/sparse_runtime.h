#pragma once
#include <windows.h>

struct SparseRuntime {
    using Pardiso=void (__cdecl*)(void**,const int*,const int*,const int*,const int*,const int*,const void*,const int*,const int*,int*,const int*,int*,const int*,void*,void*,int*);
    using Initialize=void (__cdecl*)(void**,const int*,int*);
    using LocalThreads=int (__cdecl*)(int);
    HMODULE module=nullptr;
    Pardiso solve=nullptr;
    Initialize initialize=nullptr;
    LocalThreads threads=nullptr;
};

const SparseRuntime& calix_sparse_runtime();
