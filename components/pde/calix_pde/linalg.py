"""Finite-element sparse factorization through the native Eigen core."""
from backend.native import kernel


def solve(matrix,load):
    return kernel.sparse_solve(matrix,load)
