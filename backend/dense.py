"""Runtime-dispatched matrix products without changing exact or floating precision."""
import sympy as s
import sys
from .native import kernel


def machine_matrix(value):
    """Pack an inexact real matrix when the optional numeric runtime is loaded."""
    np = sys.modules.get('numpy')
    if np is None:
        return None
    rows = value.tolist() if isinstance(value, s.MatrixBase) else value
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list) or not rows[0]:
        return None
    width = len(rows[0])
    if any(not isinstance(row, list) or len(row) != width for row in rows):
        return None
    values = [item for row in rows for item in row]
    if not any(isinstance(item, (float, s.Float)) for item in values):
        return None
    if any(not isinstance(item, (int, float, s.Rational, s.Float))
           or isinstance(item, s.Float) and item._prec > 53
           or isinstance(item, (int, s.Integer)) and abs(item) > 2**53 for item in values):
        return None
    try:
        packed = np.asarray(rows, dtype=float)
        return packed if np.isfinite(packed).all() else None
    except (TypeError, ValueError, OverflowError):
        return None


def product(left,right):
    if not kernel.available or left.cols!=right.rows or left.rows*left.cols*right.cols<32768:
        return None
    values=list(left)+list(right)
    if any(not isinstance(v,s.Number) or v.is_real is not True or v.is_finite is not True for v in values):
        return None
    integers=all(v.is_Integer and -128<=v<=127 for v in values)
    machine=all(v.is_Integer or isinstance(v,s.Float) and v._prec<=53 for v in values) and any(isinstance(v,s.Float) for v in values)
    if not integers and not machine:return None
    result,route=kernel.dense_dot(left.tolist(),right.tolist(),integer=integers)
    return s.Matrix(result),route
