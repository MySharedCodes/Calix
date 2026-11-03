"""Retain output labels only in complete authored case notebooks."""
import json
from pathlib import Path
from example_annotations import annotate_notebook

root = Path(__file__).resolve().parents[1]
titles = {json.loads((root/'frontend/src/starter.json').read_text(encoding='utf-8'))['title']}
titles.update(n['title'] for n in json.loads((root/'frontend/src/example-notebooks.json').read_text(encoding='utf-8')))
count = 0
for path in (root/'examples').glob('*.calix'):
    notebook = json.loads(path.read_text(encoding='utf-8'))
    if notebook['title'] in titles:
        path.write_text(json.dumps(annotate_notebook(notebook),ensure_ascii=False,indent=2),encoding='utf-8')
        count += 1
print(f'Annotated {count} complete case notebooks; basic demonstrations remain unlabeled')
