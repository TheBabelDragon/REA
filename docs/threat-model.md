# REA Threat Model and Responsible-Use Boundaries

## Assets

- Host system integrity and confidentiality
- Investigation records (may contain metadata about analyzed artifacts)
- User trust in reported findings

## Trust boundaries

| Boundary | Trust level |
|----------|-------------|
| Artifact content | **Untrusted** — may contain hostile data, path tricks, or embedded instructions |
| Adapter code | Trusted only if shipped with REA or reviewed by the operator |
| Investigation store | Local disk under operator control |
| Network | Untrusted; disabled by default |

## Threats and mitigations (v0.1)

| Threat | Mitigation |
|--------|------------|
| Accidental execution of malware | No automatic execution; only STATIC_ONLY experiments run; SafetyClass.FORBIDDEN cannot execute |
| Path traversal / oversized inputs | Size limits, resolve paths, bounded directory walks |
| Network exfiltration via analysis | `allow_network=False` by default; adapters declare `requires_network` |
| Credential / secret harvesting | Explicitly out of scope; adapters must not collect unrelated private data |
| Misleading confidence | Qualitative ranks only; documented semantics; unknowns called out |
| Supply-chain compromise of adapters | Capability declarations + review; minimal dependency set |
| Investigation tampering | Content digests on artifacts; export includes schema version for integrity checks |

## Explicit non-goals

- Bypassing access controls or DRM
- Stealth, persistence, or unauthorized extraction
- Automatic privilege escalation testing
- Collecting credentials or PII from analyzed systems
- Claiming calibrated probabilistic confidence without validation

## Future dynamic capabilities

Any dynamic or network-enabled experiment MUST:

1. Be opt-in
2. Require explicit authorization on the Experiment record
3. Be bounded (sandbox, timeout, resource limits)
4. Be fully audited in the investigation record
5. Fail closed if authorization or safety class is missing
