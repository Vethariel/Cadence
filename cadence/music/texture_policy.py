"""
Política de textura por use_case y desarrollo — cama sonora, solapamiento y capas por segmento.

Sin listas de género: señales de rol narrativo, energía, use_case y transforms de development.
"""

from __future__ import annotations

from cadence.schemas.song_state import (
    DevelopmentPlan,
    SectionDevelopment,
    SectionIntent,
    SongStructure,
)

TextureMode = str  # bedded | staggered | simultaneous | compact

LEAD_SUPPORTS = (
    "arp_synth", "countermelody", "synth_pluck", "chord_stab", "echo_synth", "perc_aux",
)
BED_CORE = ("bass", "pad")
GAME_CORE = ("drums", "bass", "melody")


def infer_texture_mode(
    *,
    use_case: str,
    energy_level: int,
    narrative_sections: dict[str, SectionIntent] | None = None,
    active_optional_count: int = 0,
    composition_archetype: str | None = None,
) -> TextureMode:
    uc = (use_case or "game").lower()
    arch = composition_archetype or ""
    roles = []
    max_density = 0.0
    if narrative_sections:
        roles = [s.narrative_role for s in narrative_sections.values()]
        max_density = max((s.density for s in narrative_sections.values()), default=0.5)

    if arch in ("ambient_loop", "cinematic_cutscene"):
        return "bedded"
    if arch == "compact_action":
        return "compact"
    if arch == "chiptune_dance" and energy_level >= 4:
        return "simultaneous"
    if arch == "orchestral_boss" and energy_level >= 4:
        from cadence.music.orchestral_stack_policy import effective_texture_mode_for_schedule

        return effective_texture_mode_for_schedule(
            "simultaneous",
            composition_archetype=arch,
            energy_level=energy_level,
        )

    if uc in ("loop", "cutscene"):
        return "bedded"
    if energy_level >= 4 and uc == "game":
        if any(r in roles for r in ("climax", "tension")) and max_density >= 0.85:
            if active_optional_count >= 4:
                return "simultaneous"
        if max_density >= 0.7 and not any(r == "climax" for r in roles):
            return "compact"
    if energy_level >= 4 and max_density >= 0.75:
        return "simultaneous"
    return "staggered"


def schedule_core_layers(
    *,
    use_case: str,
    energy_level: int,
    percussion_suppressed: bool,
) -> list[str]:
    """Núcleo siempre activo en el schedule (no filtrado por compás)."""
    uc = (use_case or "game").lower()
    if percussion_suppressed or (uc == "loop" and energy_level <= 2):
        return ["bass", "melody", "pad"]
    if uc == "cutscene" and energy_level <= 3:
        return ["bass", "melody", "pad"]
    return ["drums", "bass", "melody"]


def entry_stagger_for_texture(
    texture_mode: TextureMode,
    layer_id: str,
    narrative_role: str,
    *,
    composition_archetype: str | None = None,
) -> int:
    if texture_mode == "bedded" and layer_id in BED_CORE:
        return 0
    from cadence.music.orchestral_stack_policy import (
        entry_stagger_orchestral,
        orchestral_stack_active,
    )

    if orchestral_stack_active(composition_archetype):
        return entry_stagger_orchestral(layer_id, narrative_role)
    if texture_mode == "simultaneous":
        return 0
    if texture_mode == "compact" and layer_id in LEAD_SUPPORTS:
        return min(2, _default_stagger(layer_id, narrative_role))
    from cadence.music.layer_schedule import _entry_stagger

    return _entry_stagger(layer_id, narrative_role)


def _default_stagger(layer_id: str, role: str) -> int:
    from cadence.music.layer_schedule import CLIMAX_STAGGER, LAYER_STAGGER

    if role == "climax":
        return CLIMAX_STAGGER.get(layer_id, LAYER_STAGGER.get(layer_id, 0))
    return LAYER_STAGGER.get(layer_id, 0)


