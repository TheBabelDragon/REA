# REA Architecture

## Overview

REA is a modular, evidence-driven reverse-engineering framework. It turns
observable artifacts into structured, evidence-backed reconstructions without
executing inspected code by default.

**v0.3** extends single-artifact analysis into **project-level** reverse
engineering: bounded multi-file intake, Python AST project analysis, and a
typed evidence graph with provenance on every asserted relationship.

## Pipeline

```
intake → observations → evidence → evidence graph → hypotheses
      → experiments (static) → reconstruction → validation → persist/export
```

### Single-file path

Unchanged from v0.2: `register_artifact` → `SourceCodeAdapter` → evidence →
hypotheses → reconstruction → trusted validation harness.

### Project path (v0.3)

When the target is a directory (or `--project` is set):

1. **Bounded project intake** (`rea.intake.project.intake_project`)
   - Recursive discovery of supported source/config files
   - Configurable file-count, per-file-size, total-size, depth limits
   - Skips VCS metadata, virtualenvs, build outputs, configured exclusions
   - Rejects symlink escapes outside the project root; does not follow
     symlink directories by default
   - Detects files that change during read
   - Records relative path, SHA-256 digest, language, analysis status

2. **Project analysis** (`PythonProjectAdapter`)
   - Standard-library AST only; never imports or executes project code
   - Extracts imports, definitions, statically resolvable calls
   - Dynamic imports / reflection → unresolved uncertainty
   - Missing local imports → unresolved references

3. **Evidence graph** (`build_project_evidence_graph`)
   - Nodes: file, module, symbol, observation, evidence, external, unresolved
   - Directed edges: contains, imports, defines, calls, unresolved_ref, …
   - Certainty: observed | inferred | unresolved
   - Every observed relationship links to supporting evidence where available
   - Integrity checks for missing refs, duplicate ids, invalid edges
   - Deterministic canonical serialization for stable kinds

## Core models

- **Artifact**, **Observation**, **Evidence**, **Hypothesis**, **Experiment**
- **SystemModel** / **Component** / **InterfaceSpec**
- **ValidationReport** / **ValidationFinding**
- **ProjectFileRecord** — per-file intake record
- **EvidenceGraph** / **GraphNode** / **GraphEdge** — typed graph
- **Investigation** — aggregate; `validate_references()` checks integrity

## Adapter contract

### Single-file: `AnalysisAdapter`

`capabilities()`, `can_analyze()`, `analyze()`. Never execute untrusted
artifacts. Include provenance on every Observation.

### Project: `ProjectAnalysisAdapter`

`capabilities()`, `can_analyze_project()`, `analyze_project(root, files, artifacts)`.
Same safety rules. Core does not couple to one language; Python is the first
implementation.

## Evidence vs inference

Directly observed facts become evidence with relation `derived_from`.
Graph edges carry `RelationCertainty`. Hypotheses may be inferred and must
carry explicit assumptions. Missing evidence never silently becomes a
verified fact. Incomplete call-graph recovery is an explicit limitation.

## Validation

1. Reference integrity and presence checks.
2. Trusted pure-function harness — independent of the artifact.
3. `reproducibility.artifact_executed` is always `false` in the default pipeline.

## Storage

`JsonInvestigationStore` under `~/.rea/data/investigations/`.
Atomic write (temp + `os.replace`). Deterministic JSON (`sort_keys`).
Path traversal in investigation IDs is rejected.

## Safety

Fail closed; static by default. No network by default. No automatic execution
of inspected artifacts. See [threat-model.md](threat-model.md).
