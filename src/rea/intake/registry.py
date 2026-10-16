"""Artifact registration, metadata extraction, and input validation."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

from rea.core.config import REAConfig, DEFAULT_CONFIG
from rea.core.errors import IntakeError, SafetyBoundaryError
from rea.core.models import Artifact, ArtifactKind, content_digest

_SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp",
    ".hpp", ".cc", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".cs", ".m", ".mm", ".r", ".jl", ".lua", ".sh", ".bash", ".zsh", ".ps1",
    ".sql", ".html", ".htm", ".css", ".scss", ".vue", ".svelte",
}
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".json", ".yaml", ".yml", ".toml", ".xml",
    ".csv", ".ini", ".cfg", ".conf", ".log", ".gitignore", ".dockerfile",
}
_ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"}
_BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".elf",
    ".class", ".jar", ".apk", ".ipa", ".wasm",
}


def detect_kind(path: Path) -> ArtifactKind:
    if path.is_dir():
        return ArtifactKind.DIRECTORY
    if not path.is_file():
        return ArtifactKind.UNKNOWN
    suffix = path.suffix.lower()
    if suffix in _SOURCE_EXTENSIONS:
        return ArtifactKind.SOURCE_CODE
    if suffix in _TEXT_EXTENSIONS:
        return ArtifactKind.TEXT
    if suffix in _ARCHIVE_EXTENSIONS:
        return ArtifactKind.ARCHIVE
    if suffix in _BINARY_EXTENSIONS:
        return ArtifactKind.BINARY
    try:
        with path.open("rb") as f:
            sample = f.read(8192)
        if b"\x00" in sample:
            return ArtifactKind.BINARY
        sample.decode("utf-8")
        return ArtifactKind.TEXT
    except (OSError, UnicodeDecodeError):
        return ArtifactKind.UNKNOWN


def register_artifact(
    path: str | Path, *, config: REAConfig | None = None, notes: str | None = None
) -> Artifact:
    cfg = config or DEFAULT_CONFIG
    p = Path(path).resolve()
    if not p.exists():
        raise IntakeError(f"path does not exist: {p}")
    if p.is_file():
        size = p.stat().st_size
        if size > cfg.safety.max_artifact_size_bytes:
            raise SafetyBoundaryError(
                f"artifact size {size} exceeds limit {cfg.safety.max_artifact_size_bytes} bytes"
            )
        try:
            data = p.read_bytes()
            digest = content_digest(data)
        except OSError as exc:
            raise IntakeError(f"cannot read artifact: {exc}") from exc
        kind = detect_kind(p)
        mime, _ = mimetypes.guess_type(str(p))
        return Artifact(
            kind=kind, origin=str(p),
            metadata={"filename": p.name, "suffix": p.suffix.lower(), "mime_type": mime, "is_file": True, "is_dir": False},
            content_digest=digest, size_bytes=size, notes=notes,
        )
    if p.is_dir():
        entries: list[str] = []
        try:
            for root, dirs, files in os.walk(p):
                if len(entries) >= cfg.safety.max_files_per_directory:
                    dirs.clear()
                    break
                rel = Path(root).relative_to(p)
                for name in files:
                    entries.append(str(rel / name) if str(rel) != "." else name)
                    if len(entries) >= cfg.safety.max_files_per_directory:
                        break
        except OSError as exc:
            raise IntakeError(f"cannot walk directory: {exc}") from exc
        return Artifact(
            kind=ArtifactKind.DIRECTORY, origin=str(p),
            metadata={"filename": p.name, "is_file": False, "is_dir": True,
                      "entry_count": len(entries), "entries_sample": entries[:100],
                      "truncated": len(entries) >= cfg.safety.max_files_per_directory},
            notes=notes,
        )
    raise IntakeError(f"unsupported path type: {p}")
