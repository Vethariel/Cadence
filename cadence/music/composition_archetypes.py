"""
Registro central de arquetipos compositivos del pipeline.

Los arquetipos son plantillas de composición (capas, densidad, paleta), distintos
de los ~200 géneros en genre_catalog. Los nombres canónicos están alineados con
benchmark_profiles donde aplica; los IDs legacy del LLM se normalizan vía aliases.
"""

from __future__ import annotations

from typing import Final

COMPOSITION_ARCHETYPES: Final[tuple[str, ...]] = (
    "sparse_loop",
    "lofi_downtempo",
    "moderate_cinematic",
    "dense_dance",
    "energetic_game",
    "compact_action",
    "industrial_combat",
    "orchestral_boss",
    "hybrid_epic",
    "menu_theme",
    "stealth_tension",
    "default_game",
)

# IDs legacy / benchmark → id canónico del pipeline
ARCHETYPE_ALIASES: Final[dict[str, str]] = {
    "ambient_loop": "sparse_loop",
    "cinematic_cutscene": "moderate_cinematic",
    "chiptune_dance": "dense_dance",
    "boss_orchestral": "orchestral_boss",
}

ALL_ACCEPTED_ARCHETYPES: frozenset[str] = frozenset(
    COMPOSITION_ARCHETYPES,
) | frozenset(ARCHETYPE_ALIASES.keys())

# Familia de política compartida (voz, textura, ensemble, densidad)
ARCHETYPE_POLICY_FAMILY: Final[dict[str, str]] = {
    "sparse_loop": "sparse",
    "lofi_downtempo": "sparse",
    "stealth_tension": "sparse",
    "moderate_cinematic": "cinematic",
    "menu_theme": "cinematic",
    "dense_dance": "dense",
    "industrial_combat": "dense",
    "energetic_game": "energetic",
    "compact_action": "compact",
    "orchestral_boss": "orchestral",
    "hybrid_epic": "orchestral",
    "default_game": "default",
}


def normalize_archetype(raw: str | None) -> str:
    """Devuelve el id canónico; desconocido → default_game."""
    key = (raw or "").strip().lower()
    if not key:
        return "default_game"
    if key in ARCHETYPE_ALIASES:
        return ARCHETYPE_ALIASES[key]
    if key in COMPOSITION_ARCHETYPES:
        return key
    return "default_game"


def is_valid_archetype(raw: str | None) -> bool:
    key = (raw or "").strip().lower()
    return key in ALL_ACCEPTED_ARCHETYPES


def policy_family(archetype: str | None) -> str:
    return ARCHETYPE_POLICY_FAMILY.get(normalize_archetype(archetype), "default")


def matches_archetype(archetype: str | None, *targets: str) -> bool:
    canon = normalize_archetype(archetype)
    return any(canon == normalize_archetype(t) for t in targets)


def matches_policy_family(archetype: str | None, family: str) -> bool:
    return policy_family(archetype) == family


def all_archetype_scores() -> dict[str, float]:
    return {a: 0.0 for a in COMPOSITION_ARCHETYPES}


# Sin familias ensemble (woodwind, strings_ensemble, etc.)
ARCHETYPE_SUPPRESSES_ENSEMBLE: frozenset[str] = frozenset({
    "sparse_loop",
    "lofi_downtempo",
    "stealth_tension",
    "compact_action",
    "energetic_game",
    "dense_dance",
    "industrial_combat",
})


def suppresses_ensemble(archetype: str | None) -> bool:
    return normalize_archetype(archetype) in ARCHETYPE_SUPPRESSES_ENSEMBLE


def archetype_optional_budget(
    archetype: str | None,
    energy_level: int,
    use_case: str,
) -> tuple[int, int] | None:
    """
    (max_optionals, max_lead_optionals) fijos por arquetipo, o None = reglas genéricas.
    """
    arch = normalize_archetype(archetype)
    uc = (use_case or "game").lower()
    energy = max(1, min(5, energy_level))

    if arch == "compact_action":
        return 3, 1
    if arch == "energetic_game":
        return 3, 2
    if arch == "dense_dance" and energy >= 4:
        return 4, 3
    if arch == "orchestral_boss" and energy >= 4:
        return 5, 3
    if arch == "hybrid_epic" and energy >= 4:
        return 5, 3
    if arch == "moderate_cinematic":
        return 3, 1
    if arch == "sparse_loop":
        return (0, 0) if uc == "loop" else (2, 0)
    if arch == "lofi_downtempo":
        return (2, 0)
    if arch == "stealth_tension":
        return 2, 0
    if arch == "menu_theme":
        return 2, 1
    return None


def format_archetypes_for_llm() -> str:
    """Lista compacta para el prompt del technical_spec."""
    return " | ".join(COMPOSITION_ARCHETYPES)
