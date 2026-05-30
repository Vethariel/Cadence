"""
Arquetipo compositivo inferido del perfil de estilo y el prompt.

Desacopla dense_dance, compact_action y orchestral_boss en estrategia, capas y melodía.
Prioridad: use_case y términos del prompt > tags enriquecidos (ruidosos).
"""

from __future__ import annotations

from dataclasses import dataclass
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

_PROMPT_WEIGHT = 8.0
_USE_CASE_WEIGHT = 6.0
_TAG_WEIGHT = 2.0
_ENERGY_WEIGHT = 1.0

_CHIPTUNE_PROMPT = (
    "chiptune", "eurobeat", "arcade", "8-bit", "8bit", "bit", "nes", "snes",
    "game boy", "victory", "combate arcade",
)
_CHIPTUNE_TAGS = frozenset({
    "chiptune", "eurobeat", "arcade", "8-bit", "8bit", "bit", "nes", "snes",
    "game boy", "gb", "battle", "victory",
})
_ORCHESTRAL_PROMPT = (
    "orchestral", "orquesta", "orquestal", "symphonic", "sinfón", "sinfon",
    "cinematic", "cinemat", "epic", "épico", "epico", "film score", "trailer",
    "hybrid orchestral",
)
_ORCHESTRAL_TAGS = frozenset({
    "orchestral", "symphonic", "cinematic", "epic", "hybrid orchestral",
    "film score", "trailer",
})
_COMPACT_MARKERS = (
    "compact", "compacta", "compacto", "pocos instrumentos", "few instruments",
    "minimal layers", "capas compact", "orquestación compacta",
    "plataforma", "platform", "kraid", "metroid", "sin orquesta",
    "sin capas orquestales", "no orchestral", "without orchestral",
)
_COMPACT_TAGS = frozenset({
    "platform", "platformer", "action", "combat", "adventure",
})
_BOSS_PROMPT = ("boss", "jefe", "boss fight", "pelea de jefe", "final boss")
_LOOP_PROMPT = (
    "loop", "overworld", "exploración", "exploration", "ambiente calmado",
    "poca percusión", "pads y drones", "música de fondo",
)
_CUTSCENE_PROMPT = (
    "cutscene", "diálogo", "dialogo", "narrativa moderada", "pasillo",
    "tensión contenida", "sin edm", "sin fraseo de batalla",
)
_ANTI_ORCHESTRA_PROMPT = (
    "sin orquesta", "sin capas orquestales", "no orchestral", "without orchestral",
    "sin edm ni dubstep ni orquesta", "pocos instrumentos a la vez",
    "orquestación compacta",
)


@dataclass(frozen=True)
class ArchetypeDecision:
    archetype: CompositionArchetype
    reason: str


def _genre_keys(profile: MusicalStyleProfile | None) -> set[str]:
    if not profile or not profile.genres:
        return set()
    return {g.lower().strip() for g in profile.genres}


def _prompt_lower(raw_prompt: str) -> str:
    return (raw_prompt or "").lower()


def _prompt_has(prompt: str, terms: tuple[str, ...]) -> bool:
    return any(t in prompt for t in terms)


def _tags_have(keys: set[str], candidates: frozenset[str]) -> bool:
    return bool(keys & candidates) or any(
        any(c in k for c in candidates) for k in keys
    )


def _score_prompt_archetypes(prompt: str, use_case: str, energy: int) -> dict[str, float]:
    scores: dict[str, float] = {a: 0.0 for a in (
        "ambient_loop", "cinematic_cutscene", "chiptune_dance",
        "compact_action", "orchestral_boss", "default_game",
    )}
    uc = (use_case or "game").lower()

    if _prompt_has(prompt, _LOOP_PROMPT) or uc == "loop":
        scores["ambient_loop"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _CUTSCENE_PROMPT) or uc == "cutscene":
        scores["cinematic_cutscene"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _CHIPTUNE_PROMPT):
        scores["chiptune_dance"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _COMPACT_MARKERS):
        scores["compact_action"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _ORCHESTRAL_PROMPT) or _prompt_has(prompt, _BOSS_PROMPT):
        scores["orchestral_boss"] += _PROMPT_WEIGHT * 0.6
        if _prompt_has(prompt, _BOSS_PROMPT):
            scores["orchestral_boss"] += _PROMPT_WEIGHT * 0.4
    if uc == "game" and energy >= 4:
        scores["default_game"] += _PROMPT_WEIGHT * 0.3

    return scores


