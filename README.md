# REA — Reverse Engineer Anything

**Modular, evidence-driven reverse-engineering framework.**

REA turns observable artifacts into structured, evidence-backed, testable reconstructions.

> **v0.2:** Static analysis of source-code and text artifacts, evidence-linked hypotheses, trusted pure-function behavioral validation, atomic investigation persistence, and deterministic JSON export. **No automatic execution of inspected artifacts. No network by default.**

## Install

```bash
pip install -e ".[dev]"
# or
PYTHONPATH=src python -m rea.cli.main --help
```

Requires Python 3.11+.

## CLI

```bash
rea inspect samples/hello_calc.py
rea analyze samples/hello_calc.py
rea investigate samples/hello_calc.py
rea report inv_<id>
rea validate inv_<id>
rea export inv_<id> --format json -o out.json
```

| Command | Purpose | Typical exit codes |
|---------|---------|--------------------|
| `inspect` | Fingerprint artifact, list capabilities | 0 ok, 2 intake/safety |
| `analyze` | Structural observations only | 0 ok, 3 unsupported |
| `investigate` | Full pipeline → persist investigation | 0 ok, 1/3 errors |
| `report` | Evidence, hypotheses, reconstruction, validation | 0 ok, 4 not found |
| `validate` | Re-run integrity + trusted harness checks | 0 all match, 1 mismatches, 4 not found |
| `export` | Deterministic JSON dump | 0 ok, 4 not found |

## Pipeline

```
Artifact → Intake → Observations → Evidence → Hypotheses
         → Experiments → Reconstruction → Validation → Report
```

### Implemented (v0.2)

- **Intake:** SHA-256 digest, size limits, safe path handling, actionable errors for missing/unreadable/oversized inputs.
- **Observations:** Language, structure (AST for Python), dependencies, content summary, metadata — with provenance.
- **Evidence:** Stable IDs, source observation links, relation types (supports / contradicts / derived_from).
- **Hypotheses:** Explicit claims, supporting/contradicting evidence, assumptions, qualitative confidence ranks (not probabilities).
- **Reconstruction:** Components, interfaces, dependencies, unresolved areas.
- **Validation:** Reference integrity + **trusted pure-function harness** (never executes the artifact). Includes deliberate pass and fail cases.
- **Persistence:** Atomic JSON writes under `~/.rea/data/investigations/`, schema-versioned, loadable by report/validate/export.
- **Export:** Deterministic JSON (`sort_keys=True`).

### Planned (not implemented)

- Dynamic / sandboxed execution (opt-in only)
- Network observation
- Multi-file project graph refinement
- Calibrated confidence scores
- Binary / archive deep analysis

## Worked example (`samples/hello_calc.py`)

```bash
rea investigate samples/hello_calc.py
# → Investigation inv_xxxxxxxxxxxx
rea report inv_xxxxxxxxxxxx
rea validate inv_xxxxxxxxxxxx
rea export inv_xxxxxxxxxxxx --format json -o /tmp/hello_inv.json
```

Expected outcomes:

1. Artifact fingerprinted (kind=source_code, SHA-256, size).
2. Observations: language=python, functions include `add`/`subtract`/…, class `Calculator`, imports `math`.
3. Hypotheses linked to evidence (language high-confidence supported; pure-function semantics open/medium with explicit assumptions).
4. Reconstruction lists module + functions + class; unresolved notes static-only limits.
5. Validation: integrity checks pass; trusted-harness arithmetic cases for observed functions pass; deliberate mismatch fails; unsupported claims stay unverified.
6. Export/readback preserves investigation identity and structure.

## Confidence semantics

| Rank | Meaning |
|------|---------|
| `high` | Directly observed, single unambiguous signal |
| `medium` | Supported by evidence but assumptions remain |
| `low` | Weak or conflicting signals |
| `unknown` | Insufficient evidence |

Confidence is **qualitative**. REA never fabricates probabilities or claims empirical certainty without measurements.

## Safety

- Inspected artifacts are **never** automatically executed.
- Network disabled by default.
- Fail closed on safety boundary violations (size limits, forbidden experiment classes, path traversal in store IDs).
- Behavioral validation runs only a trusted independent harness, not the artifact under analysis.
- Successful static analysis is **not** presented as proof of runtime equivalence.

See [docs/threat-model.md](docs/threat-model.md).

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
mypy src --ignore-missing-imports
```

CI runs on Python 3.11 and 3.12 (lint, type-check, tests).

## License

MIT
