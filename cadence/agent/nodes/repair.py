from cadence.schemas.song_state import SongState, ValidationResult


# ── Prioridad de reparación por check fallido ─────────────────
# Checks que requieren regenerar rhythm (drums + bass)
RHYTHM_CHECKS = {"tracks_present", "drums_present", "timing_order", "velocity_range"}

# Checks que requieren regenerar solo melodía
MELODY_CHECKS = {"melody_coverage", "melody_variety", "pitch_range"}


def failed_check_names(errors: list[str]) -> set[str]:
    names = set()
    for err in errors:
        if err.startswith("[") and "]" in err:
            names.add(err[1 : err.index("]")])
    return names


def determine_repair_target(state: SongState) -> str:
    """
    Decide qué nodo re-ejecutar según los checks que fallaron.
    Retorna 'rhythm_engine' o 'melody_composer'.
    """
    validation = state.get("validation_result")
    if not validation or not validation.errors:
        return "melody_composer"

    failed = failed_check_names(validation.errors)
    errors_text = " ".join(validation.errors).lower()

    # tracks_present: depende de qué track falta
    if "tracks_present" in failed:
        if "melody" in errors_text and "drums" not in errors_text and "bass" not in errors_text:
            return "melody_composer"
        return "rhythm_engine"

    if failed & {"drums_present"}:
        return "rhythm_engine"

    if failed & MELODY_CHECKS:
        return "melody_composer"

    # timing / velocity: inferir del track mencionado en el mensaje
    if failed & {"timing_order", "velocity_range"}:
        if "melody" in errors_text:
            return "melody_composer"
        if "drums" in errors_text or "bass" in errors_text:
            return "rhythm_engine"
        return "rhythm_engine"

    return "melody_composer"


def repair_node(state: SongState) -> dict:
    """
    Incrementa retry_count y registra el nodo destino de reparación.
    """
    target = determine_repair_target(state)
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "repair_target": target,
    }


def route_after_repair(state: SongState) -> str:
    """Enruta al nodo correcto según repair_target."""
    return state.get("repair_target") or "melody_composer"
