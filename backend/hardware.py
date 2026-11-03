"""Physical CPU topology; never infer core count from SMT thread count alone."""
import ctypes as ct
from functools import lru_cache
import os
import sys


@lru_cache(maxsize=1)
def physical_cores():
    if sys.platform=='win32':
        api=ct.WinDLL('kernel32',use_last_error=True).GetLogicalProcessorInformationEx
        api.argtypes=[ct.c_int,ct.c_void_p,ct.POINTER(ct.c_ulong)]
        api.restype=ct.c_int
        size=ct.c_ulong()
        api(0,None,ct.byref(size))
        if size.value:
            buffer=ct.create_string_buffer(size.value)
            if api(0,buffer,ct.byref(size)):
                offset=0;count=0
                while offset+8<=size.value:
                    relationship,length=ct.cast(ct.byref(buffer,offset),ct.POINTER(ct.c_ulong*2)).contents
                    if length<8 or offset+length>size.value:break
                    if relationship==0:count+=1
                    offset+=length
                if count:return count
    # Conservative fallback on platforms without topology information.
    return max(1,(os.cpu_count() or 1)//2)


def default_workers():
    value=os.environ.get('CALIX_MAX_WORKERS')
    return min(physical_cores(),max(1,int(value))) if value and value.isdecimal() else physical_cores()


@lru_cache(maxsize=1)
def original_affinity():
    if sys.platform!='win32':return None
    api=ct.WinDLL('kernel32',use_last_error=True)
    api.GetCurrentProcess.restype=ct.c_void_p
    api.GetProcessAffinityMask.argtypes=[ct.c_void_p,ct.POINTER(ct.c_size_t),ct.POINTER(ct.c_size_t)]
    process,system=ct.c_size_t(),ct.c_size_t()
    if not api.GetProcessAffinityMask(api.GetCurrentProcess(),ct.byref(process),ct.byref(system)):return None
    return process.value


def limit_process_cores(maximum):
    """Keep all threads of a calculation process within the physical core budget."""
    allowed=original_affinity()
    if allowed is None:return None
    api=ct.WinDLL('kernel32',use_last_error=True)
    info=api.GetLogicalProcessorInformationEx
    info.argtypes=[ct.c_int,ct.c_void_p,ct.POINTER(ct.c_ulong)]
    size=ct.c_ulong();info(0,None,ct.byref(size))
    buffer=ct.create_string_buffer(size.value)
    if not info(0,buffer,ct.byref(size)):raise OSError(ct.get_last_error(),'Cannot read CPU topology')
    offset=0;selected=0;count=0
    while offset+32<=size.value:
        relationship,length=ct.cast(ct.byref(buffer,offset),ct.POINTER(ct.c_ulong*2)).contents
        if length<32 or offset+length>size.value:break
        if relationship==0:
            group_count=ct.c_ushort.from_buffer(buffer,offset+30).value
            for group in range(group_count):
                entry=offset+32+group*(ct.sizeof(ct.c_size_t)+8)
                mask=ct.c_size_t.from_buffer(buffer,entry).value
                number=ct.c_ushort.from_buffer(buffer,entry+ct.sizeof(ct.c_size_t)).value
                if number==0 and mask&allowed and count<maximum:
                    selected|=mask&allowed;count+=1
        offset+=length
    if not selected:return None
    api.GetCurrentProcess.restype=ct.c_void_p
    api.SetProcessAffinityMask.argtypes=[ct.c_void_p,ct.c_size_t]
    if not api.SetProcessAffinityMask(api.GetCurrentProcess(),selected):raise OSError(ct.get_last_error(),'Cannot apply CPU core limit')
    return {'physical_cores':count,'logical_mask':hex(selected)}
