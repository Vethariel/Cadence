"""
Contexto opcional para suites/benchmarks — evita repetir la misma tonalidad seguida.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator

_recent_signatures: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "tonal_batch_recent",
    default=None,
)


def tonal_signature(key: str, mode: str) -> str:
    return f"{key.strip()}:{mode.strip().lower()}"


def get_batch_recent_signatures() -> list[str]:
    """Firmas recientes en el contexto batch activo (vacío si no hay suite)."""
    recent = _recent_signatures.get()
    return list(recent) if recent is not None else []


def record_tonal_choice(key: str, mode: str) -> None:
    """Registra tonalidad tras una generación dentro de un batch activo."""
    recent = _recent_signatures.get()
    if recent is None:
        return
    sig = tonal_signature(key, mode)
    recent.append(sig)
    if len(recent) > 32:
        del recent[:-32]


class TonalBatchContext:
    """Acumula tonalidades en generaciones consecutivas (benchmark suite, tests)."""

    def __init__(self) -> None:
        self._signatures: list[str] = []

    def record(self, key: str, mode: str) -> None:
        record_tonal_choice(key, mode)

    @property
    def signatures(self) -> list[str]:
        return list(self._signatures)

    def __enter__(self) -> TonalBatchContext:
        self._token = _recent_signatures.set(self._signatures)
        return self

    def __exit__(self, *args: object) -> None:
        _recent_signatures.reset(self._token)


@contextmanager
def tonal_batch_session() -> Iterator[TonalBatchContext]:
    """Helper para tests o scripts que corren varios prompts seguidos."""
    ctx = TonalBatchContext()
    with ctx:
        yield ctx
