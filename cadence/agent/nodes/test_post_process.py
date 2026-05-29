"""Tests Fase 7: crescendo, humanize, post_process."""

from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import (
    RhythmEvent,
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    Track,
    UserIntent,
)
from cadence.agent.nodes.post_process import post_process_node
from cadence.music.crescendo import apply_crescendo, section_velocity_multipliers
from cadence.music.humanize import humanize_tracks
from cadence.agent.nodes.narrative_apply import section_intent_map


def _mock_state(tracks):
    narrative = SongNarrative(
        logline="Rise and fall",
        arc_type="rise-climax-fall",
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="calm",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
            ),
            SectionIntent(
                id="outro", narrative_role="release", emotional_target="calm",
                density=0.35, harmonic_tension=0.1, rhythmic_complexity=0.2,
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="test")],
        "intent": UserIntent(
            raw_prompt="test", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=120, key="C", mode="minor", structure=["intro", "drop", "outro"],
        ),
        "structure": SongStructure(
            sections=["intro", "drop", "outro"],
            bars_per_section={"intro": 4, "drop": 8, "outro": 4},
            total_bars=16,
            estimated_duration_ms=32000,
        ),
        "narrative": narrative,
        "generation_seed": 99,
        "tracks": tracks,
    }


def _note(t, section, vel=80, pitch=65):
    return RhythmEvent(
        t=t, type="note", pitch=pitch, duration_ms=200,
        velocity=vel, beat_index=0, section=section,
    )


def test_crescendo_boosts_climax_section():
    tracks = [
        Track(
            id="melody", instrument="Lead", role="lead",
            events=[
                _note(0, "intro", vel=80),
                _note(8000, "drop", vel=80),
                _note(24000, "outro", vel=80),
            ],
        ),
    ]
    state = _mock_state(tracks)
    intent_map = section_intent_map(state["narrative"])
    result = apply_crescendo(tracks, state["structure"], 120, intent_map)
    by_section = {e.section: e.velocity for e in result[0].events}
    assert by_section["drop"] > by_section["intro"]
    assert by_section["drop"] > by_section["outro"]
    print("✓ test_crescendo_boosts_climax_section OK")


def test_section_multipliers_follow_density():
    narrative = _mock_state([])["narrative"]
    mults = section_velocity_multipliers(
        ["intro", "drop", "outro"],
        section_intent_map(narrative),
    )
    assert mults["drop"] > mults["intro"]
    print("✓ test_section_multipliers_follow_density OK")


def test_humanize_adds_timing_jitter():
    tracks = [
        Track(
            id="melody", instrument="Lead", role="lead",
            events=[_note(i * 500, "drop") for i in range(20)],
        ),
    ]
    original_ts = [e.t for e in tracks[0].events]
    humanized = humanize_tracks(tracks, generation_seed=42)
    new_ts = [e.t for e in humanized[0].events]
    assert new_ts != original_ts
    assert all(t >= 0 for t in new_ts)
    assert new_ts == sorted(new_ts)
    print("✓ test_humanize_adds_timing_jitter OK")


def test_humanize_deterministic():
    tracks = [
        Track(
            id="melody", instrument="Lead", role="lead",
            events=[_note(i * 500, "drop") for i in range(10)],
        ),
    ]
    a = humanize_tracks(tracks, 7)[0].events
    b = humanize_tracks(tracks, 7)[0].events
    assert [e.t for e in a] == [e.t for e in b]
    assert [e.velocity for e in a] == [e.velocity for e in b]
    print("✓ test_humanize_deterministic OK")


def test_post_process_node_pipeline():
    tracks = [
        Track(
            id="melody", instrument="Lead", role="lead",
            events=[
                _note(i * 400, "intro", vel=70, pitch=60 + i % 4)
                for i in range(8)
            ] + [
                _note(3200 + i * 200, "drop", vel=70, pitch=65 + i % 5)
                for i in range(20)
            ],
        ),
        Track(
            id="drums", instrument="Drums", role="rhythm",
            events=[
                RhythmEvent(
                    t=i * 200, type="drum_hit", pitch=36,
                    duration_ms=100, velocity=90, beat_index=0, section="drop",
                )
                for i in range(30)
            ],
        ),
    ]
    state = _mock_state(tracks)
    result = post_process_node(state)
    processed = result["tracks"]
    melody = next(t for t in processed if t.id == "melody")
    intro_vel = [e.velocity for e in melody.events if e.section == "intro"]
    drop_vel = [e.velocity for e in melody.events if e.section == "drop"]
    assert sum(drop_vel) / len(drop_vel) > sum(intro_vel) / len(intro_vel)
    assert len({e.t for e in melody.events}) > 1
    print("✓ test_post_process_node_pipeline OK")


if __name__ == "__main__":
    test_crescendo_boosts_climax_section()
    test_section_multipliers_follow_density()
    test_humanize_adds_timing_jitter()
    test_humanize_deterministic()
    test_post_process_node_pipeline()
    print("\n✓ All phase 7 tests passed")
