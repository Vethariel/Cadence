from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import (
    UserIntent, TechnicalProposal, SongStructure, Track, RhythmEvent
)
from cadence.agent.nodes.validator import validator_node

def _make_base_state(tracks):
    return {
        "messages": [HumanMessage(content="test")],
        "intent": UserIntent(
            raw_prompt="test",
            knowledge_level="non_technical",
            use_case="game",
            mood="dark",
            style_tags=["techno"],
        ),
        "technical_proposal": None,
        "structure": SongStructure(
            sections=["intro", "drop", "outro"],
            bars_per_section={"intro": 4, "drop": 8, "outro": 4},
            total_bars=16,
            estimated_duration_ms=26400,
        ),
        "tracks": tracks,
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

def _make_note(t, pitch=65, section="drop"):
    return RhythmEvent(
        t=t, type="note", pitch=pitch,
        duration_ms=200, velocity=90,
        beat_index=0, section=section,
    )

def _make_drum(t, section="drop"):
    return RhythmEvent(
        t=t, type="drum_hit", pitch=36,
        duration_ms=100, velocity=100,
        beat_index=0, section=section,
    )

def test_passes():
    """Estado válido — debe pasar con score >= 0.8."""
    # Melodía cubre intro + drop + outro hasta ~26000ms
    melody_events = (
        [_make_note(i * 400, pitch=65 + (i % 5), section="intro") for i in range(8)] +
        [_make_note(3200 + i * 200, pitch=65 + (i % 5), section="drop") for i in range(60)] +
        [_make_note(15200 + i * 400, pitch=65 + (i % 3), section="outro") for i in range(28)]
    )
    # Drums cubren las tres secciones activas
    drum_events = (
        [_make_drum(i * 200, section="intro") for i in range(15)] +
        [_make_drum(3200 + i * 100, section="drop") for i in range(80)] +
        [_make_drum(15200 + i * 200, section="outro") for i in range(15)]
    )
    tracks = [
        Track(id="melody", instrument="Lead", midi_channel=0, role="lead",
              events=melody_events),
        Track(id="drums",  instrument="Drums", midi_channel=9, role="rhythm",
              events=drum_events),
        Track(id="bass",   instrument="Bass",  midi_channel=1, role="bass",
              events=[_make_note(i * 400, pitch=41, section="drop") for i in range(20)]),
    ]
    result = validator_node(_make_base_state(tracks))
    v = result["validation_result"]
    print(f"[passes] score={v.score}  passed={v.passed}  errors={v.errors}")
    assert v.passed, f"Debería pasar: {v.errors}"
    print("✓ test_passes OK")

def test_missing_melody():
    """Sin track de melodía — debe fallar."""
    tracks = [
        Track(id="drums", instrument="Drums", midi_channel=9, role="rhythm",
              events=[_make_drum(i * 100) for i in range(20)]),
        Track(id="bass",  instrument="Bass",  midi_channel=1, role="bass",
              events=[_make_note(i * 400, pitch=41) for i in range(10)]),
    ]
    result = validator_node(_make_base_state(tracks))
    v = result["validation_result"]
    print(f"[missing_melody] score={v.score}  passed={v.passed}  errors={v.errors}")
    assert not v.passed
    assert any("melody" in e.lower() or "tracks" in e.lower() for e in v.errors)
    print("✓ test_missing_melody OK")

def test_low_coverage():
    """Melodía que cubre solo el 20% de la duración — debe fallar."""
    melody_events = [_make_note(i * 200, section="drop") for i in range(5)]
    tracks = [
        Track(id="melody", instrument="Lead", midi_channel=0, role="lead", events=melody_events),
        Track(id="drums",  instrument="Drums", midi_channel=9, role="rhythm",
              events=[_make_drum(i * 100) for i in range(20)]),
        Track(id="bass",   instrument="Bass",  midi_channel=1, role="bass",
              events=[_make_note(i * 400, pitch=41) for i in range(10)]),
    ]
    result = validator_node(_make_base_state(tracks))
    v = result["validation_result"]
    print(f"[low_coverage] score={v.score}  passed={v.passed}  errors={v.errors}")
    assert not v.passed
    assert any("coverage" in e.lower() or "cubre" in e.lower() for e in v.errors)
    print("✓ test_low_coverage OK")

def test_monotone_melody():
    """Melodía con un solo pitch — debe fallar por falta de variedad."""
    melody_events = [_make_note(i * 200, pitch=65, section="drop") for i in range(60)]
    tracks = [
        Track(id="melody", instrument="Lead", midi_channel=0, role="lead", events=melody_events),
        Track(id="drums",  instrument="Drums", midi_channel=9, role="rhythm",
              events=[_make_drum(i * 100) for i in range(20)]),
        Track(id="bass",   instrument="Bass",  midi_channel=1, role="bass",
              events=[_make_note(i * 400, pitch=41) for i in range(10)]),
    ]
    result = validator_node(_make_base_state(tracks))
    v = result["validation_result"]
    print(f"[monotone] score={v.score}  passed={v.passed}  errors={v.errors}")
    assert not v.passed
    assert any("monótona" in e or "variety" in e.lower() for e in v.errors)
    print("✓ test_monotone_melody OK")

if __name__ == "__main__":
    test_passes()
    print("---")
    test_missing_melody()
    print("---")
    test_low_coverage()
    print("---")
    test_monotone_melody()
    print("\n✓ todos los tests del validator OK")
