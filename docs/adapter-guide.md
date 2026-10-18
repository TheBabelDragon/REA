# Adapter Guide

## Single-file adapters

Implement `AnalysisAdapter`:

```python
from rea.core.interfaces import AnalysisAdapter, AdapterCapability
from rea.core.models import Artifact, Observation

class MyAdapter(AnalysisAdapter):
    def capabilities(self) -> list[AdapterCapability]: ...
    def can_analyze(self, artifact: Artifact) -> bool: ...
    def analyze(self, artifact: Artifact) -> list[Observation]: ...
```

Register via `default_adapters()` in `rea.adapters.registry`.

**Rules**

- Never execute, import, or evaluate inspected artifact code.
- Never require network unless capability declares `requires_network=True`
  and the caller has opted in.
- Attach provenance (`adapter`, `capability_id`, `version`) on every observation.
- Surface failures; do not silently swallow analysis errors.

## Project adapters (v0.3)

Implement `ProjectAnalysisAdapter`:

```python
from rea.core.interfaces import ProjectAnalysisAdapter, AdapterCapability
from rea.core.models import Artifact, Observation, ProjectFileRecord

class MyProjectAdapter(ProjectAnalysisAdapter):
    def capabilities(self) -> list[AdapterCapability]: ...
    def can_analyze_project(self, files: list[ProjectFileRecord]) -> bool: ...
    def analyze_project(
        self, root: str, files: list[ProjectFileRecord], artifacts: list[Artifact]
    ) -> list[Observation]: ...
```

Register via `default_project_adapters()`.

### Python project adapter

`PythonProjectAdapter` uses `ast.parse` only:

- Imports (absolute and relative), definitions, top-level structure
- Calls resolved only when the callee is a local definition or an imported name
- `importlib`, `__import__`, `getattr`, `eval`, `exec` → dynamic uncertainty
- Missing local-package imports → unresolved references
- Does **not** claim complete call-graph recovery

## Built-in adapters

| Adapter | Scope | Languages |
|---------|-------|-----------|
| `SourceCodeAdapter` | Single file / shallow directory sample | Python AST + heuristics |
| `PythonProjectAdapter` | Multi-file project | Python AST |

## Testing adapters

- Provide fixtures under `tests/` that never require executing the sample.
- Assert `provenance["execution"] is False` (or equivalent) for project adapters.
- Cover missing imports, circular imports, dynamic imports, and unsupported files.