def _score_tag_archetypes(keys: set[str], energy: int) -> dict[str, float]:
    scores: dict[str, float] = {a: 0.0 for a in (
        "ambient_loop", "cinematic_cutscene", "chiptune_dance",
        "compact_action", "orchestral_boss", "default_game",
    )}
    if _tags_have(keys, _CHIPTUNE_TAGS):
        scores["chiptune_dance"] += _TAG_WEIGHT
    if _tags_have(keys, _ORCHESTRAL_TAGS):
        scores["orchestral_boss"] += _TAG_WEIGHT
    if keys & _COMPACT_TAGS:
        scores["compact_action"] += _TAG_WEIGHT
    if energy <= 1:
        scores["ambient_loop"] += _TAG_WEIGHT
    if energy <= 2:
        scores["cinematic_cutscene"] += _TAG_WEIGHT * 0.5
    return scores


def _score_use_case(use_case: str, energy: int) -> dict[str, float]:
    scores: dict[str, float] = {a: 0.0 for a in (
        "ambient_loop", "cinematic_cutscene", "chiptune_dance",
        "compact_action", "orchestral_boss", "default_game",
    )}
    uc = (use_case or "game").lower()
    if uc == "loop":
        scores["ambient_loop"] += _USE_CASE_WEIGHT
    elif uc == "cutscene":
        scores["cinematic_cutscene"] += _USE_CASE_WEIGHT
    elif uc == "game":
        scores["default_game"] += _USE_CASE_WEIGHT * 0.4
        if energy >= 4:
            scores["compact_action"] += _USE_CASE_WEIGHT * 0.3
    return scores


def resolve_compact_vs_orchestral_precedence(
    *,
    compact_prompt: bool,
    orchestral_prompt: bool,
    anti_orchestra_prompt: bool,
    boss_prompt: bool,
    platform_prompt: bool,
    epic_layers_prompt: bool,
) -> ArchetypeDecision | None:
    """
    Matriz explícita cuando el prompt mezcla compacto/plataforma y boss/orquesta.

    Precedencia (de mayor a menor):
      1) anti-orquesta explícita → compact_action
      2) plataforma/compact + boss sin épica masiva → compact_action
      3) épica orquestal / muchas capas sin compact → orchestral_boss
      4) ambos sin desempate → compact_action (brief de juego acción)
    """
    if not (compact_prompt or platform_prompt) or not (orchestral_prompt or boss_prompt):
        return None

    if anti_orchestra_prompt:
        return ArchetypeDecision(
            "compact_action",
            "precedence_matrix:anti_orchestra_in_prompt_over_orchestral_tags",
        )

    if (compact_prompt or platform_prompt) and boss_prompt and not epic_layers_prompt:
        return ArchetypeDecision(
            "compact_action",
            "precedence_matrix:platform_or_compact_boss_over_orchestral_boss",
        )

    if epic_layers_prompt and orchestral_prompt and not anti_orchestra_prompt:
        return ArchetypeDecision(
            "orchestral_boss",
            "precedence_matrix:epic_orchestral_layers_over_compact_hint",
        )

    if compact_prompt or platform_prompt:
        return ArchetypeDecision(
            "compact_action",
            "precedence_matrix:compact_default_when_mixed_with_orchestral_terms",
        )

    return None


