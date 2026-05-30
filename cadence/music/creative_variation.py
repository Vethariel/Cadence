"""
Límites de variación creativa — alta variación dentro de anclas narrativas.
"""

from __future__ import annotations

from cadence.music.repertoire_signals import max_optional_budget
from cadence.schemas.song_state import CreativeVariationBounds, NarrativeAnchors

OPTIONAL_LAYER_POOL = (
    "pad", "countermelody", "echo_synth", "arp_synth",
    "chord_stab", "synth_pluck", "perc_aux", "fx_riser",
)


def build_creative_variation_bounds(
    anchors: NarrativeAnchors,
    *,
    energy_level: int = 3,
    use_case: str = "game",
    composition_archetype: str | None = None,
    generation_seed: int = 0,
) -> CreativeVariationBounds:
    """
    Deriva cuánta libertad tienen timbres, patrones y microfraseo
    sin romper narrative_anchors.
    """
    max_opt, max_lead = max_optional_budget(
        use_case, energy_level, composition_archetype=composition_archetype,
    )
    arch = composition_archetype or ""
    avg_density = sum(a.density for a in anchors.sections) / max(1, len(anchors.sections))

    if arch == "compact_action":
        max_opt = min(max_opt, 3)
        max_lead = 1
        pattern_var = 0.35
        micro_var = 0.45
        fill_var = 0.30
        timbre_var = 0.40
    elif arch == "chiptune_dance":
        max_opt = min(max_opt + 1, 6)
        max_lead = min(max_lead + 1, 3)
        pattern_var = 0.85
        micro_var = 0.90
        fill_var = 0.75
        timbre_var = 0.55
    elif arch == "orchestral_boss":
        max_opt = min(max_opt + 1, 6)
        max_lead = min(max_lead + 1, 3)
        pattern_var = 0.65
        micro_var = 0.55
        fill_var = 0.50
        timbre_var = 0.70
    elif (use_case or "game").lower() in ("loop", "cutscene"):
        max_opt = min(max_opt, 2)
        max_lead = min(max_lead, 1)
        pattern_var = 0.30
        micro_var = 0.35
        fill_var = 0.20
        timbre_var = 0.35
    else:
        pattern_var = 0.55 + (energy_level - 3) * 0.08
        micro_var = 0.50 + avg_density * 0.35
        fill_var = 0.40 + (energy_level - 3) * 0.06
        timbre_var = 0.55

    pattern_var = max(0.2, min(0.95, pattern_var))
    micro_var = max(0.2, min(0.95, micro_var))
    fill_var = max(0.1, min(0.85, fill_var))
    timbre_var = max(0.2, min(0.90, timbre_var))
    secondary = min(0.85, 0.35 + micro_var * 0.45)

    pool = list(OPTIONAL_LAYER_POOL)
    if energy_level <= 2:
        pool = ["pad", "countermelody", "fx_riser"]
    elif arch == "compact_action":
        pool = ["pad", "countermelody", "echo_synth", "perc_aux"]

    return CreativeVariationBounds(
        max_optional_layers=max_opt,
        max_lead_optionals=max_lead,
        allowed_optional_layers=pool,
        pattern_variance=round(pattern_var, 3),
        micro_phrase_variance=round(micro_var, 3),
        fill_density=round(fill_var, 3),
        timbre_variance=round(timbre_var, 3),
        secondary_motif_variance=round(secondary, 3),
        generation_seed=generation_seed,
    )


def clamp_optional_layer_ids(
    layer_ids: set[str],
    bounds: CreativeVariationBounds | None,
) -> set[str]:
    """Filtra capas opcionales al pool y presupuesto creativo."""
    if not bounds:
        return layer_ids
    core = {"drums", "bass", "melody"}
    optionals = [i for i in layer_ids if i not in core]
    allowed = set(bounds.allowed_optional_layers)
    filtered = core | {i for i in optionals if i in allowed}
    if len([i for i in filtered if i not in core]) > bounds.max_optional_layers:
        keep = []
        for iid in bounds.allowed_optional_layers:
            if iid in filtered and len(keep) < bounds.max_optional_layers:
                keep.append(iid)
        filtered = core | set(keep)
    return filtered


def format_variation_for_llm(bounds: CreativeVariationBounds | None) -> str:
    if not bounds:
        return ""
    return (
        "=== VARIACIÓN CREATIVA (libertad dentro de anclas) ===\n"
        f"Capas opcionales: máx {bounds.max_optional_layers}, "
        f"leads máx {bounds.max_lead_optionals}\n"
        f"Pool permitido: {', '.join(bounds.allowed_optional_layers)}\n"
        f"Varianza — patrones: {bounds.pattern_variance:.0%}, "
        f"microfraseo: {bounds.micro_phrase_variance:.0%}, "
        f"fills: {bounds.fill_density:.0%}, timbres: {bounds.timbre_variance:.0%}, "
        f"motivos secundarios: {bounds.secondary_motif_variance:.0%}\n"
    )
