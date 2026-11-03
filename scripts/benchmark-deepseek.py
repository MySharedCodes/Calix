"""Independent fresh Harness sessions; clocks include planning and tool execution."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / 'work/ai-benchmark-v0126'
HARNESS = Path(os.environ['LOCALAPPDATA']) / 'Programs/DeepSeek Harness/resources/runtime/cli/bin/dsh.cmd'
PATCH = ROOT / 'work/deepseek-account-v0125.yml'
PROBLEMS = '''请实际计算以下六题：
1. 精确计算 k 从 1 到 500 的 k^6 之和。
2. 求 x^4 exp(-3 x^2) 在整个实数轴上的积分，保留解析形式。
3. 求方程组 x+y+z=6、x^2+y^2+z^2=14、x*y=2 的所有实数解。
4. 求矩阵 {{4,1,0,2},{1,5,2,0},{0,2,6,1},{2,0,1,7}} 的行列式及精确逆矩阵。
5. 求 x''(t)+3*x'(t)+2*x(t)=exp(-t)，x(0)=0、x'(0)=1 的解析解。
6. 将 650 grain 换算为克，并求该质量以 890 m/s 运动时的动能（焦耳）。
每题都必须通过通用的求和、积分、方程/ODE、矩阵或单位工具从输入求出，不能预置解析解或把熟知答案写入脚本再验证。
将实际工具输入、原始输出、results.json（六题结果，按题号排列）、简短 report.md 写在当前任务目录；不要读取其它试验目录、修改软件源代码或设置。阅读当前目录的说明文件。此次仅计时，不要打开桌面。'''


def execute(route, number):
    folder = BENCH / f'{route}-{number:02}'
    folder.mkdir(parents=True, exist_ok=False)
    if route == 'calix':
        for name in ('AGENTS.md', 'API.md', 'AI-CONTROL.md'):
            shutil.copy2(ROOT / name, folder / name)
        # Use the source launcher so this experiment does not depend on an old installed runtime.
        guide = (folder / 'AGENTS.md').read_text(encoding='utf8')
        guide += '\nFor this task, use D:/Calix/calix-cli.exe. Save task artifacts in the current directory.\n'
        (folder / 'AGENTS.md').write_text(guide, encoding='utf8')
    else:
        (folder / 'AGENTS.md').write_text(
            '# Available calculation environment\n\n'
            'Choose your own local tools. Python with SymPy, NumPy, SciPy and Pint is at '
            '`D:/Calix/.venv/Scripts/python.exe`. This is the same environment available to the other route. '
            'Do not use the Calix application, CLI, API, source code, documentation or result files. '
            'Only write in the current directory.\n', encoding='utf8')
    (folder / 'task.txt').write_text(PROBLEMS, encoding='utf8')
    started_at = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    started = time.perf_counter()
    with (folder / 'events.jsonl').open('w', encoding='utf8') as out, (folder / 'stderr.txt').open('w', encoding='utf8') as err:
        process = subprocess.Popen([str(HARNESS), '--profile', 'headless', '--patch', str(PATCH), '--json', '-'],
            cwd=folder, env={**os.environ, 'DSH_PERMISSION_MODE': 'danger-full-access'},
            stdin=subprocess.PIPE, stdout=out, stderr=err, text=True, encoding='utf8',
            creationflags=subprocess.CREATE_NO_WINDOW)
        print(json.dumps({'route': route, 'trial': number, 'event': 'started', 'pid': process.pid}), flush=True)
        try:
            process.communicate(PROBLEMS, timeout=900)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)
    elapsed = time.perf_counter() - started
    events = []
    for line in (folder / 'events.jsonl').read_text(encoding='utf8', errors='replace').splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    final = next((e.get('text') for e in reversed(events) if e.get('type') == 'final'), None)
    result = {'route': route, 'trial': number, 'started_at': started_at,
        'ended_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'wall_seconds': elapsed,
        'harness_returncode': process.returncode, 'final': final,
        'tool_calls': sum(e.get('type') == 'tool_call' for e in events),
        'step_tokens': [e.get('usage') for e in events if e.get('phase') == 'step_end']}
    (folder / 'execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'route': route, 'trial': number, 'wall_seconds': elapsed,
        'finished': bool(final), 'returncode': process.returncode}), flush=True)
    return result


if __name__ == '__main__':
    BENCH.mkdir(parents=True, exist_ok=True)
    runs = []
    for route, number in [('calix', 1), ('free', 1), ('free', 2), ('calix', 2)]:
        runs.append(execute(route, number))
        (BENCH / 'executions.json').write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding='utf8')
