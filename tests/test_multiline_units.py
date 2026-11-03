import pytest

from backend.engine import Engine
from backend.syntax import InputError, parse


def visible(code):
    result = Engine().execute(code)
    return result['items'] if result['kind'] == 'group' else [result]


@pytest.mark.parametrize('code, expected', [
    ('1+1\n3*4\n5^2', ['2', '12', '25']),
    ('\n1+1\r\n\r\n3*4\n', ['2', '12']),
    ('x=3\nx^2\nx+1', ['3', '9', '4']),
    ('x=3;\nx^2\nx+1;', ['9']),
    ('1;2\n3;4\n5;', ['2', '4']),
    ('2\n-3\n+4', ['2', '-3', '4']),
    ('2 +\n3\n2\n*3\n8\n/2\n2\n^3', ['5', '6', '4', '8']),
    ('Det[{{1,\n2},\n{3,4}}]\nSin[\nPi/2\n]\n(2+\n3)', ['-2', '1', '5']),
    ('2 (3+4)\n2 x', ['14', '2*x']),
    ('(x=2;x+1)\nx', ['3', '2']),
    ('x=1;\ny=2;', ['Null']),
])
def test_multiline_semantics(code, expected):
    assert [item['text'] for item in visible(code)] == expected


def test_multiline_plots_and_suppression():
    result = visible('x=3;\nx^2\nPlot[Sin[t],{t,0,Pi}]\nx+1;')
    assert [item['kind'] for item in result] == ['expression', 'plot']
    assert result[0]['text'] == '9'
    assert visible('x=3;\ny=2;')[0]['latex'] == ''


@pytest.mark.parametrize('code', ['1\nSin[', '1\n2+', '1\n{2,}', '1\n)'])
def test_malformed_multiline(code):
    with pytest.raises(InputError):
        parse(code)


def test_multiline_result_limit():
    assert len(visible('\n'.join(['1']*40))) == 40
    with pytest.raises(InputError, match='40 visible results'):
        Engine().execute('\n'.join(['1']*41))


@pytest.mark.parametrize('code, slash', [
    ('UnitConvert[72[km/h],"m/s"]', r'\mathrm{m}/\mathrm{s}'),
    ('UnitConvert[1[Pa*s],"kg/(m*s)"]', r'\mathrm{kg}/\left(\mathrm{m}\!\cdot\!\mathrm{s}\right)'),
    ('UnitConvert[1[Hz],"1/s"]', r'1/\mathrm{s}'),
    ('UnitConvert[1[m/s^2],"m/s^2"]', r'\mathrm{m}/\mathrm{s}^{2}'),
])
def test_unit_latex_uses_slash(code, slash):
    result = Engine().execute(code)
    assert slash in result['latex']
    assert '[' in result['text'] and ']' in result['text']
    assert r'\frac' not in result['latex']


def test_numeric_fraction_preserved():
    result = Engine().execute('UnitConvert[(1/3)[m/s],"m/s"]')
    assert r'\frac{1}{3}' in result['latex']
    assert r'\mathrm{m}/\mathrm{s}' in result['latex']
