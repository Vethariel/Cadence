from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.music.style_profile import (
    format_profile_for_llm,
    merge_proposal_genre_tags,
)
from cadence.schemas.song_state import SongState, TechnicalProposal


# ── Nodo ─────────────────────────────────────────────────────

def technical_parser_node(state: SongState) -> dict:
    """
    Extrae parámetros musicales explícitos del prompt del usuario.
    Solo debe llamarse cuando intent.knowledge_level == 'technical'.
    Escribe en technical_proposal para unificar con la ruta non_technical.
    """

    intent = state["intent"]
    profile = state.get("style_profile")

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.1,
    ).with_structured_output(TechnicalProposal)

    system = SystemMessage(content=(
        "Eres un parser musical de Cadence. "
        "Tu tarea es EXTRAER parámetros técnicos explícitos del prompt del usuario, "
        "no inventar valores creativos.\n\n"
        "Reglas de extracción:\n"
        "- bpm: número explícito en el prompt (ej. '140 BPM'). Si no aparece, usa 120.\n"
        "- key: nota raíz en notación estándar (C, D, F#, Bb). Solo la letra/nombre.\n"
        "- mode: 'major' o 'minor' según el prompt (ej. 'D minor', 'A major').\n"
        "- time_signature: lista [numerador, denominador] si se menciona compás "
        "(ej. '4/4' → [4,4]). Default [4,4].\n"
        "- genre_tags: géneros explícitos en el prompt; si faltan, usa los del perfil de estilo.\n"
        "- structure: secciones mencionadas en orden (ej. 'intro-verse-chorus-outro'). "
        "Si no hay estructura explícita, usa ['intro', 'verse', 'chorus', 'outro'].\n"
        "- energy_level: infiere 1-5 del tono del prompt si no hay valor explícito.\n"
        "- reasoning: resume qué extrajiste del texto y qué valores usaste por defecto.\n\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt del usuario: {intent.raw_prompt}\n"
        f"Pistas del router: {', '.join(intent.style_tags) or 'ninguna'}\n"
        f"Mood: {intent.mood}\n"
        f"Uso: {intent.use_case}\n\n"
        f"{format_profile_for_llm(profile)}"
    ))

    result: TechnicalProposal = llm.invoke([system, human])
    merged_tags = merge_proposal_genre_tags(result.genre_tags, profile)
    proposal = result.model_copy(update={"genre_tags": merged_tags})

    return {"technical_proposal": proposal}