def segment_layer_delta(
    transform: str,
    *,
    texture_mode: TextureMode,
    use_case: str,
    available: set[str],
    segment_index: int = 0,
) -> tuple[list[str], list[str]]:
    """Capas a añadir/quitar al inicio de un DevelopmentSegment."""
    add: list[str] = []
    remove: list[str] = []
    uc = (use_case or "game").lower()

    if texture_mode == "bedded" or uc in ("loop", "cutscene"):
        # Solo re-entrar cama en el primer micro-arco (evita spam de add pad/bass)
        if segment_index == 0:
            for lid in BED_CORE:
                if lid in available:
                    add.append(lid)

    sparse_like = transform in ("sparse", "fragment", "resolve", "pedal")
    dense_like = transform in ("climax", "augment", "call_response", "sequence_up")

    if sparse_like:
        for lid in LEAD_SUPPORTS:
            if lid in available:
                remove.append(lid)
    elif dense_like and texture_mode in ("simultaneous", "staggered", "compact"):
        order = ("arp_synth", "countermelody", "chord_stab", "echo_synth", "synth_pluck", "perc_aux")
        cap = 3 if texture_mode == "simultaneous" else (1 if texture_mode == "compact" else 2)
        if segment_index >= 1 and texture_mode == "staggered":
            cap = min(cap + 1, 3)
        if segment_index >= 2 and texture_mode == "simultaneous":
            cap = min(cap + 1, 4)
        for lid in order:
            if lid in available and len([x for x in add if x in LEAD_SUPPORTS]) < cap:
                add.append(lid)
    elif transform in ("expand", "introduce", "ostinato"):
        if "pad" in available and "pad" not in add:
            add.append("pad")

    add = list(dict.fromkeys(add))
    remove = [lid for lid in remove if lid not in add]
    return add, remove


def build_segment_schedule_pending(
    structure: SongStructure,
    development: DevelopmentPlan | None,
    available: set[str],
    intent_map: dict[str, SectionIntent],
    *,
    use_case: str,
    texture_mode: TextureMode,
    composition_archetype: str | None = None,
) -> list[tuple[int, str, str]]:
    """Entradas (global_bar, add|remove, layer_id) desde subdivisiones de desarrollo."""
    if not development:
        return []

    from cadence.music.layer_schedule import section_start_bars

    starts = section_start_bars(structure)
    pending: list[tuple[int, str, str]] = []

    for sec_dev in development.sections:
        if not sec_dev.segments:
            continue
        intent = intent_map.get(sec_dev.section_id)
        base_bar = starts.get(sec_dev.section_id, 0)
        for seg_idx, seg in enumerate(sec_dev.segments):
            gbar = base_bar + seg.start_bar
            role = intent.narrative_role if intent else "establish"
            from cadence.music.orchestral_stack_policy import orchestral_stack_active

            if orchestral_stack_active(composition_archetype):
                from cadence.music.orchestral_stack_policy import (
                    segment_layer_delta_orchestral,
                )

                remove, add = segment_layer_delta_orchestral(
                    seg.transform,
                    available=available,
                    segment_index=seg_idx,
                    section_role=role,
                )
            else:
                add, remove = segment_layer_delta(
                    seg.transform,
                    texture_mode=texture_mode,
                    use_case=use_case,
                    available=available,
                    segment_index=seg_idx,
                )
            for lid in remove:
                pending.append((gbar, "remove", lid))
            for lid in add:
                pending.append((gbar, "add", lid))

    return pending


def arrangement_required_layers(
    use_case: str,
    percussion_suppressed: bool,
    *,
    active_instrument_ids: set[str] | None = None,
) -> list[str]:
    """Capas que el validador exige en tracks; prioriza el plan de orquestación."""
    if active_instrument_ids:
        return sorted(active_instrument_ids)
    if percussion_suppressed or (use_case or "game").lower() in ("loop", "cutscene"):
        return ["bass", "melody", "pad"]
    return ["drums", "bass", "melody"]
