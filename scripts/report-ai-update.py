"""Check raw responses and keep complete agent clocks separate from CLI clocks."""
import json
from pathlib import Path
import statistics

import sympy as s
from sympy.parsing.mathematica import parse_mathematica

root = Path(__file__).resolve().parents[1]
folder = root/'work/ai-benchmark-v0127-final'
load = lambda path: json.loads(path.read_text(encoding='utf8'))
baseline = load(root/'work/ai-benchmark-v0126/summary.json')
runs = load(folder/'executions.json')
k,x,y,z,t = s.symbols('k x y z t')
a = s.Matrix([[4,1,0,2],[1,5,2,0],[0,2,6,1],[2,0,1,7]])
checks = []
for run in runs:
    trial = folder/f"calix-{run['trial']:02}"
    matches = []
    for path in trial.glob('*.json'):
        data = load(path)
        if isinstance(data,dict) and data.get('ok') and data.get('result',{}).get('kind')=='group':
            items = data['result']['items']
            if len(items)==6:
                matches.append((path,data,items))
    assert matches, f'No full actual response in {trial}'
    path,data,items = matches[0]
    text = [item['text'] for item in items]
    assert parse_mathematica(text[0]) == s.summation(k**6,(k,1,500))
    assert s.simplify(parse_mathematica(text[1])-s.integrate(x**4*s.exp(-3*x*x),(x,-s.oo,s.oo)))==0
    expected_solutions = s.solve([x+y+z-6,x*x+y*y+z*z-14,x*y-2],(x,y,z),dict=True)
    expected_text = str(expected_solutions).replace('[','{').replace(']','}')
    assert text[2] == expected_text
    matrix_result = parse_mathematica(text[3])
    assert matrix_result[0] == a.det()
    assert a*s.Matrix(matrix_result[1]) == s.eye(4)
    ode = parse_mathematica(text[4]).rhs
    assert s.simplify(s.diff(ode,t,2)+3*s.diff(ode,t)+2*ode-s.exp(-t))==0
    assert ode.subs(t,0)==0 and s.diff(ode,t).subs(t,0)==1
    mass = 650*s.Rational('0.06479891')
    energy = mass/1000*890**2/2
    assert text[5] == '{'+str(mass)+'[g], '+str(energy)+'[J]}'
    assert data['result']['execution']['thread_limit']==8
    checks.append({'trial':trial.name,'response':path.name,'six_answers_correct':True,'worker_limit':8})
assert len(runs)==2 and all(run['returncode']==0 and run['final'] for run in runs)
median = statistics.median(run['wall_seconds'] for run in runs)
old = baseline['agent_median_seconds']['calix']
free = baseline['agent_median_seconds']['free']
before = load(root/'work/ai-overhead-v0126/timing.json')
after = load(root/'work/ai-overhead-v0127/timing.json')
summary = {'version':'0.1.27','agent_seconds':{'before_calix':old,'after_calix':median,'previous_self_selected':free},
    'calix_reduction_percent':100*(1-median/old),'relative_to_previous_self_selected_percent':100*(median/free-1),
    'trials':runs,'independent_checks':checks,'cli_before':before['medians'],'cli_after':after['medians'],
    'pipe_roundtrip':after['pipe_roundtrip']}
(folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
rows='\n'.join(f"| Calix 0.1.27 | {run['trial']} | {run['wall_seconds']:.2f} | {run['tool_calls']} | 6/6 |" for run in runs)
cli_rows='\n'.join(f"| {label} | {before['medians'][key]:.3f} | {after['medians'][key]:.3f} | {100*(1-after['medians'][key]/before['medians'][key]):.1f}% |"
    for key,label in [('single','一次新 CLI 调用，1+1'),('six_cells','六个 notebook 单元'),('six_in_one','一个 .wl 文件六题')])
report=f'''# Calix 0.1.27：AI 调用和笔记本交付验证

日期：2026-10-31。本机 DeepSeek Harness，deepseek-flash，high reasoning，headless。
六题与上一版相同：精确求和、高斯积分、方程组、矩阵行列式及逆矩阵、初值 ODE、grain 单位和动能。
说明文件放在任务目录，任务提示不介绍软件；两轮使用全新会话，调试上限 8 Workers。

## 完整 AI 工作流程

计时从 Harness 启动到最终答复，包括读文档、模型及网络等待、编写代码、工具调用、检查和写报告。
计时期间不进行大型编译或测试，不打开 GUI。下表为最终安装版测试。

| 路线 | 轮次 | 秒 | 工具调用数 | 独立检查 |
|---|---:|---:|---:|---|
{rows}

本版中位数 {median:.2f} 秒；上一版 Calix 为 {old:.2f} 秒，减少 {100*(1-median/old):.1f}%。
此前自选 Python/SymPy/Pint 路线中位数为 {free:.2f} 秒。
本版相对该历史自选路线的时间变化为 {100*(median/free-1):+.1f}%（负数代表更短）。
这是时间分开的两轮小样本对照，包含模型生成与网络波动，不能据此认定通用速度优势。
原始输入和完整工具响应均保存，校验代码重新求解参考答案，没有只检查模型报告。
此前本版的探索两轮为 89.82 和 118.87 秒，包含失效连接发现延迟，服务上限为 24；
保留在 ai-benchmark-v0127 中，不混入最终 8 Workers 数据。

## CLI 本身的调用开销

安装版、常驻服务已启动、8 Workers；每项运行八次，排除首轮预热，余下七次取中位数。
包含客户端启动、传输和实际计算，不包含 AI 思考、文件编写和 GUI。

| 操作 | 0.1.26 秒 | 0.1.27 秒 | 减少 |
|---|---:|---:|---:|
{cli_rows}

持久 JSONL pipe 的二十次逐条请求中位数为 {after['pipe_roundtrip']['median_seconds']*1000:.2f} ms，
排除了首条客户端启动及连接发现，不能作为冷启动时间。
失效服务记录的额外回归检查单独保存在 packaged-export-v0127/verification.json。

## 笔记本可靠性

Windows 启动支持位置文件参数；文件打开统一接受 UTF-8 起始 BOM。
原始 DeepSeek 笔记本不改写。已通过 Explorer 文件关联启动，使用 UI Automation 核对实际标题；
另测手动打开、内部 BOM 字符保留和根式渲染。
AI 用 --notebook 导出带真实结果的标准文件，validate 离线检查结构与语法。
结构语法检查不证明数学或物理模型正确；自动打开后的内核为新会话，需要继续计算时重跑定义。

求解器、原始精确值不因显示合并根式而改变；未知符号正负和复数分支不强制合并。
全套 Python 测试 303 项通过，连接发现最终补丁后的 API 测试 21 项通过；
Rust 启动参数测试及 JavaScript BOM 测试通过。安装测试检查原有笔记本和设置保持。
'''
(folder/'REPORT.md').write_text(report,encoding='utf8')
print(json.dumps({'agent_median_seconds':median,'checks':checks},ensure_ascii=False))
