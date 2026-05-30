"""Guion narrativo determinista a partir de estructura y use_case."""

from __future__ import annotations

from cadence.music.development_theory import DEFAULT_MOTIF
from cadence.schemas.song_state import (
    CreativeBrief,
    SectionIntent,
    SongNarrative,
    TechnicalProposal,
    UserIntent,
)

_SECTION_DEFAULTS: dict[str, tuple[str, str, float, float, float, str]] = {
    # id → role, emotion, density, harmonic_tension, rhythmic_complexity, transition_out
    "intro": ("establish", "anticipation", 0.35, 0.25, 0.35, "none"),
    "verse": ("establish", "focused", 0.55, 0.45, 0.5, "none"),
    "pre-chorus": ("tension", "rising", 0.65, 0.6, 0.6, "riser"),
    "pre_chorus": ("tension", "rising", 0.65, 0.6, 0.6, "riser"),
    "build-up": ("tension", "rising", 0.75, 0.7, 0.65, "riser"),
    "build_up": ("tension", "rising", 0.75, 0.7, 0.65, "riser"),
    "buildup": ("tension", "rising", 0.75, 0.7, 0.65, "riser"),
    "drop": ("climax", "intense", 1.0, 0.85, 0.8, "cut"),
    "climax": ("climax", "intense", 1.0, 0.9, 0.85, "cut"),
    "main-theme": ("climax", "heroic", 0.9, 0.75, 0.7, "none"),
    "main_theme": ("climax", "heroic", 0.9, 0.75, 0.7, "none"),
    "bridge": ("transition", "uncertain", 0.6, 0.55, 0.55, "filter_sweep"),
    "breakdown": ("reflection", "sparse", 0.3, 0.35, 0.4, "fade"),
    "chorus": ("climax", "triumphant", 0.85, 0.7, 0.75, "none"),
    "outro": ("release", "resolved", 0.25, 0.15, 0.3, "fade"),
    "outro_loop": ("release", "stable", 0.3, 0.2, 0.35, "fade"),
    "pad_layering": ("establish", "calm", 0.4, 0.3, 0.25, "none"),
    "melodic_motif": ("establish", "hopeful", 0.5, 0.4, 0.45, "none"),
    "dialogue_bed": ("establish", "neutral", 0.35, 0.25, 0.2, "none"),
    "tension_swell": ("tension", "uneasy", 0.65, 0.65, 0.5, "riser"),
    "stealth_bed": ("establish", "cautious", 0.3, 0.25, 0.25, "none"),
    "chase": ("tension", "urgent", 0.85, 0.75, 0.8, "none"),
    "menu_theme": ("establish", "welcoming", 0.45, 0.35, 0.4, "none"),
    "shop_bed": ("establish", "friendly", 0.4, 0.3, 0.35, "none"),
    "victory_sting": ("climax", "triumphant", 0.9, 0.7, 0.75, "cut"),
    "defeat_sting": ("release", "somber", 0.35, 0.4, 0.3, "fade"),
    "horror_bed": ("establish", "dread", 0.45, 0.5, 0.35, "none"),
    "exploration_bed": ("establish", "hopeful", 0.45, 0.35, 0.4, "none"),
    "dungeon_bed": ("establish", "ominous", 0.5, 0.45, 0.4, "none"),
}

_USE_CASE_ARC: dict[str, str] = {
    "loop": "loop-stable",
    "cutscene": "dialogue-tension-release",
    "animation": "rise-climax-fall",
    "game": "rise-climax-fall",
}

# Overrides por forma (section_id → role, emotion, density, ht, rc, transition)
_FORM_SECTION_OVERRIDES: dict[str, dict[str, tuple[str, str, float, float, float, str]]] = {
    "boss_edm": {
        "drop": ("climax", "euphoric", 1.0, 0.9, 0.85, "cut"),
        "build-up": ("tension", "urgent", 0.8, 0.75, 0.7, "riser"),
    },
    "boss_orchestral": {
        "main-theme": ("climax", "heroic", 0.95, 0.8, 0.75, "none"),
        "climax": ("climax", "triumphant", 1.0, 0.9, 0.8, "cut"),
        "bridge": ("transition", "uncertain", 0.55, 0.5, 0.5, "filter_sweep"),
    },
    "loop_ambient": {
        "pad_layering": ("establish", "calm", 0.35, 0.25, 0.2, "none"),
        "melodic_motif": ("establish", "hopeful", 0.45, 0.35, 0.3, "none"),
    },
    "cutscene_arc": {
        "dialogue_bed": ("establish", "neutral", 0.3, 0.2, 0.15, "none"),
        "tension_swell": ("tension", "uneasy", 0.7, 0.65, 0.45, "riser"),
    },
    "loop_stealth": {
        "stealth_bed": ("establish", "cautious", 0.25, 0.2, 0.2, "none"),
    },
    "cutscene_chase": {
        "chase": ("tension", "urgent", 0.9, 0.8, 0.85, "none"),
    },
    "chase_sequence": {
        "chase": ("tension", "urgent", 0.88, 0.78, 0.82, "none"),
    },
    "victory_fanfare": {
        "chorus": ("climax", "triumphant", 0.95, 0.75, 0.8, "cut"),
    },
    "defeat_sting": {
        "defeat_sting": ("release", "defeated", 0.4, 0.45, 0.35, "fade"),
    },
    "menu_theme": {
        "menu_theme": ("establish", "welcoming", 0.5, 0.4, 0.45, "none"),
    },
    "horror_ambient": {
        "horror_bed": ("establish", "dread", 0.5, 0.55, 0.35, "none"),
    },
    "edm_double_drop": {
        "drop": ("climax", "euphoric", 1.0, 0.9, 0.85, "cut"),
        "climax": ("climax", "euphoric", 1.0, 0.95, 0.9, "cut"),
    },
}


