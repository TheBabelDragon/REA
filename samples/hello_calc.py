#!/usr/bin/env python3
"""Minimal sample artifact for REA end-to-end demonstration.

A tiny calculator module with clear structure for static analysis.
"""

from __future__ import annotations

import math
from typing import Callable


def add(a: float, b: float) -> float:
    """Return the sum of a and b."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Return a minus b."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Return the product of a and b."""
    return a * b


def divide(a: float, b: float) -> float:
    """Return a divided by b. Raises ZeroDivisionError if b is zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b


def power(base: float, exp: float) -> float:
    """Return base raised to exp using math.pow."""
    return math.pow(base, exp)


OPERATIONS: dict[str, Callable[[float, float], float]] = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
    "^": power,
}


class Calculator:
    """Simple stateful calculator."""

    def __init__(self) -> None:
        self.history: list[str] = []

    def compute(self, op: str, a: float, b: float) -> float:
        if op not in OPERATIONS:
            raise ValueError(f"unknown operation: {op}")
        result = OPERATIONS[op](a, b)
        self.history.append(f"{a} {op} {b} = {result}")
        return result

    def clear(self) -> None:
        self.history.clear()


if __name__ == "__main__":
    calc = Calculator()
    print(calc.compute("+", 2, 3))
    print(calc.compute("*", 4, 5))
    print(calc.history)
