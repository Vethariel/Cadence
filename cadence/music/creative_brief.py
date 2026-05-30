"""Helpers para CreativeBrief — formato y fusión con intent determinista."""

from __future__ import annotations

from cadence.schemas.song_state import CreativeBrief


def format_creative_brief_for_technical(brief: CreativeBrief) -> str:
    """Bloque legible para el nodo technical_spec."""
    moods = ", ".join(brief.mood_keywords) if brief.mood_keywords else "—"
    hints = ", ".join(brief.style_hints) if brief.style_hints else "—"
    return (
        "=== BRIEF DRAMÁTICO ===\n"
        f"Logline: {brief.logline}\n"
        f"Objetivo dramático: {brief.dramatic_objective}\n"
        f"Arco emocional: {brief.emotional_arc}\n"
        f"Escena y contexto: {brief.scene_and_context}\n"
        f"Viaje del oyente: {brief.listener_journey}\n"
        f"Moods: {moods}\n"
        f"Uso sugerido: {brief.use_case}\n"
        f"Pistas de estilo: {hints}\n\n"
        f"Brief ampliado:\n{brief.enriched_prompt}\n"
    )


def combined_prompt_text(raw_prompt: str, brief: CreativeBrief | None) -> str:
    """Texto unificado para heurísticas deterministas (géneros, semilla)."""
    parts = [raw_prompt.strip()]
    if brief:
        parts.append(brief.enriched_prompt.strip())
        parts.extend(brief.style_hints)
        parts.extend(brief.mood_keywords)
    return "\n".join(p for p in parts if p)
