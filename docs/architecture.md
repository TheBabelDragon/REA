# REA Architecture (v0.2)

## Pipeline

```
Artifact → Intake → Observations → Evidence Graph → Hypotheses
         → Experiments → Reconstruction → Validation → Report / Export
```

## Domain models

All models carry `schema_version` and stable IDs (`art_`, `obs_`, `ev_`, `hyp_`, `inv_`, …).  
See `src/rea/core/models.py`.

- **Artifact** — origin, kind, SHA-256 digest, size, metadata  
- **Observation** — typed payload + provenance (adapter, capability)  
- **Evidence** — links to observation IDs; relation (supports / contradicts / derived_from)  
- **Hypothesis** — claim, status, qualitative confidence, supporting/contradicting evidence, unresolved assumptions  
- **Experiment** — static-only by default; safety class enforced  
- **SystemModel** — components, interfaces, dependencies, unresolved areas  
- **ValidationReport** — findings (expected/actual/matched), limitations, reproducibility metadata  
- **Investigation** — full aggregate; `validate_references()` checks integrity  

## Adapter contract

Implement `AnalysisAdapter` with `capabilities()`, `can_analyze()`, `analyze()`.  
Never execute untrusted artifacts. Include provenance on every Observation.

## Evidence vs inference

Directly observed facts (language detection, AST symbols) become evidence with relation `derived_from`.  
Hypotheses may be *inferred* (e.g. pure-function semantics from names) and must carry explicit assumptions and non-`SUPPORTED` status when runtime proof is absent.  
Missing evidence never silently becomes a verified fact.

## Validation

1. Reference integrity and presence checks.  
2. Trusted pure-function harness for observed arithmetic-style symbols — **independent of the artifact**.  
3. Deliberate mismatch and unsupported-claim cases demonstrate failure reporting.  

`reproducibility.artifact_executed` is always `false` in the default pipeline.

## Storage

`JsonInvestigationStore` under `~/.rea/data/investigations/`.  
Atomic write (temp + `os.replace`). Deterministic JSON (`sort_keys`).  
Path traversal in investigation IDs is rejected.

## Safety

Fail closed; static by default. See [threat-model.md](threat-model.md).
