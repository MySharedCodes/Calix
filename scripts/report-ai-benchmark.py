"""Validate trial answers and report agent wall time separately from tool time."""
import json
from pathlib import Path
import statistics

import pint
import sympy as sp

root = Path(__file__).resolve().parents[1]
bench = root / 'work/ai-benchmark-v0126'

def load(path):
    return json.loads(path.read_text(encoding='utf8'))

def expression(value):
    text = str(value).replace('^', '**').replace('Pi', 'pi')
    text = text.replace('Exp[', 'exp(').replace(']', ')')
    return sp.sympify(text)

k, x, y, z, t = sp.symbols('k x y z t')
matrix = sp.Matrix([[4,1,0,2],[1,5,2,0],[0,2,6,1],[2,0,1,7]])
reference_sum = sp.summation(k**6, (k,1,500))
reference_integral = sp.integrate(x**4*sp.exp(-3*x**2), (x,-sp.oo,sp.oo))
reference_solutions = {tuple(solution[v] for v in (x,y,z)) for solution in
    sp.solve([x+y+z-6,x*x+y*y+z*z-14,x*y-2],(x,y,z),dict=True)}
f = sp.Function('x')
reference_ode = sp.dsolve(sp.Eq(f(t).diff(t,2)+3*f(t).diff(t)+2*f(t),sp.exp(-t)),
    ics={f(0):0,f(t).diff(t).subs(t,0):1}).rhs
units = pint.UnitRegistry()
mass = (650*units.grain).to('gram').magnitude
energy = (650*units.grain*(890*units.meter/units.second)**2/2).to('joule').magnitude
checks = []
for trial in ('calix-01','free-01','free-02','calix-02'):
    data = load(bench / trial / 'results.json')
    if trial == 'calix-01':
        data = {str(row['problem']):row for row in data['results']}
    a, b, c, d, e, g = [data[str(n)] for n in range(1,7)]
    assert expression(a.get('exact', a.get('exact_sum'))) == reference_sum
    assert sp.simplify(expression(b.get('exact', b.get('exact_integral'))) - reference_integral) == 0
    solutions = {tuple(expression(row[v]) for v in ('x','y','z')) if isinstance(row,dict)
                 else tuple(map(expression,row)) for row in c['real_solutions']}
    assert solutions == reference_solutions
    inverse = d.get('inverse', d.get('inverse_exact'))
    computed_inverse = sp.Matrix([[expression(v) for v in row] for row in inverse])
    assert expression(d['determinant']) == matrix.det()
    assert matrix*computed_inverse == sp.eye(4)
    ode_text = e.get('rhs',e.get('x_t',e['solution']))
    if '==' in ode_text:
        ode_text = ode_text.split('==',1)[1]
    elif ' = ' in ode_text:
        ode_text = ode_text.split(' = ',1)[1]
    assert sp.simplify(expression(ode_text)-reference_ode) == 0
    mass_value = g.get('mass_g',g.get('mass_grams'))
    energy_value = g.get('kinetic_energy_J',g.get('kinetic_energy_joules'))
    if isinstance(mass_value,dict):
        mass_value = mass_value['exact']
    if isinstance(energy_value,dict):
        energy_value = energy_value['exact']
    assert abs(float(expression(mass_value))-mass) < 1e-9
    assert abs(float(expression(energy_value))-energy) < 1e-7
    checks.append({'trial':trial,'six_answers_correct':True})

runs = load(bench / 'executions.json')
assert len(runs)==4 and all(run['harness_returncode']==0 and run['final'] for run in runs)
medians = {route:statistics.median(run['wall_seconds'] for run in runs if run['route']==route)
           for route in ('calix','free')}
runtime = load(bench / 'prepared-runtime/timing.json')
summary = {'agent_median_seconds':medians, 'calix_agent_slowdown_percent':100*(medians['calix']/medians['free']-1),
    'prepared_runtime':runtime, 'independent_answer_checks':checks,
    'trials':[{'route':run['route'],'trial':run['trial'],'seconds':run['wall_seconds'],
               'tool_calls':run['tool_calls']} for run in runs]}
