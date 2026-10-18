"""Pure arithmetic helpers."""

from __future__ import annotations


def add(a: float, b: float) -> float:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


def power(base: float, exp: float) -> float:
    return base ** exp


def _private_helper(x: float) -> float:
    return x * 2
