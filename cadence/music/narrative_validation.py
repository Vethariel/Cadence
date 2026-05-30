"""Checks de coherencia narrativa mínima (direccional, no uniformidad rígida)."""

from __future__ import annotations

from cadence.music.scale_theory import KEY_MIDI_ROOT, scale_semitones
from cadence.schemas.song_state import (
    NarrativeAnchors,
    NarrativeContract,
    RhythmEvent,
    SectionIntent,
    SongStructure,
    Track,
)


def _key_section_ids(
    contract: NarrativeContract | None,
    anchors: NarrativeAnchors | None,
    intent_map: dict[str, SectionIntent],
) -> list[str]:
    if anchors and anchors.key_section_ids:
        return list(anchors.key_section_ids)
    if contract:
        return [
            sid for sid in contract.section_ids
            if sid in intent_map and (
                intent_map[sid].narrative_role in ("climax", "tension", "drop")
                or intent_map[sid].density >= 0.65
            )
        ]
    return []


def _events_in_section(tracks: list[Track], section_id: str) -> list[RhythmEvent]:
    out: list[RhythmEvent] = []
    for track in tracks:
        for e in track.events:
            if e.section == section_id and e.type in ("note", "drum_hit", "chord"):
                out.append(e)
    return out


def check_narrative_key_section_coverage(
    tracks: list[Track],
    structure: SongStructure,
    contract: NarrativeContract | None,
    anchors: NarrativeAnchors | None,
    intent_map: dict[str, SectionIntent],
) -> tuple[bool, str]:
    """Secciones narrativas clave deben tener actividad audible (no vacías)."""
    if not contract or not intent_map:
        return True, ""

    key_ids = _key_section_ids(contract, anchors, intent_map)
    if not key_ids:
        return True, ""

    silent = []
    for sid in key_ids:
        evs = _events_in_section(tracks, sid)
        if len(evs) < 3:
            silent.append(sid)

    if silent:
        return False, (
            f"Secciones clave sin actividad suficiente: {silent} "
            f"(contrato: {contract.section_ids})"
        )
    return True, ""


def check_narrative_intensity_direction(
    tracks: list[Track],
    sections: list[str],
    intent_map: dict[str, SectionIntent],
    contract: NarrativeContract | None,
) -> tuple[bool, str]:
    """
    La sección de mayor density narrativa debe sonar más intensa que la de menor
    (comparación direccional, no umbrales absolutos).
    """
    if not contract or not intent_map or len(sections) < 2:
        return True, ""

    target_density = {
        s: intent_map[s].density
        for s in sections
        if s in intent_map
    }
    if len(target_density) < 2:
        return True, ""

    buckets: dict[str, list[int]] = {s: [] for s in sections}
    for track in tracks:
        for e in track.events:
            if e.type in ("note", "drum_hit") and e.section in buckets:
                buckets[e.section].append(e.velocity)

    actual = {s: sum(v) / len(v) for s, v in buckets.items() if v}
    if len(actual) < 2:
        return True, ""

    peak_narrative = max(target_density, key=target_density.get)
    quiet_narrative = min(target_density, key=target_density.get)
    if target_density[peak_narrative] - target_density[quiet_narrative] < 0.2:
        return True, ""

    peak_vel = actual.get(peak_narrative, 0)
    quiet_vel = actual.get(quiet_narrative, 0)
    margin = 5.0
    if peak_vel < quiet_vel + margin:
        return False, (
            f"Intensidad invertida: '{peak_narrative}' (density={target_density[peak_narrative]:.2f}, "
            f"vel μ={peak_vel:.1f}) no supera a '{quiet_narrative}' "
            f"(density={target_density[quiet_narrative]:.2f}, vel μ={quiet_vel:.1f})."
        )
    return True, ""


def _pitch_matches_motif_degree(
    pitch: int,
    key: str,
    mode: str,
    motif_degrees: list[int],
) -> bool:
    root = KEY_MIDI_ROOT.get(key, 60)
    scale = scale_semitones(mode)
    rel = (pitch - root) % 12
    motif_pcs = {scale[d % 7] for d in motif_degrees}
    return rel in motif_pcs


def check_global_motif_continuity(
    tracks: list[Track],
    contract: NarrativeContract | None,
    anchors: NarrativeAnchors | None,
    intent_map: dict[str, SectionIntent],
    *,
    key: str = "C",
    mode: str = "minor",
) -> tuple[bool, str]:
    """
    En secciones clave, parte de la melodía debe reflejar el motivo global del contrato.
    """
    motif = list(contract.global_motif) if contract and contract.global_motif else []
    if len(motif) < 2:
        return True, ""

    key_ids = _key_section_ids(contract, anchors, intent_map)
    if not key_ids:
        key_ids = contract.section_ids[:2] if contract else []

    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody:
        return True, ""

    notes = [
        e for e in melody.events
        if e.type == "note" and e.section in key_ids
    ]
    if len(notes) < 4:
        return True, ""

    hits = sum(
        1 for e in notes
        if _pitch_matches_motif_degree(e.pitch, key, mode, motif)
    )
    ratio = hits / len(notes)
    if ratio < 0.18:
        return False, (
            f"Motivo global [{', '.join(str(d) for d in motif)}] poco presente en secciones "
            f"clave ({ratio:.0%} de notas; se espera coherencia direccional ≥18%)."
        )
    return True, ""
