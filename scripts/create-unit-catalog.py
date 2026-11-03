"""Export Pint's installed definitions and common prefixed aliases for editor completion."""
import json
from pathlib import Path
from backend.units import registry, ALIASES, unit_label

root = Path(__file__).resolve().parents[1]
names = set(registry) | set(ALIASES)
prefixes = ('q','r','y','z','a','f','p','n','u','µ','μ','m','c','d','da','h','k','M','G','T','P','E','Z','Y','R','Q')
for base in ('m','s','g','A','K','mol','N','Pa','J','W','C','V','ohm','S','F','H','Wb','T','Hz','L','eV','bar','Bq','Gy','Sv','kat','byte','bit'):
    for prefix in prefixes:
        name = prefix+base
        try:
            registry.Unit(name)
        except Exception:
            continue
        names.add(name)
records = []
for name in sorted(names):
    try:
        unit = registry.Unit(name)
        if len(name) <= 50:
            records.append({'label': name, 'detail': unit_label(unit)})
    except Exception:
        continue
(root/'frontend/src/unit-catalog.json').write_text(json.dumps(records, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
print(f'{len(records)} searchable unit names and prefixed aliases')
