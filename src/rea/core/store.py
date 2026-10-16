"""Local-first investigation store (JSON files)."""

from __future__ import annotations

import json
from pathlib import Path

from rea.core.config import DEFAULT_CONFIG, REAConfig
from rea.core.errors import InvestigationNotFoundError
from rea.core.interfaces import InvestigationStore
from rea.core.models import Investigation


class JsonInvestigationStore(InvestigationStore):
    """Persist investigations as versioned JSON documents on local disk."""

    def __init__(self, config: REAConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.root = self.config.storage.resolved_investigations_dir()

    def _path(self, investigation_id: str) -> Path:
        return self.root / f"{investigation_id}.json"

    def save(self, investigation: Investigation) -> None:
        path = self._path(investigation.id)
        data = investigation.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load(self, investigation_id: str) -> Investigation:
        path = self._path(investigation_id)
        if not path.exists():
            raise InvestigationNotFoundError(investigation_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return Investigation.model_validate(data)

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("inv_*.json"))
