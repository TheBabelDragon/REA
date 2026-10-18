"""Python project static analysis (stdlib AST only). Never executes project code."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from rea.core.errors import AdapterError
from rea.core.interfaces import AdapterCapability, ProjectAnalysisAdapter
from rea.core.models import (
    Artifact,
    FileAnalysisStatus,
    Observation,
    ObservationType,
    ProjectFileRecord,
)


def _path_to_module(relative_path: str) -> str:
    p = relative_path.replace("\\", "/")
    if p.endswith(".py"):
        p = p[:-3]
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    elif p == "__init__":
        p = ""
    return p.replace("/", ".")


class PythonProjectAdapter(ProjectAnalysisAdapter):
    CAP_ID = "python.project.static.v1"

    def capabilities(self) -> list[AdapterCapability]:
        return [
            AdapterCapability(
                id=self.CAP_ID,
                name="Python Project Static Analysis",
                description="Multi-file Python AST: imports, definitions, resolvable calls.",
                supported_kinds=["source_code", "directory"],
                produces_observation_types=[
                    ObservationType.STRUCTURE.value,
                    ObservationType.DEPENDENCY.value,
                    ObservationType.SYMBOL.value,
                    ObservationType.METADATA.value,
                ],
                requires_execution=False,
                requires_network=False,
                limitations=[
                    "No dynamic execution of inspected code.",
                    "Only statically resolvable calls recorded.",
                    "Does not recover a complete call graph.",
                ],
            )
        ]

    def can_analyze_project(self, files: list[ProjectFileRecord]) -> bool:
        return any(
            f.language == "python" and f.status == FileAnalysisStatus.PENDING for f in files
        )

    def analyze_project(
        self, root: str, files: list[ProjectFileRecord], artifacts: list[Artifact]
    ) -> list[Observation]:
        art_by_id = {a.id: a for a in artifacts}
        module_map: dict[str, ProjectFileRecord] = {}
        for f in files:
            if f.language == "python" and f.status in (
                FileAnalysisStatus.PENDING,
                FileAnalysisStatus.ANALYZED,
            ):
                module_map[_path_to_module(f.relative_path)] = f
        observations: list[Observation] = []
        for f in files:
            if f.language != "python":
                continue
            if f.status not in (FileAnalysisStatus.PENDING, FileAnalysisStatus.ANALYZED):
                continue
            if not f.artifact_id or f.artifact_id not in art_by_id:
                continue
            art = art_by_id[f.artifact_id]
            try:
                observations.extend(self._analyze_module(f, art, module_map))
                f.status = FileAnalysisStatus.ANALYZED
            except AdapterError as exc:
                f.status = FileAnalysisStatus.ERROR
                f.error = str(exc)
                observations.append(
                    Observation(
                        artifact_id=art.id,
                        observation_type=ObservationType.METADATA,
                        payload={"path": f.relative_path, "analysis_error": str(exc)},
                        provenance=self._provenance(),
                    )
                )
        return observations

    def _provenance(self) -> dict[str, Any]:
        return {
            "adapter": self.name(),
            "capability_id": self.CAP_ID,
            "version": "0.3.0",
            "execution": False,
        }

    def _analyze_module(
        self,
        record: ProjectFileRecord,
        artifact: Artifact,
        module_map: dict[str, ProjectFileRecord],
    ) -> list[Observation]:
        path = Path(record.absolute_path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise AdapterError(f"cannot read {path}: {exc}") from exc
        try:
            tree = ast.parse(text, filename=record.relative_path)
        except SyntaxError as exc:
            return [
                Observation(
                    artifact_id=artifact.id,
                    observation_type=ObservationType.METADATA,
                    payload={"path": record.relative_path, "syntax_error": str(exc)},
                    provenance=self._provenance(),
                )
            ]
        module_name = _path_to_module(record.relative_path)
        imports: list[dict[str, Any]] = []
        definitions: list[dict[str, Any]] = []
        dynamic: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(
                        {
                            "module": alias.name,
                            "names": [{"name": alias.name, "asname": alias.asname}],
                            "level": 0,
                            "lineno": getattr(node, "lineno", None),
                            "kind": "import",
                        }
                    )
                    if alias.name.startswith("importlib"):
                        dynamic.append(
                            {"kind": "dynamic_import_module", "name": alias.name,
                             "lineno": getattr(node, "lineno", None), "certainty": "unresolved"}
                        )
            elif isinstance(node, ast.ImportFrom):
                imports.append(
                    {
                        "module": node.module or "",
                        "names": [{"name": a.name, "asname": a.asname} for a in node.names],
                        "level": node.level or 0,
                        "lineno": getattr(node, "lineno", None),
                        "kind": "from",
                    }
                )
                if node.module and node.module.startswith("importlib"):
                    dynamic.append(
                        {"kind": "dynamic_import_module", "name": node.module,
                         "lineno": getattr(node, "lineno", None), "certainty": "unresolved"}
                    )
            elif isinstance(node, ast.Call):
                func = node.func
                name = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name in ("__import__", "getattr", "eval", "exec") or (
                    name and "importlib" in str(name)
                ):
                    dynamic.append(
                        {"kind": "dynamic_call", "name": name or "?",
                         "lineno": getattr(node, "lineno", None), "certainty": "unresolved"}
                    )
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append(
                    {"name": node.name, "kind": "function",
                     "lineno": getattr(node, "lineno", None),
                     "args": [a.arg for a in node.args.args]}
                )
            elif isinstance(node, ast.ClassDef):
                definitions.append(
                    {"name": node.name, "kind": "class",
                     "lineno": getattr(node, "lineno", None),
                     "methods": [n.name for n in node.body
                                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]}
                )
        resolved, unresolved = [], []
        for imp in imports:
            target = imp["module"]
            if target in module_map:
                resolved.append(
                    {**imp, "resolved": True,
                     "resolved_path": module_map[target].relative_path}
                )
            elif any(
                m == target.split(".")[0] or m.startswith(target.split(".")[0] + ".")
                for m in module_map
            ):
                unresolved.append({**imp, "resolved": False})
            else:
                resolved.append({**imp, "resolved": False, "external": True})
        return [
            Observation(
                artifact_id=artifact.id,
                observation_type=ObservationType.STRUCTURE,
                payload={
                    "language": "python",
                    "module": module_name,
                    "relative_path": record.relative_path,
                    "imports": imports,
                    "definitions": definitions,
                    "functions": [d["name"] for d in definitions if d["kind"] == "function"],
                    "classes": [d["name"] for d in definitions if d["kind"] == "class"],
                    "calls_resolved": [],
                    "calls_unresolved": [],
                    "dynamic_uncertainty": dynamic,
                    "top_level_count": len(tree.body),
                },
                provenance=self._provenance(),
            ),
            Observation(
                artifact_id=artifact.id,
                observation_type=ObservationType.DEPENDENCY,
                payload={
                    "module": module_name,
                    "relative_path": record.relative_path,
                    "dependencies": [i["module"] for i in imports],
                    "resolved_imports": resolved,
                    "unresolved_imports": unresolved,
                },
                provenance=self._provenance(),
            ),
            Observation(
                artifact_id=artifact.id,
                observation_type=ObservationType.METADATA,
                payload={
                    "path": record.relative_path,
                    "module": module_name,
                    "digest": record.content_digest,
                    "language": "python",
                },
                provenance=self._provenance(),
            ),
        ]
