import json
from pathlib import Path
from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import (
    UserIntent, TechnicalProposal, SongStructure,
    Track, RhythmEvent, ValidationResult,
)
from cadence.agent.nodes.exporter import export_node

def _make_event(t, pitch=65, section="drop"):
    return RhythmEvent(
        t=t, type="note", pitch=pitch,
        duration_ms=200, velocity=90,
        beat_index=t // 100, section=section,
    )

def test_exporter():
    state = {
        "messages": [HumanMessage(content="test")],
        "intent": UserIntent(
            raw_prompt="canción oscura para jefe final",
            knowledge_level="non_technical",
            use_case="game",
            mood="dark, aggressive",
            style_tags=["techno", "dubstep"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=145,
            time_signature=[4, 4],
            key="F",
            mode="minor",
            genre_tags=["techno", "dubstep"],
            energy_level=5,
            structure=["intro", "drop", "outro"],
            reasoning="test",
        ),
        "structure": SongStructure(
            sections=["intro", "drop", "outro"],
            bars_per_section={"intro": 4, "drop": 16, "outro": 4},
            total_bars=24,
            estimated_duration_ms=39669,
        ),
        "tracks": [
            Track(id="melody", instrument="Lead Synth",
                  midi_channel=0, role="lead",
                  events=[_make_event(i * 200, section="drop") for i in range(80)]),
            Track(id="drums",  instrument="Drum Kit",
                  midi_channel=9, role="rhythm",
                  events=[_make_event(i * 100, pitch=36, section="drop") for i in range(160)]),
            Track(id="bass",   instrument="Bass Synth",
                  midi_channel=1, role="bass",
                  events=[_make_event(i * 400, pitch=41, section="drop") for i in range(40)]),
        ],
        "validation_result": ValidationResult(
            score=1.0, errors=[], warnings=[], passed=True
        ),
        "retry_count": 0,
        "request_id": "test-export-req",
        "pipeline_trace": [],
        "export_path": None,
        "rsong_data": None,
    }

    result = export_node(state)
    export_path = Path(result["export_path"])
    rsong_data  = result["rsong_data"]

    print(f"export_path     : {export_path}")
    print(f"file exists     : {export_path.exists()}")
    print(f"title           : {rsong_data['header']['title']}")
    print(f"bpm             : {rsong_data['header']['bpm']}")
    print(f"key             : {rsong_data['header']['key']}")
    print(f"duration_ms     : {rsong_data['header']['duration_ms']}")
    print(f"cue_points      : {rsong_data['game_meta']['cue_points']}")
    print(f"loop_point_ms   : {rsong_data['game_meta']['loop_point_ms']}")
    print(f"intensity_curve : {rsong_data['game_meta']['intensity_curve']}")
    print(f"tracks          : {[t['id'] for t in rsong_data['tracks']]}")
    print(f"total events    : {sum(t['event_count'] for t in rsong_data['tracks'])}")

    # Verificar estructura del archivo
    assert export_path.exists()
    with open(export_path) as f:
        loaded = json.load(f)
    assert loaded["rsong_version"] == "1.0"
    assert loaded["generated_by"] == "cadence"
    assert len(loaded["tracks"]) == 3
    assert all("events" in t for t in loaded["tracks"])
    assert loaded["game_meta"]["loop_point_ms"] >= 0
    assert len(loaded["game_meta"]["intensity_curve"]) == 3
    assert len(loaded["game_meta"]["cue_points"]) == 3
    assert loaded["quality"]["quality_status"] == "passed"
    assert loaded["quality"]["request_id"] == "test-export-req"
    assert loaded["quality"]["generation_seed"] == 0
    assert loaded["quality"]["retry_count"] == 0
    assert "failed_checks" in loaded["quality"]
    assert loaded["validation"]["passed"] is True

    print("✓ test_exporter OK")

if __name__ == "__main__":
    test_exporter()
