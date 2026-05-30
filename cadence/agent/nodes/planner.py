from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.music.narrative_contract import _normalize_section_id
from cadence.music.structure_templates import structure_planner_penalty_hint
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


def _build_contract_context(state: SongState) -> str:
    contract = state.get("narrative_contract")
    if not contract:
        return ""
    return (
        "=== CONTRATO NARRATIVO (INMUTABLE) ===\n"
        f"section_ids (orden fijo): {', '.join(contract.section_ids)}\n"
        f"arc_type: {contract.arc_type}\n"
        f"global_motif: {contract.global_motif}\n"
        f"prompt_intent_signature: {contract.prompt_intent_signature}\n"
        "NO renombres, NO omitas ni reordenes secciones respecto al contrato.\n"
        "Solo ajusta compases (bars_per_section) y duración total.\n"
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

    contract = state.get("narrative_contract")
    if not contract:
        raise ValueError("structure_planner requiere narrative_contract en el estado")

    context = _build_context(state)
    contract_ctx = _build_contract_context(state)
    narrative_ctx = _build_narrative_context(state)

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("structure_planner"),
    ).with_structured_output(StructurePlannerOutput)

    system = SystemMessage(content=(
        "Eres un compositor experto en estructura musical para videojuegos y animaciones. "
        "Tu tarea es definir la macro-estructura formal: compases por sección y duración. "
        "El CONTRATO NARRATIVO fija los section_ids y su orden — debes usarlos tal cual. "
        "Asegúrate de que sections y bars_per_section usen EXACTAMENTE esos IDs, "
        "sin agregar ni omitir ninguna. "
        "Calcula estimated_duration_ms así: "
        "(total_bars * beats_per_bar * 60000) / BPM. "
        "Si hay guion narrativo, respeta density y narrative_role al decidir "
        "cuántos compases tiene cada sección. "
        "Si el brief pide loop, cutscene, boss o edm y el contrato aún parece pop genérico, "
        "NO expandas a intro-verse-chorus-outro: respeta los IDs del contrato y asigna compases "
        "como si la forma fuera la del prompt (más build-up/drop, más beds, más loop). "
        "Responde SOLO con el objeto estructurado."
    ))

    penalty = structure_planner_penalty_hint(state)
    human = HumanMessage(content=(
        f"{context}\n\n"
        f"{contract_ctx}\n"
        f"{narrative_ctx}\n"
        f"{penalty}\n"
        "Define compases por sección según density y narrative_role. "
        "sections DEBE ser la lista exacta del contrato en el mismo orden."
    ))

    result: StructurePlannerOutput = llm.invoke([system, human])

    canonical = list(contract.section_ids)
    bars = dict(result.bars_per_section)
    remapped_bars: dict[str, int] = {}
    for cid in canonical:
        if cid in bars:
            remapped_bars[cid] = bars[cid]
        else:
            for key, val in bars.items():
                if _normalize_section_id(key) == _normalize_section_id(cid):
                    remapped_bars[cid] = val
                    break
            if cid not in remapped_bars:
                remapped_bars[cid] = 8

    total_bars = sum(remapped_bars.values())
    proposal = state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120
    beats_per_bar = proposal.time_signature[0] if proposal else 4
    duration_ms = int((total_bars * beats_per_bar * 60000) / max(bpm, 1))

    structure = SongStructure(
        sections=canonical,
        bars_per_section=remapped_bars,
        total_bars=total_bars,
        estimated_duration_ms=result.estimated_duration_ms or duration_ms,
    )

    return {"structure": structure}
