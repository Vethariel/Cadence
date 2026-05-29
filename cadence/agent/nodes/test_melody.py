from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import (
    UserIntent, TechnicalProposal, SongStructure, Track
)
from cadence.agent.nodes.melody import melody_composer_node

def test_melody():
    state = {
        "messages": [HumanMessage(content="canción oscura para jefe final")],
        "intent": UserIntent(
            raw_prompt="canción oscura para jefe final",
            knowledge_level="non_technical",
            use_case="game",
            mood="dark, aggressive",
            style_tags=["techno", "dubstep", "dark"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=145,
            time_signature=[4, 4],
            key="F",
            mode="minor",
            genre_tags=["techno", "dubstep", "dark industrial"],
            energy_level=5,
            structure=["intro", "build-up", "drop", "breakdown", "climax", "outro"],
            reasoning="145 BPM para urgencia...",
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "breakdown", "climax", "outro"],
            bars_per_section={"intro": 8, "build-up": 16, "drop": 32,
                              "breakdown": 16, "climax": 32, "outro": 8},
            total_bars=112,
            estimated_duration_ms=184827,
        ),
        "tracks": [
            Track(id="drums", instrument="Drum Kit",
                  midi_channel=9, role="rhythm", events=[]),
            Track(id="bass", instrument="Bass Synth",
                  midi_channel=1, role="bass", events=[]),
        ],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    result = melody_composer_node(state)
    tracks = result["tracks"]
    melody = next(t for t in tracks if t.id == "melody")

    print(f"total tracks    : {len(tracks)}")
    print(f"melody events   : {len(melody.events)}")
    print(f"first note      : t={melody.events[0].t}ms  pitch={melody.events[0].pitch}  vel={melody.events[0].velocity}  section={melody.events[0].section}")
    print(f"last note       : t={melody.events[-1].t}ms  section={melody.events[-1].section}")

    sections_covered = set(e.section for e in melody.events)
    print(f"sections covered: {sorted(sections_covered)}")

    assert len(tracks) == 3, f"Esperados 3 tracks, got {len(tracks)}"
    assert len(melody.events) > 0

    # Todas las notas deben estar en rango MIDI válido
    for e in melody.events:
        assert 21 <= e.pitch <= 108, f"Pitch fuera de rango: {e.pitch}"

    # drop o climax deben tener melodía
    assert "drop" in sections_covered or "climax" in sections_covered

    # drums y bass se preservan
    ids = [t.id for t in tracks]
    assert "drums" in ids
    assert "bass" in ids

    print("✓ test_melody OK")

if __name__ == "__main__":
    test_melody()
