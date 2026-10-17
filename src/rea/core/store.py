"""Local-first investigation store (JSON files).

Uses atomic writes and schema-versioned serialization so later
report / validate / export commands can reload the same investigation.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from rea.core.config import DEFAULT_CONFIG, REAConfig
from rea.core.errors import InvestigationNotFoundError
from rea.core.interfaces import InvestigationStore
from rea.core.models import Investigation


def _deterministic_dump(investigation: Investigation) -> str:
    """Serialize with sorted keys for byte-stable output (timestamps remain)."""
    data = investigation.model_dump(mode="json")
    return json.dumps(data, indent=2, sort_keys=True, default=str) + "\n"


class JsonInvestigationStore(InvestigationStore):
    def __init__(self, config: REAConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.root = self.config.storage.resolved_investigations_dir()

    def _path(self, investigation_id: str) -> Path:
        # Reject path traversal in investigation IDs
        if "/" in investigation_id or "\\" in investigation_id or ".." in investigation_id:
            raise InvestigationNotFoundError(investigation_id)
        return self.root / f"{investigation_id}.json"

    def save(self, investigation: Investigation) -> None:
        path = self._path(investigation.id)
        text = _deterministic_dump(investigation)
        # Atomic write: temp file in same directory then replace
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.root), prefix=f".{investigation.id}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def load(self, investigation_id: str) -> Investigation:
        path = self._path(investigation_id)
        if not path.exists():
            raise InvestigationNotFoundError(investigation_id)
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise InvestigationNotFoundError(investigation_id) from exc
        try:
            return Investigation.model_validate(data)
        except Exception as exc:
            raise InvestigationNotFoundError(investigation_id) from exc

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("inv_*.json"))
