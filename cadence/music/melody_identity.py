"""Identidad de pista melody desde orchestration_plan (sin registry de instrumentos)."""

from __future__ import annotations

from cadence.music.timbre_library import gm_name
from cadence.schemas.song_state import OrchestrationPlan


def melody_instrument_from_state(state: dict) -> tuple[str, int | None]:
    """
    Nombre GM y programa efectivos del lead melody desde orchestration_plan.
    Usado al componer/exportar para que UI y diagnóstico no muestren 'Lead Synth' genérico.
    """
    plan = state.get("orchestration_plan")
    if plan is not None:
        for entry in plan.instruments:
            if entry.instrument_id == "melody" and entry.active:
                name = (entry.display_name or "").strip() or gm_name(entry.gm_program)
                return name, entry.gm_program
    return "Melody", None
