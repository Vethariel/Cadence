"""Identidad de pista melody — nombre/programa desde orchestration_plan."""

import cadence.instruments  # noqa: F401
from cadence.music.instrument_catalog import (
    _separate_melody_echo_synth_programs,
    melody_instrument_from_state,
)
from cadence.schemas.song_state import RhythmEvent, Track
from cadence.music.timbre_library import STYLE_PALETTES, palette_echo_differs_from_melody
from cadence.schemas.song_state import InstrumentAssignment, OrchestrationPlan
from cadence.test_fixtures.pipeline_coherence import build_aligned_pipeline_state


def test_all_style_palettes_echo_differs_from_melody():
    for name, palette in STYLE_PALETTES.items():
        assert palette_echo_differs_from_melody(palette), (
            f"paleta {name}: echo_synth == melody"
        )


def test_melody_instrument_from_orchestration_plan():
    state = build_aligned_pipeline_state(generation_seed=42)
    state["orchestration_plan"] = OrchestrationPlan(
        ensemble_concept="test",
        drum_pattern="techno",
        bass_pattern="driving",
        instruments=[
            InstrumentAssignment(
                instrument_id="melody",
                gm_program=27,
                display_name="Clean Electric Guitar",
                active=True,
            ),
        ],
    )
    name, prog = melody_instrument_from_state(state)
    assert name == "Clean Electric Guitar"
    assert prog == 27


def test_melody_track_metadata_matches_orchestration_plan():
    """Simula el ensamblado de Track tras compose (sin invocar LLM)."""
    state = build_aligned_pipeline_state(generation_seed=99)
    state["orchestration_plan"] = OrchestrationPlan(
        ensemble_concept="test",
        drum_pattern="techno",
        bass_pattern="driving",
        instruments=[
            InstrumentAssignment(
                instrument_id="melody",
                gm_program=0,
                display_name="Acoustic Grand Piano",
                active=True,
            ),
        ],
    )
    name, gm = melody_instrument_from_state(state)
    track = Track(
        id="melody",
        instrument=name,
        instrument_id="melody",
        midi_channel=0,
        role="lead",
        gm_program=gm,
        events=[
            RhythmEvent(t=0, type="note", pitch=60, duration_ms=100, velocity=80),
        ],
    )
    assert track.instrument == "Acoustic Grand Piano"
    assert track.gm_program == 0
    assert track.instrument != "Lead Synth"


def test_separate_melody_echo_synth_programs_unit():
    by_id = {
        "melody": InstrumentAssignment(
            instrument_id="melody", gm_program=80, display_name="Lead Square", active=True,
        ),
        "echo_synth": InstrumentAssignment(
            instrument_id="echo_synth", gm_program=80, display_name="Lead Square", active=True,
        ),
    }
    _separate_melody_echo_synth_programs(
        by_id,
        generation_seed=77,
        timbre_context={
            "genre_tags": ["techno"],
            "use_case": "game",
            "composition_archetype": "compact_action",
        },
    )
    assert by_id["melody"].gm_program != by_id["echo_synth"].gm_program


if __name__ == "__main__":
    test_all_style_palettes_echo_differs_from_melody()
    test_melody_instrument_from_orchestration_plan()
    test_melody_track_metadata_matches_orchestration_plan()
    test_separate_melody_echo_synth_programs_unit()
    print("All melody_track_identity tests passed.")
