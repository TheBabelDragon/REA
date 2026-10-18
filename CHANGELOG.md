# Changelog

## [0.3.0] — 2026-10-18 (development)

### Added
- Bounded multi-file **project intake** with file-count, size, depth limits and exclusions
- Symlink-escape rejection; changing-file detection; unsupported/oversized status records
- `ProjectAnalysisAdapter` interface and **PythonProjectAdapter** (stdlib AST only)
- Typed **evidence graph** (files, modules, symbols, edges with provenance and certainty)
- Project path integrated into `create_investigation` / `run_full_pipeline` and CLI (`--project`)
- Sample multi-module package: `samples/multi_pkg/`
- Tests for intake safety, graph integrity, unresolved/dynamic imports, determinism, no-execution

### Safety
- Inspected project code is never imported or executed
- No network by default; no dynamic sandbox in this milestone
- Unresolved and dynamic references are explicit, not confirmed edges

### Docs
- Architecture, adapter guide, and threat model updated for project analysis

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
