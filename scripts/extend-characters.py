"""Extend the shared catalog with Unicode mathematical alphabets and symbols."""
import json
from pathlib import Path
import string
import unicodedata

path = Path(__file__).resolve().parents[1] / 'backend/characters.json'
rows = json.loads(path.read_text(encoding='utf-8'))
present = {row[0] for row in rows}
legacy = {'ScriptCapitalB': 'ℬ', 'ScriptCapitalE': 'ℰ', 'ScriptCapitalF': 'ℱ',
          'ScriptCapitalH': 'ℋ', 'ScriptCapitalI': 'ℐ', 'ScriptCapitalL': 'ℒ',
          'ScriptCapitalM': 'ℳ', 'ScriptCapitalR': 'ℛ', 'Scripte': 'ℯ',
          'Scriptg': 'ℊ', 'Scripto': 'ℴ'}
for style, alias in [('SCRIPT', 'sc'), ('FRAKTUR', 'fr'), ('DOUBLE-STRUCK', 'ds'), ('BOLD', 'bo')]:
    for letter in string.ascii_letters:
        capital = letter.isupper()
        name = style.title().replace('-', '') + ('Capital' if capital else '') + letter.upper() if capital else style.title().replace('-', '') + letter
        try:
            glyph = unicodedata.lookup(f'MATHEMATICAL {style} {"CAPITAL" if capital else "SMALL"} {letter.upper()}')
        except KeyError:
            glyph = legacy.get(name)
            if glyph is None:
                try: glyph = unicodedata.lookup(f'{"DOUBLE-STRUCK" if style == "DOUBLE-STRUCK" else "BLACK-LETTER"} CAPITAL {letter.upper()}')
                except KeyError: continue
        if name not in present:
            rows.append([name, glyph, alias + letter]); present.add(name)
for row in [
    ['PlusMinus','±','+-','pm'], ['MinusPlus','∓','-+','mp'], ['Dot','⋅','dot'],
    ['Cross','⨯','cross'], ['Not','¬','not'], ['Implies','⇒','implies'],
    ['Equivalent','⇔','iff'], ['LeftArrow','←','left'], ['LeftRightArrow','↔','lr'],
    ['HBar','ℏ','hbar'], ['EmptySet','∅','empty'], ['Angle','∠','angle'],
    ['Aleph','ℵ','aleph'], ['Ellipsis','…','...'], ['VerticalEllipsis','⋮','vdots'],
    ['DiagonalEllipsis','⋱','ddots'], ['TensorProduct','⊗','tensor'], ['CirclePlus','⊕','oplus'],
    ['Square','□','square'], ['FilledSquare','■','fsquare'], ['Checkmark','✓','check'],
]:
    if row[0] not in present: rows.append(row); present.add(row[0])
path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(rows)} named characters')
