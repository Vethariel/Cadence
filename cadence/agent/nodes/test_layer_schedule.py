"""Tests Fase 5b: LayerSchedule, echo_synth, ritmo armónico."""

from langchain_core.messages import HumanMessage

import cadence.instruments  # noqa: F401
from cadence.schemas.song_state import (
    LayerSchedule,
    LayerScheduleEntry,
    RhythmEvent,
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    Track,
    UserIntent,
)
from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.agent.nodes.orchestra import compose_orchestra_node
from cadence.instruments.context import build_compose_context
from cadence.instruments.registry import compose_layer, list_instruments
from cadence.music.harmony_theory import _bars_per_chord, build_harmony_plan
from cadence.music.layer_schedule import (
    active_layers_at_bar,
    build_layer_schedule,
    filter_events_by_schedule,
    global_bar_from_ms,
)


def _boss_fight_state():
    narrative = SongNarrative(
        logline="Boss awakens and escalates to collapse",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
                transition_out="filter_sweep",
            ),
            SectionIntent(
                id="build-up", narrative_role="tension", emotional_target="urgency",
                density=0.7, harmonic_tension=0.6, rhythmic_complexity=0.6,
                transition_out="riser",
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
                transition_out="cut",
            ),
            SectionIntent(
                id="breakdown", narrative_role="reflection", emotional_target="dread",
                density=0.15, harmonic_tension=0.3, rhythmic_complexity=0.2,
                transition_out="pickup",
            ),
            SectionIntent(
                id="outro", narrative_role="release", emotional_target="calm",
                density=0.3, harmonic_tension=0.1, rhythmic_complexity=0.2,
                transition_out="fade",
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="boss fight techno")],
        "intent": UserIntent(
            raw_prompt="boss fight", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno", "dubstep"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "build-up", "drop", "breakdown", "outro"],
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "breakdown", "outro"],
            bars_per_section={
                "intro": 4, "build-up": 8, "drop": 8, "breakdown": 4, "outro": 4,
            },
            total_bars=28,
            estimated_duration_ms=48000,
        ),
        "narrative": narrative,
        "generation_seed": 42,
        "tracks": [],
    }


def test_registry_has_echo_synth():
    assert "echo_synth" in list_instruments()
    print("✓ test_registry_has_echo_synth OK")


def test_bars_per_chord_faster_under_tension():
    assert _bars_per_chord(0.85, "tension") == 1
    assert _bars_per_chord(0.55, "tension") == 2
    assert _bars_per_chord(0.8, "climax") == 1
    assert _bars_per_chord(0.3, "reflection") == 4
    print("✓ test_bars_per_chord_faster_under_tension OK")


def test_harmony_drop_has_short_chords():
    state = _boss_fight_state()
    intent_map = {s.id: s for s in state["narrative"].sections}
    plan = build_harmony_plan(
        sections=state["structure"].sections,
        key="F",
        mode="minor",
        narrative_sections=intent_map,
    )
    drop = next(s for s in plan.sections if s.section_id == "drop")
    assert all(c.bars <= 2 for c in drop.progression)
    assert any(c.bars == 1 for c in drop.progression)
    print("✓ test_harmony_drop_has_short_chords OK")


def test_layer_schedule_adds_and_removes():
    state = _boss_fight_state()
    arrangement = arrangement_planner_node(state)["arrangement"]
    schedule = arrangement.layer_schedule
    assert schedule is not None
    assert len(schedule.entries) > 0
    assert "echo_synth" in [l.instrument_id for l in arrangement.layers]

    available = {l.instrument_id for l in arrangement.layers}
    bar0 = active_layers_at_bar(schedule, 0, available)
    assert "drums" in bar0
    assert "echo_synth" not in bar0

    last_bar = state["structure"].total_bars - 1
    late = active_layers_at_bar(schedule, last_bar, available)
    assert "echo_synth" not in late or "perc_aux" not in late
    print(f"  schedule entries: {len(schedule.entries)}")
    print("✓ test_layer_schedule_adds_and_removes OK")


def test_filter_events_by_schedule():
    schedule = LayerSchedule(
        entries=[
            LayerScheduleEntry(bar=4, add=["pad"], remove=[]),
            LayerScheduleEntry(bar=12, add=[], remove=["pad"]),
        ],
        core_layers=["drums", "bass"],
    )
    events = [
        RhythmEvent(t=0, type="note", pitch=60, duration_ms=500, velocity=80),
        RhythmEvent(t=8000, type="note", pitch=62, duration_ms=500, velocity=80),
        RhythmEvent(t=24000, type="note", pitch=64, duration_ms=500, velocity=80),
    ]
    available = {"drums", "bass", "pad"}
    filtered = filter_events_by_schedule(events, "pad", schedule, 120, available)
    assert len(filtered) == 1
    assert filtered[0].pitch == 62
    assert global_bar_from_ms(8000, 120) == 4
    print("✓ test_filter_events_by_schedule OK")


def test_echo_synth_from_melody():
    state = _boss_fight_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["arrangement"] = arrangement_planner_node(state)["arrangement"]
    state["tracks"] = [
        Track(
            id="melody",
            instrument="Lead",
            role="lead",
            events=[
                RhythmEvent(
                    t=21000, type="note", pitch=72, duration_ms=400,
                    velocity=100, section="drop",
                ),
                RhythmEvent(
                    t=23000, type="note", pitch=74, duration_ms=400,
                    velocity=90, section="drop",
                ),
            ],
        ),
    ]
    echo_layer = next(
        l for l in state["arrangement"].layers if l.instrument_id == "echo_synth"
    )
    ctx = build_compose_context(state, echo_layer)
    track = compose_layer(ctx)
    assert track is not None
    assert track.id == "echo_synth"
    assert len(track.events) >= 1
    assert all(e.velocity < 100 for e in track.events)
    assert all(e.t >= 500 for e in track.events)
    print("✓ test_echo_synth_from_melody OK")


def test_schedule_reduces_active_layers_over_time():
    state = _boss_fight_state()
    arrangement = arrangement_planner_node(state)["arrangement"]
    schedule = arrangement.layer_schedule
    available = {l.instrument_id for l in arrangement.layers}

    counts = []
    for bar in range(0, state["structure"].total_bars, 4):
        active = active_layers_at_bar(schedule, bar, available)
        counts.append(len(active))

    assert max(counts) > min(counts), "debe haber variación de capas activas"
    print(f"  layer counts by quartile: {counts}")
    print("✓ test_schedule_reduces_active_layers_over_time OK")


if __name__ == "__main__":
    test_registry_has_echo_synth()
    test_bars_per_chord_faster_under_tension()
    test_harmony_drop_has_short_chords()
    test_layer_schedule_adds_and_removes()
    test_filter_events_by_schedule()
    test_echo_synth_from_melody()
    test_schedule_reduces_active_layers_over_time()
    print("\n✓ All phase 5b tests passed")
