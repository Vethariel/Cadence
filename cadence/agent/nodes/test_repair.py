from cadence.schemas.song_state import ValidationResult
from cadence.agent.nodes.repair import determine_repair_layers, failed_check_names


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
    assert determine_repair_layers(state) == ["melody"]
    print("✓ melody_coverage → [melody]")


def test_melody_variety_routes_to_melody():
    state = _state_with_errors([
        "[melody_variety] Melodía demasiado monótona: solo 1 pitch(es) únicos.",
    ])
    assert determine_repair_layers(state) == ["melody"]
    print("✓ melody_variety → [melody]")


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
    assert determine_repair_layers(state) == ["melody"]
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
    assert determine_repair_layers(state) == ["melody"]
    print("✓ pitch_range → [melody]")


def test_timing_drums_routes_to_rhythm():
    state = _state_with_errors([
        "[timing_order] Track 'drums': eventos fuera de orden cronológico",
    ])
    layers = set(determine_repair_layers(state))
    assert "drums" in layers
    print("✓ timing_order (drums) → rhythm layers")


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
    print("\n✓ todos los tests de repair OK")
