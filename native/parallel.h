#pragma once
#include <algorithm>
#include <atomic>
#include <exception>
#include <thread>
#include <vector>

int calix_thread_limit();
void calix_record_threads(int count);

template<class Function>
int calix_parallel_for(int count,int grain,Function function) {
    const int threads=std::max(1,std::min(calix_thread_limit(),count/grain));
    calix_record_threads(threads);
    if(threads==1) {
        for(int i=0;i<count;++i) { const int status=function(i);if(status)return status; }
        return 0;
    }
    std::atomic<int> status{0};
    std::vector<std::thread> workers;
    auto run=[&](int worker) {
        try {
            for(int i=count*worker/threads;i<count*(worker+1)/threads && !status.load();++i) {
                const int error=function(i);if(error)status.store(error);
            }
        }catch(...){status.store(-5);}
    };
    try {
        for(int i=1;i<threads;++i)workers.emplace_back(run,i);
    }catch(...) {
        status.store(-5);
        for(auto& worker:workers)worker.join();
        return -5;
    }
    run(0);
    for(auto& worker:workers)worker.join();
    return status.load();
}
