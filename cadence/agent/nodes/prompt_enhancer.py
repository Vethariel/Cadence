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
        "que el usuario no dijo pero que encajan — evita vaguedades.\n"
        "- logline: una sola frase con protagonista, objetivo, obstáculo y giro final.\n"
        "- dramatic_objective: una frase breve y verificable, sin relleno literario.\n"
        "- central_conflict: conflicto central único (1 sola tensión principal).\n"
        "- emotional_arc: exactamente 3 hitos emocionales en formato A → B → C.\n"
        "- scene_and_context: incluir microcontexto concreto (situación jugable/cinemática).\n"
        "- scenario_assumption: si el prompt es ambiguo o muy corto, agrega 1 suposición explícita; "
        "si no aplica, deja cadena vacía.\n"
        "- listener_journey: 2–4 frases, específicas, sin clichés.\n"
        "- mood_keywords: 3–6 palabras en inglés (dark, urgent, melancholic…). "
        "La primera es tono dominante y la segunda matiz secundario.\n"
        "- dominant_tone y secondary_tone: describe esos dos tonos en lenguaje natural.\n"
        "- negative_constraints: 2–5 cosas que NO debe transmitir "
        "(ej. 'no comic relief', 'no triumphant victory').\n"
        "- use_case: game | animation | loop | cutscene según el contexto del brief.\n"
        "- style_hints: 2–5 pistas de estilo en lenguaje natural "
        "(ej. 'hybrid orchestral boss', 'sparse ambient loop') — no sustituyen géneros del catálogo.\n"
        "- enriched_prompt: 1–2 párrafos (máx. 120 palabras) que integren logline, conflicto central, "
        "escena y arco emocional, incluyendo 1 detalle distintivo no obvio.\n"
        "- reasoning: 1 frase sobre tu elección dramática y chequeo de coherencia entre logline, "
        "objetivo y arco.\n\n"
        "- coherence_notes: 1 frase explícita validando coherencia entre logline, central_conflict, "
        "dramatic_objective y emotional_arc.\n\n"
        "Reglas de calidad:\n"
        "- Evita frases genéricas tipo 'epic journey' sin contexto concreto.\n"
        "- No mezcles más de un conflicto central principal.\n"
        "- No uses listas ni viñetas dentro de enriched_prompt.\n\n"
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
