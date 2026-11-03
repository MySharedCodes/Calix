"""Check current documentation links; optionally run onboarding calculations."""
import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CURRENT = [
    'README.md', 'README.zh-CN.md', 'CONTRIBUTING.md', 'SECURITY.md',
    'docs/README.md', 'docs/GETTING-STARTED.md', 'docs/GETTING-STARTED.en.md', 'docs/USER-GUIDE.md',
    'docs/INSTALLATION.md', 'docs/EXAMPLES.md', 'docs/TROUBLESHOOTING.md',
    'docs/DEVELOPMENT.md', 'docs/RELEASING.md', 'docs/ROADMAP.md',
    'docs/SUPPORTED-SYNTAX.md', 'docs/STATISTICS-AND-UNITS.md', 'docs/PDE.md',
    'docs/ACCEPTANCE.md', 'docs/CHANGES-0.1.28.md',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true', help='Also execute Wolfram blocks in README and onboarding guides')
    args = parser.parse_args()
    errors = []
    links = 0
    for name in CURRENT:
        source = ROOT / name
        text = source.read_text(encoding='utf-8')
        prose = re.sub(r'^```[^\n]*\n.*?^```\s*$', '', text, flags=re.M | re.S)
        for match in re.finditer(r'!?\[[^\]\n]*\]\((<[^>]+>|[^)\n]+)\)', prose):
            href = match[1].strip().strip('<>')
            target = urlsplit(href)
            if target.scheme or target.netloc or not target.path:
                continue
            path = (source.parent / unquote(target.path)).resolve()
            links += 1
            if not path.is_relative_to(ROOT) or not path.exists():
                errors.append(f'{name}: missing local target {href}')
            elif path.is_file() and not path.stat().st_size:
                errors.append(f'{name}: empty linked file {href}')
    print(f'Checked {links} local links in {len(CURRENT)} current documents')
    if args.execute:
        sys.path.insert(0, str(ROOT))
        from backend.engine import Engine
        from backend.native import kernel
        kernel.configure_threads(8)
        count = 0
        for name in ('README.md', 'docs/GETTING-STARTED.md', 'docs/GETTING-STARTED.en.md', 'docs/USER-GUIDE.md'):
            engine = Engine()
            for index, code in enumerate(re.findall(r'```wolfram\s*\n(.*?)```', (ROOT / name).read_text(encoding='utf-8'), re.S), 1):
                try:
                    result = engine.execute(code)
                    if not result:
                        raise ValueError('Missing result')
                    count += 1
                    print(f'  OK {name}, block {index}: {result["kind"]}')
                except Exception as exc:
                    errors.append(f'{name}, Wolfram block {index}: {exc}')
        print(f'Executed {count} onboarding code blocks')
    for error in errors:
        print(error, file=sys.stderr)
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
