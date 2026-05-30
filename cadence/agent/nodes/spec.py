"""Nodo LLM: propuesta técnica desde brief dramático + prompt original."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from cadence.config import settings
from cadence.music.creative_brief import format_creative_brief_for_technical
from cadence.music.genre_catalog import format_genre_catalog_for_llm
from cadence.music.seed_policy import node_temperature
from cadence.music.instrument_catalog import format_orchestration_catalog_for_llm
from cadence.music.technical_proposal_apply import format_composition_patterns_for_llm
from cadence.music.scale_theory import format_modes_for_llm
from cadence.music.meter_theory import format_time_signatures_for_llm
from cadence.music.structure_catalog import (
    format_structure_catalog_for_llm,
    format_structure_hints_for_spec,
    suggest_forms,
)
from cadence.schemas.song_state import SongState, TechnicalProposal


def _user_prompt(state: SongState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def technical_spec_node(state: SongState) -> dict:
    """
    Traduce el brief dramático en parámetros técnicos (BPM, key, energía, géneros, forma).
    Respeta datos explícitos del prompt original; el resto lo infiere del brief.
    """
    raw = _user_prompt(state)
    brief = state.get("creative_brief")
    if not brief:
        raise ValueError("technical_spec requiere creative_brief del prompt_enhancer")

    use_case = brief.use_case
    from cadence.music.strategy_pools import compute_generation_seed

    seed_guess = compute_generation_seed(raw, 0)
    suggested = suggest_forms(
        use_case=use_case,
        genre_tags=[],
        energy_level=3,
        brief=brief,
        raw_prompt=raw,
        generation_seed=seed_guess,
    )
    catalog = format_genre_catalog_for_llm()
    form_catalog = format_structure_catalog_for_llm(suggested=suggested)
    structure_hints = format_structure_hints_for_spec(
        use_case=use_case,
        genre_tags=[],
        energy_level=3,
        brief=brief,
        raw_prompt=raw,
        generation_seed=seed_guess,
    )
    genre_hints = list(brief.style_hints) + list(brief.mood_keywords)
    energy_guess = 3
    if brief.mood_keywords:
        mood_l = " ".join(brief.mood_keywords).lower()
        if any(w in mood_l for w in ("intense", "urgent", "epic", "triumph")):
            energy_guess = 4
    orch_catalog = format_orchestration_catalog_for_llm(
        use_case=use_case,
        genre_tags=genre_hints,
        mood=brief.mood_keywords[0] if brief.mood_keywords else "",
        energy_level=energy_guess,
    )
    patterns_catalog = format_composition_patterns_for_llm()

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("technical_spec"),
    ).with_structured_output(TechnicalProposal)

    system = SystemMessage(content=(
        "Eres el compositor técnico de Cadence (música para videojuegos).\n"
        "Recibes el prompt original del usuario y un BRIEF DRAMÁTICO ampliado.\n"
        "Tu salida es TechnicalProposal: la realidad musical concreta del brief.\n\n"
        f"{catalog}\n\n"
        f"{form_catalog}\n\n"
        f"{orch_catalog}\n\n"
        f"{patterns_catalog}\n\n"
        "Reglas — composición COMPLETA (el código solo valida y genera notas):\n"
        "- Rellena forma, géneros, energía, orquestación (instruments[]) Y patrones rítmicos/armónicos.\n"
        "- El prompt original manda si trae BPM, tonalidad, compás o secciones explícitas.\n"
        f"- mode: {format_modes_for_llm()} (dórico/frigio para modal/exótico).\n"
        f"- time_signature: [{format_time_signatures_for_llm()}] — default [4, 4].\n"
        "- genre_tags: 3–8 ids EXACTOS del catálogo de géneros.\n"
        "- structure_form: UN id del catálogo de formas (prioriza sugeridas).\n"
        "- structure: solo si el usuario listó secciones; si no, [].\n"
        "- instruments[]: TODAS las capas activas con instrument_id, role, gm_program, active.\n"
        "- drum_pattern y bass_pattern: OBLIGATORIOS si hay drums o bass activos.\n"
        "- harmony_pool: OBLIGATORIO (define la armonía de toda la pieza).\n"
        "- Patrones de capa (arp/stab/perc/pluck/counter/echo): rellena si esa capa está active.\n"
        "- texture_mode y composition_archetype: elige según brief (no dejes vacío salvo duda).\n"
        "- global_motif: 3–5 grados 0–6 que definan el tema (ej. [0,2,4,2] en menor).\n"
        "- ensemble_concept + melody_texture + reasoning (2–3 frases de decisiones).\n"
        "- bars_per_section / target_total_bars: opcional según duración.\n"
        "Responde SOLO con el objeto TechnicalProposal estructurado."
    ))

    human = HumanMessage(content=(
        f"=== PROMPT ORIGINAL ===\n{raw}\n\n"
        f"{format_creative_brief_for_technical(brief)}\n\n"
        f"{structure_hints}\n\n"
        "Define TechnicalProposal para componer esta pieza."
    ))

    result: TechnicalProposal = llm.invoke([system, human])
    return {"technical_proposal": result}
