"""Umbrales de densidad melódica por arquetipo — composición, post y validador."""

from __future__ import annotations

from cadence.schemas.song_state import SectionIntent

# Perfil benchmark dense_dance ≈ chiptune_dance + default_game denso en alta energía
DENSE_MELODY_ARCHETYPES = frozenset({"chiptune_dance"})


def is_dense_melody_target(
    composition_archetype: str | None,
    *,
    energy_level: int = 3,
    melody_texture: str = "balanced",
    use_case: str = "game",
) -> bool:
    arch = composition_archetype or ""
    if arch in DENSE_MELODY_ARCHETYPES:
        return True
    uc = (use_case or "game").lower()
    if arch == "default_game" and uc == "game" and energy_level >= 4:
        return melody_texture in ("dense", "percussive")
    return False


def melody_notes_per_bar_target(
    composition_archetype: str | None,
    energy_level: int,
    *,
    narrative_role: str | None = None,
    melody_texture: str = "balanced",
    use_case: str = "game",
) -> int:
    """Notas mínimas por compás en secciones densas (post-proceso y hints LLM)."""
    arch = composition_archetype or ""
    role = narrative_role or ""
    if arch == "chiptune_dance":
        if role in ("climax", "tension"):
            return 10 if energy_level >= 5 else 9
        return 9 if energy_level >= 5 else 8
    if is_dense_melody_target(
        arch, energy_level=energy_level, melody_texture=melody_texture, use_case=use_case,
    ):
        if role in ("climax", "tension"):
            return 8 if energy_level >= 5 else 7
        return 7 if energy_level >= 4 else 6
    if arch == "compact_action":
        return 6 if energy_level >= 4 else 5
    if melody_texture in ("dense", "percussive"):
        return 7 if energy_level >= 5 else 6
    return 4


def melody_max_long_gap_ratio(
    composition_archetype: str | None,
    energy_level: int = 3,
    *,
    melody_texture: str = "balanced",
    use_case: str = "game",
) -> float | None:
    """Máx. fracción de huecos largos entre notas; None = no aplicar check."""
    arch = composition_archetype or ""
    if arch == "chiptune_dance":
        return 0.18 if energy_level >= 5 else 0.22
    if is_dense_melody_target(
        arch, energy_level=energy_level, melody_texture=melody_texture, use_case=use_case,
    ):
        return 0.28
    if arch == "compact_action" and energy_level >= 4:
        return 0.32
    return None


def melody_min_notes_per_bar_validator(
    composition_archetype: str | None,
    energy_level: int,
    *,
    melody_texture: str = "balanced",
    use_case: str = "game",
) -> float | None:
    """Media mínima de notas melódicas por compás; None = sin umbral."""
    arch = composition_archetype or ""
    if arch == "chiptune_dance":
        return 5.5 if energy_level >= 5 else 5.0
    if is_dense_melody_target(
        arch, energy_level=energy_level, melody_texture=melody_texture, use_case=use_case,
    ):
        return 4.5 if energy_level >= 5 else 4.0
    return None


def melody_rest_ratio_for_intent(
    intent: SectionIntent | None,
    *,
    use_case: str = "game",
    composition_archetype: str | None = None,
    energy_level: int = 3,
    melody_texture: str = "balanced",
) -> float:
    arch = composition_archetype or ""
    if arch == "chiptune_dance":
        if intent and intent.narrative_role in ("climax", "tension"):
            return 0.02
        if intent and intent.density >= 0.7:
            return 0.04
        return 0.05
    if is_dense_melody_target(
        arch, energy_level=energy_level, melody_texture=melody_texture, use_case=use_case,
    ):
        if intent and intent.narrative_role in ("climax", "tension"):
            return 0.05
        if intent and intent.density >= 0.7:
            return 0.08
        return 0.10
    uc = (use_case or "game").lower()
    if arch == "compact_action":
        if intent and intent.narrative_role in ("climax", "tension"):
            return 0.06
        return 0.10
    if intent is None:
        return 0.15 if uc in ("loop", "cutscene") else 0.1
    if uc in ("loop", "cutscene"):
        if intent.density < 0.35:
            return 0.28
        if intent.density < 0.55:
            return 0.18
        return 0.12
    if intent.density < 0.35:
        return 0.45
    if intent.density < 0.55:
        return 0.25
    if intent.narrative_role in ("climax", "tension"):
        return 0.05
    return 0.15
