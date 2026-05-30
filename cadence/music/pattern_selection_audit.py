"""Auditoría de selección de patrones — candidatos, pesos y motivo."""

from __future__ import annotations

import math
from collections import Counter

from cadence.music.pattern_registry import pattern_family
from cadence.schemas.song_state import PatternFieldAudit, PatternSelectionAudit


def build_selection_reason(
    *,
    chosen: str,
    weights: dict[str, float],
    seed: int,
    salt: int,
    jitter: int,
    target_ratio: float,
    field: str,
) -> str:
    """Texto legible: por qué ganó el candidato elegido."""
    ranked = sorted(weights.items(), key=lambda x: (-x[1], x[0]))
    top = ranked[:4]
    top_str = ", ".join(f"{pid}={w:.2f}" for pid, w in top)
    fam = pattern_family(chosen)
    return (
        f"weighted_pick field={field} seed={seed} salt={salt} "
        f"jitter={jitter} target={target_ratio:.4f} "
        f"chosen={chosen} family={fam}; top_weights=[{top_str}]"
    )


def pattern_family_entropy(pattern_ids: list[str]) -> float:
    """Entropía Shannon (bits) sobre familias de patrón."""
    if not pattern_ids:
        return 0.0
    families = [pattern_family(p) for p in pattern_ids]
    counts = Counter(families)
    n = len(families)
    entropy = 0.0
    for c in counts.values():
        p = c / n
        if p > 0:
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def rhythm_combo_signature(drum: str, bass: str, harmony: str) -> str:
    return f"{pattern_family(drum)}|{pattern_family(bass)}|{harmony}"
