"""Compás y duración temporal — BPM siempre referido a negra (quarter note)."""

from __future__ import annotations

# [numerador, denominador] admitidos en TechnicalProposal
COMMON_TIME_SIGNATURES: tuple[tuple[int, int], ...] = (
    (4, 4), (3, 4), (2, 4), (5, 4), (6, 4), (7, 4),
    (6, 8), (9, 8), (12, 8), (3, 8),
)

_DEFAULT = (4, 4)


def normalize_time_signature(raw: list[int] | None) -> list[int]:
    if not raw or len(raw) < 2:
        return list(_DEFAULT)
    num = max(1, min(16, int(raw[0])))
    den = int(raw[1])
    if den not in (2, 4, 8, 16):
        den = 4
    pair = (num, den)
    if pair not in COMMON_TIME_SIGNATURES:
        # Aceptar valores razonables aunque no estén en el catálogo corto
        if den == 4 and num <= 12:
            pass
        elif den == 8 and num in (3, 6, 9, 12):
            pass
        else:
            return list(_DEFAULT)
    return [num, den]


def beats_per_bar(time_signature: list[int] | None = None) -> int:
    """Negras (quarter notes) por compás — para ms_per_bar."""
    num, den = normalize_time_signature(time_signature)
    if den == 4:
        return num
    if den == 8:
        return max(1, num // 2)
    if den == 2:
        return num * 2
    return num


def steps_per_bar(time_signature: list[int] | None = None, *, subdivisions: int = 4) -> int:
    """Steps de semicorchea (1/16 de negra) por compás."""
    num, den = normalize_time_signature(time_signature)
    if den == 8:
        return num * 2
    if den == 2:
        return num * subdivisions * 2
    return num * subdivisions


def ms_per_bar(bpm: int, time_signature: list[int] | None = None) -> float:
    bpm = max(bpm, 1)
    return (60000 / bpm) * beats_per_bar(time_signature)


def ms_per_step(bpm: int, time_signature: list[int] | None = None) -> float:
    steps = max(steps_per_bar(time_signature), 1)
    return ms_per_bar(bpm, time_signature) / steps


def format_time_signatures_for_llm() -> str:
    labels = [f"{n}/{d}" for n, d in COMMON_TIME_SIGNATURES]
    return ", ".join(labels)
