from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.music.style_profile import format_profile_for_llm, merge_proposal_genre_tags
from cadence.schemas.song_state import SongState, TechnicalProposal


# ── Nodo ─────────────────────────────────────────────────────

def technical_proposal_node(state: SongState) -> dict:
    """
    Recibe un intent no técnico y propone valores musicales concretos.
    Solo debe llamarse cuando intent.knowledge_level == 'non_technical'.
    """

    intent = state["intent"]
    profile = state.get("style_profile")

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("technical_proposal"),
    ).with_structured_output(TechnicalProposal)

    system = SystemMessage(content=(
        "Eres un compositor experto en música para videojuegos y animaciones. "
        "Tu tarea es traducir una descripción creativa en parámetros musicales técnicos precisos. "
        "Piensa en el contexto de uso, el mood y el perfil de estilo enriquecido para tomar decisiones coherentes. "
        "Los genre_tags deben alinearse con los géneros del perfil de estilo, no con etiquetas genéricas incorrectas. "
        "Si el perfil es chiptune/arcade, energy 4-5; si es compact/platform, energy 4 sin orquesta masiva; "
        "si es orchestral boss, energy 4-5 con géneros orquestales. "
        "Responde SOLO con el objeto estructurado, sin explicaciones adicionales."
    ))

    human = HumanMessage(content=(
        f"Descripción del usuario: {intent.raw_prompt}\n"
        f"Contexto de uso: {intent.use_case}\n"
        f"Mood detectado: {intent.mood}\n"
        f"Pistas del router: {', '.join(intent.style_tags)}\n\n"
        f"{format_profile_for_llm(profile)}\n\n"
        "Propón los parámetros técnicos más adecuados para esta canción. "
        "El campo reasoning debe explicar brevemente por qué elegiste esos valores."
    ))

    result: TechnicalProposal = llm.invoke([system, human])
    merged_tags = merge_proposal_genre_tags(result.genre_tags, profile)
    proposal = result.model_copy(update={"genre_tags": merged_tags})

    return {"technical_proposal": proposal}
