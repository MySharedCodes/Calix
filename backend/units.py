"""COMSOL-style unit suffixes, using Pint's dimensional and affine unit rules."""
import pint
import sympy as s
from fractions import Fraction
from functools import lru_cache
import re
from .syntax import InputError
from .presentation import expression_latex, expression_string

registry = pint.UnitRegistry(autoconvert_offset_to_baseunit=True, non_int_type=Fraction)

ALIASES = {
    '米': 'm', '厘米': 'cm', '毫米': 'mm', '微米': 'um', '纳米': 'nm', '千米': 'km',
    '秒': 's', '毫秒': 'ms', '微秒': 'us', '分钟': 'min', '小时': 'h', '天': 'day',
    '千克': 'kg', '公斤': 'kg', '克': 'g', '毫克': 'mg', '吨': 'tonne',
    '安培': 'A', '毫安': 'mA', '微安': 'uA', '开尔文': 'K', '摄氏度': 'degC', '华氏度': 'degF',
    '摩尔': 'mol', '坎德拉': 'cd', '弧度': 'rad', '角度': 'deg', '度': 'deg',
    '牛顿': 'N', '帕斯卡': 'Pa', '帕': 'Pa', '焦耳': 'J', '瓦特': 'W', '瓦': 'W',
    '库仑': 'C', '伏特': 'V', '伏': 'V', '欧姆': 'ohm', '西门子': 'S', '法拉': 'F',
    '亨利': 'H', '韦伯': 'Wb', '特斯拉': 'T', '赫兹': 'Hz', '流明': 'lm', '勒克斯': 'lx',
    '升': 'L', '毫升': 'mL', '电子伏特': 'eV', '电子伏': 'eV', '千瓦时': 'kWh',
    '大气压': 'atm', '巴': 'bar', '毫米汞柱': 'mmHg', '英寸': 'inch', '英尺': 'ft',
    '英里': 'mile', '磅': 'lb', '盎司': 'oz', '节': 'knot', '公顷': 'hectare',
    '贝克勒尔': 'Bq', '戈瑞': 'Gy', '西弗': 'Sv', '卡特': 'kat', '原子质量单位': 'u',
    '埃': 'angstrom', '天文单位': 'au', '光年': 'light_year', '秒差距': 'parsec',
    '比特': 'bit', '字节': 'byte', '百分比': 'percent', '转每分': 'rpm',
}
for alias, target in ALIASES.items():
    registry.define(f'@alias {registry.get_name(target)} = {alias}')

# Pint restores pickled quantities through its application registry in every worker.
pint.set_application_registry(registry)


def normalize_unit(text):
    text = text.replace('°C', 'degC').replace('°F', 'degF').replace('°', 'deg').replace('Ω', 'ohm').replace('Ω', 'ohm').replace('μ', 'u').replace('µ', 'u')
    return re.sub(r'(?<=[A-Za-z\u0080-\uffff)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)',
                  lambda match: '^'+match.group(1).translate(str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻', '0123456789-')), text)


@lru_cache(maxsize=2048)
def parse_unit(text):
    if len(text) > 1000:
        raise InputError('Unit expressions are limited to 1,000 characters')
    return registry.parse_units(normalize_unit(text))


def unit_text(node):
    if node.kind == 'string':
        return node.value
    if node.kind == "symbol":
        return {"degC": "degC", "degF": "degF"}.get(node.value, node.value)
    if node.kind == "number":
        return node.value
    if node.kind == "group":
        return f"({unit_text(node.args[0])})"
    if node.kind == "unary" and node.value in ("+", "-"):
        return node.value + unit_text(node.args[0])
    if node.kind == "binary" and node.value in ("*", "/", "^"):
        op = "**" if node.value == "^" else node.value
        return f"({unit_text(node.args[0])}{op}{unit_text(node.args[1])})"
    raise InputError("Invalid unit expression; use m, m/s, kg*m/s^2, etc.")


def quantity(magnitude, unit):
    try:
        if isinstance(unit, str):
            unit = parse_unit(unit)
        return registry.Quantity(magnitude, unit)
    except (pint.PintError, TypeError, ValueError) as exc:
        raise InputError(f"Invalid unit: {exc}") from None


def dimensionless(value, angle=False):
    if isinstance(value, pint.Quantity):
        try:
            if angle and value.units == registry.degree:
                value = s.sympify(value.magnitude) * s.pi / 180
            else:
                value = value.to("radian").magnitude if angle else value.to("").magnitude
        except pint.PintError:
            raise InputError("This function requires a dimensionless argument") from None
    return s.sympify(value)


def format_quantity(value):
    magnitude = s.sympify(value.magnitude)
    if not value.units._units:
        return expression_string(magnitude), expression_latex(magnitude)
    return f"{expression_string(magnitude)}[{unit_label(value.units)}]", expression_latex(magnitude) + r"\;[" + unit_label(value.units, latex=True) + "]"


def unit_label(unit, latex=False):
    # Pint 0.24's formatter cannot format Fraction exponents on Python 3.12.
    numerator, denominator = [], []
    for name, exponent in unit._units.items():
        exponent = s.Rational(exponent)
        label = registry.get_symbol(name)
        term = r"\mathrm{" + label + "}" if latex else label
        power = abs(exponent)
        if power != 1:
            term += "^{" + s.latex(power) + "}" if latex else "^" + (str(power) if power.q == 1 else f"({power})")
        (numerator if exponent > 0 else denominator).append(term)
    joiner = r"\!\cdot\!" if latex else " · "
    top = joiner.join(numerator) or ("1" if denominator else "")
    if not denominator:
        return top
    bottom = joiner.join(denominator)
    if latex:
        return top + "/" + (r"\left(" + bottom + r"\right)" if len(denominator) > 1 else bottom)
    return top + " / " + (f"({bottom})" if len(denominator) > 1 else bottom)


DERIVED_UNITS = ("N", "Pa", "J", "W", "C", "V", "ohm", "S", "F", "H", "Wb", "T", "Hz", "lm", "lx", "Gy", "kat")


def unit_cost(unit):
    return sum(abs(float(power)) for power in unit._units.values()) + 0.25*len(unit._units)


@lru_cache(maxsize=512)
def preferred_unit(unit):
    if len(unit._units) == 1 and next(iter(unit._units.values())) == 1:
        return unit
    for name in DERIVED_UNITS:
        target = registry.Unit(name)
        if unit.dimensionality == target.dimensionality:
            return target
    best = registry.Quantity(1, unit).to_base_units().units
    if unit_cost(unit) <= unit_cost(best):
        best = unit
    # Try one or two named factors, retaining any remaining SI base dimensions.
    factors = [registry.Unit(name)**power for name in DERIVED_UNITS for power in (1, -1, 2, -2)]
    for factor in factors:
        remainder = registry.Quantity(1, unit/factor).to_base_units().units
        candidate = factor*remainder
        if unit_cost(candidate) < unit_cost(best):
            best = candidate
    if unit_cost(best) > 3:
        for first in factors[:]:
            for name in DERIVED_UNITS:
                for power in (1, -1):
                    factor = first*registry.Unit(name)**power
                    candidate = factor*registry.Quantity(1, unit/factor).to_base_units().units
                    if unit_cost(candidate) < unit_cost(best):
                        best = candidate
    return best


def simplify_quantity(value):
    if not isinstance(value, pint.Quantity):
        raise InputError('UnitSimplify expects a quantity or a unit string')
    if value.units in (registry.degree, registry.radian) or any(not registry._units[name].is_multiplicative for name in value.units._units):
        return value
    if value.dimensionless:
        return value.to("")
    return value.to(preferred_unit(value.units))
