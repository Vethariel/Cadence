from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.schemas.song_state import SongState, TechnicalProposal


# ── Nodo ─────────────────────────────────────────────────────

def technical_proposal_node(state: SongState) -> dict:
    """
    Recibe un intent no técnico y propone valores musicales concretos.
    Solo debe llamarse cuando intent.knowledge_level == 'non_technical'.
    """

    intent = state["intent"]

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.4,
    ).with_structured_output(TechnicalProposal)

    system = SystemMessage(content=(
        "Eres un compositor experto en música para videojuegos y animaciones. "
        "Tu tarea es traducir una descripción creativa en parámetros musicales técnicos precisos. "
        "Piensa en el contexto de uso, el mood y los estilos detectados para tomar decisiones coherentes. "
        "Responde SOLO con el objeto estructurado, sin explicaciones adicionales."
    ))

    human = HumanMessage(content=(
        f"Descripción del usuario: {intent.raw_prompt}\n"
        f"Contexto de uso: {intent.use_case}\n"
        f"Mood detectado: {intent.mood}\n"
        f"Estilos detectados: {', '.join(intent.style_tags)}\n\n"
        "Propón los parámetros técnicos más adecuados para esta canción. "
        "El campo reasoning debe explicar brevemente por qué elegiste esos valores."
    ))

    result: TechnicalProposal = llm.invoke([system, human])

    return {"technical_proposal": result}
