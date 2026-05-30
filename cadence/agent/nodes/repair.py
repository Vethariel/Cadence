from __future__ import annotations

from cadence.schemas.song_state import SongState
from cadence.music.orchestral_arrangement import orchestral_repair_layer_ids
from cadence.music.style_archetype import get_composition_archetype

RHYTHM_LAYERS = {"drums", "bass", "pad", "fx_riser", "perc_aux"}
MELODY_LAYERS = {"melody", "countermelody", "echo_synth"}
OPTIONAL_LAYERS = {
    "pad", "countermelody", "echo_synth", "arp_synth",
    "chord_stab", "synth_pluck", "perc_aux", "fx_riser",
}

MELODY_ONLY_CHECKS = frozenset({
    "melody_coverage",
    "melody_variety",
    "pitch_range",
    "melody_loop",
    "melody_leaps",
    "melody_rest_density",
    "melody_notes_per_bar",
})
INSTRUMENTAL_CHECKS = frozenset({
    "instrumental_richness",
    "planned_layers",
    "orchestral_layers",
})
POST_PROCESS_ACTION_CHECKS = frozenset({
    "dynamic_range",
    "intensity_arc",
    "narrative_intensity",
})
NARRATIVE_MELODY_CHECKS = frozenset({"narrative_motif", "narrative_key_coverage"})
RHYTHM_CHECKS = frozenset({"drums_present", "timing_order"})
MELODY_CHECKS = MELODY_ONLY_CHECKS


def failed_check_names(errors: list[str]) -> set[str]:
    names = set()
    for err in errors:
        if err.startswith("[") and "]" in err:
            names.add(err[1 : err.index("]")])
    return names


def optional_layers_for_repair(state: SongState) -> list[str]:
    """Capas opcionales a re-componer tras fallo de riqueza instrumental."""
    core = {"drums", "bass", "melody"}
    arrangement = state.get("arrangement")
    if arrangement:
        ids = [
            l.instrument_id for l in arrangement.layers
            if l.instrument_id not in core
        ]
        if ids:
            return sorted(set(ids))
    return sorted(OPTIONAL_LAYERS)


def determine_repair_plan(state: SongState) -> dict:
    """
    Mapea checks fallidos → target del grafo, capas y acciones concretas.

    - instrumental_richness / planned_layers → restaurar capas + schedule
    - dynamic_range → recalc_dynamic_range en post_process
    - intensity_arc → adjust_section_intensity en post_process
    - Fallos melódicos puros → solo capas MELODY_LAYERS
    """
    validation = state.get("validation_result")
    empty = {
        "repair_target": "compose_orchestra",
        "repair_layers": ["melody"],
        "repair_actions": [],
    }
    if not validation or not validation.errors:
        return empty

    failed = failed_check_names(validation.errors)
    errors_text = " ".join(validation.errors).lower()
    actions: list[str] = []
    layers: set[str] = set()
    non_melody = failed - MELODY_ONLY_CHECKS

    archetype = get_composition_archetype(state)

    if failed & INSTRUMENTAL_CHECKS:
        actions.append("restore_optional_layers")
        if archetype == "orchestral_boss":
            layers |= set(orchestral_repair_layer_ids())
            layers |= {"drums", "bass"}
        else:
            layers |= set(optional_layers_for_repair(state))

    if "dynamic_range" in failed:
        actions.append("recalc_dynamic_range")
    if failed & {"intensity_arc", "narrative_intensity"}:
        actions.append("adjust_section_intensity")

    if failed & NARRATIVE_MELODY_CHECKS:
        if "narrative_key_coverage" in failed:
            actions.append("restore_optional_layers")
            layers |= set(optional_layers_for_repair(state))
        if "narrative_motif" in failed:
            layers |= MELODY_LAYERS

    if "tracks_present" in failed:
        if (
            "melody" in errors_text
            and "drums" not in errors_text
            and "bass" not in errors_text
        ):
            layers = {"melody"}
        else:
            layers |= RHYTHM_LAYERS | MELODY_LAYERS

    if failed & RHYTHM_CHECKS:
        layers |= RHYTHM_LAYERS

    if failed & MELODY_ONLY_CHECKS:
        layers |= MELODY_LAYERS

    if failed & {"timing_order", "velocity_range"}:
        if "melody" in errors_text and "drums" not in errors_text:
            layers |= MELODY_LAYERS
        else:
            layers |= RHYTHM_LAYERS

    # Target del grafo (prioridad: re-arreglo > re-composición > post_process)
    if "restore_optional_layers" in actions:
        target = "arrangement_planner"
        if not layers:
            layers |= set(optional_layers_for_repair(state))
    elif layers:
        target = "compose_orchestra"
    elif actions:
        target = "post_process"
    elif failed <= MELODY_ONLY_CHECKS:
        target = "compose_orchestra"
        layers = set(MELODY_LAYERS)
    else:
        target = "compose_orchestra"
        layers = RHYTHM_LAYERS | MELODY_LAYERS

    # Evitar fallback excesivo a solo melodía si el fallo no es melódico puro
    melody_only = layers <= MELODY_LAYERS and layers
    if melody_only and non_melody:
        if failed & INSTRUMENTAL_CHECKS:
            if archetype == "orchestral_boss":
                layers |= set(orchestral_repair_layer_ids()) | {"drums", "bass"}
            else:
                layers |= set(optional_layers_for_repair(state))
            target = "arrangement_planner"
            if "restore_optional_layers" not in actions:
                actions.append("restore_optional_layers")
        elif failed & RHYTHM_CHECKS:
            layers |= RHYTHM_LAYERS
        elif failed & POST_PROCESS_ACTION_CHECKS and not (failed & MELODY_ONLY_CHECKS):
            target = "post_process"
            if not actions:
                actions.append("recalc_dynamic_range")

    if not layers and target == "compose_orchestra":
        layers = set(MELODY_LAYERS) if failed <= MELODY_ONLY_CHECKS else (RHYTHM_LAYERS | MELODY_LAYERS)

    return {
        "repair_target": target,
        "repair_layers": sorted(layers) if layers else None,
        "repair_actions": actions,
    }


def determine_repair_layers(state: SongState) -> list[str]:
    """Compat: capas a re-componer."""
    plan = determine_repair_plan(state)
    return plan.get("repair_layers") or ["melody"]


def repair_node(state: SongState) -> dict:
    """Incrementa retry_count y registra plan de reparación."""
    from cadence.observability.pipeline_log import (
        failed_check_names_from_state,
        log_repair_intervention,
    )

    plan = determine_repair_plan(state)
    retry_count = state.get("retry_count", 0) + 1
    validation = state.get("validation_result")
    score = validation.score if validation else None

    out: dict = {
        "retry_count": retry_count,
        "repair_target": plan["repair_target"],
        "repair_layers": plan.get("repair_layers"),
        "repair_actions": plan.get("repair_actions") or [],
    }
    out.update(
        log_repair_intervention(
            state,
            retry_count=retry_count,
            failed_checks=failed_check_names_from_state(state),
            repair_target=plan["repair_target"],
            repair_layers=plan.get("repair_layers"),
            repair_actions=plan.get("repair_actions") or [],
            validation_score=score,
        ),
    )
    return out


def route_after_repair(state: SongState) -> str:
    return state.get("repair_target") or "compose_orchestra"
