"""Sample multi-module package for REA project analysis demos."""

from multi_pkg.core.calc import Calculator
from multi_pkg.utils.mathops import add, multiply

__all__ = ["Calculator", "add", "multiply"]
