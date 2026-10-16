# REA — Reverse Engineer Anything

**Modular, evidence-driven reverse-engineering framework.**

REA turns observable artifacts and behavior into structured, evidence-backed, testable reconstructions.

> **v0.1:** Static analysis of source-code and text artifacts. No automatic execution. No network by default.

## Install

```bash
pip install -e ".[dev]"
# or
PYTHONPATH=src python -m rea.cli.main --help
```

## CLI

```bash
rea inspect samples/hello_calc.py
rea analyze samples/hello_calc.py
rea investigate samples/hello_calc.py
rea report inv_<id>
rea validate inv_<id>
rea export inv_<id> --format json -o out.json
```

## Pipeline

```
Artifact → Intake → Observations → Evidence → Hypotheses
         → Experiments → Reconstruction → Validation
```

## Safety

Never executes unknown artifacts automatically. Network disabled by default. Fail closed on safety boundary violations. See docs/threat-model.md.

## License

MIT
