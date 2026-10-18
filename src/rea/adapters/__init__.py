"""Pluggable analysis adapters."""

from rea.adapters.python_project import PythonProjectAdapter
from rea.adapters.registry import (
    adapters_for,
    all_capabilities,
    default_adapters,
    default_project_adapters,
)
from rea.adapters.source_code import SourceCodeAdapter

__all__ = [
    "SourceCodeAdapter",
    "PythonProjectAdapter",
    "default_adapters",
    "default_project_adapters",
    "adapters_for",
    "all_capabilities",
]
