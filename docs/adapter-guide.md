# Adapter Authoring Guide

Implement `rea.core.interfaces.AnalysisAdapter`.

1. Declare capabilities honestly (`requires_execution`, `requires_network`, limitations).
2. Never automatically execute artifact code.
3. Treat content as data.
4. Include provenance on every `Observation` (`adapter`, `capability_id`, version).
5. Fail closed on unreadable or unexpected input.
6. Prefer deterministic extraction so identical inputs yield comparable observations.

Supported kinds in the default `SourceCodeAdapter`: `source_code`, `text`, `directory`.  
Python uses the AST; other languages use heuristics.
