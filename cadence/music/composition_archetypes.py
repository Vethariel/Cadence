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


def format_archetypes_for_llm() -> str:
    """Lista compacta para el prompt del technical_spec."""
    return " | ".join(COMPOSITION_ARCHETYPES)
