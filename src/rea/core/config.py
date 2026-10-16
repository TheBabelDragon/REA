"""Configuration and safety defaults for REA."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SafetyConfig(BaseModel):
    """Hard safety boundaries. Fail closed on violation."""

    allow_network: bool = False
    allow_execution: bool = False
    allow_credential_collection: bool = False
    max_artifact_size_bytes: int = 50 * 1024 * 1024  # 50 MiB
    max_files_per_directory: int = 10_000
    require_explicit_authorization_for_dynamic: bool = True


class StorageConfig(BaseModel):
    """Local-first storage locations."""

    data_dir: Path = Field(default_factory=lambda: Path.home() / ".rea" / "data")
    investigations_dir: Path | None = None  # defaults to data_dir / investigations

    def resolved_investigations_dir(self) -> Path:
        base = self.investigations_dir or (self.data_dir / "investigations")
        base.mkdir(parents=True, exist_ok=True)
        return base


class REAConfig(BaseModel):
    """Top-level configuration."""

    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    schema_version: str = "1.0.0"


DEFAULT_CONFIG = REAConfig()
