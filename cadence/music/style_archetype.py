"""
Arquetipo compositivo inferido del perfil de estilo y el prompt.

Doce plantillas de composición (ver composition_archetypes). Prioridad:
use_case y términos del prompt > tags enriquecidos (ruidosos).
"""

from __future__ import annotations

from dataclasses import dataclass

from cadence.music.composition_archetypes import (
    ALL_ACCEPTED_ARCHETYPES,
    COMPOSITION_ARCHETYPES,
    all_archetype_scores,
    normalize_archetype,
)
from cadence.schemas.song_state import MusicalStyleProfile

CompositionArchetype = str  # uno de COMPOSITION_ARCHETYPES

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
    "orquestación compacta", "sin capas orquestales masivas",
)
_ANTI_CHIPTUNE_PROMPT = (
    "sin chiptune", "sin eurobeat", "no chiptune", "without chiptune",
)
_LOFI_PROMPT = (
    "lofi", "lo-fi", "lo fi", "chillhop", "study beats", "downtempo suave",
    "hip hop instrumental", "beats relajados",
)
_LOFI_TAGS = frozenset({
    "lofi", "lo-fi", "chillhop", "downtempo", "study", "relaxing", "jazz hop",
})
_INDUSTRIAL_PROMPT = (
    "industrial", "cyberpunk", "dnb", "drum and bass", "drum'n'bass",
    "hard techno", "aggrotech", "bullet hell", "danmaku",
)
_INDUSTRIAL_TAGS = frozenset({
    "industrial", "cyberpunk", "dnb", "drum and bass", "techno", "hardcore",
    "aggrotech",
})
_MENU_PROMPT = (
    "main menu", "menú principal", "title screen", "pantalla de título",
    "character select", "selección de personaje", "hub music",
)
_STEALTH_PROMPT = (
    "stealth", "infiltración", "infiltration", "sigilo", "sneak",
    "tensión cautelosa", "suspenso bajo",
)
_HYBRID_EPIC_PROMPT = (
    "épica híbrida", "epica hibrida", "hybrid epic", "trailer game",
    "orquesta con sintetizadores", "cinematic game", "confrontación épica",
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
    scores = all_archetype_scores()
    uc = (use_case or "game").lower()

    if _prompt_has(prompt, _LOOP_PROMPT) or uc == "loop":
        scores["sparse_loop"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _LOFI_PROMPT):
        scores["lofi_downtempo"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _CUTSCENE_PROMPT) or uc == "cutscene":
        scores["moderate_cinematic"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _CHIPTUNE_PROMPT):
        scores["dense_dance"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _INDUSTRIAL_PROMPT):
        scores["industrial_combat"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _COMPACT_MARKERS):
        scores["compact_action"] += _PROMPT_WEIGHT * 0.7
        scores["energetic_game"] += _PROMPT_WEIGHT * 0.5
    if _prompt_has(prompt, _BOSS_PROMPT):
        scores["energetic_game"] += _PROMPT_WEIGHT * 0.5
        scores["orchestral_boss"] += _PROMPT_WEIGHT * 0.4
    if _prompt_has(prompt, _ORCHESTRAL_PROMPT):
        scores["orchestral_boss"] += _PROMPT_WEIGHT * 0.5
        scores["hybrid_epic"] += _PROMPT_WEIGHT * 0.35
    if _prompt_has(prompt, _MENU_PROMPT):
        scores["menu_theme"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _STEALTH_PROMPT):
        scores["stealth_tension"] += _PROMPT_WEIGHT
    if _prompt_has(prompt, _HYBRID_EPIC_PROMPT):
        scores["hybrid_epic"] += _PROMPT_WEIGHT
    if uc == "game" and energy >= 4:
        scores["default_game"] += _PROMPT_WEIGHT * 0.25
        scores["energetic_game"] += _PROMPT_WEIGHT * 0.2

    return scores


def _score_tag_archetypes(keys: set[str], energy: int) -> dict[str, float]:
    scores = all_archetype_scores()
    if _tags_have(keys, _CHIPTUNE_TAGS):
        scores["dense_dance"] += _TAG_WEIGHT
    if _tags_have(keys, _LOFI_TAGS):
        scores["lofi_downtempo"] += _TAG_WEIGHT
    if _tags_have(keys, _INDUSTRIAL_TAGS):
        scores["industrial_combat"] += _TAG_WEIGHT
    if _tags_have(keys, _ORCHESTRAL_TAGS):
        scores["orchestral_boss"] += _TAG_WEIGHT
        scores["hybrid_epic"] += _TAG_WEIGHT * 0.5
    if keys & _COMPACT_TAGS:
        scores["compact_action"] += _TAG_WEIGHT
        scores["energetic_game"] += _TAG_WEIGHT * 0.5
    if energy <= 1:
        scores["sparse_loop"] += _TAG_WEIGHT
        scores["lofi_downtempo"] += _TAG_WEIGHT * 0.5
    if energy <= 2:
        scores["moderate_cinematic"] += _TAG_WEIGHT * 0.5
        scores["stealth_tension"] += _TAG_WEIGHT * 0.4
    return scores


def _score_use_case(use_case: str, energy: int) -> dict[str, float]:
    scores = all_archetype_scores()
    uc = (use_case or "game").lower()
    if uc == "loop":
        scores["sparse_loop"] += _USE_CASE_WEIGHT
        if energy <= 2:
            scores["lofi_downtempo"] += _USE_CASE_WEIGHT * 0.4
    elif uc == "cutscene":
        scores["moderate_cinematic"] += _USE_CASE_WEIGHT
    elif uc == "game":
        scores["default_game"] += _USE_CASE_WEIGHT * 0.35
        if energy >= 4:
            scores["energetic_game"] += _USE_CASE_WEIGHT * 0.35
            scores["compact_action"] += _USE_CASE_WEIGHT * 0.2
    return scores


def resolve_compact_vs_orchestral_precedence(
    *,
    compact_prompt: bool,
    orchestral_prompt: bool,
    anti_orchestra_prompt: bool,
    boss_prompt: bool,
    platform_prompt: bool,
    epic_layers_prompt: bool,
    anti_chiptune_prompt: bool,
) -> ArchetypeDecision | None:
    """
    Matriz explícita cuando el prompt mezcla compacto/plataforma y boss/orquesta.

    Precedencia (de mayor a menor):
      1) plataforma + boss + compacto sin épica masiva → energetic_game
      2) anti-orquesta explícita + boss → energetic_game o compact_action
      3) épica orquestal / muchas capas sin compact → orchestral_boss
      4) compact sin boss → compact_action
    """
    if not (compact_prompt or platform_prompt) and not (orchestral_prompt or boss_prompt):
        return None

    if (
        (compact_prompt or platform_prompt)
        and boss_prompt
        and not epic_layers_prompt
        and (anti_orchestra_prompt or anti_chiptune_prompt or not orchestral_prompt)
    ):
        return ArchetypeDecision(
            "energetic_game",
            "precedence_matrix:platform_compact_boss_over_orchestral_boss",
        )

    if anti_orchestra_prompt and (compact_prompt or platform_prompt):
        if boss_prompt:
            return ArchetypeDecision(
                "energetic_game",
                "precedence_matrix:anti_orchestra_platform_boss",
            )
        return ArchetypeDecision(
            "compact_action",
            "precedence_matrix:anti_orchestra_in_prompt_over_orchestral_tags",
        )

    if epic_layers_prompt and orchestral_prompt and not anti_orchestra_prompt:
        return ArchetypeDecision(
            "orchestral_boss",
            "precedence_matrix:epic_orchestral_layers_over_compact_hint",
        )

    if compact_prompt or platform_prompt:
        if boss_prompt and not epic_layers_prompt:
            return ArchetypeDecision(
                "energetic_game",
                "precedence_matrix:compact_boss_default",
            )
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
    anti_chiptune = _prompt_has(prompt, _ANTI_CHIPTUNE_PROMPT)
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
        anti_chiptune_prompt=anti_chiptune,
    )
    if matrix is not None:
        return matrix

    if _prompt_has(prompt, _LOFI_PROMPT) or _tags_have(keys, _LOFI_TAGS):
        if energy <= 3 or uc == "loop":
            return ArchetypeDecision(
                "lofi_downtempo",
                f"lofi_prompt_or_tags energy={energy} use_case={uc!r}",
            )

    if _prompt_has(prompt, _MENU_PROMPT) and energy <= 3:
        return ArchetypeDecision("menu_theme", "menu_or_title_screen_prompt")

    if _prompt_has(prompt, _STEALTH_PROMPT) and energy <= 3:
        return ArchetypeDecision("stealth_tension", "stealth_infiltration_prompt")

    if uc == "loop" or (_prompt_has(prompt, _LOOP_PROMPT) and energy <= 2):
        return ArchetypeDecision(
            "sparse_loop",
            f"use_case={uc!r} energy={energy} prompt_loop_terms",
        )

    if (
        uc == "game"
        and energy >= 4
        and _tags_have(keys, _ORCHESTRAL_TAGS)
        and (
            _prompt_has(prompt, _BOSS_PROMPT)
            or _tags_have(keys, frozenset({"boss fight", "combat", "boss"}))
        )
        and epic_layers
        and not anti_orchestra
    ):
        return ArchetypeDecision(
            "orchestral_boss",
            f"use_case=game boss_orchestral_tags energy={energy}",
        )

    if (
        energy >= 4
        and _tags_have(keys, _ORCHESTRAL_TAGS)
        and _prompt_has(prompt, _HYBRID_EPIC_PROMPT)
        and not anti_orchestra
    ):
        return ArchetypeDecision("hybrid_epic", "hybrid_epic_orchestral_game_prompt")

    if uc == "cutscene" or _prompt_has(prompt, _CUTSCENE_PROMPT):
        if _prompt_has(prompt, _CHIPTUNE_PROMPT) and not _tags_have(keys, _ORCHESTRAL_TAGS):
            return ArchetypeDecision(
                "dense_dance",
                "cutscene_with_chiptune_prompt_terms",
            )
        if (
            energy >= 4
            and _tags_have(keys, _ORCHESTRAL_TAGS)
            and _prompt_has(prompt, _BOSS_PROMPT)
            and epic_layers
        ):
            return ArchetypeDecision(
                "orchestral_boss",
                "cutscene_terms_but_boss_orchestral_tags",
            )
        return ArchetypeDecision(
            "moderate_cinematic",
            f"use_case={uc!r} cutscene_prompt_terms",
        )

    if (
        energy >= 4
        and (_prompt_has(prompt, _INDUSTRIAL_PROMPT) or _tags_have(keys, _INDUSTRIAL_TAGS))
    ):
        return ArchetypeDecision(
            "industrial_combat",
            f"industrial_tags_or_prompt energy={energy}",
        )

    scores = all_archetype_scores()
    for src in (
        _score_use_case(uc, energy),
        _score_prompt_archetypes(prompt, uc, energy),
        _score_tag_archetypes(keys, energy),
    ):
        for k, v in src.items():
            scores[k] += v

    scores["default_game"] += _ENERGY_WEIGHT * 0.5

    if _prompt_has(prompt, _CHIPTUNE_PROMPT) and not _tags_have(keys, _ORCHESTRAL_TAGS):
        scores["dense_dance"] += _PROMPT_WEIGHT
        scores["orchestral_boss"] -= _TAG_WEIGHT * 2

    if anti_orchestra:
        scores["orchestral_boss"] -= _PROMPT_WEIGHT
        scores["hybrid_epic"] -= _TAG_WEIGHT
        scores["energetic_game"] += _PROMPT_WEIGHT * 0.6
        scores["compact_action"] += _PROMPT_WEIGHT * 0.4

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

    return ArchetypeDecision(best, reason)


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


