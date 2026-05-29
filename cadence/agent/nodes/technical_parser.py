from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.schemas.song_state import SongState, TechnicalProposal


# ── Nodo ─────────────────────────────────────────────────────

def technical_parser_node(state: SongState) -> dict:
    """
    Extrae parámetros musicales explícitos del prompt del usuario.
    Solo debe llamarse cuando intent.knowledge_level == 'technical'.
    Escribe en technical_proposal para unificar con la ruta non_technical.
    """

    intent = state["intent"]

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
        "- genre_tags: géneros/estilos mencionados explícitamente.\n"
        "- structure: secciones mencionadas en orden (ej. 'intro-verse-chorus-outro'). "
        "Si no hay estructura explícita, usa ['intro', 'verse', 'chorus', 'outro'].\n"
        "- energy_level: infiere 1-5 del tono del prompt si no hay valor explícito.\n"
        "- reasoning: resume qué extrajiste del texto y qué valores usaste por defecto.\n\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt del usuario: {intent.raw_prompt}\n"
        f"Estilos detectados por el router: {', '.join(intent.style_tags) or 'ninguno'}\n"
        f"Mood: {intent.mood}\n"
        f"Uso: {intent.use_case}"
    ))

    result: TechnicalProposal = llm.invoke([system, human])

    return {"technical_proposal": result}
