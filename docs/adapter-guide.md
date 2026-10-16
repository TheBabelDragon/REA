# Adapter Authoring Guide

## Contract

Implement `rea.core.interfaces.AnalysisAdapter`:

```python
from rea.core.interfaces import AnalysisAdapter, AdapterCapability
from rea.core.models import Artifact, Observation

class MyAdapter(AnalysisAdapter):
    def capabilities(self) -> list[AdapterCapability]:
        return [AdapterCapability(
            id="my.adapter.v1",
            name="My Adapter",
            description="...",
            supported_kinds=["source_code"],
            produces_observation_types=["structure"],
            requires_execution=False,
            requires_network=False,
            limitations=["Does not handle encrypted files"],
        )]

    def can_analyze(self, artifact: Artifact) -> bool:
        return artifact.kind.value in {"source_code"}

    def analyze(self, artifact: Artifact) -> list[Observation]:
        # Static inspection only unless authorized
        ...
```

## Rules

1. **Declare honestly** — list limitations; never claim unsupported kinds.
2. **No automatic execution** — if you need to run code, require `SafetyClass` and explicit authorization (not available in v0.1 default path).
3. **Treat content as data** — do not `eval`, `exec`, or shell-out to artifact paths.
4. **Provenance** — every Observation must include adapter name and capability id.
5. **Fail closed** — raise `AdapterError` or `SafetyBoundaryError` rather than inventing results.
6. **Determinism** — prefer deterministic extraction so experiments are reproducible.

## Registration

Add the adapter to `rea.adapters.registry.default_adapters()` or pass an explicit list to pipeline functions.

## Testing

Provide unit tests that:

- Assert capability declarations
- Run against a fixture artifact
- Confirm no network/execution side effects
- Cover rejection of unsupported kinds