(bench / 'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
rows = '\n'.join(f"| {r['route']} | {r['trial']} | {r['wall_seconds']:.2f} | {r['tool_calls']} | 6/6 |" for r in runs)
report = f'''# DeepSeek Harness 控制 Calix 对照测试

测试日期：2026-10-31；本机 DeepSeek Harness，headless profile，deepseek-flash，high reasoning。
每次使用全新会话，顺序为 Calix、自选工具、自选工具、Calix。相同六题和交付要求，
软件说明放在试验目录的 AGENTS.md、AI-CONTROL.md、API.md，任务提示中未介绍 Calix。
自选路线可用同一 Python 环境的 SymPy、NumPy、SciPy、Pint，自行选工具，禁止使用 Calix。
CPU Workers 上限为 8；六题为小型符号计算，不代表并行 FEM 或 SIMD 性能。

## 完整任务时间

从 Harness 进程启动至最终答复，包括读说明、思考、编写输入、实际调用、验证和写报告。
模型网络等待也包含在内。测试期间没有并行进行大型编译，没有打开 GUI。

| 路线 | 轮次 | 秒 | 工具调用数 | 答案检查 |
|---|---:|---:|---:|---|
{rows}

Calix 中位数 **{medians['calix']:.2f} 秒**；自选工具中位数 **{medians['free']:.2f} 秒**。
这批任务中 Calix 全流程慢 **{summary['calix_agent_slowdown_percent']:.1f}%**，未观察到整体加速。
Calix 首轮逐题调用，第二轮采用 notebook 批量调用；第二轮目录说明补充了批量调用建议。
两轮的目录说明均保留在原始数据中，因此本试验也包含说明文档版本的差异。

## 输入准备后的命令执行

另取第二轮两条路线的实际输入，交替重复执行。排除第一对预热，各取五次中位数：

| 路线 | 秒 |
|---|---:|
| Calix：一次 run 执行六个单元 | {runtime['median_seconds']['calix']:.3f} |
| 自选工具：Python/SymPy/Pint 脚本 | {runtime['median_seconds']['free']:.3f} |

这项命令测试 Calix 约为 **{runtime['free_over_calix']:.2f} 倍速度**。
它包括客户端或 Python 启动、工具计算及结果写入，但不包括 AI 准备输入和 GUI 启动。
Calix 使用已经启动的常驻服务，自选脚本每次重新导入库；这不是纯求解器性能对比。
两个输入都由模型生成，额外验证与格式化工作并不完全相同。
保留了 Calix 的一次 {max(m['seconds'] for m in runtime['measurements'] if m['route']=='calix'):.2f} 秒波动，未选择性删除慢样本。

## 正确性与范围

六题包含六次方求和、高斯型积分、三元代数方程组、4×4 行列式与精确逆矩阵、
带初值的二阶非齐次 ODE、grain 单位换算及动能。四次任务均 6/6 正确。
已检查实际脚本使用通用 summation/integrate/solve/dsolve/矩阵/单位运算，未预置最终解。
独立校验重算参考解，检查方程组完整解集、矩阵逆乘积、ODE 表达式和单位结果。
校验程序是 scripts/report-ai-benchmark.py，summary.json 保存检查记录。

这只是每条路线两次任务的小样本；模型生成与网络延迟有波动，不能据此保证其他任务更快。
符号计算服务与发行版采用相同计算核心，本轮开发修改的是 CLI、文档及 GUI 交接。
本轮计时不包含打开桌面，自动打开功能另做安装版端到端验证。
早期 exploratory 数据因自选脚本预置了熟知答案，不用于以上任何结论。

原始数据按四个试验目录保存，包含任务、说明、Harness JSONL、实际输入、原始输出和报告。
运行器：scripts/benchmark-deepseek.py；命令计时器：scripts/benchmark-cli-runtime.py。
'''
(bench / 'REPORT.md').write_text(report,encoding='utf8')
print(json.dumps({'checks':checks,'medians':medians,'prepared_ratio':runtime['free_over_calix']},ensure_ascii=False))
