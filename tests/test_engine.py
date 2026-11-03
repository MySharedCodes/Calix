import math
import pytest
from backend.engine import Engine
from backend.syntax import InputError, parse
from backend.native import kernel


@pytest.mark.parametrize("code, expected", [
    ("1/3+1/6", "1/2"), ("-2^2", "-4"), ("2^3^2", "512"),
    ("2 (3+4)", "14"), ("Sum[1/n^2,{n,1,Infinity}]", "(1/6)*Pi^2"),
    ("Product[k,{k,1,5}]", "120"), ("D[Sin[x^2],x]", "2*x*Cos[x^2]"),
    ("Integrate[2 x,x]", "x^2"), ("Limit[Sin[x]/x,x->0]", "1"),
    ("Hypergeometric2F1[1,1,2,0]", "HypergeometricPFQ[{1, 1}, {2}, 0]"),
])
def test_symbolic(code, expected):
    assert Engine().execute(code)["text"] == expected


def test_units():
    engine = Engine()
    assert engine.execute("3[m]+20[cm]")["text"] == "3.20000000000000[m]" or engine.execute("3[m]+20[cm]")["text"] == "16/5[m]"
    assert "100000" in engine.execute('UnitConvert[1[bar],"Pa"]')["text"]
    assert engine.execute("Sin[90[deg]]")["text"] == "1"
    with pytest.raises(Exception):
        engine.execute("3[m]+2[s]")
    with pytest.raises(Exception):
        engine.execute("Exp[2[m]]")


def test_scope():
    engine = Engine()
    engine.execute("x=7")
    assert engine.execute("D[x^2,x]")["text"] == "2*x"
    assert engine.execute("x")["text"] == "7"
    assert engine.execute("Clear[x];x")["text"] == "x"


def test_equations():
    engine = Engine()
    assert "2^(1/2)" in engine.execute("Solve[x^2==2,x]")["text"]
    assert "e^{a x}" in engine.execute("DSolve[y'[x]==a y[x],y[x],x]")["latex"]
    result = engine.execute("RSolve[{a[n+1]==2 a[n]+1,a[0]==0},a[n],n]")
    assert "2^n - 1" in result["text"]


@pytest.mark.parametrize("code", ['__import__["os"]', 'Run["calc"]', 'x @ y', 'Sin['])
def test_rejected_input(code):
    with pytest.raises((InputError, ValueError)):
        Engine().execute(code)


def test_assumptions():
    assert Engine().execute("Assuming[x>0,Simplify[Sqrt[x^2]]]")["text"] == "x"


def test_native_solvers():
    assert kernel.available, "Build the C++ core before running the test suite"
    engine = Engine()
    assert abs(float(engine.execute("FindRoot[x^2-2,{x,0,2}]")["text"])-math.sqrt(2)) < 1e-10
    assert abs(float(engine.execute("NIntegrate[Sin[x],{x,0,Pi}]")["text"])-2) < 1e-10
    with pytest.raises(ValueError):
        engine.execute("FindRoot[1/x,{x,-1,1}]")
    result = engine.execute("NDSolve[{y'[t]==-y[t],y[0]==1},y,{t,0,5}]")
    assert abs(result["traces"][0]["y"][-1]-math.exp(-5)) < 1e-7


def test_plots():
    engine = Engine()
    curve = engine.execute("Plot[1/x,{x,-1,1}]")
    assert None in curve["traces"][0]["y"]
    surface = engine.execute("Plot3D[Sin[x] Cos[y],{x,-3,3},{y,-3,3}]")
    assert surface["plot_type"] == "surface"
    assert len(surface["z"]) == 65
    assert engine.execute("ParametricPlot[{Cos[t],Sin[t]},{t,0,2 Pi}]")["plot_type"] == "curve"
    assert engine.execute("ContourPlot[x^2+y^2,{x,-2,2},{y,-2,2}]")["plot_type"] == "contour"


def test_unknown_options_rejected():
    with pytest.raises(InputError):
        Engine().execute("Plot[x,{x,0,1},MadeUp->1]")


def test_unicode_and_named_symbols():
    engine = Engine()
    assert engine.execute("Sin[π/2]")["text"] == "1"
    assert engine.execute(r"Sin[\[Pi]/2]")["text"] == "1"
    assert engine.execute("3 × 4 − 2")["text"] == "10"


def test_affine_units_and_exact_scale():
    engine = Engine()
    assert engine.execute("3[m]+20[cm]")["text"] == "16/5[m]"
    assert engine.execute('UnitConvert[0[degC],"K"]')["text"] == "5463/20[K]"
    assert engine.execute('UnitConvert[10[delta_degC],"delta_degF"]')["text"] == "18[Δ°F]"


def test_multivariate_and_initial_conditions():
    engine = Engine()
    assert engine.execute("D[x^3 y^2,{x,2},y]")["text"] == "12*x*y"
    assert engine.execute("Solve[x^2==-1,x,Reals]")["text"] == "EmptySet"
    assert "Exp[-2*x]" in engine.execute("DSolve[{y'[x]==-2 y[x],y[0]==1},y[x],x]")["text"]


def test_physical_plot_axes():
    result = Engine().execute("Plot[3[m/s]*t,{t,0[s],2[s]}]")
    assert result["axes"] == ["t [s]", "y [m]"]
    assert result["traces"][0]["y"][-1] == 6
    with pytest.raises(Exception):
        Engine().execute("Plot[{t*1[m],t*1[s]},{t,0,1}]")


def test_second_order_initial_derivative():
    result = Engine().execute("DSolve[{y''[x]+y[x]==0,y[0]==1,y'[0]==0},y[x],x]")
    assert "Cos[x]" in result["text"]


