"""Static source-code and text analysis adapter. NEVER executes artifact code."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from rea.core.errors import AdapterError, SafetyBoundaryError
from rea.core.interfaces import AdapterCapability, AnalysisAdapter
from rea.core.models import Artifact, ArtifactKind, Observation, ObservationType


class SourceCodeAdapter(AnalysisAdapter):
    CAP_ID = "source_code.static.v1"

    def capabilities(self) -> list[AdapterCapability]:
        return [AdapterCapability(
            id=self.CAP_ID,
            name="Source Code Static Analysis",
            description="Inventory, language detection, structural extraction, content summary.",
            supported_kinds=[
                ArtifactKind.SOURCE_CODE.value,
                ArtifactKind.TEXT.value,
                ArtifactKind.DIRECTORY.value,
            ],
            produces_observation_types=[
                ObservationType.FILE_INVENTORY.value,
                ObservationType.LANGUAGE_DETECTION.value,
                ObservationType.STRUCTURE.value,
                ObservationType.DEPENDENCY.value,
                ObservationType.CONTENT_SUMMARY.value,
                ObservationType.METADATA.value,
            ],
            requires_execution=False,
            requires_network=False,
            limitations=[
                "No dynamic execution.",
                "Python AST for .py; heuristics for other languages.",
                "Binary/archive/network unsupported.",
            ],
        )]

    def can_analyze(self, artifact: Artifact) -> bool:
        return artifact.kind in {
            ArtifactKind.SOURCE_CODE,
            ArtifactKind.TEXT,
            ArtifactKind.DIRECTORY,
        }

    def analyze(self, artifact: Artifact) -> list[Observation]:
        if not self.can_analyze(artifact):
            raise AdapterError(f"cannot analyze kind={artifact.kind.value}")
        if artifact.kind == ArtifactKind.DIRECTORY:
            return self._analyze_directory(artifact)
        return self._analyze_file(artifact)

    def _provenance(self) -> dict:
        return {"adapter": self.name(), "capability_id": self.CAP_ID, "version": "0.1.0"}

    def _analyze_file(self, artifact: Artifact) -> list[Observation]:
        path = Path(artifact.origin)
        if not path.is_file():
            raise AdapterError(f"expected file: {path}")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise AdapterError(f"cannot read {path}: {exc}") from exc
        observations: list[Observation] = []
        lang = self._detect_language(path, text)
        observations.append(Observation(
            artifact_id=artifact.id,
            observation_type=ObservationType.LANGUAGE_DETECTION,
            payload={"language": lang, "filename": path.name},
            provenance=self._provenance(),
        ))
        lines = text.splitlines()
        observations.append(Observation(
            artifact_id=artifact.id,
            observation_type=ObservationType.CONTENT_SUMMARY,
            payload={
                "line_count": len(lines),
                "char_count": len(text),
                "non_empty_lines": sum(1 for ln in lines if ln.strip()),
                "preview": "\n".join(lines[:30]),
            },
            provenance=self._provenance(),
        ))
        if lang == "python" and path.suffix.lower() in {".py", ".pyi"}:
            struct, deps = self._python_structure(text)
        else:
            struct, deps = self._heuristic_structure(text, lang)
        if struct:
            observations.append(Observation(
                artifact_id=artifact.id,
                observation_type=ObservationType.STRUCTURE,
                payload=struct,
                provenance=self._provenance(),
            ))
        if deps:
            observations.append(Observation(
                artifact_id=artifact.id,
                observation_type=ObservationType.DEPENDENCY,
                payload={"dependencies": deps},
                provenance=self._provenance(),
            ))
        observations.append(Observation(
            artifact_id=artifact.id,
            observation_type=ObservationType.METADATA,
            payload={
                "path": str(path),
                "size_bytes": artifact.size_bytes,
                "digest": artifact.content_digest,
            },
            provenance=self._provenance(),
        ))
        return observations

    def _analyze_directory(self, artifact: Artifact) -> list[Observation]:
        path = Path(artifact.origin)
        entries = artifact.metadata.get("entries_sample", [])
        observations = [Observation(
            artifact_id=artifact.id,
            observation_type=ObservationType.FILE_INVENTORY,
            payload={
                "root": str(path),
                "entry_count": artifact.metadata.get("entry_count", 0),
                "entries_sample": entries,
                "truncated": artifact.metadata.get("truncated", False),
            },
            provenance=self._provenance(),
        )]
        analyzed = 0
        for rel in entries:
            if analyzed >= 20:
                break
            child = path / rel
            if not child.is_file() or child.suffix.lower() not in {
                ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".h", ".cpp",
                ".md", ".txt", ".json", ".toml", ".yaml", ".yml",
            }:
                continue
            try:
                kind = (
                    ArtifactKind.SOURCE_CODE
                    if child.suffix.lower()
                    in {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".h", ".cpp"}
                    else ArtifactKind.TEXT
                )
                child_art = Artifact(
                    kind=kind,
                    origin=str(child),
                    metadata={"filename": child.name},
                    size_bytes=child.stat().st_size,
                )
                child_art.id = artifact.id
                for o in self._analyze_file(child_art):
                    o.payload["relative_path"] = rel
                    observations.append(o)
                analyzed += 1
            except (OSError, AdapterError, SafetyBoundaryError):
                continue
        return observations

    def _detect_language(self, path: Path, text: str) -> str:
        mapping = {
            ".py": "python",
            ".pyi": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".md": "markdown",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".sh": "shell",
            ".bash": "shell",
        }
        if path.suffix.lower() in mapping:
            return mapping[path.suffix.lower()]
        first = text.splitlines()[0] if text else ""
        if first.startswith("#!"):
            if "python" in first:
                return "python"
            if "node" in first:
                return "javascript"
            if "bash" in first or "sh" in first:
                return "shell"
        return "unknown"

    def _python_structure(self, text: str) -> tuple[dict, list[str]]:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return self._heuristic_structure(text, "python")
        imports: list[str] = []
        functions: list[str] = []
        classes: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}" if mod else alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return (
            {
                "language": "python",
                "imports": sorted(set(imports)),
                "functions": functions,
                "classes": classes,
                "top_level_count": len(tree.body),
            },
            sorted(set(imports)),
        )

    def _heuristic_structure(self, text: str, lang: str) -> tuple[dict, list[str]]:
        imports: list[str] = []
        functions: list[str] = []
        classes: list[str] = []
        for m in re.finditer(
            r"^\s*(?:import|from|require|include|use)\s+['\"]?([\w./-]+)",
            text,
            re.MULTILINE,
        ):
            imports.append(m.group(1))
        for m in re.finditer(
            r"^\s*(?:def|function|fn|func)\s+(\w+)",
            text,
            re.MULTILINE,
        ):
            functions.append(m.group(1))
        for m in re.finditer(
            r"^\s*(?:class|struct|interface|type)\s+(\w+)",
            text,
            re.MULTILINE,
        ):
            classes.append(m.group(1))
        return (
            {
                "language": lang,
                "imports": sorted(set(imports))[:50],
                "functions": functions[:50],
                "classes": classes[:50],
                "heuristic": True,
            },
            sorted(set(imports))[:50],
        )
