"""Reproducible local measurements; compares the same expression and precision."""
import json
import math
import platform
from pathlib import Path
import statistics
import time
import sympy as s
from backend.engine import Engine
from backend.native import kernel

root = Path(__file__).resolve().parents[1]
x = s.Symbol("x")
expression = s.sin(x) * s.exp(-x*x/20) + s.cos(3*x) / (1+x*x)
points = [-10 + i * 20 / 100000 for i in range(100001)]
reference = s.lambdify(x, expression, modules="math")


def measure(fn, rounds=7):
    times = []
    result = None
    for _ in range(rounds):
        start = time.perf_counter()
        result = fn()
        times.append((time.perf_counter()-start)*1000)
    return {"median_ms": round(statistics.median(times), 3), "min_ms": round(min(times), 3)}, result


native_time, native = measure(lambda: kernel.batch(expression, [x], [points]))
python_time, python = measure(lambda: [reference(p) for p in points])
error = max(abs(a-b) for a, b in zip(native, python))
assert error < 1e-12
engine = Engine()
cases = ["1/3+Sqrt[2]", "Solve[x^4-5 x^2+4==0,x]", "Integrate[Exp[-x^2],x]", "Sum[1/n^2,{n,1,Infinity}]", "Plot3D[Sin[x] Cos[y],{x,-3,3},{y,-3,3}]", "NIntegrate[Exp[-x^2],{x,-3,3}]", "FindRoot[Cos[x]-x,{x,0,1}]", "NDSolve[{y'[t]==-y[t],y[0]==1},y,{t,0,10}]"]
measurements = {}
for code in cases:
    engine.execute(code)
    measurements[code] = measure(lambda: engine.execute(code), rounds=5)[0]
report = {"platform": platform.platform(), "python": platform.python_version(), "precision": "IEEE-754 double for native measurements", "native_100001_samples": native_time, "python_math_100001_samples": python_time, "max_absolute_error": error, "cases_warm": measurements, "note": "Includes Python/C ABI array conversion. Warm process, no UI transport. Not a comparison with Mathematica."}
(root / "work/benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
