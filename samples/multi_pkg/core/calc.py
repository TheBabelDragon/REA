"""Calculator module with local and cross-module calls."""

from __future__ import annotations

from multi_pkg.utils.mathops import add, multiply
from multi_pkg.utils import power  # may resolve via package

# Missing import — should surface as unresolved if treated as local package miss
# from multi_pkg.missing import ghost  # left commented; dynamic below

import importlib  # dynamic uncertainty


class Calculator:
    def __init__(self) -> None:
        self.history: list[str] = []

    def compute(self, op: str, a: float, b: float) -> float:
        if op == "+":
            result = add(a, b)
        elif op == "*":
            result = multiply(a, b)
        elif op == "^":
            result = power(a, b)
        else:
            raise ValueError(f"unknown op: {op}")
        self.history.append(f"{a} {op} {b} = {result}")
        return result

    def load_plugin(self, name: str):
        """Dynamic import — must be marked unresolved, never executed."""
        return importlib.import_module(name)


def ghost_call():
    """Calls an undefined name — unresolved reference."""
    return missing_function(1, 2)  # noqa: F821
