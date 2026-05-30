"""Roles de capa (lead, bass, rhythm, pad, fx) — elección LLM y normalización."""

from __future__ import annotations

from typing import Literal

from cadence.instruments.registry import get_instrument

InstrumentRole = Literal["lead", "bass", "rhythm", "pad", "fx"]

VALID_INSTRUMENT_ROLES: frozenset[str] = frozenset({"lead", "bass", "rhythm", "pad", "fx"})

_PERCUSSION_IDS = frozenset({"drums", "perc_aux"})


def default_role_for_instrument(instrument_id: str) -> InstrumentRole:
    """Rol por defecto del registro de instrumentos."""
    defn = get_instrument(instrument_id)
    role = (defn.role or "lead").strip().lower()
    if role in VALID_INSTRUMENT_ROLES:
        return role  # type: ignore[return-value]
    return "lead"


def normalize_instrument_role(
    instrument_id: str,
    role: str | None,
) -> InstrumentRole:
    """
    Valida rol del LLM; percusión siempre rhythm; fallback al registro.
    """
    iid = (instrument_id or "").strip().lower()
    if iid in _PERCUSSION_IDS:
        return "rhythm"
    raw = (role or "").strip().lower()
    if raw in VALID_INSTRUMENT_ROLES:
        return raw  # type: ignore[return-value]
    return default_role_for_instrument(iid)


def is_percussion_role(role: str) -> bool:
    return (role or "").strip().lower() == "rhythm"


def format_roles_for_llm() -> str:
    return (
        "Roles válidos por capa (campo role en cada instrument):\n"
        "  lead — melodía principal, arps, stabs, contramelodía\n"
        "  bass — línea de bajo\n"
        "  rhythm — batería y percusión (drums, perc_aux)\n"
        "  pad — capas armónicas sostenidas\n"
        "  fx — risers y efectos (fx_riser)\n"
        "El role puede diferir del id (ej. arp_synth con role=lead); "
        "drums/perc_aux deben usar role=rhythm."
    )
