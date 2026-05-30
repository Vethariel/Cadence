"""Macro-estructura determinista: compases por forma, brief y densidad narrativa."""

from __future__ import annotations

from cadence.schemas.song_state import (
    NarrativeContract,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.music.structure_catalog import resolve_bars_per_section


def bars_for_section(
    *,
    density: float,
    use_case: str,
    energy_level: int,
    section_id: str,
) -> int:
    """Compases heurísticos cuando no hay forma ni overrides del LLM."""
    sid = section_id.lower()
    uc = (use_case or "game").lower()

    if uc == "loop" and "outro" in sid:
        return 4
    if uc == "cutscene" and "dialogue" in sid:
        return 8

    if density >= 0.85:
        base = 16 if energy_level >= 4 else 12
    elif density >= 0.7:
        base = 12 if energy_level >= 4 else 8
    elif density >= 0.4:
        base = 8
    else:
        base = 4

    if "intro" in sid and density < 0.5:
        return min(base, 6)
    if "outro" in sid:
        return min(base, 8)
    return base


def build_structure_deterministic(
    proposal: TechnicalProposal,
    narrative: SongNarrative,
    intent: UserIntent,
    *,
    narrative_contract: NarrativeContract | None = None,
) -> SongStructure:
    """Construye SongStructure con IDs del contrato y compases resueltos."""
    section_ids = (
        list(narrative_contract.section_ids)
        if narrative_contract
        else list(proposal.structure)
    )
    intent_by_id = {s.id: s for s in narrative.sections}

    density_bars: dict[str, int] = {}
    for sid in section_ids:
        sec = intent_by_id.get(sid)
        density = sec.density if sec else 0.5
        density_bars[sid] = bars_for_section(
            density=density,
            use_case=intent.use_case,
            energy_level=proposal.energy_level,
            section_id=sid,
        )

    bars = resolve_bars_per_section(
        section_ids,
        proposal,
        use_case=intent.use_case,
        default_density_bars=density_bars,
    )

    total_bars = sum(bars.values())
    from cadence.music.meter_theory import beats_per_bar

    bpm = max(proposal.bpm, 1)
    duration_ms = int((total_bars * beats_per_bar(proposal.time_signature) * 60000) / bpm)

    return SongStructure(
        sections=section_ids,
        bars_per_section=bars,
        total_bars=total_bars,
        estimated_duration_ms=duration_ms,
    )
