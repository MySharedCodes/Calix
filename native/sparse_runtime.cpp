#include "sparse_runtime.h"
#include "cpu.h"
#include <mutex>

namespace {
SparseRuntime runtime;
std::mutex loading;
template<class Function>
Function address(HMODULE module,const char* name,const char* alternate=nullptr) {
    auto result=GetProcAddress(module,name);
    if(!result && alternate)result=GetProcAddress(module,alternate);
    return reinterpret_cast<Function>(result);
}
}

const SparseRuntime& calix_sparse_runtime(){return runtime;}

CALIX_CPU_API int calix_load_sparse_runtime(const wchar_t* path) {
    std::lock_guard<std::mutex> lock(loading);
    if(runtime.module)return 0;
    if(!path || !*path)return -6;
    auto module=LoadLibraryExW(path,nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_DEFAULT_DIRS);
    if(!module)return -6;
    SparseRuntime candidate;
    candidate.module=module;
    candidate.solve=address<SparseRuntime::Pardiso>(module,"pardiso","PARDISO");
    candidate.initialize=address<SparseRuntime::Initialize>(module,"pardisoinit","PARDISOINIT");
    candidate.threads=address<SparseRuntime::LocalThreads>(module,"MKL_Set_Num_Threads_Local");
    using SetLayer=int (__cdecl*)(int);
    using Dynamic=void (__cdecl*)(int);
    auto interface_layer=address<SetLayer>(module,"MKL_Set_Interface_Layer");
    auto threading=address<SetLayer>(module,"MKL_Set_Threading_Layer");
    auto dynamic=address<Dynamic>(module,"MKL_Set_Dynamic");
    if(!candidate.solve || !candidate.initialize || !candidate.threads || !interface_layer || !threading || !dynamic || interface_layer(0)!=0 || threading(0)!=0) {
        FreeLibrary(module);return -6;
    }
    dynamic(0);
    runtime=candidate;
    return 0;
}
