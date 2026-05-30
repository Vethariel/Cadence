from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from cadence.config import settings
from cadence.music.seed_policy import node_temperature
from cadence.music.style_profile import (
    format_profile_for_llm,
    merge_proposal_genre_tags,
)
from cadence.music.strategy_pools import compute_generation_seed
from cadence.music.tonal_policy import apply_tonal_policy_to_proposal
from cadence.music.structure_templates import (
    default_structure_for_use_case,
    prompt_lists_explicit_sections,
    resolve_proposal_structure,
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
        temperature=node_temperature("technical_parser"),
    ).with_structured_output(TechnicalProposal)

    system = SystemMessage(content=(
        "Eres un parser musical de Cadence. "
        "Tu tarea es EXTRAER parámetros técnicos explícitos del prompt del usuario, "
        "no inventar valores creativos.\n\n"
        "Reglas de extracción:\n"
        "- bpm: número explícito en el prompt (ej. '140 BPM'). Si no aparece, usa 120.\n"
        "- key/mode: SOLO si el prompt indica tonalidad explícita (ej. 'D minor'). "
        "Si no hay key en el texto, deja key='C' y mode='minor' como placeholder — "
        "el sistema asignará tonalidad por política.\n"
        "- time_signature: lista [numerador, denominador] si se menciona compás "
        "(ej. '4/4' → [4,4]). Default [4,4].\n"
        "- genre_tags: géneros explícitos en el prompt; si faltan, usa los del perfil de estilo.\n"
        "- structure: SOLO secciones mencionadas explícitamente en el prompt, en orden. "
        "Si el usuario NO lista secciones, deja structure como lista vacía [] — "
        "el sistema derivará la forma desde use_case.\n"
        "NO uses intro-verse-chorus-outro por defecto si el prompt no lo pide.\n"
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

    if not proposal.structure or (
        not prompt_lists_explicit_sections(intent.raw_prompt)
        and len(proposal.structure) == 4
        and proposal.structure == ["intro", "verse", "chorus", "outro"]
    ):
        proposal = proposal.model_copy(
            update={
                "structure": default_structure_for_use_case(
                    intent.use_case, intent.raw_prompt,
                ),
            },
        )

    proposal = resolve_proposal_structure(proposal, intent)

    tonal_seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt, 0,
    )
    proposal, _tonal_reason = apply_tonal_policy_to_proposal(
        proposal, intent, seed=tonal_seed,
    )

    return {"technical_proposal": proposal}
