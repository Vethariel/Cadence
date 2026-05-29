from cadence.schemas.song_state import SongState


RHYTHM_LAYERS = {"drums", "bass", "pad", "fx_riser", "perc_aux"}
MELODY_LAYERS = {"melody", "countermelody", "echo_synth"}
RHYTHM_CHECKS = {"tracks_present", "drums_present", "timing_order", "velocity_range"}
MELODY_CHECKS = {"melody_coverage", "melody_variety", "pitch_range"}


def failed_check_names(errors: list[str]) -> set[str]:
    names = set()
    for err in errors:
        if err.startswith("[") and "]" in err:
            names.add(err[1 : err.index("]")])
    return names


def determine_repair_layers(state: SongState) -> list[str]:
    """Decide qué capas re-componer según checks fallidos."""
    validation = state.get("validation_result")
    if not validation or not validation.errors:
        return ["melody"]

    failed = failed_check_names(validation.errors)
    errors_text = " ".join(validation.errors).lower()
    layers: set[str] = set()

    if "tracks_present" in failed:
        if "melody" in errors_text and "drums" not in errors_text and "bass" not in errors_text:
            return ["melody"]
        return list(RHYTHM_LAYERS | MELODY_LAYERS)

    if failed & {"drums_present"}:
        layers |= RHYTHM_LAYERS

    if failed & MELODY_CHECKS:
        layers |= MELODY_LAYERS

    if failed & {"timing_order", "velocity_range"}:
        if "melody" in errors_text:
            layers |= MELODY_LAYERS
        else:
            layers |= RHYTHM_LAYERS

    if not layers:
        layers = MELODY_LAYERS

    return sorted(layers)


def repair_node(state: SongState) -> dict:
    """Incrementa retry_count y registra capas a re-componer."""
    layers = determine_repair_layers(state)
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "repair_target": "compose_orchestra",
        "repair_layers": layers,
    }


def route_after_repair(state: SongState) -> str:
    return state.get("repair_target") or "compose_orchestra"
