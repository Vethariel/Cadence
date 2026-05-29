"""
Benchmark: compara MIDIs de referencia contra métricas objetivo de Cadence.

Uso:
    uv run python -m cadence.analysis.midi_benchmark
    uv run python -m cadence.analysis.midi_benchmark examples/ASGORE.mid
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import statistics
import sys

from music21 import chord, converter, note

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

# Objetivos derivados del análisis de referencias (promedio ASGORE + Spider Dance)
TARGETS = {
    "layers_active_mean": 7.0,
    "layers_active_max": 11.0,
    "unique_pitches": 20.0,
    "melody_notes_per_bar": 8.0,
    "melody_bar_repeat_ratio": 0.15,
    "melody_leap_ratio": 0.25,
    "chord_changes_per_bar": 0.7,
    "register_octaves_mean": 4.5,
    "velocity_stdev": 20.0,
    "notes_per_bar_stdev": 25.0,
}


@dataclass
class MidiMetrics:
    file: str
    parts: int = 0
    echo_layers: int = 0
    duration_bars: float = 0.0
    total_notes: int = 0
    unique_pitches: int = 0
    velocity_stdev: float = 0.0
    notes_per_bar_mean: float = 0.0
    notes_per_bar_stdev: float = 0.0
    bar_repeat_ratio: float = 0.0
    layers_active_mean: float = 0.0
    layers_active_max: int = 0
    chord_changes_per_bar: float = 0.0
    register_octaves_mean: float = 0.0
    melody_track: str = ""
    melody_notes_per_bar: float = 0.0
    melody_unique_pitches: int = 0
    melody_bar_repeat_ratio: float = 0.0
    melody_leap_ratio: float = 0.0
    melody_rest_ratio: float = 0.0
    gaps: dict[str, float] = field(default_factory=dict)


def _find_lead_part(parts: list) -> tuple[str, list] | None:
    best: tuple[str, list] | None = None
    best_score = 0
    for p in parts:
        notes = [el for el in p.flatten().notes if isinstance(el, note.Note)]
        if len(notes) < 20:
            continue
        in_range = sum(1 for n in notes if 60 <= n.pitch.midi <= 96)
        score = in_range * len(notes)
        if score > best_score:
            best_score = score
            best = (str(p.partName or p.id)[:40], notes)
    return best


def analyze_midi(path: Path) -> MidiMetrics:
    score = converter.parse(str(path))
    flat = score.flatten()
    parts = list(score.parts) if score.parts else [score]
    m = MidiMetrics(file=path.name, parts=len(parts))

    m.echo_layers = sum(
        1 for p in parts if "echo" in (p.partName or "").lower()
    )
    m.duration_bars = float(flat.duration.quarterLength) / 4

    pitches: list[int] = []
    velocities: list[int] = []
    bar_notes: dict[int, int] = defaultdict(int)
    bar_patterns: dict[int, list] = defaultdict(list)
    bar_registers: dict[int, set] = defaultdict(set)

    for el in flat.notesAndRests:
        off = float(el.offset)
        bar = int(off // 4)
        if isinstance(el, note.Note):
            m.total_notes += 1
            pitches.append(el.pitch.midi)
            bar_notes[bar] += 1
            bar_patterns[bar].append((round((off % 4) * 4, 2), el.pitch.midi))
            bar_registers[bar].add(el.pitch.midi // 12)
            if el.volume.velocity is not None:
                velocities.append(el.volume.velocity)
        elif isinstance(el, chord.Chord):
            bar_notes[bar] += len(el.pitches)
            for p in el.pitches:
                pitches.append(p.midi)
                bar_registers[bar].add(p.midi // 12)
            if el.volume.velocity is not None:
                velocities.append(el.volume.velocity)

    densities = list(bar_notes.values())
    m.unique_pitches = len(set(pitches))
    m.velocity_stdev = statistics.stdev(velocities) if len(velocities) > 1 else 0.0
    m.notes_per_bar_mean = statistics.mean(densities) if densities else 0.0
    m.notes_per_bar_stdev = statistics.stdev(densities) if len(densities) > 1 else 0.0

    bars_sorted = sorted(bar_patterns.keys())
    repeats = sum(
        1 for i in range(1, len(bars_sorted))
        if bar_patterns[bars_sorted[i]] == bar_patterns[bars_sorted[i - 1]]
    )
    m.bar_repeat_ratio = repeats / max(1, len(bars_sorted) - 1)

    bar_active: dict[int, int] = defaultdict(int)
    for p in parts:
        active = {
            int(el.offset // 4)
            for el in p.flatten().notesAndRests
            if isinstance(el, (note.Note, chord.Chord))
        }
        for b in active:
            bar_active[b] += 1
    layer_vals = list(bar_active.values())
    m.layers_active_mean = statistics.mean(layer_vals) if layer_vals else 0.0
    m.layers_active_max = max(layer_vals) if layer_vals else 0

    chords = [el for el in flat.notes if isinstance(el, chord.Chord)]
    chord_bars = len({int(c.offset // 4) for c in chords})
    total_bars = max(int(m.duration_bars), 1)
    m.chord_changes_per_bar = chord_bars / total_bars

    reg_spread = [len(bar_registers[b]) for b in sorted(bar_registers.keys())]
    m.register_octaves_mean = statistics.mean(reg_spread) if reg_spread else 0.0

    lead = _find_lead_part(parts)
    if lead:
        name, notes = lead
        m.melody_track = name
        notes.sort(key=lambda n: n.offset)
        mel_bars: dict[int, list] = defaultdict(list)
        for n in notes:
            mel_bars[int(n.offset // 4)].append(
                (round((n.offset % 4) * 4, 2), n.pitch.midi)
            )
        mel_bar_list = sorted(mel_bars.keys())
        mel_repeats = sum(
            1 for i in range(1, len(mel_bar_list))
            if mel_bars[mel_bar_list[i]] == mel_bars[mel_bar_list[i - 1]]
        )
        intervals = [
            abs(notes[i].pitch.midi - notes[i - 1].pitch.midi)
            for i in range(1, len(notes))
        ]
        gaps = [
            max(0, notes[i].offset - (notes[i - 1].offset + notes[i - 1].duration.quarterLength))
            for i in range(1, len(notes))
        ]
        m.melody_notes_per_bar = len(notes) / max(1, len(mel_bar_list))
        m.melody_unique_pitches = len({n.pitch.midi for n in notes})
        m.melody_bar_repeat_ratio = mel_repeats / max(1, len(mel_bar_list) - 1)
        m.melody_leap_ratio = sum(1 for i in intervals if i > 4) / max(1, len(intervals))
        m.melody_rest_ratio = sum(1 for g in gaps if g >= 0.5) / max(1, len(gaps))

    # Gaps vs targets (negative = below target)
    m.gaps = {
        "layers_active_mean": m.layers_active_mean - TARGETS["layers_active_mean"],
        "melody_notes_per_bar": m.melody_notes_per_bar - TARGETS["melody_notes_per_bar"],
        "melody_unique_pitches": m.melody_unique_pitches - TARGETS["unique_pitches"],
        "chord_changes_per_bar": m.chord_changes_per_bar - TARGETS["chord_changes_per_bar"],
        "register_octaves_mean": m.register_octaves_mean - TARGETS["register_octaves_mean"],
    }
    return m


def cadence_baseline() -> dict[str, float]:
    """Estimación de métricas actuales de Cadence (sin LLM en melodía)."""
    return {
        "layers_active_mean": 4.5,
        "layers_active_max": 5,
        "melody_notes_per_bar": 4.0,
        "melody_unique_pitches": 7.0,
        "melody_bar_repeat_ratio": 0.0,  # A/A'/B evita repetición exacta
        "melody_leap_ratio": 0.05,
        "chord_changes_per_bar": 0.25,  # 1 acorde / 4 compases
        "register_octaves_mean": 3.0,
        "velocity_stdev": 26.0,
        "notes_per_bar_stdev": 7.0,
        "echo_layers": 0,
    }


def print_report(metrics: list[MidiMetrics]) -> None:
    print("=" * 72)
    print("CADENCE vs REFERENCIAS — benchmark MIDI")
    print("=" * 72)
    base = cadence_baseline()

    header = f"{'métrica':<28} {'Cadence':>10} {'target':>10}"
    for m in metrics:
        header += f" {m.file[:14]:>14}"
    print(header)
    print("-" * len(header))

    rows = [
        ("capas activas (media)", "layers_active_mean", None),
        ("capas activas (máx)", "layers_active_max", None),
        ("notas melódicas / bar", "melody_notes_per_bar", None),
        ("pitches únicos melodía", "melody_unique_pitches", "unique_pitches"),
        ("cambios acorde / bar", "chord_changes_per_bar", None),
        ("octavas activas / bar", "register_octaves_mean", None),
        ("variación densidad/bar", "notes_per_bar_stdev", None),
        ("capas echo", "echo_layers", None),
    ]

    for label, key, target_key in rows:
        tk = target_key or key
        line = f"{label:<28} {base.get(key, 0):>10.1f} {TARGETS.get(tk, 0):>10.1f}"
        for m in metrics:
            val = getattr(m, key, None)
            if val is None:
                if key == "melody_unique_pitches":
                    val = m.melody_unique_pitches
                elif key == "melody_notes_per_bar":
                    val = m.melody_notes_per_bar
                elif key == "echo_layers":
                    val = m.echo_layers
            line += f" {val:>14.1f}"
        print(line)

    print("\n── pista melódica principal por referencia ──")
    for m in metrics:
        print(f"  {m.file}: {m.melody_track or '?'}")
        print(
            f"    leaps={m.melody_leap_ratio:.0%}  "
            f"bar_repeat={m.melody_bar_repeat_ratio:.0%}  "
            f"rests={m.melody_rest_ratio:.0%}"
        )


def main(argv: list[str] | None = None) -> None:
    paths = [Path(p) for p in (argv or sys.argv[1:])] if (argv or sys.argv[1:]) else sorted(EXAMPLES_DIR.glob("*.mid"))
    if not paths:
        print(f"No se encontraron .mid en {EXAMPLES_DIR}")
        sys.exit(1)
    metrics = [analyze_midi(p) for p in paths]
    print_report(metrics)


if __name__ == "__main__":
    main()
