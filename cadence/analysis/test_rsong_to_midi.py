"""Tests de conversión .rsong → MIDI."""

import json
import tempfile
from pathlib import Path

from music21 import converter

from cadence.analysis.rsong_to_midi import convert_rsong_to_midi, convert_rsong_file


def _minimal_rsong() -> dict:
    return {
        "header": {
            "title": "test_song",
            "bpm": 120,
            "time_signature": [4, 4],
            "duration_ms": 4000,
            "total_bars": 4,
        },
        "tracks": [
            {
                "id": "melody",
                "instrument": "Lead",
                "instrument_id": "melody",
                "midi_channel": 0,
                "role": "lead",
                "events": [
                    {"t": 0, "type": "note", "pitch": 72, "duration_ms": 500, "velocity": 100, "beat_index": 0, "section": "drop"},
                    {"t": 500, "type": "note", "pitch": 74, "duration_ms": 500, "velocity": 90, "beat_index": 4, "section": "drop"},
                    {"t": 1000, "type": "note", "pitch": 76, "duration_ms": 500, "velocity": 95, "beat_index": 8, "section": "drop"},
                ],
            },
            {
                "id": "drums",
                "instrument": "Drums",
                "instrument_id": "drums",
                "midi_channel": 9,
                "role": "rhythm",
                "events": [
                    {"t": 0, "type": "drum_hit", "pitch": 36, "duration_ms": 100, "velocity": 110, "beat_index": 0, "section": "drop"},
                    {"t": 500, "type": "drum_hit", "pitch": 38, "duration_ms": 100, "velocity": 100, "beat_index": 4, "section": "drop"},
                ],
            },
            {
                "id": "pad",
                "instrument": "Pad",
                "instrument_id": "pad",
                "midi_channel": 2,
                "role": "pad",
                "events": [
                    {"t": 0, "type": "chord", "pitch": 60, "duration_ms": 2000, "velocity": 50, "beat_index": 0, "section": "drop"},
                    {"t": 0, "type": "chord", "pitch": 64, "duration_ms": 2000, "velocity": 50, "beat_index": 0, "section": "drop"},
                    {"t": 0, "type": "chord", "pitch": 67, "duration_ms": 2000, "velocity": 50, "beat_index": 0, "section": "drop"},
                ],
            },
        ],
    }


def test_convert_minimal_rsong():
    with tempfile.TemporaryDirectory() as tmp:
        rsong_path = Path(tmp) / "test.rsong"
        mid_path = Path(tmp) / "test.mid"
        rsong_path.write_text(json.dumps(_minimal_rsong()), encoding="utf-8")

        result = convert_rsong_file(rsong_path, mid_path)
        assert result.exists()
        assert result.stat().st_size > 100

        score = converter.parse(str(result))
        parts = list(score.parts)
        assert len(parts) == 3
        total_notes = sum(
            1 for p in parts for el in p.flatten().notes
        )
        assert total_notes >= 8
        print(f"  parts={len(parts)}  notes={total_notes}")
        print("✓ test_convert_minimal_rsong OK")


def test_track_names_preserved():
    with tempfile.TemporaryDirectory() as tmp:
        mid_path = Path(tmp) / "test.mid"
        convert_rsong_to_midi(_minimal_rsong(), mid_path)
        score = converter.parse(str(mid_path))
        names = [str(p.partName or "") for p in score.parts]
        assert any("Melody" in n or "melody" in n.lower() for n in names)
        assert any("Drum" in n for n in names)
        print(f"  track names: {names}")
        print("✓ test_track_names_preserved OK")


if __name__ == "__main__":
    test_convert_minimal_rsong()
    test_track_names_preserved()
    print("\n✓ All rsong_to_midi tests passed")
