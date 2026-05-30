"""Contexto opcional para suites — evita repetir patrones y combos rítmicos seguidos."""

from __future__ import annotations

import contextvars
import os
from collections import deque
from contextlib import contextmanager
from typing import Iterator

_recent_patterns: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "pattern_batch_recent",
    default=None,
)

_combo_diversity_window: contextvars.ContextVar[int] = contextvars.ContextVar(
    "pattern_combo_diversity_window",
    default=0,
)

# Memoria de proceso opcional (benchmark/QA sin context manager activo).
_service_combo_recent: deque[str] = deque(maxlen=64)


def pattern_signature(
    *,
    drum: str | None = None,
    bass: str | None = None,
    harmony: str | None = None,
) -> str:
    parts = []
    if drum:
        parts.append(f"drum:{drum}")
    if bass:
        parts.append(f"bass:{bass}")
    if harmony:
        parts.append(f"harmony:{harmony}")
    return "|".join(parts)


def service_combo_diversity_window() -> int:
    """Ventana N desde env; 0 = desactivado. CADENCE_COMBO_DIVERSITY_WINDOW."""
    raw = os.environ.get("CADENCE_COMBO_DIVERSITY_WINDOW", "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def effective_combo_diversity_window() -> int:
    """Ventana activa: contexto batch > variable de entorno."""
    ctx_window = _combo_diversity_window.get()
    if ctx_window > 0:
        return ctx_window
    return service_combo_diversity_window()


def get_batch_recent_patterns() -> list[str]:
    recent = _recent_patterns.get()
    batch = list(recent) if recent is not None else []
    svc_window = service_combo_diversity_window()
    if svc_window <= 0:
        return batch
    service = list(_service_combo_recent)[-svc_window:]
    return service + batch


def combo_in_recent_window(
    *,
    drum: str,
    bass: str,
    harmony: str,
    window: int | None = None,
) -> bool:
    """True si el combo drum+bass+harmony ya apareció en las últimas N firmas."""
    w = window if window is not None else effective_combo_diversity_window()
    if w <= 0:
        return False
    recent = get_batch_recent_patterns()
    if not recent:
        return False
    sig = pattern_signature(drum=drum, bass=bass, harmony=harmony)
    return sig in recent[-w:]


def record_strategy_patterns(
    *,
    drum: str,
    bass: str,
    harmony: str,
) -> None:
    recent = _recent_patterns.get()
    sig = pattern_signature(drum=drum, bass=bass, harmony=harmony)
    if recent is not None:
        recent.append(sig)
        if len(recent) > 32:
            del recent[:-32]
    svc_w = service_combo_diversity_window()
    if svc_w > 0:
        _service_combo_recent.append(sig)


def clear_service_combo_memory() -> None:
    """Resetea memoria de proceso (tests/benchmarks)."""
    _service_combo_recent.clear()


class PatternBatchContext:
    """Acumula firmas drum/bass/harmony en generaciones consecutivas."""

    def __init__(self, *, combo_window: int = 4) -> None:
        self._signatures: list[str] = []
        self.combo_window = max(0, combo_window)

    def record(self, *, drum: str, bass: str, harmony: str) -> None:
        record_strategy_patterns(drum=drum, bass=bass, harmony=harmony)

    @property
    def signatures(self) -> list[str]:
        return list(self._signatures)

    def __enter__(self) -> PatternBatchContext:
        self._token = _recent_patterns.set(self._signatures)
        self._window_token = _combo_diversity_window.set(self.combo_window)
        return self

    def __exit__(self, *args: object) -> None:
        _recent_patterns.reset(self._token)
        _combo_diversity_window.reset(self._window_token)


@contextmanager
def pattern_batch_session(
    *,
    combo_window: int = 4,
) -> Iterator[PatternBatchContext]:
    ctx = PatternBatchContext(combo_window=combo_window)
    with ctx:
        yield ctx
