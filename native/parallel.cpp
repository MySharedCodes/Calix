#include "parallel.h"
#include "cpu.h"

namespace {
std::atomic<int> limit{1};
std::atomic<int> observed{1};
}
int calix_thread_limit(){return limit.load();}
void calix_record_threads(int count){observed.store(count);}
CALIX_CPU_API int calix_set_threads(int count) {
    if(count<1 || count>1024)return -1;
    limit.store(count);return count;
}
CALIX_CPU_API int calix_last_threads(){return observed.load();}
