# REA Threat Model (v0.2)

## Trust boundaries

| Input | Trust level | Handling |
|-------|-------------|----------|
| Artifact content | **Untrusted** | Read as data only; never executed by default pipeline |
| User-supplied paths | Untrusted | Resolved, existence-checked, size-limited |
| Investigation IDs | Untrusted | Path separators and `..` rejected |
| Trusted validation harness | Trusted | Independent pure functions maintained by REA |

## Guarantees (implemented)

- No automatic execution of inspected artifacts.
- Network disabled by default (`SafetyConfig.allow_network = False`).
- Configurable max artifact size (default 50 MiB); oversized inputs raise `SafetyBoundaryError`.
- Experiments with `SafetyClass.FORBIDDEN` cannot be marked executed.
- Network experiments require explicit authorization.
- Store refuses path-traversal investigation IDs.
- Validation harness does not import or exec the artifact.

## Non-goals / residual risks

- A user may still manually run an artifact outside REA.
- Future dynamic/sandboxed modes (not implemented) must be opt-in, authorized, bounded, and audited.
- Heuristic structure extraction may miss or mislabel symbols; hypotheses surface assumptions accordingly.
- Deterministic serialization still includes timestamps (documented as volatile).

## Fail closed

Safety boundary violations, missing files, unsupported kinds, and corrupt investigation records produce actionable errors and non-zero exit codes rather than partial silent success.
