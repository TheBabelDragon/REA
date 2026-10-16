# REA Architecture

## Pipeline

```
Artifact
   |
   v
 Intake          register path, detect kind, compute digest, bound size
   |
   v
 Observations    adapters produce typed Observation records with provenance
   |
   v
 Evidence Graph  each observation -> Evidence (DERIVED_FROM); later SUPPORTS / CONTRADICTS
   |
   v
 Hypotheses      competing claims with ConfidenceRank + evidence links + assumptions
   |
   v
 Experiments     STATIC_ONLY by default; expected vs actual; reproducibility metadata
   |
   v
 Reconstruction  SystemModel: components, interfaces, dependencies, unresolved_areas
   |
   v
 Validation      checks for reference integrity, grounding, consistency, mismatches
```

## Domain models

All models carry `schema_version` and stable IDs (`art_`, `obs_`, `ev_`, `hyp_`, `exp_`, `inv_`, …).

- **Artifact** — kind, origin, metadata, content digest, acquisition time
- **Observation** — artifact ref, type, payload, adapter provenance
- **Evidence** — source observation IDs, relation, summary, integrity
- **Hypothesis** — claim, status, confidence rank, supporting/contradicting evidence, assumptions
- **Experiment** — objective, safety class, expected/actual, authorization flag
- **SystemModel** — components, interfaces, dependencies, unresolved areas
- **ValidationReport** — tests, findings (match/mismatch), limitations
- **Investigation** — container; exportable as versioned JSON

## Adapter contract

Adapters implement `AnalysisAdapter`:

1. `capabilities()` — honest declaration
2. `can_analyze(artifact)` — predicate
3. `analyze(artifact)` — returns list of Observation; must not execute the artifact

Built-in: `SourceCodeAdapter` (Python AST + regex heuristics).

## Storage

`JsonInvestigationStore` writes one JSON file per investigation under `~/.rea/data/investigations/` (configurable). Local-first; no mandatory database or cloud service.

## Safety

See threat-model.md. Core principle: fail closed; static by default; no automatic execution of untrusted artifacts.
