"""Run bounded validation tiers and retain machine-readable evidence."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CORE = ['tests/test_engine.py', 'tests/test_independent_validation.py', 'tests/test_presentation.py',
        'tests/test_multiline_units.py', 'tests/test_service.py', 'tests/test_cli_api.py',
        'tests/test_release_licensing.py']
NUMERICAL = ['tests/test_cpu_dispatch.py', 'tests/test_execution_runtime.py',
             'tests/test_parallel_sparse.py', 'tests/test_triangular_mesh.py', 'tests/test_pde.py']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tier', choices=['core', 'numerical', 'examples'], default='core')
    parser.add_argument('--timeout', type=int, default=900)
    parser.add_argument('--output', type=Path, default=ROOT/'work/verification')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('CALIX_MAX_WORKERS', '8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    commands = [[sys.executable, '-m', 'pytest', *CORE, '-q', '-k', 'not shipped_examples and not physics_starter', f'--junitxml={args.output / "core.xml"}'],
                ['node', 'tests/workspace-codec.cjs'], ['node', 'tests/workspace-history.cjs'],
                [sys.executable, 'scripts/check-docs.py', '--execute']]
    if args.tier == 'numerical':
        commands = [[sys.executable, '-m', 'pytest', *NUMERICAL, '-q', f'--junitxml={args.output / "numerical.xml"}']]
    elif args.tier == 'examples':
        commands = [[sys.executable, '-m', 'pytest', 'tests/test_engine.py', '-q', '-s', '-o', 'faulthandler_timeout=120', '-k', 'shipped_examples or physics_starter', f'--junitxml={args.output / "examples.xml"}']]
    records = []
    for index, command in enumerate(commands):
        start = time.perf_counter()
        with (args.output/f'{args.tier}-{index}.log').open('w', encoding='utf-8') as log:
            try:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                status = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], stdout=log, stderr=log)
                else:
                    process.kill()
                process.wait()
                status = 'timeout'
        records.append({'command': command, 'exit_code': status, 'seconds': round(time.perf_counter()-start, 3)})
        print(f'{args.tier} check {index+1}: {status}', flush=True)
    result = {'tier': args.tier, 'passed': all(item['exit_code'] == 0 for item in records), 'checks': records}
    (args.output/f'{args.tier}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
