from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import UserIntent, TechnicalProposal, SongStructure
from cadence.agent.nodes.rhythm import rhythm_engine_node

def test_rhythm():
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
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    result = rhythm_engine_node(state)
    tracks = result["tracks"]

    for track in tracks:
        print(f"\ntrack           : {track.id}")
        print(f"instrument      : {track.instrument}")
        print(f"role            : {track.role}")
        print(f"total events    : {len(track.events)}")
        print(f"first event     : t={track.events[0].t}ms  pitch={track.events[0].pitch}  vel={track.events[0].velocity}  section={track.events[0].section}")
        print(f"last event      : t={track.events[-1].t}ms  section={track.events[-1].section}")

    assert len(tracks) == 2
    assert tracks[0].id == "drums"
    assert tracks[1].id == "bass"
    assert len(tracks[0].events) > 0
    assert len(tracks[1].events) > 0

    # Verificar que los eventos cubren todas las secciones excepto breakdown en bass
    drum_sections = set(e.section for e in tracks[0].events)
    assert "drop" in drum_sections
    assert "climax" in drum_sections

    bass_sections = set(e.section for e in tracks[1].events)
    assert "breakdown" not in bass_sections, "El bajo debe descansar en breakdown"

    print("\n✓ test_rhythm OK")

if __name__ == "__main__":
    test_rhythm()
