"""
Convierte archivos .rsong de Cadence a MIDI estándar para análisis comparativo.

Uso:
    uv run python -m cadence.analysis.rsong_to_midi output/cancion.rsong
    uv run python -m cadence.analysis.rsong_to_midi output/*.rsong -o output/midis/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from midiutil import MIDIFile

# GM program por instrument_id (paridad con cadence-ui/src/audio/gm-programs.js)
INSTRUMENT_PROGRAM: dict[str, int] = {
    "melody": 80,
    "countermelody": 53,
    "echo_synth": 88,
    "arp_synth": 12,
    "bass": 38,
    "pad": 89,
    "fx_riser": 119,
    "chord_stab": 62,
}

# Fallback por rol si no hay instrument_id conocido
ROLE_PROGRAM: dict[str, int | None] = {
    "lead": 80,
    "bass": 38,
    "pad": 89,
    "fx": 80,
    "rhythm": None,
}

# Nombres de pista reconocibles por music21 / midi_benchmark
TRACK_DISPLAY_NAMES: dict[str, str] = {
    "melody": "Lead Melody",
    "countermelody": "Counter Melody",
    "echo_synth": "Echo Synth",
    "arp_synth": "Arp Synth",
    "drums": "Drums",
    "bass": "Bass",
    "pad": "Pad",
    "perc_aux": "Perc Aux",
    "fx_riser": "FX Riser",
    "chord_stab": "Chord Stab",
}


def load_rsong(path: Path | str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ms_to_quarters(ms: float, bpm: float) -> float:
    return (ms / 1000.0) * (bpm / 60.0)


def _track_program(track: dict) -> int | None:
    if track.get("gm_program") is not None:
        return int(track["gm_program"])
    iid = track.get("instrument_id") or track.get("id")
    if iid and iid in INSTRUMENT_PROGRAM:
        return INSTRUMENT_PROGRAM[iid]
    role = track.get("role", "lead")
    return ROLE_PROGRAM.get(role)


def _track_channel(track: dict) -> int:
    role = track.get("role", "lead")
    if role == "rhythm" or track.get("id") == "drums" or track.get("instrument_id") == "perc_aux":
        return 9
    channel = track.get("midi_channel", 0)
    return min(15, max(0, channel))


def _track_name(track: dict) -> str:
    tid = track.get("id") or track.get("instrument_id") or "track"
    return TRACK_DISPLAY_NAMES.get(tid, track.get("instrument") or tid)


def convert_rsong_to_midi(
    rsong: dict,
    output_path: Path | str,
    *,
    include_meta: bool = True,
) -> Path:
    """
    Escribe un archivo MIDI multitrack desde datos .rsong.

    Cada track de rsong → una pista MIDI con nombre, canal y eventos note/drum_hit/chord.
    """
    output_path = Path(output_path)
    tracks = rsong.get("tracks") or []
    if not tracks:
        raise ValueError("El .rsong no contiene tracks.")

    header = rsong.get("header", {})
    bpm = float(header.get("bpm", 120))
    ts = header.get("time_signature", [4, 4])
    ts_num, ts_den = int(ts[0]), int(ts[1])

    mf = MIDIFile(
        numTracks=len(tracks),
        removeDuplicates=False,
        deinterleave=False,
        ticks_per_quarternote=480,
    )

    for track_idx, track in enumerate(tracks):
        name = _track_name(track)
        channel = _track_channel(track)

        mf.addTrackName(track_idx, 0, name)
        if track_idx == 0:
            mf.addTempo(track_idx, 0, bpm)
            mf.addTimeSignature(track_idx, 0, ts_num, ts_den, 24, 8)

        program = _track_program(track)
        if program is not None and channel != 9:
            mf.addProgramChange(track_idx, channel, 0, program)

        events = sorted(track.get("events") or [], key=lambda e: (e["t"], e.get("beat_index", 0)))
        for event in events:
            etype = event.get("type", "note")
            if etype == "rest":
                continue

            pitch = int(event.get("pitch", 60))
            velocity = max(1, min(127, int(event.get("velocity", 80))))
            start = ms_to_quarters(float(event["t"]), bpm)
            duration = max(0.05, ms_to_quarters(float(event.get("duration_ms", 100)), bpm))

            mf.addNote(
                track_idx,
                channel,
                pitch,
                start,
                duration,
                velocity,
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        mf.writeFile(f)

    if include_meta:
        meta_path = output_path.with_suffix(".midi_meta.json")
        meta = {
            "source_rsong": rsong.get("header", {}).get("title"),
            "bpm": bpm,
            "duration_ms": header.get("duration_ms"),
            "tracks": [t.get("id") for t in tracks],
            "strategies": rsong.get("game_meta", {}).get("strategies"),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    return output_path


def convert_rsong_file(
    input_path: Path | str,
    output_path: Path | str | None = None,
) -> Path:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if input_path.suffix.lower() != ".rsong":
        raise ValueError(f"Se esperaba .rsong, recibido: {input_path}")

    rsong = load_rsong(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(".mid")
    return convert_rsong_to_midi(rsong, output_path)


def main(argv: list[str] | None = None) -> None:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args and args[0] in ("-h", "--help") else 1)

    output_dir: Path | None = None
    paths: list[Path] = []
    i = 0
    while i < len(args):
        if args[i] in ("-o", "--output") and i + 1 < len(args):
            output_dir = Path(args[i + 1])
            i += 2
        else:
            paths.append(Path(args[i]))
            i += 1

    for path in paths:
        if not path.exists():
            print(f"  [skip] no existe: {path}")
            continue
        out = (output_dir / path.with_suffix(".mid").name) if output_dir else None
        result = convert_rsong_file(path, out)
        print(f"  {path.name} → {result}")


if __name__ == "__main__":
    main()
