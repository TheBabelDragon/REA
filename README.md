# REA — Reverse Engineer Anything

**Modular, evidence-driven reverse-engineering framework.**

REA turns observable artifacts and behavior into structured, evidence-backed, testable reconstructions. Every finding is traceable to observations; hypotheses and unknowns are explicit; investigations are exportable and replayable.

> **v0.1 scope:** Static analysis of source-code and text artifacts. No automatic execution of untrusted code. No network access by default. Pluggable adapters for future binary, API, website, protocol, and hardware targets.

## Purpose

- Inventory artifacts and report what analysis is actually supported
- Collect structural observations with full provenance
- Build an evidence graph linking findings to original observations
- Form competing hypotheses with qualitative confidence ranks
- Plan and run only safe (static) experiments
- Reconstruct a system model with unresolved areas called out
- Validate reconstructions and export portable investigation records

## Architecture

```
Artifact → Intake → Observations → Evidence Graph → Hypotheses
         → Experiments → Reconstruction → Validation Report
```

| Module | Responsibility |
|--------|----------------|
| `rea.core` | Domain types, config, errors, interfaces, local store |
| `rea.intake` | Artifact registration, metadata, validation |
| `rea.adapters` | Pluggable analysis adapters + capability declarations |
| `rea.analysis` | Observation collection pipeline |
| `rea.evidence` | Evidence records and graph construction |
| `rea.hypotheses` | Hypothesis formation and confidence |
| `rea.experiments` | Safe experiment planning and execution |
| `rea.reconstruction` | System model and interface specs |
| `rea.validation` | Validation reports and mismatch detection |
| `rea.cli` | Command-line interface |

## Installation

```bash
pip install -e ".[dev]"
# or with PYTHONPATH
PYTHONPATH=src python -m rea.cli.main --help
```

Requires Python 3.11+.

## CLI examples

```bash
rea inspect samples/hello_calc.py
rea analyze samples/hello_calc.py
rea investigate samples/hello_calc.py
rea report inv_<id>
rea validate inv_<id>
rea export inv_<id> --format json -o investigation.json
rea version
```

## Safety and trust boundaries

REA is an **analysis framework**, not an unrestricted execution engine.

- Never executes unknown artifacts automatically
- Treats all input artifacts as untrusted data
- Network access and external side effects disabled by default
- Dynamic experiments (future) will be opt-in, bounded, auditable, and explicitly authorized
- Fail closed when an operation exceeds its safety boundary

See [docs/threat-model.md](docs/threat-model.md).

## Confidence semantics

Confidence ranks are **qualitative**, not calibrated probabilities:

| Rank | Meaning |
|------|---------|
| `high` | Multiple independent observations, no contradictions |
| `medium` | Supporting observations exist; coverage incomplete |
| `low` | Sparse or indirect evidence |
| `unknown` | Insufficient information |

## Limitations (v0.1)

- Source-code and text static analysis only
- No binary decompilation, no dynamic instrumentation
- Directory analysis is shallow
- Experiments are static re-parse / integrity checks only

## License

MIT

## Responsible use

Intended for legitimate security research, software understanding, interoperability, and education. Users must comply with applicable law and license terms of analyzed artifacts.
