# REA — Reverse Engineer Anything

**Modular, evidence-driven reverse-engineering framework.**

REA turns observable artifacts into structured, evidence-backed, testable reconstructions.

> **v0.2.1:** Static analysis, evidence-linked hypotheses, trusted pure-function validation (built-in or user fixtures), atomic persistence, deterministic JSON export. **No automatic execution of inspected artifacts. No network by default.**

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
rea investigate samples/hello_calc.py --fixtures samples/hello_calc_fixtures.json
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

### Implemented (v0.2.1)

- **Intake:** SHA-256 digest, size limits, safe path handling, actionable errors.
- **Observations / Evidence / Hypotheses:** Provenance-linked, qualitative confidence.
- **Reconstruction:** Components, interfaces, dependencies, unresolved areas.
- **Validation:** Reference integrity + **trusted pure-function harness** (never executes the artifact).
  - Default built-in arithmetic cases (includes a deliberate mismatch to show failure reporting).
  - **User fixtures** via `--fixtures path.json` or `metadata.validation_fixtures` (clean pass path; no deliberate mismatch).
- **Persistence:** Atomic JSON under `~/.rea/data/investigations/`.
- **Export:** Deterministic JSON (`sort_keys=True`).

### Fixture file format

```json
{
  "cases": [
    {"function": "add", "args": [2, 3], "expected": 5.0}
  ]
}
```

Only functions with a trusted harness entry are evaluated. The inspected artifact is never imported or executed.

### Planned (not implemented)

- Dynamic / sandboxed execution of the artifact (opt-in only)
- Network observation
- Multi-file project graph refinement
- Calibrated confidence scores
- Binary / archive deep analysis

## Worked example

```bash
# Default path (includes deliberate mismatch → validate may exit 1)
rea investigate samples/hello_calc.py

# Fixture path (trusted cases only → validate should exit 0)
rea investigate samples/hello_calc.py --fixtures samples/hello_calc_fixtures.json
rea report inv_<id>
rea validate inv_<id>
rea export inv_<id> --format json -o /tmp/hello_inv.json
```

## Confidence semantics

| Rank | Meaning |
|------|---------|
| `high` | Directly observed, single unambiguous signal |
| `medium` | Supported by evidence but assumptions remain |
| `low` | Weak or conflicting signals |
| `unknown` | Insufficient evidence |

Confidence is **qualitative**. REA never fabricates probabilities.

## Safety

- Inspected artifacts are **never** automatically executed.
- Network disabled by default.
- Fail closed on safety boundary violations.
- Behavioral validation uses only a trusted independent harness.
- User fixtures are trusted inputs; they still do not cause artifact execution.

See [docs/threat-model.md](docs/threat-model.md).

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
mypy src --ignore-missing-imports
```

CI runs on Python 3.11 and 3.12.

## License

MIT
