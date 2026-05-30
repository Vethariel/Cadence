from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from typing import Literal

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.schemas.song_state import SongState, UserIntent


# ── Salida estructurada del LLM ───────────────────────────────

class RouterOutput(BaseModel):
    knowledge_level: Literal["technical", "non_technical"] = Field(
        description=(
            "technical: el prompt incluye al menos 2 de estos elementos: "
            "BPM, compás, tonalidad, escala, nombre de modo musical, "
            "progresión de acordes, estructura de secciones explícita. "
            "non_technical: el prompt es descriptivo, emocional o contextual "
            "sin términos musicales precisos."
        )
    )
    use_case: Literal["game", "animation", "loop", "cutscene"] = Field(
        description="Contexto de uso inferido del prompt."
    )
    mood: str = Field(description="Estado emocional o atmósfera detectada, en inglés. Ej: 'energetic', 'melancholic'.")
    style_tags: list[str] = Field(
        description="Pistas iniciales de estilo (2–6); el tag_enricher las expande después.",
    )


# ── Nodo ─────────────────────────────────────────────────────

def music_knowledge_router(state: SongState) -> dict:
    """
    Clasifica el prompt del usuario como técnico o no técnico
    y extrae intención básica: uso, mood y estilo.
    """

    # Tomar el último mensaje humano del estado
    user_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_message = msg.content
            break

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("router"),
    ).with_structured_output(RouterOutput)

    system = SystemMessage(content=(
        "Eres el router de Cadence, un sistema de composición musical para juegos y animaciones. "
        "Tu única tarea es analizar el prompt del usuario y clasificarlo. "
        "Responde SOLO con el objeto estructurado solicitado, sin explicaciones."
    ))

    human = HumanMessage(content=f"Prompt del usuario: {user_message}")

    result: RouterOutput = llm.invoke([system, human])

    intent = UserIntent(
        raw_prompt=user_message,
        knowledge_level=result.knowledge_level,
        use_case=result.use_case,
        mood=result.mood,
        style_tags=result.style_tags,
    )

    return {"intent": intent}
