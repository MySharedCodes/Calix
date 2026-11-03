"""Windows job ownership ensures worker processes exit with the desktop service."""
import ctypes as ct
from ctypes import wintypes as wt
import os

_job = None


def own_process_tree():
    global _job
    if os.name != "nt":
        return
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ct.c_void_p, wt.LPCWSTR]
    kernel.CreateJobObjectW.restype = wt.HANDLE
    kernel.GetCurrentProcess.restype = wt.HANDLE
    kernel.SetInformationJobObject.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
    kernel.CloseHandle.argtypes = [wt.HANDLE]

    class BasicLimits(ct.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ct.c_int64), ("PerJobUserTimeLimit", ct.c_int64),
                    ("LimitFlags", wt.DWORD), ("MinimumWorkingSetSize", ct.c_size_t),
                    ("MaximumWorkingSetSize", ct.c_size_t), ("ActiveProcessLimit", wt.DWORD),
                    ("Affinity", ct.c_size_t), ("PriorityClass", wt.DWORD), ("SchedulingClass", wt.DWORD)]

    class IOCounters(ct.Structure):
        _fields_ = [(name, ct.c_uint64) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class ExtendedLimits(ct.Structure):
        _fields_ = [("BasicLimitInformation", BasicLimits), ("IoInfo", IOCounters),
                    ("ProcessMemoryLimit", ct.c_size_t), ("JobMemoryLimit", ct.c_size_t),
                    ("PeakProcessMemoryUsed", ct.c_size_t), ("PeakJobMemoryUsed", ct.c_size_t)]

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ct.WinError(ct.get_last_error())
    limits = ExtendedLimits()
    # Workers remain owned; only an explicitly launched desktop may break away.
    limits.BasicLimitInformation.LimitFlags = 0x2000 | 0x100 | 0x800
    limits.ProcessMemoryLimit = 1536 * 1024 * 1024
    if not kernel.SetInformationJobObject(job, 9, ct.byref(limits), ct.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        error = ct.get_last_error()
        kernel.CloseHandle(job)
        raise ct.WinError(error)
    _job = job
