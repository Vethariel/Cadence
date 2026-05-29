"""
Benchmark: compara MIDIs de referencia y salidas Cadence (.rsong → .mid).

Evalúa cada pieza contra rangos del arquetipo de estilo (no un promedio global).
Incluye índice de riqueza instrumental.

Uso:
    uv run python -m cadence.analysis.midi_benchmark
    uv run python -m cadence.analysis.midi_benchmark examples/ASGORE.mid
    uv run python -m cadence.analysis.midi_benchmark output/*.rsong
    uv run python -m cadence.analysis.midi_benchmark --compare
    uv run python -m cadence.analysis.midi_benchmark output/foo.rsong --style dense_dance
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
import json
import statistics
import sys
import tempfile

from music21 import chord, converter, note

from cadence.analysis.benchmark_profiles import (
    ARCHETYPE_DEFS,
    METRIC_LABELS,
    RICHNESS_COMPONENT_LABELS,
    StyleEvaluation,
    build_style_profiles,
    evaluate_against_style,
    format_meta_summary,
    infer_archetype,
    infer_archetype_from_path,
    load_rsong_meta,
)
from cadence.analysis.rsong_to_midi import convert_rsong_file

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


@dataclass
class MidiMetrics:
    file: str
    source_path: str = ""
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
    archetype: str = ""
    evaluation: StyleEvaluation | None = None


def _find_lead_part(parts: list) -> tuple[str, list] | None:
    preferred_names = ("lead melody", "melody", "lead synth", "lead")
    for preferred in preferred_names:
        for p in parts:
            name = str(p.partName or p.id or "").lower()
            if preferred not in name:
                continue
            if "echo" in name or "arp" in name or "counter" in name:
                continue
            notes = [el for el in p.flatten().notes if isinstance(el, note.Note)]
            if len(notes) >= 8:
                return (str(p.partName or p.id)[:40], notes)

    best: tuple[str, list] | None = None
    best_score = 0
    for p in parts:
        name = str(p.partName or p.id or "").lower()
        if any(x in name for x in ("arp", "drum", "bass", "pad", "perc", "fx", "stab")):
            continue
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
    m = MidiMetrics(file=path.name, source_path=str(path))
    m.parts = len(parts)

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

    return m


def resolve_input_path(path: Path, temp_dir: Path | None = None) -> tuple[Path, Path | None]:
    if path.suffix.lower() == ".rsong":
        if temp_dir:
            mid = temp_dir / path.with_suffix(".mid").name
        else:
            mid = path.with_suffix(".mid")
        convert_rsong_file(path, mid)
        if temp_dir:
            return mid, mid
        return mid, None
    return path, None


def collect_default_paths() -> list[Path]:
    refs = sorted(EXAMPLES_DIR.glob("*.mid"))
    cadence = sorted(OUTPUT_DIR.glob("*.rsong"))
    return refs + cadence


def _is_reference(m: MidiMetrics) -> bool:
    return EXAMPLES_DIR.name in m.source_path or (
        m.file.endswith(".mid") and "cadence" not in m.file.lower()
    )


def _is_cadence_output(m: MidiMetrics) -> bool:
    return m.file.endswith(".rsong") or "cadence" in m.file.lower()


def print_archetype_catalog(
    profiles: dict,
    metrics_by_file: dict[str, MidiMetrics],
) -> None:
    print("\n── Arquetipos de referencia (rangos, no promedios) ──")
    for arch_id, profile in profiles.items():
        refs = ", ".join(profile.references)
        print(f"\n  [{arch_id}] {profile.label}")
        print(f"    refs: {refs}")
        print(f"    {profile.description}")
        key_metrics = (
            "layers_active_mean", "melody_notes_per_bar",
            "melody_leap_ratio", "instrumental_richness",
        )
        for key in ("layers_active_mean", "melody_notes_per_bar", "parts", "register_octaves_mean"):
            if key not in profile.ranges:
                continue
            lo, hi = profile.ranges[key]
            ref_span = " | ".join(
                f"{name.split('.')[0]}={getattr(metrics_by_file[name], key, 0):.1f}"
                for name in profile.references
                if name in metrics_by_file
            )
            print(f"    {METRIC_LABELS.get(key, key):<28} rango {lo:.1f}–{hi:.1f}  ({ref_span})")


def print_style_evaluation(m: MidiMetrics) -> None:
    ev = m.evaluation
    if not ev:
        return

    status = "✓" if ev.fit_ratio >= 0.6 else "✗"
    print(f"\n{'─' * 72}")
    print(f"{status} {m.file}")
    print(f"  arquetipo: {ev.profile.label} ({ev.profile.id})")
    if ev.meta_summary:
        print(f"  meta: {ev.meta_summary}")

    ir = ev.instrumental_richness
    ir_ok = "✓" if ir.in_style_range else "○"
    print(
        f"  {ir_ok} riqueza instrumental: {ir.score:.0f}/100  "
        f"(banda estilo {ir.reference_lo:.0f}–{ir.reference_hi:.0f})"
    )
    comp_parts = [
        f"{RICHNESS_COMPONENT_LABELS.get(k, k)}={v:.0f}"
        for k, v in ir.components.items()
    ]
    print(f"      componentes: {', '.join(comp_parts)}")
    print(f"  ajuste al estilo: {ev.fit_ratio:.0%} ({sum(c.in_range for c in ev.checks)}/{len(ev.checks)} métricas en rango)")
    print(f"  melodía: {m.melody_track or '?'}  leaps={m.melody_leap_ratio:.0%}  rests={m.melody_rest_ratio:.0%}")

    print(f"\n  {'métrica':<28} {'valor':>8} {'rango':>14} {'refs':>12} {'ok':>4}")
    for check in ev.checks:
        mark = "✓" if check.in_range else "·"
        rng = f"{check.lo:.1f}–{check.hi:.1f}"
        if check.key in ("melody_leap_ratio", "melody_rest_ratio"):
            val_s = f"{check.value:.0%}"
            rng = f"{check.lo:.0%}–{check.hi:.0%}"
            ref_s = check.reference_span.replace(".0", "").replace(".1", "")
        else:
            val_s = f"{check.value:.1f}"
            ref_s = check.reference_span
        print(f"  {check.label:<28} {val_s:>8} {rng:>14} {ref_s:>12} {mark:>4}")


def print_reference_table(metrics: list[MidiMetrics]) -> None:
    refs = [m for m in metrics if _is_reference(m)]
    if not refs:
        return

    print("\n── Corpus de referencia ──")
    header = f"{'archivo':<22} {'capas':>6} {'mel/bar':>7} {'leaps':>6} {'rests':>6} {'oct':>5} {'pistas':>6}"
    print(header)
    print("-" * len(header))
    for m in refs:
        arch = infer_archetype_from_path(Path(m.file))
        print(
            f"{m.file[:22]:<22} {m.layers_active_mean:>6.1f} "
            f"{m.melody_notes_per_bar:>7.1f} {m.melody_leap_ratio:>5.0%} "
            f"{m.melody_rest_ratio:>5.0%} {m.register_octaves_mean:>5.1f} {m.parts:>6}"
            f"  → {arch}"
        )


def print_report(
    metrics: list[MidiMetrics],
    profiles: dict,
    metrics_by_file: dict[str, MidiMetrics],
) -> None:
    print("=" * 72)
    print("CADENCE — benchmark por estilo (rangos de referencia)")
    print("=" * 72)

    print_reference_table(metrics)
    print_archetype_catalog(profiles, metrics_by_file)

    cadence = [m for m in metrics if _is_cadence_output(m)]
    if cadence:
        print("\n── Evaluación Cadence ──")
        for m in cadence:
            print_style_evaluation(m)
    else:
        print("\n  (sin salidas Cadence — solo corpus de referencia)")


def attach_evaluations(
    metrics: list[MidiMetrics],
    profiles: dict,
    metrics_by_file: dict[str, MidiMetrics],
    *,
    style_override: str | None = None,
    path_meta: dict[str, dict] | None = None,
) -> None:
    path_meta = path_meta or {}
    for m in metrics:
        if not _is_cadence_output(m):
            continue

        if style_override and style_override in profiles:
            arch_id = style_override
            meta_summary = f"arquetipo forzado: {style_override}"
        else:
            meta = path_meta.get(m.file, {})
            arch_id = infer_archetype(
                use_case=meta.get("use_case"),
                energy_level=meta.get("energy_level"),
                genre_tags=meta.get("genre_tags"),
                title=meta.get("title", m.file),
            )
            meta_summary = format_meta_summary(meta) if meta else ""

        profile = profiles[arch_id]
        m.archetype = arch_id
        m.evaluation = evaluate_against_style(
            m,
            profile,
            meta_summary=meta_summary,
            metrics_by_file=metrics_by_file,
        )


def load_reference_metrics() -> dict[str, MidiMetrics]:
    """Métricas del corpus de examples/ — base para rangos por arquetipo."""
    refs: dict[str, MidiMetrics] = {}
    for path in sorted(EXAMPLES_DIR.glob("*.mid")):
        m = analyze_midi(path)
        refs[m.file] = m
    return refs


def main(argv: list[str] | None = None) -> None:
    args = list(argv or sys.argv[1:])
    compare_mode = "--compare" in args
    style_override: str | None = None

    if "--style" in args:
        idx = args.index("--style")
        if idx + 1 < len(args):
            style_override = args[idx + 1]
        args = [a for i, a in enumerate(args) if i not in (idx, idx + 1)]

    if compare_mode:
        args = [a for a in args if a != "--compare"]

    if args:
        paths = [Path(p) for p in args]
    elif compare_mode or OUTPUT_DIR.exists():
        paths = collect_default_paths()
    else:
        paths = sorted(EXAMPLES_DIR.glob("*.mid"))

    if not paths:
        print(f"No se encontraron .mid en {EXAMPLES_DIR} ni .rsong en {OUTPUT_DIR}")
        sys.exit(1)

    metrics: list[MidiMetrics] = []
    path_meta: dict[str, dict] = {}

    with tempfile.TemporaryDirectory(prefix="cadence_mid_") as tmp:
        temp_root = Path(tmp)
        for path in paths:
            if not path.exists():
                print(f"  [skip] no existe: {path}")
                continue
            midi_path, _ = resolve_input_path(
                path, temp_root if path.suffix.lower() == ".rsong" else None,
            )
            m = analyze_midi(midi_path)
            if path.suffix.lower() == ".rsong":
                m.file = path.name
                m.source_path = str(path)
                try:
                    path_meta[path.name] = load_rsong_meta(path)
                except (json.JSONDecodeError, OSError):
                    pass
            metrics.append(m)

    if not metrics:
        print("No se pudo analizar ningún archivo.")
        sys.exit(1)

    metrics_by_file = load_reference_metrics()
    for m in metrics:
        metrics_by_file[m.file] = m

    existing = {m.file for m in metrics}
    for ref_m in metrics_by_file.values():
        if ref_m.file.endswith(".mid") and ref_m.file not in existing:
            metrics.append(ref_m)

    profiles = build_style_profiles(metrics_by_file)

    attach_evaluations(
        metrics, profiles, metrics_by_file,
        style_override=style_override,
        path_meta=path_meta,
    )

    print_report(metrics, profiles, metrics_by_file)


if __name__ == "__main__":
    main()
