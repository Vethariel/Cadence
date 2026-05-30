"""
Anclas narrativas — límites de baja variación intra-request.

Los nodos creativos no pueden desviar densidad, rol dramático ni tensión-release
fuera de estos anclajes.
"""

from __future__ import annotations

from cadence.music.narrative_contract import contract_section_intent_map
from cadence.schemas.song_state import (
    NarrativeAnchors,
    NarrativeContract,
    SectionNarrativeAnchor,
    SectionIntent,
    SongNarrative,
)

KEY_SECTION_ROLES = frozenset({"climax", "tension", "release"})
KEY_SECTION_IDS = frozenset({
    "drop", "climax", "chorus", "build-up", "buildup", "main_theme", "boss",
})

ROLE_TENSION: dict[str, float] = {
    "silence": 0.05,
    "reflection": 0.25,
    "establish": 0.35,
    "transition": 0.45,
    "release": 0.55,
    "tension": 0.75,
    "climax": 0.95,
}


def _is_key_section(section_id: str, intent: SectionIntent) -> bool:
    sid = section_id.lower().replace(" ", "_")
    if sid in KEY_SECTION_IDS or any(k in sid for k in KEY_SECTION_IDS):
        return True
    if intent.narrative_role in KEY_SECTION_ROLES and intent.density >= 0.55:
        return True
    return intent.density >= 0.85


def _melody_coverage_min(intent: SectionIntent, is_key: bool) -> float:
    if intent.narrative_role == "silence":
        return 0.0
    if is_key:
        return 0.75 if intent.density >= 0.7 else 0.65
    if intent.density >= 0.7:
        return 0.60
    if intent.density < 0.35:
        return 0.25
    return 0.45


def build_narrative_anchors(
    narrative: SongNarrative,
    contract: NarrativeContract,
) -> NarrativeAnchors:
    """Congela anclas desde contrato + guion alineado."""
    intent_map = contract_section_intent_map(narrative, contract)
    anchors: list[SectionNarrativeAnchor] = []
    key_ids: list[str] = []
    curve: list[float] = []

    for sid in contract.section_ids:
        intent = intent_map[sid]
        is_key = _is_key_section(sid, intent)
        if is_key:
            key_ids.append(sid)
        tension = ROLE_TENSION.get(intent.narrative_role, 0.5)
        tension = min(1.0, tension * 0.7 + intent.harmonic_tension * 0.3)
        curve.append(round(tension, 3))
        anchors.append(SectionNarrativeAnchor(
            section_id=sid,
            narrative_role=intent.narrative_role,
            density=round(intent.density, 3),
            harmonic_tension=round(intent.harmonic_tension, 3),
            rhythmic_complexity=round(intent.rhythmic_complexity, 3),
            emotional_target=intent.emotional_target,
            is_key_section=is_key,
            melody_coverage_min=_melody_coverage_min(intent, is_key),
        ))

    return NarrativeAnchors(
        arc_type=contract.arc_type,
        global_motif=list(contract.global_motif),
        section_ids=list(contract.section_ids),
        sections=anchors,
        tension_release_curve=curve,
        key_section_ids=key_ids,
    )


def anchor_for_section(
    anchors: NarrativeAnchors | None,
    section_id: str,
) -> SectionNarrativeAnchor | None:
    if not anchors:
        return None
    for a in anchors.sections:
        if a.section_id == section_id:
            return a
    return None


def density_floor(anchors: NarrativeAnchors | None, section_id: str, default: float = 0.25) -> float:
    a = anchor_for_section(anchors, section_id)
    if not a:
        return default
    return max(0.12, a.density - 0.12)


def density_ceiling(anchors: NarrativeAnchors | None, section_id: str, default: float = 1.0) -> float:
    a = anchor_for_section(anchors, section_id)
    if not a:
        return default
    return min(1.0, a.density + 0.15)


def format_anchors_for_llm(anchors: NarrativeAnchors | None) -> str:
    if not anchors:
        return ""
    lines = [
        "=== ANCLAS NARRATIVAS (no alterar semántica por sección) ===",
        f"arc_type: {anchors.arc_type} | motivo: {anchors.global_motif}",
        f"secciones clave: {', '.join(anchors.key_section_ids) or '—'}",
        "Por sección (density / tensión / cobertura mel mín):",
    ]
    for a, t in zip(anchors.sections, anchors.tension_release_curve):
        key = " [KEY]" if a.is_key_section else ""
        lines.append(
            f"  • {a.section_id}{key}: role={a.narrative_role}, "
            f"density={a.density:.2f}, harm_t={a.harmonic_tension:.2f}, "
            f"curve_t={t:.2f}, mel_cover≥{a.melody_coverage_min:.0%}",
        )
    lines.append(
        "Los nodos creativos (timbres, patrones, adornos) deben respetar estas anclas."
    )
    return "\n".join(lines)
