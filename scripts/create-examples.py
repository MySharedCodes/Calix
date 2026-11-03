import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dest = root / "examples"
dest.mkdir(exist_ok=True)
for retired in ('三天体-平面引力运动.calix','00-projectile-with-linear-drag.calix','单位换算.calix','单位运算.calix','石英与空气-电磁波反射和透射.calix'):
    (dest/retired).unlink(missing_ok=True)
notebooks = {
    "01-calculations-and-units": ["1/3 + Sqrt[2]", "N[Pi,80]", "Sum[1/n^2,{n,1,Infinity}]", "Product[k,{k,1,10}]", "N[Hypergeometric2F1[1/2,1/2,1,1/2],40]", 'UnitConvert[3[m]+20[cm],"cm"]', 'UnitConvert[0[degC],"K"]', "Sin[90[deg]]"],
    "02-symbolic-equations": ["Assuming[x>0,Simplify[Sqrt[x^2]]]", "D[x^3 y^2,{x,2},y]", "Integrate[Exp[-x^2],x]", "Integrate[Exp[-a x],{x,0,Infinity}]", "Solve[{x+y==3,x-y==1},{x,y}]", "RSolve[{a[n+1]==2 a[n]+1,a[0]==0},a[n],n]", "DSolve[{y''[x]+y[x]==0,y[0]==1,y'[0]==0},y[x],x]"],
    "03-plots": ["Plot[{Sin[x],Cos[x]},{x,-Pi,Pi}]", "Plot[1/x,{x,-2,2},PlotRange->{-5,5}]", "Plot[3[m/s]*t,{t,0[s],2[s]}]", "Plot3D[Sin[x] Cos[y],{x,-Pi,Pi},{y,-Pi,Pi}]", "ContourPlot[x^2-y^2,{x,-3,3},{y,-3,3}]", "ParametricPlot[{Cos[3 t],Sin[2 t]},{t,0,2 Pi}]", "ParametricPlot3D[{Cos[t],Sin[t],t/4},{t,0,6 Pi}]"],
    "04-native-solvers": ["FindRoot[Cos[x]-x,{x,0,1}]", "NIntegrate[Exp[-x^2],{x,-3,3}]", "NDSolve[{y'[t]==-y[t]+Sin[t],y[0]==1},y,{t,0,15}]"],
}
for title, codes in notebooks.items():
    content = {"format": "calix-notebook", "version": 1, "title": title, "cells": [{"id": f"example-{i}", "mode": "source", "code": code} for i, code in enumerate(codes)]}
    (dest / f"{title}.calix").write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Created {len(notebooks)} notebooks")
animation = {"format": "calix-notebook", "version": 1, "title": "05-animation", "cells": [
    {"id": "trajectory", "mode": "source", "code": "Animate[ParametricPlot[{Cos[t],Sin[t]},{t,0,2 Pi}]]"},
    {"id": "frames", "mode": "source", "code": "Animate[Plot[Sin[x-a],{x,-Pi,Pi}],{a,0,2 Pi}]"},
]}
(dest / "05-animation.calix").write_text(json.dumps(animation, ensure_ascii=False, indent=2), encoding="utf-8")
starter = json.loads((root / "frontend/src/starter.json").read_text(encoding="utf-8"))
starter.update(format="calix-notebook", version=1)
for i, cell in enumerate(starter["cells"]):
    cell["id"] = f"physics-{i}"
(dest / "00-projectile-with-air-resistance.calix").write_text(json.dumps(starter, ensure_ascii=False, indent=2), encoding="utf-8")
cases = json.loads((root / "frontend/src/example-notebooks.json").read_text(encoding="utf-8"))
for index, notebook in enumerate(cases, 6):
    notebook.update(format="calix-notebook", version=1)
    for cell_index, cell in enumerate(notebook["cells"]):
        cell["id"] = f"case-{index}-{cell_index}"
    (dest / f"{notebook['title'].replace('：', '-')}.calix").write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
