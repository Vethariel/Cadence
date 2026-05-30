"""Genera perfiles de inspiración abstractos a partir del corpus MIDI local.

Uso:
    uv run python -m cadence.analysis.build_inspiration_profiles
    uv run python -m cadence.analysis.build_inspiration_profiles --output examples/inspiration_profiles.json
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from datetime import datetime, UTC
from pathlib import Path
from statistics import mean

from music21 import chord, converter, note

from cadence.analysis.benchmark_profiles import ARCHETYPE_DEFS
from cadence.analysis.midi_benchmark import EXAMPLES_DIR, analyze_midi
from cadence.music.composition_archetypes import COMPOSITION_ARCHETYPES, policy_family


DEFAULT_OUTPUT = Path(__file__).with_name("inspiration_profiles.json")

_TARGET_KEYS = (
    "layers_active_mean",
    "layers_active_max",
    "melody_notes_per_bar",
    "melody_leap_ratio",
    "melody_rest_ratio",
    "chord_changes_per_bar",
    "register_octaves_mean",
)

_NAME_RULES: tuple[tuple[str, str], ...] = (
    ("aquatic", "sparse_loop"),
    ("sweden", "sparse_loop"),
    ("lavender", "sparse_loop"),
    ("corridors", "sparse_loop"),
    ("corridor", "moderate_cinematic"),
    ("to zanarkand", "moderate_cinematic"),
    ("grandma", "moderate_cinematic"),
    ("gerudo", "moderate_cinematic"),
    ("milf", "moderate_cinematic"),
    ("bad apple", "dense_dance"),
    ("spider dance", "dense_dance"),
    ("u.n. owen", "dense_dance"),
    ("stardust speedway", "dense_dance"),
    ("big blue", "energetic_game"),
    ("sparkmandrill", "energetic_game"),
    ("kraid", "energetic_game"),
    ("vampire killer", "compact_action"),
    ("contra", "compact_action"),
    ("doom", "industrial_combat"),
    ("quake", "industrial_combat"),
    ("destati", "orchestral_boss"),
    ("gwyn", "orchestral_boss"),
    ("asgore", "orchestral_boss"),
    ("megalith", "hybrid_epic"),
    ("halo", "hybrid_epic"),
    ("dearly beloved", "menu_theme"),
    ("prelude", "menu_theme"),
    ("mgs", "stealth_tension"),
    ("unatco", "stealth_tension"),
    ("beneath the mask", "lofi_downtempo"),
    (" 1am", "lofi_downtempo"),
    ("1pm", "lofi_downtempo"),
)


def _nonzero_list(values: list[float], eps: float = 1e-9) -> bool:
    return any(abs(float(v)) > eps for v in values)


def _safe_stdev(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mu = mean(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return var ** 0.5


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int((len(sorted_values) - 1) * q)
    return float(sorted_values[idx])


def _range(values: list[float]) -> list[float]:
    if not values:
        return [0.0, 0.0]
    lo = round(min(values), 3)
    hi = round(max(values), 3)
    return [lo, hi]


def _style_cues(metrics: dict[str, list[float]]) -> list[str]:
    cues: list[str] = []
    layers_hi = metrics.get("layers_active_mean", [0.0, 0.0])[1]
    melody_hi = metrics.get("melody_notes_per_bar", [0.0, 0.0])[1]
    leaps_hi = metrics.get("melody_leap_ratio", [0.0, 0.0])[1]
    rests_hi = metrics.get("melody_rest_ratio", [0.0, 0.0])[1]
    harmony_hi = metrics.get("chord_changes_per_bar", [0.0, 0.0])[1]

    if layers_hi >= 6:
        cues.append("stack_denso_multicapa")
    elif layers_hi <= 3:
        cues.append("stack_compacto_o_sparse")
    else:
        cues.append("stack_medio_controlado")

    if melody_hi >= 10:
        cues.append("melodia_muy_activa")
    elif melody_hi <= 5:
        cues.append("melodia_espaciada")
    else:
        cues.append("melodia_moderada")

    if leaps_hi >= 0.4:
        cues.append("saltos_amplios")
    elif leaps_hi <= 0.2:
        cues.append("movimiento_conjunto")

    if rests_hi >= 0.2:
        cues.append("fraseo_con_respiros")
    else:
        cues.append("fraseo_continuo")

    if harmony_hi >= 0.9:
        cues.append("ritmo_armonico_rapido")
    elif harmony_hi <= 0.4:
        cues.append("ritmo_armonico_lento")

    cues.append("evitar_copia_literal_de_melodias")
    return cues


def _metrics_payload(
    refs: list[str],
    metrics_by_file: dict[str, object],
    inspiration_by_file: dict[str, dict],
    *,
    label: str,
    description: str,
) -> dict:
    target_metrics: dict[str, list[float]] = {}
    for key in _TARGET_KEYS:
        vals = [float(getattr(metrics_by_file[r], key, 0.0)) for r in refs]
        target_metrics[key] = _range(vals)

    rhythm_signature_16 = [
        round(mean(inspiration_by_file[r]["rhythm_signature_16"][i] for r in refs), 4)
        for i in range(16)
    ]

    interval_keys = (
        "step_1_2",
        "skip_3_4",
        "leap_5_7",
        "leap_8_plus",
        "ascending_ratio",
        "descending_ratio",
    )
    melody_interval_histogram = {
        k: round(mean(float(inspiration_by_file[r]["melody_interval_histogram"].get(k, 0.0)) for r in refs), 4)
        for k in interval_keys
    }

    roles = ("melody", "bass", "pad", "countermelody")
    role_register_ranges: dict[str, dict[str, float]] = {}
    for role in roles:
        lows = [inspiration_by_file[r]["role_register_ranges"].get(role, {}).get("min", 0.0) for r in refs]
        highs = [inspiration_by_file[r]["role_register_ranges"].get(role, {}).get("max", 0.0) for r in refs]
        if any(v > 0 for v in lows + highs):
            role_register_ranges[role] = {
                "min": round(mean(v for v in lows if v > 0), 2) if any(v > 0 for v in lows) else 0.0,
                "max": round(mean(v for v in highs if v > 0), 2) if any(v > 0 for v in highs) else 0.0,
            }

    cadence_types = ("authentic_like", "plagal_like", "deceptive_like", "half_like", "suspended_like")
    cadence_tendencies = {
        c: round(mean(float(inspiration_by_file[r]["cadence_tendencies"].get(c, 0.0)) for r in refs), 4)
        for c in cadence_types
    }

    layer_roles = ("melody", "bass", "pad", "countermelody", "drums", "fx")
    layer_timeline_template = {}
    for role in layer_roles:
        vecs = [inspiration_by_file[r]["layer_timeline_template"].get(role, [0.0, 0.0, 0.0, 0.0]) for r in refs]
        avg_vec = [
            round(mean(float(v[i]) for v in vecs), 4) for i in range(4)
        ]
        if _nonzero_list(avg_vec):
            layer_timeline_template[role] = avg_vec

    # Harmonic rhythm deep
    harmonic_rhythm_deep = {
        "chord_hold_beats_mean": round(mean(float(inspiration_by_file[r]["harmonic_rhythm_deep"]["chord_hold_beats_mean"]) for r in refs), 4),
        "chord_hold_beats_stdev": round(mean(float(inspiration_by_file[r]["harmonic_rhythm_deep"]["chord_hold_beats_stdev"]) for r in refs), 4),
        "chord_change_density_curve_4q": [
            round(mean(float(inspiration_by_file[r]["harmonic_rhythm_deep"]["chord_change_density_curve_4q"][i]) for r in refs), 4)
            for i in range(4)
        ],
    }

    # Dynamics profile
    dynamics_profile = {
        "velocity_mean": round(mean(float(inspiration_by_file[r]["dynamics_profile"]["velocity_mean"]) for r in refs), 4),
        "velocity_stdev": round(mean(float(inspiration_by_file[r]["dynamics_profile"]["velocity_stdev"]) for r in refs), 4),
        "dynamic_range_p90_p10": round(mean(float(inspiration_by_file[r]["dynamics_profile"]["dynamic_range_p90_p10"]) for r in refs), 4),
        "accent_on_strong_beat_ratio": round(mean(float(inspiration_by_file[r]["dynamics_profile"]["accent_on_strong_beat_ratio"]) for r in refs), 4),
    }

    # Motivicity signature
    contour_keys = ("ascending", "descending", "arch", "zigzag", "static")
    contour_hist = {
        k: round(mean(float(inspiration_by_file[r]["motivicity_signature"]["contour_hist"].get(k, 0.0)) for r in refs), 4)
        for k in contour_keys
    }
    motif_repeat_ratio_4 = round(
        mean(float(inspiration_by_file[r]["motivicity_signature"]["motif_repeat_ratio_4"]) for r in refs),
        4,
    )
    ngram_counter: Counter[str] = Counter()
    for r in refs:
        for ng in inspiration_by_file[r]["motivicity_signature"].get("top_interval_ngrams_4", []):
            ngram_counter[str(ng)] += 1
    top_ngrams = [k for k, _ in ngram_counter.most_common(6)]
    motivicity_signature = {
        "motif_repeat_ratio_4": motif_repeat_ratio_4,
        "top_interval_ngrams_4": top_ngrams,
        "contour_hist": contour_hist,
    }

    return {
        "label": label,
        "description": description,
        "reference_count": len(refs),
        "references_used": refs,
        "target_metrics": target_metrics,
        "rhythm_signature_16": rhythm_signature_16,
        "melody_interval_histogram": melody_interval_histogram,
        "role_register_ranges": role_register_ranges,
        "cadence_tendencies": cadence_tendencies,
        "layer_timeline_template": layer_timeline_template,
        "harmonic_rhythm_deep": harmonic_rhythm_deep,
        "dynamics_profile": dynamics_profile,
        "motivicity_signature": motivicity_signature,
        "style_cues": _style_cues(target_metrics),
    }


def _guess_archetype_from_name(file_name: str) -> str:
    name = file_name.lower().replace("_", " ")
    for marker, archetype in _NAME_RULES:
        if marker in name:
            return archetype
    return "default_game"


def _role_from_name(part_name: str) -> str:
    name = (part_name or "").lower()
    if any(k in name for k in ("drum", "kick", "snare", "perc")):
        return "drums"
    if "bass" in name:
        return "bass"
    if any(k in name for k in ("pad", "string", "choir")):
        return "pad"
    if any(k in name for k in ("counter", "response")):
        return "countermelody"
    if any(k in name for k in ("fx", "rise", "sweep")):
        return "fx"
    if any(k in name for k in ("lead", "melody")):
        return "melody"
    return "melody"


def _extract_inspiration(path: Path) -> dict:
    score = converter.parse(str(path))
    parts = list(score.parts) if score.parts else [score]
    flat = score.flatten()
    total_bars = max(1.0, float(flat.duration.quarterLength) / 4.0)

    # rhythm_signature_16
    rhythm_bins = [0.0] * 16
    onsets = 0
    for el in flat.notes:
        offset_q = float(el.offset)
        slot = int(round((offset_q % 4.0) * 4.0)) % 16
        rhythm_bins[slot] += 1.0
        onsets += 1
    if onsets > 0:
        rhythm_signature_16 = [round(v / onsets, 4) for v in rhythm_bins]
    else:
        rhythm_signature_16 = rhythm_bins

    # melody_interval_histogram (lead heuristic)
    lead_notes = []
    for p in parts:
        pname = str(p.partName or p.id or "").lower()
        if "lead" in pname or "melody" in pname:
            lead_notes = [n for n in p.flatten().notes if isinstance(n, note.Note)]
            if len(lead_notes) >= 8:
                break
    if not lead_notes:
        lead_notes = [n for n in flat.notes if isinstance(n, note.Note)]
    lead_notes = sorted(lead_notes, key=lambda n: float(n.offset))
    intervals = [
        int(lead_notes[i].pitch.midi - lead_notes[i - 1].pitch.midi)
        for i in range(1, len(lead_notes))
    ]
    abs_intervals = [abs(i) for i in intervals]
    n_int = max(1, len(abs_intervals))
    melody_interval_histogram = {
        "step_1_2": round(sum(1 for x in abs_intervals if 1 <= x <= 2) / n_int, 4),
        "skip_3_4": round(sum(1 for x in abs_intervals if 3 <= x <= 4) / n_int, 4),
        "leap_5_7": round(sum(1 for x in abs_intervals if 5 <= x <= 7) / n_int, 4),
        "leap_8_plus": round(sum(1 for x in abs_intervals if x >= 8) / n_int, 4),
        "ascending_ratio": round(sum(1 for x in intervals if x > 0) / n_int, 4),
        "descending_ratio": round(sum(1 for x in intervals if x < 0) / n_int, 4),
    }

    # motivicity_signature
    interval_ngrams = []
    if len(intervals) >= 4:
        interval_ngrams = [tuple(intervals[i : i + 4]) for i in range(len(intervals) - 3)]
    ng_counter = Counter(interval_ngrams)
    repeated = sum(c for _, c in ng_counter.items() if c > 1)
    total_ngrams = max(1, len(interval_ngrams))
    motif_repeat_ratio_4 = round(repeated / total_ngrams, 4)
    top_interval_ngrams_4 = ["[" + ",".join(str(int(x)) for x in ng) + "]" for ng, _ in ng_counter.most_common(6)]

    contour_hist = {"ascending": 0, "descending": 0, "arch": 0, "zigzag": 0, "static": 0}
    if len(lead_notes) >= 5:
        pitch_seq = [int(n.pitch.midi) for n in lead_notes]
        for i in range(len(pitch_seq) - 4):
            w = pitch_seq[i : i + 5]
            diffs = [w[j + 1] - w[j] for j in range(4)]
            if all(d > 0 for d in diffs):
                contour_hist["ascending"] += 1
            elif all(d < 0 for d in diffs):
                contour_hist["descending"] += 1
            elif diffs[0] > 0 and diffs[1] > 0 and diffs[2] < 0 and diffs[3] < 0:
                contour_hist["arch"] += 1
            elif diffs[0] * diffs[1] < 0 and diffs[1] * diffs[2] < 0:
                contour_hist["zigzag"] += 1
            else:
                contour_hist["static"] += 1
    contour_total = max(1, sum(contour_hist.values()))
    contour_hist = {k: round(v / contour_total, 4) for k, v in contour_hist.items()}

    # role_register_ranges + layer timeline template
    role_pitches: dict[str, list[int]] = {
        "melody": [], "bass": [], "pad": [], "countermelody": [], "drums": [], "fx": [],
    }
    role_quartile_activity = {
        "melody": [0, 0, 0, 0],
        "bass": [0, 0, 0, 0],
        "pad": [0, 0, 0, 0],
        "countermelody": [0, 0, 0, 0],
        "drums": [0, 0, 0, 0],
        "fx": [0, 0, 0, 0],
    }
    quartile_bars = max(1, int(total_bars / 4))

    for p in parts:
        role = _role_from_name(str(p.partName or p.id or ""))
        events = p.flatten().notes
        for el in events:
            if isinstance(el, note.Note):
                role_pitches[role].append(int(el.pitch.midi))
                bar = int(float(el.offset) // 4)
                q = min(3, bar // quartile_bars)
                role_quartile_activity[role][q] += 1
            elif isinstance(el, chord.Chord):
                for pt in el.pitches:
                    role_pitches[role].append(int(pt.midi))
                bar = int(float(el.offset) // 4)
                q = min(3, bar // quartile_bars)
                role_quartile_activity[role][q] += 1

    role_register_ranges = {}
    for role, pitches in role_pitches.items():
        if pitches:
            role_register_ranges[role] = {
                "min": float(min(pitches)),
                "max": float(max(pitches)),
            }

    layer_timeline_template = {}
    for role, vec in role_quartile_activity.items():
        total = sum(vec)
        if total > 0:
            layer_timeline_template[role] = [round(v / total, 4) for v in vec]
        else:
            layer_timeline_template[role] = [0.0, 0.0, 0.0, 0.0]

    # cadence_tendencies (heurística de raíces de acordes al final)
    chords = [el for el in flat.notes if isinstance(el, chord.Chord)]
    cadence_tendencies = {
        "authentic_like": 0.0,
        "plagal_like": 0.0,
        "deceptive_like": 0.0,
        "half_like": 0.0,
        "suspended_like": 0.0,
    }
    if len(chords) >= 2:
        pen = int(chords[-2].root().pitchClass) if chords[-2].root() else 0
        last = int(chords[-1].root().pitchClass) if chords[-1].root() else 0
        motion = (last - pen) % 12
        if motion in (7, 5):
            cadence_tendencies["authentic_like"] = 1.0
        elif motion in (5,):
            cadence_tendencies["plagal_like"] = 1.0
        elif motion in (9,):
            cadence_tendencies["deceptive_like"] = 1.0
        elif motion in (2,):
            cadence_tendencies["half_like"] = 1.0
        else:
            cadence_tendencies["suspended_like"] = 1.0

    # harmonic_rhythm_deep
    chord_holds = []
    chord_bar_counts = [0, 0, 0, 0]
    quartile_bars = max(1, int(total_bars / 4))
    for ch in chords:
        chord_holds.append(float(ch.duration.quarterLength) / 1.0)
        bar = int(float(ch.offset) // 4)
        q = min(3, bar // quartile_bars)
        chord_bar_counts[q] += 1
    if chord_holds:
        hold_mean = round(mean(chord_holds), 4)
        hold_stdev = round(_safe_stdev(chord_holds), 4)
    else:
        hold_mean = 0.0
        hold_stdev = 0.0
    q_norm = [round(c / max(1, quartile_bars), 4) for c in chord_bar_counts]
    harmonic_rhythm_deep = {
        "chord_hold_beats_mean": hold_mean,
        "chord_hold_beats_stdev": hold_stdev,
        "chord_change_density_curve_4q": q_norm,
    }

    # dynamics_profile
    velocities = []
    strong_beat_accents = 0
    strong_beat_events = 0
    for el in flat.notes:
        if isinstance(el, note.Note):
            vel = el.volume.velocity if el.volume.velocity is not None else 80
            velocities.append(float(vel))
            beat_in_bar = float(el.offset) % 4.0
            is_strong = abs(beat_in_bar - 0.0) < 1e-3 or abs(beat_in_bar - 2.0) < 1e-3
            if is_strong:
                strong_beat_events += 1
                if vel >= 95:
                    strong_beat_accents += 1
        elif isinstance(el, chord.Chord):
            vel = el.volume.velocity if el.volume.velocity is not None else 80
            velocities.append(float(vel))
    if velocities:
        sv = sorted(velocities)
        p10 = _quantile(sv, 0.10)
        p90 = _quantile(sv, 0.90)
        dynamics_profile = {
            "velocity_mean": round(mean(velocities), 4),
            "velocity_stdev": round(_safe_stdev(velocities), 4),
            "dynamic_range_p90_p10": round(max(0.0, p90 - p10), 4),
            "accent_on_strong_beat_ratio": round(
                strong_beat_accents / max(1, strong_beat_events), 4,
            ),
        }
    else:
        dynamics_profile = {
            "velocity_mean": 0.0,
            "velocity_stdev": 0.0,
            "dynamic_range_p90_p10": 0.0,
            "accent_on_strong_beat_ratio": 0.0,
        }

    return {
        "rhythm_signature_16": rhythm_signature_16,
        "melody_interval_histogram": melody_interval_histogram,
        "role_register_ranges": role_register_ranges,
        "cadence_tendencies": cadence_tendencies,
        "layer_timeline_template": layer_timeline_template,
        "harmonic_rhythm_deep": harmonic_rhythm_deep,
        "dynamics_profile": dynamics_profile,
        "motivicity_signature": {
            "motif_repeat_ratio_4": motif_repeat_ratio_4,
            "top_interval_ngrams_4": top_interval_ngrams_4,
            "contour_hist": contour_hist,
        },
    }


def build_profiles() -> dict:
    metrics_by_file = {}
    inspiration_by_file = {}
    for mid in sorted(EXAMPLES_DIR.glob("*.mid")):
        metrics_by_file[mid.name] = analyze_midi(mid)
        inspiration_by_file[mid.name] = _extract_inspiration(mid)

    profiles: dict[str, dict] = {}
    # 1) Compatibilidad con arquetipos benchmark previos.
    for raw_archetype, spec in ARCHETYPE_DEFS.items():
        archetype = "orchestral_boss" if raw_archetype == "boss_orchestral" else raw_archetype
        refs = [r for r in spec["references"] if r in metrics_by_file]
        if not refs:
            continue
        profiles[archetype] = _metrics_payload(
            refs,
            metrics_by_file,
            inspiration_by_file,
            label=spec["label"],
            description=spec["description"],
        )

    # 2) Clasificación nominal del corpus ampliado para cubrir los 12 arquetipos.
    grouped: dict[str, list[str]] = {a: [] for a in COMPOSITION_ARCHETYPES}
    for file_name in sorted(metrics_by_file.keys()):
        grouped.setdefault(_guess_archetype_from_name(file_name), []).append(file_name)

    for archetype in COMPOSITION_ARCHETYPES:
        if archetype in profiles:
            continue
        refs = grouped.get(archetype, [])
        if refs:
            profiles[archetype] = _metrics_payload(
                refs,
                metrics_by_file,
                inspiration_by_file,
                label=archetype.replace("_", " ").title(),
                description="Perfil derivado por clasificación nominal del corpus local.",
            )

    # 3) Fallback por familia de política para cubrir cualquier hueco restante.
    for archetype in COMPOSITION_ARCHETYPES:
        if archetype in profiles:
            continue
        fam = policy_family(archetype)
        same_family = [
            a for a in COMPOSITION_ARCHETYPES
            if a in profiles and a != archetype and policy_family(a) == fam
        ]
        if not same_family:
            same_family = [a for a in COMPOSITION_ARCHETYPES if a in profiles]
        if not same_family:
            continue

        merged_metrics: dict[str, list[float]] = {}
        refs_used: list[str] = []
        for key in _TARGET_KEYS:
            lows = [profiles[a]["target_metrics"][key][0] for a in same_family]
            highs = [profiles[a]["target_metrics"][key][1] for a in same_family]
            merged_metrics[key] = [round(min(lows), 3), round(max(highs), 3)]
        for a in same_family:
            refs_used.extend(profiles[a].get("references_used", []))
        refs_used = sorted(set(refs_used))

        # Agrega también rasgos de inspiración de la familia.
        rhythm_signature_16 = [
            round(mean(float(profiles[a].get("rhythm_signature_16", [0.0] * 16)[i]) for a in same_family), 4)
            for i in range(16)
        ]
        interval_keys = (
            "step_1_2",
            "skip_3_4",
            "leap_5_7",
            "leap_8_plus",
            "ascending_ratio",
            "descending_ratio",
        )
        melody_interval_histogram = {
            k: round(
                mean(float(profiles[a].get("melody_interval_histogram", {}).get(k, 0.0)) for a in same_family),
                4,
            )
            for k in interval_keys
        }
        cadence_keys = ("authentic_like", "plagal_like", "deceptive_like", "half_like", "suspended_like")
        cadence_tendencies = {
            k: round(
                mean(float(profiles[a].get("cadence_tendencies", {}).get(k, 0.0)) for a in same_family),
                4,
            )
            for k in cadence_keys
        }
        harmonic_rhythm_deep = {
            "chord_hold_beats_mean": round(
                mean(float(profiles[a].get("harmonic_rhythm_deep", {}).get("chord_hold_beats_mean", 0.0)) for a in same_family),
                4,
            ),
            "chord_hold_beats_stdev": round(
                mean(float(profiles[a].get("harmonic_rhythm_deep", {}).get("chord_hold_beats_stdev", 0.0)) for a in same_family),
                4,
            ),
            "chord_change_density_curve_4q": [
                round(
                    mean(
                        float(profiles[a].get("harmonic_rhythm_deep", {}).get("chord_change_density_curve_4q", [0.0, 0.0, 0.0, 0.0])[i])
                        for a in same_family
                    ),
                    4,
                )
                for i in range(4)
            ],
        }
        dynamics_profile = {
            "velocity_mean": round(
                mean(float(profiles[a].get("dynamics_profile", {}).get("velocity_mean", 0.0)) for a in same_family),
                4,
            ),
            "velocity_stdev": round(
                mean(float(profiles[a].get("dynamics_profile", {}).get("velocity_stdev", 0.0)) for a in same_family),
                4,
            ),
            "dynamic_range_p90_p10": round(
                mean(float(profiles[a].get("dynamics_profile", {}).get("dynamic_range_p90_p10", 0.0)) for a in same_family),
                4,
            ),
            "accent_on_strong_beat_ratio": round(
                mean(float(profiles[a].get("dynamics_profile", {}).get("accent_on_strong_beat_ratio", 0.0)) for a in same_family),
                4,
            ),
        }
        contour_keys = ("ascending", "descending", "arch", "zigzag", "static")
        contour_hist = {
            k: round(
                mean(float(profiles[a].get("motivicity_signature", {}).get("contour_hist", {}).get(k, 0.0)) for a in same_family),
                4,
            )
            for k in contour_keys
        }
        motif_repeat_ratio_4 = round(
            mean(float(profiles[a].get("motivicity_signature", {}).get("motif_repeat_ratio_4", 0.0)) for a in same_family),
            4,
        )
        ng_counter: Counter[str] = Counter()
        for a in same_family:
            for ng in profiles[a].get("motivicity_signature", {}).get("top_interval_ngrams_4", []):
                ng_counter[str(ng)] += 1
        motivicity_signature = {
            "motif_repeat_ratio_4": motif_repeat_ratio_4,
            "top_interval_ngrams_4": [k for k, _ in ng_counter.most_common(6)],
            "contour_hist": contour_hist,
        }
        roles = ("melody", "bass", "pad", "countermelody", "drums", "fx")
        layer_timeline_template = {
            role: [
                round(
                    mean(
                        float(profiles[a].get("layer_timeline_template", {}).get(role, [0.0, 0.0, 0.0, 0.0])[i])
                        for a in same_family
                    ),
                    4,
                )
                for i in range(4)
            ]
            for role in roles
        }
        role_register_ranges = {}
        for role in ("melody", "bass", "pad", "countermelody"):
            mins = [
                float(profiles[a].get("role_register_ranges", {}).get(role, {}).get("min", 0.0))
                for a in same_family
                if float(profiles[a].get("role_register_ranges", {}).get(role, {}).get("min", 0.0)) > 0
            ]
            maxs = [
                float(profiles[a].get("role_register_ranges", {}).get(role, {}).get("max", 0.0))
                for a in same_family
                if float(profiles[a].get("role_register_ranges", {}).get(role, {}).get("max", 0.0)) > 0
            ]
            if mins or maxs:
                role_register_ranges[role] = {
                    "min": round(mean(mins), 2) if mins else 0.0,
                    "max": round(mean(maxs), 2) if maxs else 0.0,
                }

        profiles[archetype] = {
            "label": archetype.replace("_", " ").title(),
            "description": (
                "Perfil sintetizado desde arquetipos de la misma familia "
                f"({fam}) para asegurar cobertura total."
            ),
            "reference_count": len(refs_used),
            "references_used": refs_used,
            "target_metrics": merged_metrics,
            "style_cues": _style_cues(merged_metrics),
            "synthesized_from": same_family,
            "rhythm_signature_16": rhythm_signature_16,
            "melody_interval_histogram": melody_interval_histogram,
            "role_register_ranges": role_register_ranges,
            "cadence_tendencies": cadence_tendencies,
            "layer_timeline_template": layer_timeline_template,
            "harmonic_rhythm_deep": harmonic_rhythm_deep,
            "dynamics_profile": dynamics_profile,
            "motivicity_signature": motivicity_signature,
        }

    return {
        "version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "derived_from_local_midi_metrics",
        "profiles": profiles,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Ruta de salida JSON (default: cadence/analysis/inspiration_profiles.json)",
    )
    args = parser.parse_args()

    payload = build_profiles()
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Perfiles escritos en {args.output}")


if __name__ == "__main__":
    main()

