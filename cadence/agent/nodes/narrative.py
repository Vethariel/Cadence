from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.schemas.song_state import SongState, SongNarrative


# ── Nodo ─────────────────────────────────────────────────────

def narrative_planner_node(state: SongState) -> dict:
    """
    Define el guion dramático de la pieza: arco narrativo e intención
    por sección. Debe ejecutarse después de tener technical_proposal.
    """

    intent = state["intent"]
    proposal = state["technical_proposal"]

    if not proposal:
        raise ValueError("narrative_planner requiere technical_proposal en el estado")

    section_list = ", ".join(proposal.structure)

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("narrative_planner"),
    ).with_structured_output(SongNarrative)

    system = SystemMessage(content=(
        "Eres un director musical de videojuegos. "
        "Tu tarea es definir el GUION NARRATIVO de una pieza — no notas ni compases, "
        "sino qué historia cuenta y qué debe sentir el oyente en cada sección.\n\n"
        "Reglas:\n"
        "- Debes producir EXACTAMENTE una SectionIntent por cada sección listada, "
        "en el mismo orden, con id igual al nombre de la sección.\n"
        "- narrative_role: función dramática (establish=tema inicial, tension=build, "
        "climax=pico, reflection=pausa/breakdown, release=outro, transition=puente, silence=vacío).\n"
        "- density: 0.0–1.0 — cuánta energía/capas debe tener la sección.\n"
        "- harmonic_tension y rhythmic_complexity: escala 0.0–1.0 acorde al rol.\n"
        "- transition_out: cómo sale la sección hacia la siguiente "
        "(riser=build-up, cut=corte seco al drop, filter_sweep, pickup, fade, none).\n"
        "- global_motif: 3–5 grados de escala (0-6) que unifiquen la pieza.\n"
        "- arc_type debe reflejar el use_case (game=rise-climax-fall, loop=loop-stable, etc.).\n\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt: {intent.raw_prompt}\n"
        f"Uso: {intent.use_case}\n"
        f"Mood: {intent.mood}\n"
        f"Géneros: {', '.join(proposal.genre_tags)}\n"
        f"Energía global: {proposal.energy_level}/5\n"
        f"Tonalidad: {proposal.key} {proposal.mode} | {proposal.bpm} BPM\n\n"
        f"Secciones (en orden, una SectionIntent por cada una): {section_list}\n\n"
        "Define el guion narrativo completo."
    ))

    result: SongNarrative = llm.invoke([system, human])

    # Alinear ids con la estructura propuesta
    expected = proposal.structure
    if len(result.sections) != len(expected):
        raise ValueError(
            f"narrative sections ({len(result.sections)}) != "
            f"proposal structure ({len(expected)})"
        )
    aligned = []
    for i, sec in enumerate(result.sections):
        aligned.append(sec.model_copy(update={"id": expected[i]}))
    result = result.model_copy(update={"sections": aligned})

    return {"narrative": result}
