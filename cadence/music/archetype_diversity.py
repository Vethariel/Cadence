"""
Diversidad instrumental y estructural por arquetipo compositivo.

Centraliza formas musicales priorizadas, pools de capas opcionales y helpers
para rotar variantes con generation_seed sin romper presupuestos compactos.
"""

from __future__ import annotations

from cadence.music.composition_archetypes import normalize_archetype

# Formas del catálogo (structure_forms_data) priorizadas por arquetipo — orden = preferencia.
ARCHETYPE_STRUCTURE_FORMS: dict[str, tuple[str, ...]] = {
    "sparse_loop": (
        "loop_ambient", "loop_exploration", "loop_dungeon", "loop_town",
        "loop_travel", "loop_underwater",
    ),
    "lofi_downtempo": (
        "loop_ambient", "loop_town", "emotional_piano", "puzzle_calm", "rest_camp",
    ),
    "moderate_cinematic": (
        "cutscene_arc", "cutscene_emotional", "cutscene_reveal", "emotional_piano",
        "stealth_tension", "puzzle_calm",
    ),
    "dense_dance": (
        "boss_chiptune", "arcade_pop", "edm_melodic", "game_standard",
        "edm_double_drop", "boss_edm",
    ),
    "energetic_game": (
        "game_standard", "combat_intense", "pre_battle", "wave_combat",
        "boss_extended", "combat_survival",
    ),
    "compact_action": (
        "combat_intense", "game_standard", "pre_battle", "wave_combat",
    ),
    "industrial_combat": (
        "boss_edm", "boss_dnb", "boss_dubstep", "techno_minimal",
        "dnb_roller", "combat_intense",
    ),
    "orchestral_boss": (
        "boss_orchestral", "boss_extended", "boss_hybrid", "boss_multi_phase",
        "cinematic_action", "boss_metal",
    ),
    "hybrid_epic": (
        "boss_hybrid", "orchestral_edm", "cinematic_action", "boss_orchestral",
        "trailer_short", "animation_climax",
    ),
    "menu_theme": (
        "menu_theme", "title_screen", "shop_theme", "jazz_lounge", "funk_groove",
    ),
    "stealth_tension": (
        "loop_stealth", "stealth_tension", "horror_ambient", "cutscene_horror",
        "puzzle_calm",
    ),
    "default_game": (
        "game_standard", "combat_intense", "combat_raid", "cinematic_action",
    ),
}

# Capas opcionales permitidas por arquetipo (variedad de color sin ensemble).
ARCHETYPE_OPTIONAL_LAYERS: dict[str, tuple[str, ...]] = {
    "sparse_loop": ("pad", "fx_riser"),
    "lofi_downtempo": ("pad", "echo_synth", "fx_riser"),
    "moderate_cinematic": ("pad", "countermelody", "echo_synth", "fx_riser"),
    "dense_dance": (
        "arp_synth", "countermelody", "echo_synth", "chord_stab",
        "synth_pluck", "perc_aux",
    ),
    "energetic_game": (
        "countermelody", "echo_synth", "chord_stab", "arp_synth", "perc_aux",
    ),
    "compact_action": ("pad", "countermelody", "echo_synth", "perc_aux"),
    "industrial_combat": (
        "arp_synth", "chord_stab", "echo_synth", "perc_aux", "synth_pluck",
    ),
    "orchestral_boss": (
        "pad", "countermelody", "echo_synth", "arp_synth", "chord_stab",
        "perc_aux", "fx_riser",
    ),
    "hybrid_epic": (
        "pad", "countermelody", "echo_synth", "arp_synth", "chord_stab", "perc_aux",
    ),
    "menu_theme": ("pad", "countermelody", "echo_synth", "synth_pluck"),
    "stealth_tension": ("pad", "echo_synth", "fx_riser"),
    "default_game": (
        "pad", "countermelody", "echo_synth", "arp_synth", "chord_stab", "perc_aux",
    ),
}

