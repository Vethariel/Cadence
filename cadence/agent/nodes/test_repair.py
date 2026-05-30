from cadence.schemas.song_state import ValidationResult
from cadence.agent.nodes.repair import (
    determine_repair_layers,
    determine_repair_plan,
    failed_check_names,
)


def _state_with_errors(errors: list[str], retry_count: int = 0):
    return {
        "validation_result": ValidationResult(
            score=0.5, errors=errors, warnings=[], passed=False
        ),
        "retry_count": retry_count,
    }


def test_melody_coverage_routes_to_melody():
    state = _state_with_errors([
        "[melody_coverage] Melodía cubre solo 40% de la duración total.",
    ])
    layers = determine_repair_layers(state)
    assert "melody" in layers
    assert "countermelody" in layers
    print("✓ melody_coverage → melody + countermelody")


def test_melody_variety_routes_to_melody():
    state = _state_with_errors([
        "[melody_variety] Melodía demasiado monótona: solo 1 pitch(es) únicos.",
    ])
    layers = determine_repair_layers(state)
    assert "melody" in layers
    print("✓ melody_variety → melody layers")


def test_missing_drums_routes_to_rhythm_layers():
    state = _state_with_errors([
        "[tracks_present] Tracks faltantes: {'drums'}",
    ])
    layers = set(determine_repair_layers(state))
    assert "drums" in layers and "melody" in layers
    print("✓ tracks_present (drums) → rhythm + melody layers")


def test_missing_melody_routes_to_melody():
    state = _state_with_errors([
        "[tracks_present] Tracks faltantes: {'melody'}",
    ])
    layers = determine_repair_layers(state)
    assert layers == ["melody"]
    print("✓ tracks_present (melody) → [melody]")


def test_drums_present_routes_to_rhythm():
    state = _state_with_errors([
        "[drums_present] Drums ausentes en demasiadas secciones: {'drop'}",
    ])
    layers = set(determine_repair_layers(state))
    assert "drums" in layers
    print("✓ drums_present → drums layer")


def test_pitch_range_routes_to_melody():
    state = _state_with_errors([
        "[pitch_range] 3 notas fuera de rango MIDI (21-108): [10, 12, 15]",
    ])
    layers = determine_repair_layers(state)
    assert "melody" in layers
    print("✓ pitch_range → melody layers")


def test_timing_drums_routes_to_rhythm():
    state = _state_with_errors([
        "[timing_order] Track 'drums': eventos fuera de orden cronológico",
    ])
    layers = set(determine_repair_layers(state))
    assert "drums" in layers
    print("✓ timing_order (drums) → rhythm layers")


def test_instrumental_richness_routes_to_arrangement():
    state = _state_with_errors([
        "[instrumental_richness] Riqueza instrumental baja: capas activas μ=2.0",
    ])
    plan = determine_repair_plan(state)
    assert plan["repair_target"] == "arrangement_planner"
    assert "restore_optional_layers" in plan["repair_actions"]
    print("✓ instrumental_richness → arrangement + restore_optionals")


def test_dynamic_range_routes_to_post_process():
    state = _state_with_errors(["[dynamic_range] Dinámica plana entre secciones"])
    plan = determine_repair_plan(state)
    assert plan["repair_target"] == "post_process"
    assert "recalc_dynamic_range" in plan["repair_actions"]
    print("✓ dynamic_range → post_process")


def test_intensity_arc_routes_to_post_process():
    state = _state_with_errors([
        "[intensity_arc] Sección clave 'drop' no alcanza la intensidad esperada",
    ])
    plan = determine_repair_plan(state)
    assert plan["repair_target"] == "post_process"
    assert "adjust_section_intensity" in plan["repair_actions"]
    print("✓ intensity_arc → post_process")


def test_non_melody_failure_avoids_melody_only():
    state = _state_with_errors([
        "[instrumental_richness] capas activas μ=2.0",
        "[drums_present] Drums ausentes en demasiadas secciones",
    ])
    layers = set(determine_repair_layers(state))
    assert "drums" in layers
    assert layers != {"melody"}
    print("✓ non-melody failures avoid melody-only fallback")


def test_failed_check_names_parser():
    errors = ["[melody_coverage] foo", "[drums_present] bar"]
    assert failed_check_names(errors) == {"melody_coverage", "drums_present"}
    print("✓ failed_check_names OK")


if __name__ == "__main__":
    test_failed_check_names_parser()
    test_melody_coverage_routes_to_melody()
    test_melody_variety_routes_to_melody()
    test_missing_drums_routes_to_rhythm_layers()
    test_missing_melody_routes_to_melody()
    test_drums_present_routes_to_rhythm()
    test_pitch_range_routes_to_melody()
    test_timing_drums_routes_to_rhythm()
    test_instrumental_richness_routes_to_arrangement()
    test_dynamic_range_routes_to_post_process()
    test_intensity_arc_routes_to_post_process()
    test_non_melody_failure_avoids_melody_only()
    print("\n✓ todos los tests de repair OK")