def test_shipped_examples():
    import json
    import os
    import time
    from pathlib import Path
    from backend.hardware import limit_process_cores
    workers = int(os.environ.get('CALIX_MAX_WORKERS', '8'))
    kernel.configure_threads(workers)
    print(f'Functional regression, not a performance benchmark; affinity: {limit_process_cores(workers)}', flush=True)
    for path in (Path(__file__).resolve().parents[1] / "examples").glob("*.calix"):
        print(f'Example: {path.name}', flush=True)
        engine = Engine()
        for index, cell in enumerate(json.loads(path.read_text(encoding="utf-8"))["cells"], 1):
            if cell["mode"] == "markdown":
                continue
            print(f'  cell {index}', flush=True)
            started = time.perf_counter()
            result = engine.execute(cell["code"])
            print(f'  completed in {time.perf_counter()-started:.3f}s', flush=True)
            assert result["kind"] in ("expression", "plot", "group", "animation"), (path, cell["code"])


def test_degree_suffix():
    engine = Engine()
    assert engine.execute("Sin[30°]")["text"] == "1/2"
    assert engine.execute("Cos[(45+45)°]")["text"] == "0"
    assert engine.execute("Sin[Pi/2]")["text"] == "1"
    assert engine.execute('Quantity[1,"degree"]')["kind"] == "expression"


def test_physics_starter():
    import json
    from pathlib import Path
    import sympy as s
    from backend.syntax import parse
    engine = Engine()
    starter = json.loads((Path(__file__).resolve().parents[1] / "frontend/src/starter.json").read_text(encoding="utf-8"))
    for cell in starter["cells"]:
        if cell["mode"] != "markdown":
            engine.execute(cell["code"])
    t = s.Symbol("t")
    velocity=[v.to('m/s').magnitude for v in engine.environment['u']]
    x,y=[v.to('m').magnitude for v in engine.environment['r']]
    assert abs(sum(float(v.subs(t,0))**2 for v in velocity)-890**2)<1e-6
    assert float(engine.environment['v'].to('m/s').magnitude)==890
    assert float(x.subs(t,0))==float(y.subs(t,0))==0
    landing=float(engine.environment['q'][2].to('s').magnitude)
    assert abs(float(x.subs(t,landing))-7000)<0.005
    assert abs(float(y.subs(t,landing)))<0.005
    assert float(y.subs(t,landing/2))>0


def test_multiple_results_and_vector_integration():
    result = Engine().execute("Column[{1+1, Integrate[{u,u^2},{u,0,t}], Plot[x,{x,0,1}]}]")
    assert [item["kind"] for item in result["items"]] == ["expression", "expression", "plot"]
    assert result["items"][0]["text"] == "2"
    assert "t^3" in result["items"][1]["text"]
    with pytest.raises(InputError):
        Engine().execute("Column[{}]")


def test_animation_sampling_and_scope():
    engine = Engine()
    curve = engine.execute("Animate[ParametricPlot[{Cos[t],Sin[t]},{t,0,2 Pi}]]")
    assert curve["animation_type"] == "trajectory"
    assert len(curve["values"]) == len(curve["plot"]["traces"][0]["x"])
    assert abs(curve["values"][-1] - 2*math.pi) < 1e-10
    engine.execute("a=17")
    frames = engine.execute("Animate[Plot[Sin[x-a],{x,0,Pi}],{a,0,Pi}]")
    assert frames["animation_type"] == "frames" and len(frames["frames"]) == 61
    assert abs(frames["frames"][0]["traces"][0]["y"][100] - 1) < 1e-10
    assert abs(frames["frames"][-1]["traces"][0]["y"][100] + 1) < 1e-10
    assert engine.execute("a")["text"] == "17"
    with pytest.raises(InputError):
        engine.execute("Animate[Plot[x,{x,0,1}],{a,1,0}]")


def test_dsolvevalue_preserves_requested_order():
    engine = Engine()
    engine.execute("v=DSolveValue[{x'[t]==-x[t],y'[t]==0,x[0]==2,y[0]==3},{y[t],x[t]},t]")
    assert engine.execute("First[v]")["text"] == "3"
    assert engine.execute("Last[v]")["text"] == "2*Exp[-t]"


def test_analytical_and_native_extrema():
    engine = Engine()
    assert engine.execute("Minimize[x^2-4 x+5,x]")["text"] == "{1, {x: 2}}"
    assert engine.execute("Maximize[4-x^2,{x,-3,3}]")["text"] == "{4, {x: 0}}"
    assert engine.execute("Minimize[x,{x,2,5}]")["text"] == "{2, {x: 2}}"
    assert "Infinity" in engine.execute("Minimize[-x^2,x]")["text"]
    engine.execute("answer=FindMinimum[(x-1.3)^2+2,{x,-2,3}]")
    value, at = engine.environment["answer"]
    assert abs(float(value)-2) < 1e-10 and abs(float(at[next(iter(at))])-1.3) < 1e-7
    engine.execute("answer=FindMaximum[Sin[x],{x,0,Pi}]")
    assert abs(float(engine.environment["answer"][0])-1) < 1e-10
    assert "C++" in engine.execute("FindMinimum[x,{x,0,1}]")["engine"]
    with pytest.raises((ValueError, InputError)):
        engine.execute("FindMinimum[Log[x],{x,-2,-1}]")
    with pytest.raises((ValueError, InputError)):
        engine.execute("Minimize[x^2,{x,3,2}]")


def test_matrix_examples():
    engine = Engine()
    assert engine.execute("Det[{{1,2,3},{0,4,5},{1,0,6}}]")["text"] == "22"
    assert "8" in engine.execute("Dot[{{1,2},{3,4}},{{2,0},{1,2}}]")["text"]
    assert engine.execute("Det[Inverse[{{1,2},{3,4}}]]")["text"] == "-1/2"
