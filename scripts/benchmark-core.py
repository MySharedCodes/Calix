"""Measure core cold start, warm operations and repeated-use memory on this host."""
from pathlib import Path
import argparse
import ctypes
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def working_set():
    if os.name != 'nt':
        return None
    from ctypes import wintypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    data = Counters()
    data.cb = ctypes.sizeof(data)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    return data.WorkingSetSize if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(data), data.cb) else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'work/verification/performance.json')
    parser.add_argument('--repeats', type=int, default=20)
    args = parser.parse_args()
    cold = []
    for _ in range(3):
        start = time.perf_counter()
        subprocess.run([sys.executable, '-c', 'from backend.engine import Engine; assert Engine().execute("1+1")["text"]=="2"'], cwd=ROOT, check=True, stdout=subprocess.DEVNULL, timeout=30)
        cold.append((time.perf_counter()-start)*1000)
    from backend.engine import Engine
    from backend.native import kernel
    from backend.hardware import physical_cores
    kernel.configure_threads(min(8, physical_cores()))
    engine = Engine()
    scenarios = {'exact':'Sum[k^6,{k,1,500}]', 'units':'UnitConvert[650[gr],"g"]',
                 'root':'FindRoot[Cos[x]-x,{x,0,1}]', 'integral':'NIntegrate[Exp[-x^2],{x,-3,3}]',
                 'plot':'Plot[Exp[-t]*Cos[2*t],{t,0,10}]'}
    records = {}
    for name, source in scenarios.items():
        engine.execute(source)
        times = []
        for _ in range(args.repeats):
            start = time.perf_counter(); engine.execute(source)
            times.append((time.perf_counter()-start)*1000)
        records[name] = {'median_ms': statistics.median(times), 'p95_ms': sorted(times)[max(0, math.ceil(len(times)*.95)-1)]}
    before = working_set()
    for _ in range(500):
        engine.execute('Plot[x^2,{x,-2,2}]')
    after = working_set()
    record = {'platform': platform.platform(), 'python': platform.python_version(), 'physical_cores': physical_cores(),
              'workers': min(8, physical_cores()), 'cold_start_wall_ms': cold, 'warm_operations': records,
              'memory_500_discarded_plots': {'before_bytes': before, 'after_bytes': after, 'growth_bytes': after-before if before and after else None},
              'scope': 'Source engine on this host; excludes GUI startup, packaged CLI overhead and full FEM workloads.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()
