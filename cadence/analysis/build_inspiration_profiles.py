"""Genera perfiles de inspiración abstractos a partir del corpus MIDI local.

Uso:
    uv run python -m cadence.analysis.build_inspiration_profiles
    uv run python -m cadence.analysis.build_inspiration_profiles --output examples/inspiration_profiles.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path

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
    *,
    label: str,
    description: str,
) -> dict:
    target_metrics: dict[str, list[float]] = {}
    for key in _TARGET_KEYS:
        vals = [float(getattr(metrics_by_file[r], key, 0.0)) for r in refs]
        target_metrics[key] = _range(vals)
    return {
        "label": label,
        "description": description,
        "reference_count": len(refs),
        "references_used": refs,
        "target_metrics": target_metrics,
        "style_cues": _style_cues(target_metrics),
    }


def _guess_archetype_from_name(file_name: str) -> str:
    name = file_name.lower().replace("_", " ")
    for marker, archetype in _NAME_RULES:
        if marker in name:
            return archetype
    return "default_game"


def build_profiles() -> dict:
    metrics_by_file = {}
    for mid in sorted(EXAMPLES_DIR.glob("*.mid")):
        metrics_by_file[mid.name] = analyze_midi(mid)

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

