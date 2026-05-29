"""
Perfiles de benchmark por estilo — rangos derivados de referencias, no promedios.

Cada arquetipo agrupa MIDIs de ejemplo con métricas medidas. Cadence se evalúa
contra el rango del arquetipo que coincide con use_case / energía / tags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from pathlib import Path

# ── Arquetipos y referencias ───────────────────────────────────

ARCHETYPE_DEFS: dict[str, dict] = {
    "sparse_loop": {
        "label": "Loop / ambiente",
        "references": ["Its_Pizza_Time.mid"],
        "description": "Pocas capas sostenidas, melodía espaciada, armonía clara.",
    },
    "moderate_cinematic": {
        "label": "Cutscene / moderado",
        "references": ["MILF.mid", "Its_Pizza_Time.mid"],
        "description": "Densidad media, cambios de acorde frecuentes, registro contenido.",
    },
    "dense_dance": {
        "label": "Battle / dance denso",
        "references": ["Bad Apple!!.mid", "UT_Spider_Dance_v2_Lu9.mid"],
        "description": "Melodía muy densa, saltos amplios, capas medias-altas.",
    },
    "energetic_game": {
        "label": "Boss energético / game action",
        "references": ["Energetic - good sound.mid"],
        "description": "Stack compacto (~4 capas), arp y counter densos, saltos altos.",
    },
    "boss_orchestral": {
        "label": "Boss / orquestal",
        "references": ["ASGORE.mid", "UT_Spider_Dance_v2_Lu9.mid"],
        "description": "Muchas capas simultáneas, registro amplio, melodía moderada.",
    },
}

# Métricas evaluadas contra rango del arquetipo
RANGE_METRICS = (
    "parts",
    "layers_active_mean",
    "layers_active_max",
    "echo_layers",
    "melody_notes_per_bar",
    "melody_unique_pitches",
    "melody_leap_ratio",
    "melody_rest_ratio",
    "chord_changes_per_bar",
    "register_octaves_mean",
    "notes_per_bar_stdev",
    "unique_pitches",
)

METRIC_LABELS: dict[str, str] = {
    "parts": "pistas MIDI",
    "layers_active_mean": "capas activas (media)",
    "layers_active_max": "capas activas (máx)",
    "echo_layers": "capas echo",
    "melody_notes_per_bar": "notas melódicas / bar",
    "melody_unique_pitches": "pitches únicos melodía",
    "melody_leap_ratio": "saltos melodía (>4 st)",
    "melody_rest_ratio": "silencios melodía",
    "chord_changes_per_bar": "cambios acorde / bar",
    "register_octaves_mean": "octavas activas / bar",
    "notes_per_bar_stdev": "variación densidad / bar",
    "unique_pitches": "pitches únicos (global)",
    "instrumental_richness": "riqueza instrumental",
}

# Pesos para índice de riqueza instrumental (0–100)
RICHNESS_COMPONENT_LABELS: dict[str, str] = {
    "parts": "pistas",
    "layers_active_mean": "capas μ",
    "layers_active_max": "capas máx",
    "echo_layers": "echo",
    "register_octaves_mean": "registro",
    "unique_pitches": "timbres",
    "chord_changes_per_bar": "armonía",
}

RICHNESS_WEIGHTS: dict[str, float] = {
    "parts": 0.12,
    "layers_active_mean": 0.28,
    "layers_active_max": 0.18,
    "echo_layers": 0.08,
    "register_octaves_mean": 0.14,
    "unique_pitches": 0.12,
    "chord_changes_per_bar": 0.08,
}


@dataclass
class StyleProfile:
    id: str
    label: str
    description: str
    references: list[str]
    ranges: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class MetricCheck:
    key: str
    label: str
    value: float
    lo: float
    hi: float
    in_range: bool
    reference_span: str = ""


@dataclass
class InstrumentalRichness:
    score: float
    components: dict[str, float]
    reference_lo: float
    reference_hi: float
    in_style_range: bool


@dataclass
class StyleEvaluation:
    profile: StyleProfile
    checks: list[MetricCheck]
    fit_ratio: float
    instrumental_richness: InstrumentalRichness
    meta_summary: str = ""


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _metric_range(values: list[float], padding: float = 0.12) -> tuple[float, float]:
    if not values:
        return (0.0, 1.0)
    lo, hi = min(values), max(values)
    if lo == hi:
        margin = max(abs(lo) * padding, 0.5)
        return lo - margin, hi + margin
    margin = (hi - lo) * padding
    return lo - margin, hi + margin


def build_style_profiles(
    metrics_by_file: dict[str, object],
) -> dict[str, StyleProfile]:
    """Construye rangos por arquetipo a partir de métricas medidas de referencias."""
    profiles: dict[str, StyleProfile] = {}

    for archetype_id, spec in ARCHETYPE_DEFS.items():
        ref_metrics = [
            metrics_by_file[name]
            for name in spec["references"]
            if name in metrics_by_file
        ]
        ranges: dict[str, tuple[float, float]] = {}
        for key in RANGE_METRICS:
            values = [getattr(m, key, 0.0) for m in ref_metrics]
            if values:
                ranges[key] = _metric_range(values)

        profiles[archetype_id] = StyleProfile(
            id=archetype_id,
            label=spec["label"],
            description=spec["description"],
            references=spec["references"],
            ranges=ranges,
        )

    return profiles


def _title_hint(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _tags_hint(tags: list[str]) -> set[str]:
    return {t.lower() for t in tags}


def infer_archetype(
    *,
    use_case: str | None = None,
    energy_level: int | None = None,
    genre_tags: list[str] | None = None,
    title: str = "",
) -> str:
    """
    Elige arquetipo según intención de la pieza (no un target global).
    """
    title_l = _title_hint(title)
    tags = _tags_hint(genre_tags or [])
    energy = energy_level if energy_level is not None else 3
    uc = (use_case or "game").lower()

    sparse_words = ("atmospheric", "ambient", "loop", "sparse", "drone", "ethereal", "calm")
    if uc == "loop" or any(w in title_l for w in sparse_words) or tags & {"ambient", "drone", "ethereal"}:
        return "sparse_loop"

    if uc == "cutscene" or energy <= 2 or any(w in title_l for w in ("cutscene", "dark", "cinematic")):
        return "moderate_cinematic"

    boss_words = ("boss", "orchestral", "epic", "cinematic")
    energetic_words = ("energetic", "boss fight", "combat", "action", "aggressive", "battle")
    dance_tags = tags & {"techno", "dubstep", "brostep", "edm", "house"}
    if energy >= 4 and (
        any(w in title_l for w in energetic_words)
        or tags & {"boss fight", "combat", "aggressive", "energetic"}
    ):
        if tags & {"orchestral", "cinematic", "epic"} and not dance_tags:
            return "boss_orchestral"
        if dance_tags or "techno" in title_l or "dubstep" in title_l:
            return "energetic_game"
        return "dense_dance"

    if energy >= 5 and (tags & {"orchestral", "cinematic", "epic"} or any(w in title_l for w in boss_words)):
        return "boss_orchestral"

    if energy >= 4 or any(w in title_l for w in ("aggressive", "energetic", "battle", "drop", "techno")):
        if tags & {"orchestral", "cinematic"}:
            return "boss_orchestral"
        return "dense_dance"

    if energy >= 3:
        return "dense_dance"

    return "moderate_cinematic"


def load_rsong_meta(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    header = data.get("header", {})
    game = data.get("game_meta", {})
    return {
        "use_case": game.get("use_case"),
        "energy_level": game.get("energy_level"),
        "genre_tags": header.get("genre_tags", []),
        "title": header.get("title", path.stem),
    }


def infer_archetype_from_path(path: Path) -> str:
    if path.suffix.lower() == ".rsong":
        meta = load_rsong_meta(path)
        return infer_archetype(
            use_case=meta.get("use_case"),
            energy_level=meta.get("energy_level"),
            genre_tags=meta.get("genre_tags"),
            title=meta.get("title", path.stem),
        )
    name = path.stem.lower()
    if "pizza" in name:
        return "sparse_loop"
    if "milf" in name:
        return "moderate_cinematic"
    if "energetic" in name:
        return "energetic_game"
    if "spider" in name or "bad apple" in name:
        return "dense_dance"
    if "asgore" in name:
        return "boss_orchestral"
    return "dense_dance"


def compute_instrumental_richness(
    metrics: object,
    profile: StyleProfile,
) -> InstrumentalRichness:
    """
    Índice 0–100 de riqueza instrumental: diversidad de capas, registro y paleta.
    Normalizado contra el rango del arquetipo (no contra un promedio fijo).
    """
    components: dict[str, float] = {}
    weighted = 0.0

    for key, weight in RICHNESS_WEIGHTS.items():
        val = float(getattr(metrics, key, 0.0))
        lo, hi = profile.ranges.get(key, (0.0, 1.0))
        if hi <= lo:
            norm = 0.5
        else:
            norm = _clamp01((val - lo) / (hi - lo))
        components[key] = round(norm * 100, 1)
        weighted += weight * norm

    score = round(weighted * 100, 1)

    return InstrumentalRichness(
        score=score,
        components=components,
        reference_lo=40.0,
        reference_hi=80.0,
        in_style_range=True,
    )


def compute_richness_reference_band(
    profile: StyleProfile,
    metrics_by_file: dict[str, object],
) -> tuple[float, float]:
    """Banda de riqueza instrumental esperada para el arquetipo."""
    scores = []
    for ref in profile.references:
        m = metrics_by_file.get(ref)
        if not m:
            continue
        ir = compute_instrumental_richness(m, profile)
        scores.append(ir.score)
    if not scores:
        return 40.0, 80.0
    return _metric_range(scores, padding=0.08)


def evaluate_against_style(
    metrics: object,
    profile: StyleProfile,
    *,
    meta_summary: str = "",
    metrics_by_file: dict[str, object] | None = None,
) -> StyleEvaluation:
    checks: list[MetricCheck] = []

    for key in RANGE_METRICS:
        if key not in profile.ranges:
            continue
        lo, hi = profile.ranges[key]
        val = float(getattr(metrics, key, 0.0))
        ref_vals = []
        if metrics_by_file:
            for ref in profile.references:
                rm = metrics_by_file.get(ref)
                if rm:
                    ref_vals.append(getattr(rm, key, 0.0))
        span = ""
        if ref_vals:
            span = f"{min(ref_vals):.1f}–{max(ref_vals):.1f}"
        checks.append(MetricCheck(
            key=key,
            label=METRIC_LABELS.get(key, key),
            value=val,
            lo=lo,
            hi=hi,
            in_range=lo <= val <= hi,
            reference_span=span,
        ))

    in_range = sum(1 for c in checks if c.in_range)
    fit_ratio = in_range / max(1, len(checks))

    richness = compute_instrumental_richness(metrics, profile)
    if metrics_by_file:
        r_lo, r_hi = compute_richness_reference_band(profile, metrics_by_file)
        richness.reference_lo = r_lo
        richness.reference_hi = r_hi
        richness.in_style_range = r_lo <= richness.score <= r_hi

    return StyleEvaluation(
        profile=profile,
        checks=checks,
        fit_ratio=fit_ratio,
        instrumental_richness=richness,
        meta_summary=meta_summary,
    )


def format_meta_summary(meta: dict) -> str:
    uc = meta.get("use_case", "?")
    energy = meta.get("energy_level", "?")
    tags = ", ".join((meta.get("genre_tags") or [])[:3]) or "—"
    return f"use_case={uc}  energy={energy}  tags={tags}"
