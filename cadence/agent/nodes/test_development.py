"""Tests Fase 5a: DevelopmentPlan + fraseo + countermelody."""

from langchain_core.messages import HumanMessage

import cadence.instruments  # noqa: F401
from cadence.schemas.song_state import (
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
    RhythmEvent,
)
from cadence.agent.nodes.development import development_planner_node
from cadence.agent.nodes.strategy import strategy_planner_node
from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.agent.nodes.orchestra import compose_orchestra_node
from cadence.music.development_theory import build_development_plan, compute_generation_seed
from cadence.music.melody_phrases import apply_development_to_notes, phrases_to_events
from cadence.agent.nodes.melody import MelodyNote, MelodyPhrase
from cadence.instruments import list_instruments


def _boss_state():
    narrative = SongNarrative(
        logline="Boss fight",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4, 2],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
            ),
            SectionIntent(
                id="build-up", narrative_role="tension", emotional_target="urgency",
                density=0.7, harmonic_tension=0.6, rhythmic_complexity=0.6,
                transition_out="riser",
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
            ),
            SectionIntent(
                id="breakdown", narrative_role="reflection", emotional_target="dread",
                density=0.15, harmonic_tension=0.3, rhythmic_complexity=0.2,
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="boss fight dark")],
        "intent": UserIntent(
            raw_prompt="boss fight dark", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "build-up", "drop", "breakdown"],
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "breakdown"],
            bars_per_section={"intro": 4, "build-up": 8, "drop": 8, "breakdown": 4},
            total_bars=24,
            estimated_duration_ms=41000,
        ),
        "narrative": narrative,
        "generation_seed": 0,
        "tracks": [],
    }


def test_development_planner_varies_by_role():
    state = _boss_state()
    state.update(strategy_planner_node(state))
    result = development_planner_node(state)
    dev = result["development"]
    assert dev.generation_seed == state["generation_seed"] > 0
    by_id = {s.section_id: s for s in dev.sections}
    assert by_id["intro"].transform == "introduce"
    assert by_id["drop"].transform == "climax"
    assert by_id["breakdown"].transform == "fragment"
    assert by_id["drop"].motif_variant != by_id["intro"].motif_variant
    print("✓ test_development_planner_varies_by_role OK")


def test_generation_seed_deterministic():
    s1 = compute_generation_seed("boss fight", 80)
    s2 = compute_generation_seed("boss fight", 80)
    s3 = compute_generation_seed("other prompt", 80)
    assert s1 == s2
    assert s1 != s3
    print("✓ test_generation_seed_deterministic OK")


def test_phrases_cycle_with_development():
    phrase_a = MelodyPhrase(
        bars=2,
        pattern=[
            MelodyNote(scale_degree=0, duration_steps=4, velocity=80),
            MelodyNote(scale_degree=2, duration_steps=4, velocity=85),
            MelodyNote(scale_degree=4, duration_steps=4, velocity=90),
            MelodyNote(scale_degree=2, duration_steps=4, velocity=85),
        ],
    )
    phrase_b = MelodyPhrase(
        bars=2,
        pattern=[
            MelodyNote(scale_degree=4, duration_steps=4, velocity=90),
            MelodyNote(scale_degree=2, duration_steps=4, velocity=85),
            MelodyNote(scale_degree=0, duration_steps=4, velocity=75),
            MelodyNote(scale_degree=0, duration_steps=4, velocity=70, is_rest=True),
        ],
    )
    dev = build_development_plan(
        sections=["drop"],
        global_motif=[0, 2, 4],
        generation_seed=42,
    ).sections[0]
    scale = [65, 67, 68, 70, 72, 73, 75]

    events, _, _ = phrases_to_events(
        phrases=[phrase_a, phrase_b],
        section="drop",
        total_bars=8,
        start_t=0.0,
        bpm=120,
        scale_pitches=scale,
        beat_index_start=0,
        development=dev,
    )
    assert len(events) > 10
    pitches = [e.pitch for e in events]
    assert len(set(pitches)) >= 4
    print("✓ test_phrases_cycle_with_development OK")


def test_apply_development_changes_degrees():
    notes = [
        MelodyNote(scale_degree=0, duration_steps=4, velocity=80),
        MelodyNote(scale_degree=2, duration_steps=4, velocity=80),
    ]
    dev = build_development_plan(["s"], [0, 2, 4], generation_seed=1).sections[0]
    dev = dev.model_copy(update={"transform": "sequence_up"})
    c0 = apply_development_to_notes(notes, dev, cycle_idx=0, phrase_idx=0)
    c1 = apply_development_to_notes(notes, dev, cycle_idx=1, phrase_idx=0)
    assert c0[0].scale_degree != c1[0].scale_degree
    print("✓ test_apply_development_changes_degrees OK")


def test_countermelody_in_arrangement_and_compose():
    state = _boss_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["development"] = development_planner_node(state)["development"]
    arr = arrangement_planner_node(state)["arrangement"]
    layer_ids = [l.instrument_id for l in arr.layers]
    assert "countermelody" in layer_ids
    assert "countermelody" in list_instruments()

    det_layers = [l for l in arr.layers if l.instrument_id != "melody"]
    from cadence.schemas.song_state import ArrangementPlan
    state["arrangement"] = ArrangementPlan(layers=det_layers, required_layers=["drums", "bass"])
    result = compose_orchestra_node(state)
    ids = {t.id for t in result["tracks"]}
    assert "countermelody" in ids
    cm = next(t for t in result["tracks"] if t.id == "countermelody")
    assert len(cm.events) > 0
    assert all(e.pitch >= 72 for e in cm.events[:5])
    print("✓ test_countermelody_in_arrangement_and_compose OK")


def test_phrase_bar_repeat_lower_than_old_loop():
    """Frases A/B deben producir menos repetición consecutiva que un loop 1-bar."""
    phrase = MelodyPhrase(
        bars=2,
        pattern=[
            MelodyNote(scale_degree=i % 7, duration_steps=4, velocity=80)
            for i in range(4)
        ],
    )
    scale = [60, 62, 63, 65, 67, 68, 70]
    events, _, _ = phrases_to_events(
        phrases=[phrase, phrase.model_copy(update={
            "pattern": [
                MelodyNote(scale_degree=(i + 2) % 7, duration_steps=4, velocity=85)
                for i in range(4)
            ]
        })],
        section="test",
        total_bars=8,
        start_t=0.0,
        bpm=120,
        scale_pitches=scale,
        beat_index_start=0,
        development=None,
    )
    ms_per_bar = 2000.0
    bar_pitches: dict[int, list[int]] = {}
    for e in events:
        bar_pitches.setdefault(int(e.t / ms_per_bar), []).append(e.pitch)
    bars = sorted(bar_pitches.keys())
    repeats = sum(
        1 for i in range(1, len(bars))
        if bar_pitches[bars[i]] == bar_pitches[bars[i - 1]]
    )
    assert repeats < len(bars) - 1
    print("✓ test_phrase_bar_repeat_lower_than_old_loop OK")


if __name__ == "__main__":
    test_development_planner_varies_by_role()
    test_generation_seed_deterministic()
    test_phrases_cycle_with_development()
    test_apply_development_changes_degrees()
    test_countermelody_in_arrangement_and_compose()
    test_phrase_bar_repeat_lower_than_old_loop()
    print("\n✓ All phase 5a tests passed")
