"""System model reconstruction."""

from __future__ import annotations

from datetime import datetime, timezone

from rea.core.models import Component, InterfaceSpec, Investigation, InvestigationStatus, ObservationType, SystemModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def reconstruct(investigation: Investigation) -> Investigation:
    components: list[Component] = []
    interfaces: list[InterfaceSpec] = []
    dependencies: list[dict[str, str]] = []
    unresolved: list[str] = []
    all_ev_ids = [e.id for e in investigation.evidence]
    seen: set[str] = set()

    for o in investigation.observations:
        if o.observation_type != ObservationType.STRUCTURE:
            continue
        lang = o.payload.get("language", "unknown")
        for cls_name in o.payload.get("classes") or []:
            if cls_name not in seen:
                seen.add(cls_name)
                components.append(Component(name=cls_name, kind="class" if lang == "python" else "type",
                                            description=f"From {lang} structure", evidence_ids=all_ev_ids[:3]))
        for fn_name in o.payload.get("functions") or []:
            key = f"fn:{fn_name}"
            if key not in seen:
                seen.add(key)
                components.append(Component(name=fn_name, kind="function",
                                            description=f"From {lang} structure", evidence_ids=all_ev_ids[:3]))

    for art in investigation.artifacts:
        name = art.metadata.get("filename") or art.origin
        components.insert(0, Component(name=str(name), kind="module" if art.kind.value == "source_code" else art.kind.value,
                                        description=f"Primary artifact ({art.kind.value})", evidence_ids=all_ev_ids[:2]))

    for o in investigation.observations:
        if o.observation_type == ObservationType.DEPENDENCY:
            for dep in o.payload.get("dependencies") or []:
                dependencies.append({"from": "artifact", "to": dep, "kind": "import"})

    for c in components:
        if c.kind == "function":
            interfaces.append(InterfaceSpec(name=c.name, direction="out", description=f"Callable: {c.name}", evidence_ids=c.evidence_ids))

    if not any(o.observation_type == ObservationType.BEHAVIOR for o in investigation.observations):
        unresolved.append("No runtime/behavior observations (static-only pipeline)")
    for h in investigation.hypotheses:
        if h.status.value in {"open", "proposed", "inconclusive"}:
            unresolved.append(f"Open hypothesis: {h.claim}")

    investigation.system_model = SystemModel(
        components=components, interfaces=interfaces, dependencies=dependencies,
        unresolved_areas=unresolved, evidence_ids=all_ev_ids,
    )
    investigation.status = InvestigationStatus.RECONSTRUCTED
    investigation.updated_at = _utcnow()
    return investigation
