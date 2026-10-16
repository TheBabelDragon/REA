# REA Architecture

## Pipeline

Artifact → Intake → Observations → Evidence Graph → Hypotheses → Experiments → Reconstruction → Validation

## Domain models

All models carry `schema_version` and stable IDs. See src/rea/core/models.py.

## Adapter contract

Implement AnalysisAdapter with capabilities(), can_analyze(), analyze(). Never execute untrusted artifacts.

## Storage

JsonInvestigationStore under ~/.rea/data/investigations/

## Safety

Fail closed; static by default. See threat-model.md.
