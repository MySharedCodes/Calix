"""Keep scalar calculations independent of the optional unit-library startup."""
import sys
import sympy as s


def is_quantity(value):
    pint = sys.modules.get('pint')
    return pint is not None and hasattr(pint, 'Quantity') and isinstance(value, pint.Quantity)


def dimensionless(value, angle=False):
    if not is_quantity(value):
        return s.sympify(value)
    from .units import dimensionless as convert
    return convert(value, angle=angle)


def quantity(magnitude, unit):
    from .units import quantity as make
    return make(magnitude, unit)


def unit_text(node):
    from .units import unit_text as text
    return text(node)


def format_quantity(value):
    from .units import format_quantity as format_value
    return format_value(value)


def simplify_quantity(value):
    from .units import simplify_quantity as simplify
    return simplify(value)


def unit_label(unit, latex=False):
    from .units import unit_label as label
    return label(unit, latex=latex)
