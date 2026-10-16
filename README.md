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

See docs/architecture.md for full details.

## Installation

```bash
pip install -e ".[dev]"
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
```

## Safety

REA never executes unknown artifacts automatically. Network disabled by default. Fail closed on safety boundary violations. See docs/threat-model.md.

## License

MIT