# Varianza creativa por arquetipo (patrones, microfraseo, timbres).
ARCHETYPE_VARIANCE: dict[str, dict[str, float]] = {
    "sparse_loop": {
        "pattern": 0.28, "micro": 0.32, "fill": 0.18, "timbre": 0.55,
    },
    "lofi_downtempo": {
        "pattern": 0.35, "micro": 0.40, "fill": 0.22, "timbre": 0.65,
    },
    "moderate_cinematic": {
        "pattern": 0.45, "micro": 0.50, "fill": 0.30, "timbre": 0.60,
    },
    "dense_dance": {
        "pattern": 0.88, "micro": 0.92, "fill": 0.78, "timbre": 0.62,
    },
    "energetic_game": {
        "pattern": 0.72, "micro": 0.78, "fill": 0.55, "timbre": 0.58,
    },
    "compact_action": {
        "pattern": 0.38, "micro": 0.48, "fill": 0.32, "timbre": 0.45,
    },
    "industrial_combat": {
        "pattern": 0.82, "micro": 0.85, "fill": 0.70, "timbre": 0.52,
    },
    "orchestral_boss": {
        "pattern": 0.68, "micro": 0.58, "fill": 0.52, "timbre": 0.72,
    },
    "hybrid_epic": {
        "pattern": 0.75, "micro": 0.65, "fill": 0.58, "timbre": 0.68,
    },
    "menu_theme": {
        "pattern": 0.40, "micro": 0.42, "fill": 0.25, "timbre": 0.58,
    },
    "stealth_tension": {
        "pattern": 0.32, "micro": 0.38, "fill": 0.20, "timbre": 0.50,
    },
    "default_game": {
        "pattern": 0.55, "micro": 0.52, "fill": 0.42, "timbre": 0.55,
    },
}


def archetype_from_tag_hints(genre_tags: list[str] | None) -> str | None:
    """Override de arquetipo cuando los tags son inequívocos (menú, boss, etc.)."""
    tags = {t.lower() for t in (genre_tags or [])}
    if tags & {"menu", "ui", "title", "shop", "hub"}:
        return "menu_theme"
    if tags & {"stealth", "sneak", "infiltration"}:
        return "stealth_tension"
    if tags & {"boss", "final_boss"}:
        return "orchestral_boss"
    if tags & {"chiptune", "8bit", "arcade"}:
        return "dense_dance"
    if tags & {"lofi", "chill", "downtempo"}:
        return "lofi_downtempo"
    return None


def infer_archetype_for_planning(
    *,
    raw_prompt: str = "",
    use_case: str = "game",
    energy_level: int = 3,
    genre_tags: list[str] | None = None,
    style_hints: list[str] | None = None,
) -> str:
    """Inferencia temprana (spec/prepare) antes de strategy_planner."""
    from cadence.music.style_archetype import infer_composition_archetype
    from cadence.schemas.song_state import MusicalStyleProfile

    tags = list(genre_tags or []) + list(style_hints or [])
    return infer_composition_archetype(
        style_profile=MusicalStyleProfile(genres=tags[:16]) if tags else None,
        raw_prompt=raw_prompt,
        use_case=use_case,
        energy_level=energy_level,
    )


def valid_archetype_forms(archetype: str | None) -> tuple[str, ...]:
    from cadence.music.structure_forms_data import STRUCTURE_FORMS

    arch = normalize_archetype(archetype)
    return tuple(
        fid for fid in ARCHETYPE_STRUCTURE_FORMS.get(arch, ARCHETYPE_STRUCTURE_FORMS["default_game"])
        if fid in STRUCTURE_FORMS
    )


def archetype_form_score_bonus(form_id: str, archetype: str | None) -> float:
    """Bonus al rankear formas cuando encajan con el arquetipo."""
    forms = valid_archetype_forms(archetype)
    if form_id not in forms:
        return 0.0
    return 6.0 - forms.index(form_id) * 0.6


def pick_structure_form_for_archetype(
    archetype: str | None,
    generation_seed: int = 0,
) -> str | None:
    """Elige una forma del pool del arquetipo (determinista por seed)."""
    forms = valid_archetype_forms(archetype)
    if not forms:
        return None
    return forms[generation_seed % len(forms)]


def optional_layer_pool_for_archetype(archetype: str | None) -> tuple[str, ...]:
    arch = normalize_archetype(archetype)
    return ARCHETYPE_OPTIONAL_LAYERS.get(
        arch, ARCHETYPE_OPTIONAL_LAYERS["default_game"],
    )


def variance_for_archetype(archetype: str | None) -> dict[str, float]:
    arch = normalize_archetype(archetype)
    return dict(ARCHETYPE_VARIANCE.get(arch, ARCHETYPE_VARIANCE["default_game"]))


def pick_optional_layers_for_archetype(
    archetype: str | None,
    *,
    generation_seed: int,
    max_layers: int,
) -> list[str]:
    """Subconjunto rotado del pool de capas del arquetipo."""
    pool = list(optional_layer_pool_for_archetype(archetype))
    if not pool or max_layers <= 0:
        return []
    n = min(max_layers, len(pool))
    start = generation_seed % len(pool)
    out: list[str] = []
    for i in range(n):
        out.append(pool[(start + i * 3) % len(pool)])
    return out
