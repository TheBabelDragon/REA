"""Bounded multi-file project intake.

Recursively discovers supported source and configuration files under a project
root, applying configurable file-count, per-file-size and total-size limits.
Never follows a symlink outside the selected project root. Never executes
inspected code.
"""

from __future__ import annotations

import os
from pathlib import Path

from rea.core.config import DEFAULT_CONFIG, REAConfig
from rea.core.errors import IntakeError
from rea.core.models import (
    Artifact,
    ArtifactKind,
    FileAnalysisStatus,
    ProjectFileRecord,
    content_digest,
)
from rea.intake.registry import detect_kind

_LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".cfg": "config",
    ".ini": "config",
}


def _is_excluded_dir(name: str, exclude_names: list[str]) -> bool:
    if name in exclude_names:
        return True
    if name.endswith(".egg-info"):
        return True
    return False


def _safe_resolve_under_root(path: Path, root: Path) -> Path | None:
    """Resolve path; return None if it escapes root (symlink escape / traversal)."""
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
        if hasattr(resolved, "is_relative_to"):
            if not resolved.is_relative_to(root_resolved):
                return None
        else:
            try:
                resolved.relative_to(root_resolved)
            except ValueError:
                return None
        return resolved
    except (OSError, RuntimeError):
        return None


def intake_project(
    path: str | Path,
    *,
    config: REAConfig | None = None,
    notes: str | None = None,
) -> tuple[Artifact, list[ProjectFileRecord], list[Artifact]]:
    """Discover and register files under a project root.

    Returns:
        (root_directory_artifact, file_records, per_file_artifacts)

    Raises:
        IntakeError: path missing or not a directory
        SafetyBoundaryError: limits exceeded or symlink escape
    """
    cfg = config or DEFAULT_CONFIG
    pcfg = cfg.project
    root = Path(path)
    if not root.exists():
        raise IntakeError(f"path does not exist: {root}")
    if not root.is_dir():
        raise IntakeError(f"project intake requires a directory: {root}")

    root_resolved = root.resolve()
    records: list[ProjectFileRecord] = []
    file_artifacts: list[Artifact] = []
    total_size = 0
    truncated = False
    skipped_symlink_escape = 0
    skipped_excluded = 0
    skipped_unsupported = 0

    for dirpath, dirnames, filenames in os.walk(root_resolved, followlinks=False):
        current = Path(dirpath)
        try:
            rel_dir = current.relative_to(root_resolved)
            depth = len(rel_dir.parts)
        except ValueError:
            dirnames.clear()
            continue
        if depth > pcfg.max_depth:
            dirnames.clear()
            continue

        kept: list[str] = []
        for d in dirnames:
            if _is_excluded_dir(d, pcfg.exclude_dir_names):
                skipped_excluded += 1
                continue
            child = current / d
            if child.is_symlink():
                safe = _safe_resolve_under_root(child, root_resolved)
                if safe is None:
                    skipped_symlink_escape += 1
                    continue
                if not pcfg.follow_symlinks:
                    skipped_symlink_escape += 1
                    continue
            kept.append(d)
        dirnames[:] = sorted(kept)

        for name in sorted(filenames):
            if len(records) >= pcfg.max_file_count:
                truncated = True
                dirnames.clear()
                break
            if name in pcfg.exclude_file_names:
                skipped_excluded += 1
                continue

            fpath = current / name
            is_symlink = fpath.is_symlink()
            if is_symlink:
                safe = _safe_resolve_under_root(fpath, root_resolved)
                if safe is None:
                    skipped_symlink_escape += 1
                    records.append(
                        ProjectFileRecord(
                            relative_path=str(fpath.relative_to(root_resolved)),
                            absolute_path=str(fpath),
                            status=FileAnalysisStatus.SKIPPED,
                            error="symlink escapes project root",
                            is_symlink=True,
                        )
                    )
                    continue
                target = safe
            else:
                target = fpath

            if not target.is_file():
                continue

            suffix = target.suffix.lower()
            if suffix not in pcfg.supported_suffixes:
                skipped_unsupported += 1
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        status=FileAnalysisStatus.UNSUPPORTED,
                        language=None,
                        kind=detect_kind(target),
                        is_symlink=is_symlink,
                    )
                )
                continue

            try:
                size = target.stat().st_size
            except OSError as exc:
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        status=FileAnalysisStatus.UNREADABLE,
                        error=str(exc),
                        is_symlink=is_symlink,
                    )
                )
                continue

            if size > pcfg.max_file_size_bytes:
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        size_bytes=size,
                        status=FileAnalysisStatus.OVERSIZED,
                        error=f"file size {size} exceeds limit {pcfg.max_file_size_bytes}",
                        is_symlink=is_symlink,
                        language=_LANGUAGE_BY_SUFFIX.get(suffix),
                        kind=detect_kind(target),
                    )
                )
                continue

            if total_size + size > pcfg.max_total_size_bytes:
                truncated = True
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        size_bytes=size,
                        status=FileAnalysisStatus.SKIPPED,
                        error="total project size limit reached",
                        is_symlink=is_symlink,
                    )
                )
                dirnames.clear()
                break

            try:
                data = target.read_bytes()
                size_after = target.stat().st_size
            except OSError as exc:
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        status=FileAnalysisStatus.UNREADABLE,
                        error=str(exc),
                        is_symlink=is_symlink,
                    )
                )
                continue

            if size_after != size or len(data) != size:
                records.append(
                    ProjectFileRecord(
                        relative_path=str(fpath.relative_to(root_resolved)),
                        absolute_path=str(target),
                        size_bytes=size,
                        status=FileAnalysisStatus.ERROR,
                        error="file changed during intake",
                        is_symlink=is_symlink,
                    )
                )
                continue

            digest = content_digest(data)
            total_size += size
            kind = detect_kind(target)
            language = _LANGUAGE_BY_SUFFIX.get(suffix)
            rel = str(fpath.relative_to(root_resolved))

            art = Artifact(
                kind=kind,
                origin=str(target),
                metadata={
                    "filename": target.name,
                    "suffix": suffix,
                    "relative_path": rel,
                    "is_file": True,
                    "is_dir": False,
                    "project_root": str(root_resolved),
                },
                content_digest=digest,
                size_bytes=size,
                notes=notes,
            )
            file_artifacts.append(art)
            records.append(
                ProjectFileRecord(
                    relative_path=rel,
                    absolute_path=str(target),
                    content_digest=digest,
                    size_bytes=size,
                    language=language,
                    kind=kind,
                    status=FileAnalysisStatus.PENDING,
                    is_symlink=is_symlink,
                    artifact_id=art.id,
                )
            )

    root_art = Artifact(
        kind=ArtifactKind.DIRECTORY,
        origin=str(root_resolved),
        metadata={
            "filename": root_resolved.name,
            "is_file": False,
            "is_dir": True,
            "entry_count": len(records),
            "analyzed_file_count": len(file_artifacts),
            "total_size_bytes": total_size,
            "truncated": truncated,
            "skipped_symlink_escape": skipped_symlink_escape,
            "skipped_excluded": skipped_excluded,
            "skipped_unsupported": skipped_unsupported,
            "project_intake": True,
        },
        notes=notes,
    )
    return root_art, records, file_artifacts
