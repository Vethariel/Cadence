"""Nodo LLM: amplía el prompt con dirección dramática y narrativa."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.schemas.song_state import CreativeBrief, SongState


def _user_prompt(state: SongState) -> str:
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def prompt_enhancer_node(state: SongState) -> dict:
    """
    Desarrolla el prompt del usuario en un brief teatral/dramático.
    El LLM elige qué enfatizar (escena, arco, emoción) para variar entre solicitudes.
    """
    prompt = _user_prompt(state)

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("prompt_enhancer"),
    ).with_structured_output(CreativeBrief)

    system = SystemMessage(content=(
        "Eres un director dramático de música interactiva (videojuegos y animación).\n"
        "Tu tarea es AMPLIAR el prompt del usuario en un brief creativo accionable — "
        "NO escribir notas ni BPM todavía.\n\n"
        "Debes:\n"
        "- Mantener fidelidad al prompt original; no contradecir género, escena ni intención.\n"
        "- Inventar detalles teatrales concretos (quién, dónde, qué está en juego) "
        "que el usuario no dijo pero que encajan — esto garantiza variedad entre piezas.\n"
        "- Definir objetivo dramático claro: qué debe lograr la música en gameplay o cine.\n"
        "- Describir arco emocional explícito (inicio → tensión → clímax o resolución).\n"
        "- Explicar el viaje del oyente/jugador en 2–4 frases.\n"
        "- mood_keywords: 3–6 palabras en inglés (dark, urgent, melancholic…).\n"
        "- use_case: game | animation | loop | cutscene según el contexto del brief.\n"
        "- style_hints: 2–5 pistas de estilo en lenguaje natural "
        "(ej. 'hybrid orchestral boss', 'sparse ambient loop') — no sustituyen géneros del catálogo.\n"
        "- enriched_prompt: 1–3 párrafos en prosa que integren logline, escena, arco y emoción; "
        "debe poder leerse solo y guiar la composición.\n"
        "- reasoning: 1 frase sobre tu elección dramática.\n\n"
        "NO incluyas BPM, tonalidad, compás ni lista de secciones musicales "
        "(eso lo hará el nodo técnico después).\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt del usuario:\n{prompt}\n\n"
        "Amplía este brief con dirección dramática y narrativa."
    ))

    brief: CreativeBrief = llm.invoke([system, human])
    return {"creative_brief": brief}
