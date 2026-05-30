"""Prompts de benchmark alineados con el corpus MIDI y arquetipos de referencia."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cadence.analysis.benchmark_profiles import ARCHETYPE_DEFS, infer_archetype

PROMPTS_PATH = Path(__file__).resolve().parents[2] / "examples" / "benchmark_prompts.json"


@dataclass(frozen=True)
class BenchmarkPrompt:
    id: str
    archetype: str
    label: str
    midi_refs: tuple[str, ...]
    prompt: str
    expected_use_case: str
    expected_energy: tuple[int, int]
    style_hints: tuple[str, ...]

    @property
    def export_title_hint(self) -> str:
        return f"cadence_{self.id}"


def load_benchmark_prompts(path: Path | None = None) -> list[BenchmarkPrompt]:
    data = json.loads((path or PROMPTS_PATH).read_text(encoding="utf-8"))
    out: list[BenchmarkPrompt] = []
    for item in data["prompts"]:
        exp = item.get("expected", {})
        energy = exp.get("energy_level", [3, 3])
        if isinstance(energy, list) and len(energy) >= 2:
            e_lo, e_hi = int(energy[0]), int(energy[1])
        else:
            e_lo = e_hi = int(energy) if isinstance(energy, int) else 3
        out.append(BenchmarkPrompt(
            id=item["id"],
            archetype=item["archetype"],
            label=item["label"],
            midi_refs=tuple(item.get("midi_refs", [])),
            prompt=item["prompt"],
            expected_use_case=exp.get("use_case", "game"),
            expected_energy=(e_lo, e_hi),
            style_hints=tuple(exp.get("style_hints", [])),
        ))
    return out


def prompt_by_archetype(archetype_id: str) -> BenchmarkPrompt | None:
    for p in load_benchmark_prompts():
        if p.archetype == archetype_id:
            return p
    return None


def infer_archetype_for_benchmark_prompt(bp: BenchmarkPrompt) -> str:
    """Arquetipo que el evaluador debería usar si el grafo respeta expected metadata."""
    e_mid = (bp.expected_energy[0] + bp.expected_energy[1]) // 2
    return infer_archetype(
        use_case=bp.expected_use_case,
        energy_level=e_mid,
        genre_tags=list(bp.style_hints),
        title=bp.export_title_hint,
    )


def match_benchmark_id(raw_prompt: str) -> str | None:
    """Si el prompt coincide con el catálogo, devuelve el id para export (cadence_<id>)."""
    norm = " ".join(raw_prompt.strip().lower().split())
    for bp in load_benchmark_prompts():
        if " ".join(bp.prompt.strip().lower().split()) == norm:
            return bp.id
    return None


def export_title_for_prompt(raw_prompt: str, use_case: str, mood: str) -> str:
    bid = match_benchmark_id(raw_prompt)
    if bid:
        return f"cadence_{bid}"
    mood_slug = mood[:12].replace(" ", "_") if mood else "track"
    return f"cadence_{use_case}_{mood_slug}"


def validate_prompt_catalog() -> list[str]:
    """Errores de alineación prompt ↔ arquetipo ↔ refs MIDI."""
    errors: list[str] = []
    for bp in load_benchmark_prompts():
        if bp.archetype not in ARCHETYPE_DEFS:
            errors.append(f"{bp.id}: arquetipo desconocido {bp.archetype}")
            continue
        refs = set(ARCHETYPE_DEFS[bp.archetype]["references"])
        for mid in bp.midi_refs:
            if mid not in refs:
                errors.append(
                    f"{bp.id}: {mid} no está en refs de {bp.archetype} ({refs})",
                )
        inferred = infer_archetype_for_benchmark_prompt(bp)
        if inferred != bp.archetype:
            errors.append(
                f"{bp.id}: infer={inferred} esperado={bp.archetype} "
                f"(use_case={bp.expected_use_case}, energy={bp.expected_energy}, "
                f"tags={bp.style_hints})",
            )
    return errors
