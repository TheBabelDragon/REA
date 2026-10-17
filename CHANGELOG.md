# Changelog

## [0.2.1] — 2026-10-17

### Added
- User-supplied trusted pure-function fixtures via `rea investigate --fixtures PATH`
- Sample fixtures: `samples/hello_calc_fixtures.json`
- Fixture lifecycle tests (`tests/test_fixtures.py`)

### Fixed
- Ruff E701 in shebang language detection (CI lint green)
- Ruff config focuses CI on E/F/W correctness checks

### Safety
- Fixtures are evaluated only by the trusted harness; the inspected artifact is never executed
- With user fixtures, deliberate mismatch case is omitted so `validate` can exit 0

## [0.2.0] — 2026-10-17

### Added
- End-to-end evidence pipeline: intake → observations → evidence → hypotheses → reconstruction → validation
- Atomic investigation store with path-traversal rejection and deterministic JSON
- Evidence-linked hypotheses with pure-function inferences and explicit assumptions
- Trusted pure-function behavioral validation harness (built-in cases)
- Full lifecycle and CLI tests; GitHub Actions CI on Python 3.11 and 3.12
- Architecture, threat-model, and README documentation for v0.2

### Safety
- No automatic execution of inspected artifacts
- Static-only default experiments
- Qualitative confidence ranks only
