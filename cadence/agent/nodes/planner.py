from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from cadence.config import settings
from cadence.schemas.song_state import SongState, SongStructure


# ── Salida estructurada del LLM ───────────────────────────────

class StructurePlannerOutput(BaseModel):
    sections: list[str] = Field(
        description="Secciones en orden. Ej: ['intro', 'build-up', 'drop', 'outro']"
    )
    bars_per_section: dict[str, int] = Field(
        description="Número de compases por sección. Ej: {'intro': 4, 'drop': 16}"
    )
    total_bars: int = Field(
        description="Suma total de compases de todas las secciones."
    )
    estimated_duration_ms: int = Field(
        description="Duración total estimada en milisegundos basada en BPM y compases."
    )
    reasoning: str = Field(
        description="Breve explicación de las decisiones de estructura tomadas."
    )


# ── Helper ────────────────────────────────────────────────────

def _build_context(state: SongState) -> str:
    intent = state["intent"]
    proposal = state.get("technical_proposal")

    if proposal and intent.knowledge_level == "technical":
        return (
            f"Ruta: technical — parámetros extraídos del prompt\n"
            f"BPM: {proposal.bpm}\n"
            f"Tonalidad: {proposal.key} {proposal.mode}\n"
            f"Compás: {proposal.time_signature[0]}/{proposal.time_signature[1]}\n"
            f"Géneros: {', '.join(proposal.genre_tags)}\n"
            f"Nivel de energía: {proposal.energy_level}/5\n"
            f"Estructura sugerida: {', '.join(proposal.structure)}\n"
            f"Mood: {intent.mood}\n"
            f"Uso: {intent.use_case}\n"
            f"Prompt original: {intent.raw_prompt}"
        )
    if proposal:
        return (
            f"Ruta: non_technical — parámetros propuestos por el sistema\n"
            f"BPM: {proposal.bpm}\n"
            f"Tonalidad: {proposal.key} {proposal.mode}\n"
            f"Compás: {proposal.time_signature[0]}/{proposal.time_signature[1]}\n"
            f"Géneros: {', '.join(proposal.genre_tags)}\n"
            f"Nivel de energía: {proposal.energy_level}/5\n"
            f"Estructura sugerida: {', '.join(proposal.structure)}\n"
            f"Mood: {intent.mood}\n"
            f"Uso: {intent.use_case}\n"
            f"Descripción original: {intent.raw_prompt}"
        )
    return (
        f"Ruta: technical — parámetros del usuario\n"
        f"Prompt original: {intent.raw_prompt}\n"
        f"Mood: {intent.mood}\n"
        f"Estilos: {', '.join(intent.style_tags)}\n"
        f"Uso: {intent.use_case}"
    )


def _build_narrative_context(state: SongState) -> str:
    narrative = state.get("narrative")
    if not narrative:
        return ""

    lines = [
        f"Guion narrativo: {narrative.logline}",
        f"Arco: {narrative.arc_type}",
        f"Motivo global (grados 0-6): {narrative.global_motif}",
        "",
        "Intención dramática por sección:",
    ]
    for s in narrative.sections:
        lines.append(
            f"  • {s.id}: role={s.narrative_role}, emotion={s.emotional_target}, "
            f"density={s.density:.2f}, harmonic_tension={s.harmonic_tension:.2f}, "
            f"rhythmic_complexity={s.rhythmic_complexity:.2f}, "
            f"transition_out={s.transition_out}"
        )
    lines.append("")
    lines.append(
        "Usa density para asignar compases: "
        "density >= 0.7 → secciones largas (16-32 bars); "
        "0.4-0.7 → medias (8-16 bars); "
        "< 0.4 → cortas (4-8 bars). "
        "Secciones con transition_out distinto de 'none' pueden usar +2 bars "
        "para el material de transición."
    )
    return "\n".join(lines)


# ── Nodo ─────────────────────────────────────────────────────

def structure_planner_node(state: SongState) -> dict:
    """
    Genera la macro-estructura de la canción: secciones, compases
    por sección y duración estimada.
    """

    context = _build_context(state)
    narrative_ctx = _build_narrative_context(state)

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.3,
    ).with_structured_output(StructurePlannerOutput)

    system = SystemMessage(content=(
        "Eres un compositor experto en estructura musical para videojuegos y animaciones. "
        "Tu tarea es definir la macro-estructura de una canción: qué secciones tiene, "
        "cuántos compases dura cada una, y el total. "
        "Asegúrate de que bars_per_section contenga exactamente las mismas secciones "
        "que el array sections, sin agregar ni omitir ninguna. "
        "Calcula estimated_duration_ms así: "
        "(total_bars * beats_per_bar * 60000) / BPM. "
        "Si hay guion narrativo, respeta density y narrative_role al decidir "
        "cuántos compases tiene cada sección. "
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"{context}\n\n"
        f"{narrative_ctx}\n"
        "Define la estructura completa de la canción. "
        "Cada sección debe tener un número de compases apropiado para su rol dramático."
    ))

    result: StructurePlannerOutput = llm.invoke([system, human])

    structure = SongStructure(
        sections=result.sections,
        bars_per_section=result.bars_per_section,
        total_bars=result.total_bars,
        estimated_duration_ms=result.estimated_duration_ms,
    )

    return {"structure": structure}