def _normalize_sid(section_id: str) -> str:
    return section_id.lower().replace(" ", "-")


def _section_spec(
    section_id: str,
    energy: int,
    *,
    form_id: str = "",
    position: int = 0,
    total: int = 1,
) -> tuple[str, str, float, float, float, str]:
    key = _normalize_sid(section_id)
    fid = (form_id or "").strip().lower()
    if fid and fid in _FORM_SECTION_OVERRIDES:
        override = _FORM_SECTION_OVERRIDES[fid].get(key)
        if override:
            role, emotion, density, ht, rc, tout = override
            if energy >= 4 and role == "climax":
                density = min(1.0, density + 0.05)
            return role, emotion, density, ht, rc, tout

    if key in _SECTION_DEFAULTS:
        role, emotion, density, ht, rc, tout = _SECTION_DEFAULTS[key]
        if energy >= 4 and role == "climax":
            density = min(1.0, density + 0.05)
        return role, emotion, density, ht, rc, tout
    if "drop" in key or "climax" in key:
        return _SECTION_DEFAULTS["drop"]
    if "build" in key or "tension" in key:
        return _SECTION_DEFAULTS["build-up"]
    if "outro" in key:
        return _SECTION_DEFAULTS["outro"]
    if "intro" in key:
        return _SECTION_DEFAULTS["intro"]
    spec = ("establish", "neutral", 0.5, 0.45, 0.45, "none")
    if total > 1 and fid in ("boss_edm", "game_standard", "animation_climax", "boss_extended"):
        t = position / max(1, total - 1)
        density = 0.25 + 0.55 * t
        ht = 0.2 + 0.6 * t
        return (spec[0], spec[1], min(1.0, density), min(1.0, ht), spec[4], spec[5])
    return spec


def _global_motif(proposal: TechnicalProposal, seed: int) -> list[int]:
    from cadence.music.technical_proposal_apply import normalize_global_motif

    custom = normalize_global_motif(proposal.global_motif)
    if custom:
        return custom
    mode = proposal.mode
    base = list(DEFAULT_MOTIF)
    if mode == "major":
        return [0, 2, 4, 2]
    offset = seed % 3
    return [(d + offset) % 7 for d in base]


def _arc_from_brief(brief: CreativeBrief | None, use_case: str) -> str:
    if not brief:
        return _USE_CASE_ARC.get(use_case, "rise-climax-fall")
    arc_text = (brief.emotional_arc or "").lower()
    if "loop" in arc_text or "stable" in arc_text:
        return "loop-stable"
    if "dialogue" in arc_text or "cutscene" in arc_text:
        return "dialogue-tension-release"
    return _USE_CASE_ARC.get(brief.use_case, _USE_CASE_ARC.get(use_case, "rise-climax-fall"))


def build_narrative_from_template(
    proposal: TechnicalProposal,
    intent: UserIntent,
    *,
    generation_seed: int = 0,
    creative_brief: CreativeBrief | None = None,
) -> SongNarrative:
    """Guion por sección alineado a proposal.structure y structure_form."""
    form_id = (proposal.structure_form or "").strip().lower()
    section_list = list(proposal.structure)
    total = len(section_list)
    sections: list[SectionIntent] = []
    for idx, sid in enumerate(section_list):
        role, emotion, density, ht, rc, tout = _section_spec(
            sid,
            proposal.energy_level,
            form_id=form_id,
            position=idx,
            total=total,
        )
        sections.append(SectionIntent(
            id=sid,
            narrative_role=role,  # type: ignore[arg-type]
            emotional_target=emotion,
            density=density,
            harmonic_tension=ht,
            rhythmic_complexity=rc,
            transition_out=tout,  # type: ignore[arg-type]
        ))

    uc = (intent.use_case or "game").lower()
    arc = _arc_from_brief(creative_brief, uc)
    if creative_brief and creative_brief.logline.strip():
        logline = creative_brief.logline.strip()
    else:
        mood = intent.mood or "intense"
        logline = (
            f"{intent.use_case} piece — {mood} — "
            f"{proposal.key} {proposal.mode} @ {proposal.bpm} BPM"
        )

    return SongNarrative(
        logline=logline,
        arc_type=arc,
        global_motif=_global_motif(proposal, generation_seed),
        sections=sections,
    )
