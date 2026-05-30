"""
Arquetipo compositivo inferido del perfil de estilo y el prompt.

Desacopla dense_dance, compact_action y orchestral_boss en estrategia, capas y melodía.
"""

from __future__ import annotations

from typing import Literal

from cadence.schemas.song_state import MusicalStyleProfile

CompositionArchetype = Literal[
    "ambient_loop",
    "cinematic_cutscene",
    "chiptune_dance",
    "compact_action",
    "orchestral_boss",
    "default_game",
]

_CHIPTUNE_GENRES = frozenset({
    "chiptune", "eurobeat", "arcade", "8-bit", "8bit", "bit", "nes", "snes",
    "game boy", "gb", "battle", "victory",
})
_ORCHESTRAL_GENRES = frozenset({
    "orchestral", "symphonic", "cinematic", "epic", "hybrid orchestral",
    "film score", "trailer",
})
_COMPACT_MARKERS = (
    "compact", "compacta", "compacto", "pocos instrumentos", "few instruments",
    "minimal layers", "plataforma", "platform", "kraid", "metroid",
)
_COMPACT_GENRES = frozenset({
    "platform", "action", "combat", "boss fight", "adventure",
})


def _genre_keys(profile: MusicalStyleProfile | None) -> set[str]:
    if not profile or not profile.genres:
        return set()
    return {g.lower().strip() for g in profile.genres}


def _prompt_lower(raw_prompt: str) -> str:
    return (raw_prompt or "").lower()


def _has_any(keys: set[str], candidates: frozenset[str]) -> bool:
    return bool(keys & candidates) or any(
        any(c in k for c in candidates) for k in keys
    )


def _prompt_requests_compact(prompt: str) -> bool:
    p = _prompt_lower(prompt)
    return any(m in p for m in _COMPACT_MARKERS)


def infer_composition_archetype(
    *,
    style_profile: MusicalStyleProfile | None = None,
    raw_prompt: str = "",
    use_case: str = "game",
    energy_level: int = 3,
) -> CompositionArchetype:
    """Clasificación estable para ramas de estrategia, textura y melodía."""
    uc = (use_case or "game").lower()
    keys = _genre_keys(style_profile)
    prompt = _prompt_lower(raw_prompt)

    if uc == "loop" or energy_level <= 1:
        return "ambient_loop"

    if uc == "cutscene" or energy_level <= 2:
        if _has_any(keys, _CHIPTUNE_GENRES):
            return "chiptune_dance"
        return "cinematic_cutscene"

    if _has_any(keys, _CHIPTUNE_GENRES) and not _has_any(keys, _ORCHESTRAL_GENRES):
        return "chiptune_dance"

    orchestral = _has_any(keys, _ORCHESTRAL_GENRES)
    compact_prompt = _prompt_requests_compact(raw_prompt)
    compact_genre = bool(keys & _COMPACT_GENRES)

    if compact_prompt and not orchestral:
        return "compact_action"

    if orchestral and ("boss" in prompt or "boss fight" in keys or "epic" in keys):
        if compact_prompt:
            return "compact_action"
        return "orchestral_boss"

    if orchestral and energy_level >= 4 and not _has_any(keys, _CHIPTUNE_GENRES):
        return "orchestral_boss"

    if compact_genre and energy_level >= 4 and not orchestral:
        return "compact_action"

    if "chiptune" in prompt or "eurobeat" in prompt or "arcade" in prompt:
        return "chiptune_dance"

    return "default_game"


def get_composition_archetype(
    state: dict,
    *,
    allow_infer: bool = True,
) -> CompositionArchetype:
    """
    Lee composition_archetype cacheado en SongState (fijado en strategy_planner).
    Si allow_infer, recalcula solo para tests o rutas sin strategy.
    """
    cached = state.get("composition_archetype")
    if cached:
        return cached  # type: ignore[return-value]

    if not allow_infer:
        return "default_game"

    intent = state.get("intent")
    proposal = state.get("technical_proposal")
    return infer_composition_archetype(
        style_profile=state.get("style_profile"),
        raw_prompt=intent.raw_prompt if intent else "",
        use_case=intent.use_case if intent else "game",
        energy_level=proposal.energy_level if proposal else 3,
    )


def melody_texture_for_archetype(
    archetype: CompositionArchetype,
    energy_level: int,
    use_case: str,
    requested: str = "balanced",
) -> str:
    if requested not in ("balanced", ""):
        return requested
    if archetype == "chiptune_dance":
        return "dense"
    if archetype == "compact_action":
        return "balanced"
    if archetype == "ambient_loop":
        return "sparse"
    if archetype == "cinematic_cutscene":
        return "sparse" if energy_level <= 2 else "balanced"
    if archetype == "orchestral_boss":
        return "balanced"
    from cadence.music.repertoire_signals import default_melody_texture

    return default_melody_texture(energy_level, use_case, requested)