_LLM_OVERRIDE_CONFLICTS: dict[str, frozenset[str]] = {
    "orchestral_boss": frozenset({
        "compact_action", "energetic_game", "dense_dance", "sparse_loop",
        "lofi_downtempo", "industrial_combat",
    }),
    "moderate_cinematic": frozenset({"dense_dance", "sparse_loop", "lofi_downtempo"}),
    "dense_dance": frozenset({"orchestral_boss", "moderate_cinematic", "hybrid_epic"}),
    "hybrid_epic": frozenset({"compact_action", "energetic_game", "lofi_downtempo"}),
    "energetic_game": frozenset({"orchestral_boss", "hybrid_epic"}),
}


def reconcile_llm_archetype(
    llm_archetype: str | None,
    *,
    style_profile: MusicalStyleProfile | None = None,
    raw_prompt: str = "",
    use_case: str = "game",
    energy_level: int = 3,
) -> ArchetypeDecision:
    """
    Combina composition_archetype del LLM con inferencia del prompt.
    El LLM gana solo si no contradice guardrails explícitos del brief.
    """
    decision = infer_composition_archetype_with_reason(
        style_profile=style_profile,
        raw_prompt=raw_prompt,
        use_case=use_case,
        energy_level=energy_level,
    )
    llm_raw = (llm_archetype or "").strip().lower()
    if llm_raw not in ALL_ACCEPTED_ARCHETYPES:
        return decision

    llm = normalize_archetype(llm_raw)
    inferred = decision.archetype

    if llm == inferred:
        return ArchetypeDecision(inferred, "technical_spec.composition_archetype")

    if decision.reason.startswith("precedence_matrix:"):
        return decision

    prompt = _prompt_lower(raw_prompt)
    if llm == "orchestral_boss" and _prompt_has(prompt, _ANTI_ORCHESTRA_PROMPT):
        return ArchetypeDecision(
            inferred,
            f"prompt_guardrail:anti_orchestra_overrides_llm_{llm_raw}",
        )

    conflicts = _LLM_OVERRIDE_CONFLICTS.get(llm, frozenset())
    if inferred in conflicts:
        return ArchetypeDecision(
            inferred,
            f"prompt_guardrail:{decision.reason}",
        )

    return ArchetypeDecision(llm, "technical_spec.composition_archetype")


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
        return normalize_archetype(str(cached))

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
    from cadence.music.composition_archetypes import policy_family

    arch = normalize_archetype(archetype)
    fam = policy_family(arch)
    if fam == "dense":
        return "dense"
    if fam == "compact":
        return "balanced"
    if fam == "energetic":
        return "dense" if energy_level >= 4 else "balanced"
    if fam == "sparse":
        return "sparse"
    if fam == "cinematic":
        return "sparse" if energy_level <= 2 else "balanced"
    if fam == "orchestral":
        return "balanced"
    from cadence.music.repertoire_signals import default_melody_texture

    return default_melody_texture(energy_level, use_case, requested)