def infer_composition_archetype_with_reason(
    *,
    style_profile: MusicalStyleProfile | None = None,
    raw_prompt: str = "",
    use_case: str = "game",
    energy_level: int = 3,
) -> ArchetypeDecision:
    """Clasificación con trazabilidad: use_case + prompt > tags."""
    prompt = _prompt_lower(raw_prompt)
    keys = _genre_keys(style_profile)
    uc = (use_case or "game").lower()
    energy = max(1, min(5, energy_level))

    compact_prompt = _prompt_has(prompt, _COMPACT_MARKERS)
    platform_prompt = "plataforma" in prompt or "platform" in prompt
    orchestral_prompt = _prompt_has(prompt, _ORCHESTRAL_PROMPT)
    boss_prompt = _prompt_has(prompt, _BOSS_PROMPT)
    anti_orchestra = _prompt_has(prompt, _ANTI_ORCHESTRA_PROMPT)
    epic_layers = any(
        x in prompt for x in (
            "muchas capas", "capas simultáneas", "capas simultaneas",
            "masivas capas", "orquestal épico", "orquestal epico",
            "boss orquestal", "orchestral epic",
        )
    )

    matrix = resolve_compact_vs_orchestral_precedence(
        compact_prompt=compact_prompt,
        orchestral_prompt=orchestral_prompt,
        boss_prompt=boss_prompt,
        platform_prompt=platform_prompt,
        anti_orchestra_prompt=anti_orchestra,
        epic_layers_prompt=epic_layers,
    )
    if matrix is not None:
        return matrix

    if uc == "loop" or (_prompt_has(prompt, _LOOP_PROMPT) and energy <= 2):
        return ArchetypeDecision(
            "ambient_loop",
            f"use_case={uc!r} energy={energy} prompt_loop_terms",
        )

    if uc == "cutscene" or _prompt_has(prompt, _CUTSCENE_PROMPT):
        if _prompt_has(prompt, _CHIPTUNE_PROMPT) and not _tags_have(keys, _ORCHESTRAL_TAGS):
            return ArchetypeDecision(
                "chiptune_dance",
                "cutscene_with_chiptune_prompt_terms",
            )
        return ArchetypeDecision(
            "cinematic_cutscene",
            f"use_case={uc!r} cutscene_prompt_terms",
        )

    scores: dict[str, float] = {a: 0.0 for a in (
        "ambient_loop", "cinematic_cutscene", "chiptune_dance",
        "compact_action", "orchestral_boss", "default_game",
    )}
    for src in (
        _score_use_case(uc, energy),
        _score_prompt_archetypes(prompt, uc, energy),
        _score_tag_archetypes(keys, energy),
    ):
        for k, v in src.items():
            scores[k] += v

    scores["default_game"] += _ENERGY_WEIGHT * 0.5

    if _prompt_has(prompt, _CHIPTUNE_PROMPT) and not _tags_have(keys, _ORCHESTRAL_TAGS):
        scores["chiptune_dance"] += _PROMPT_WEIGHT
        scores["orchestral_boss"] -= _TAG_WEIGHT * 2

    if anti_orchestra:
        scores["orchestral_boss"] -= _PROMPT_WEIGHT
        scores["compact_action"] += _PROMPT_WEIGHT

    if compact_prompt and not orchestral_prompt:
        scores["compact_action"] += _PROMPT_WEIGHT
        scores["orchestral_boss"] -= _TAG_WEIGHT

    if orchestral_prompt and boss_prompt and epic_layers and not anti_orchestra:
        scores["orchestral_boss"] += _PROMPT_WEIGHT

    best = max(scores, key=lambda k: scores[k])
    if scores[best] <= 0:
        best = "default_game"
        reason = "fallback_default_game_low_scores"
    else:
        runners = sorted(scores.items(), key=lambda x: -x[1])[:3]
        detail = ", ".join(f"{k}={v:.1f}" for k, v in runners)
        reason = f"scored_winner={best} ({detail}) use_case={uc!r} energy={energy}"

    return ArchetypeDecision(best, reason)  # type: ignore[arg-type]


def infer_composition_archetype(
    *,
    style_profile: MusicalStyleProfile | None = None,
    raw_prompt: str = "",
    use_case: str = "game",
    energy_level: int = 3,
) -> CompositionArchetype:
    """Clasificación estable para ramas de estrategia, textura y melodía."""
    return infer_composition_archetype_with_reason(
        style_profile=style_profile,
        raw_prompt=raw_prompt,
        use_case=use_case,
        energy_level=energy_level,
    ).archetype


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


def get_archetype_reason(state: dict) -> str | None:
    """Razón de clasificación cacheada o None."""
    return state.get("archetype_reason")


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
