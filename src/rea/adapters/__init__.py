"""Pluggable analysis adapters."""

from rea.adapters.registry import adapters_for, all_capabilities, default_adapters
from rea.adapters.source_code import SourceCodeAdapter

__all__ = ["SourceCodeAdapter", "default_adapters", "adapters_for", "all_capabilities"]
