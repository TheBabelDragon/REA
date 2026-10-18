"""Configuration and safety defaults for REA."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class SafetyConfig(BaseModel):
    allow_network: bool = False
    allow_execution: bool = False
    allow_credential_collection: bool = False
    max_artifact_size_bytes: int = 50 * 1024 * 1024
    max_files_per_directory: int = 10_000
    require_explicit_authorization_for_dynamic: bool = True


class ProjectIntakeConfig(BaseModel):
    """Bounded multi-file project intake limits and exclusions."""

    max_file_count: int = 500
    max_file_size_bytes: int = 2 * 1024 * 1024  # 2 MiB per file
    max_total_size_bytes: int = 50 * 1024 * 1024  # 50 MiB total
    max_depth: int = 20
    # Directory / path segment names to skip entirely
    exclude_dir_names: list[str] = Field(
        default_factory=lambda: [
            ".git",
            ".hg",
            ".svn",
            ".bzr",
            "__pycache__",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
            ".tox",
            ".nox",
            ".venv",
            "venv",
            "env",
            "node_modules",
            "dist",
            "build",
            ".eggs",
            ".idea",
            ".vscode",
        ]
    )
    # File name patterns (exact basenames) to skip
    exclude_file_names: list[str] = Field(
        default_factory=lambda: [
            ".DS_Store",
            "Thumbs.db",
        ]
    )
    # Supported source / config suffixes for project intake
    supported_suffixes: list[str] = Field(
        default_factory=lambda: [
            ".py",
            ".pyi",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".c",
            ".h",
            ".cpp",
            ".hpp",
            ".go",
            ".rs",
            ".rb",
            ".json",
            ".toml",
            ".yaml",
            ".yml",
            ".cfg",
            ".ini",
            ".md",
            ".txt",
        ]
    )
    follow_symlinks: bool = False  # never follow outside root regardless


class StorageConfig(BaseModel):
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".rea" / "data")
    investigations_dir: Path | None = None

    def resolved_investigations_dir(self) -> Path:
        base = self.investigations_dir or (self.data_dir / "investigations")
        base.mkdir(parents=True, exist_ok=True)
        return base


class REAConfig(BaseModel):
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    project: ProjectIntakeConfig = Field(default_factory=ProjectIntakeConfig)
    schema_version: str = "1.0.0"


DEFAULT_CONFIG = REAConfig()
