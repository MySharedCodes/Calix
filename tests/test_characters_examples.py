import json
import re
from pathlib import Path

import pytest
import sympy as s

from backend.engine import Engine
from backend.syntax import CHARACTERS, parse
from backend.units import parse_unit


@pytest.mark.parametrize('code, expected', [
    ('α=3;α^2', '9'), ('x₁=2;x₁^3', '8'),
    ('m₁₂=7;m_12+1', '8'), ('ⅇ^0+ⅈ^2', '0'),
    ('2·3+4⋅5', '26'), ('ReplaceAll[x, x→3]', '3'),
    ('Simplify[α+α]', '2*α'), ('Integrate[α*x,x]', '(1/2)*x^2*α'),
])
def test_character_evaluation(code, expected):
    assert Engine().execute(code)['text'] == expected


def test_named_characters_and_strings():
    for name, character, *_ in CHARACTERS:
        if len(character) == 1 and character.isalpha() and name != 'Pi':
            assert parse(f'\\[{name}]') == parse(character)
    assert parse('"x₁ α ·"').value == 'x₁ α ·'
    assert s.Symbol('x_12') in Engine().evaluate(parse('x₁₂+1')).free_symbols
    assert r'x_{12}' in Engine().execute('x₁₂')['latex']


def test_distributed_case_identifiers_are_mathematical():
    cases = [json.loads(Path('frontend/src/starter.json').read_text(encoding='utf-8')),
             *json.loads(Path('frontend/src/example-notebooks.json').read_text(encoding='utf-8'))]
    def check(node):
        if node.kind == 'symbol' and node.value[0].islower():
            if not re.fullmatch(r'[^\W\d_](?:_\d+)?', node.value, re.UNICODE):
                try:
                    parse_unit(node.value)
                except Exception:
                    pytest.fail(f'Nonmathematical identifier: {node.value}')
        for child in node.args:
            check(child)
    for notebook in cases:
        for cell in notebook['cells']:
            if cell['mode'] != 'markdown':
                check(parse(cell['code']))


def test_units_have_visible_multiplication_dots():
    result = Engine().execute('UnitConvert[1[kg/(m*s)],"kg/(m*s)"]')
    assert '[kg / (m · s)]' in result['text']
    assert r'\mathrm{m}\!\cdot\!\mathrm{s}' in result['latex']
    assert r'\frac' not in result['latex']
    assert 'Pa · s' in Engine().execute('1[kg/(m*s)]')['text']
