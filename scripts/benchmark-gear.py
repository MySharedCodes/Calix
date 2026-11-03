"""Time the unchanged gear notebook in isolation and retain repeatable solver state."""
import argparse
import cProfile
import hashlib
import json
import pickle
import pstats
from pathlib import Path
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=ROOT/'work/gear-benchmark/state.pickle')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--unrestricted-affinity', action='store_true', help='Reproduce direct-engine tests without the desktop CPU affinity')
    parser.add_argument('--reference-exe', type=Path, help='Compare the engine embedded in an existing local Calix binary')
    parser.add_argument('--output', type=Path, default=ROOT/'work/gear-benchmark')
    args = parser.parse_args()
    from backend.engine import Engine
    if args.reference_exe:
        from PyInstaller.archive.readers import CArchiveReader
        archived = CArchiveReader(str(args.reference_exe)).open_embedded_archive('PYZ.pyz').extract('backend.engine')
        module = types.ModuleType('backend.reference_engine')
        module.__package__ = 'backend'
        exec(archived, module.__dict__)
        Engine = module.Engine
    from backend.native import kernel
    from backend.hardware import limit_process_cores
    kernel.configure_threads(8)
    affinity = None if args.unrestricted_affinity else limit_process_cores(8)
    notebook_path = ROOT/'examples/齿轮啮合-接触与扭矩传递.calix'
    notebook = json.loads(notebook_path.read_text(encoding='utf-8'))
    cells = [(i+1, cell['code']) for i, cell in enumerate(notebook['cells']) if cell['mode'] != 'markdown']
    args.output.mkdir(parents=True, exist_ok=True)
    engine = Engine()
    if args.resume:
        # Only use locally generated benchmark state, never an untrusted notebook.
        engine.environment, engine.assumptions = pickle.loads(args.state.read_bytes())
        cells = cells[-1:]
    records = []
    for index, code in cells:
        print(f'Cell {index}: starting', flush=True)
        profiler = cProfile.Profile() if args.profile else None
        start = time.perf_counter()
        cpu_start = time.process_time()
        if profiler: profiler.enable()
        result = engine.execute(code)
        if profiler: profiler.disable()
        seconds = time.perf_counter()-start
        cpu_seconds = time.process_time()-cpu_start
        if profiler:
            profiler.dump_stats(str(args.output/f'cell-{index}.prof'))
            with (args.output/f'cell-{index}-profile.txt').open('w', encoding='utf-8') as output:
                pstats.Stats(profiler, stream=output).strip_dirs().sort_stats('cumtime').print_stats(45)
        records.append({'cell': index, 'seconds': seconds, 'cpu_seconds': cpu_seconds, 'execution': result['execution']})
        (args.output/f'cell-{index}-result.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
        print(f'Cell {index}: {seconds:.3f}s', flush=True)
        if len(cells) > 1 and index == cells[-2][0]:
            args.state.parent.mkdir(parents=True, exist_ok=True)
            args.state.write_bytes(pickle.dumps((engine.environment, engine.assumptions)))
    record = {'affinity': affinity, 'cells': records, 'workers': kernel.thread_limit,
              'profiled': args.profile, 'reference_exe': str(args.reference_exe) if args.reference_exe else None,
              'notebook_sha256': hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
              'nodes': len(engine.environment['q']), 'triangles': sum(map(len, engine.environment['f'])),
              'coordinate_type': type(engine.environment['q'][0][0]).__name__,
              'displacement_type': type(engine.environment['u']).__name__,
              'scope': 'Isolated source-engine evaluation; excludes GUI, IPC, JSON export and profiling report writes. Do not run concurrently with builds or other benchmarks.'}
    (args.output/'timing.json').write_text(json.dumps(record, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
