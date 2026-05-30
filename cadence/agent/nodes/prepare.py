"""Prepara intent, perfil de estilo y propuesta técnica normalizada (sin LLM)."""

from langchain_core.messages import HumanMessage

from cadence.music.creative_brief import combined_prompt_text
from cadence.music.prompt_resolve import resolve_intent_from_prompt
from cadence.music.strategy_pools import compute_generation_seed
from cadence.music.instrument_catalog import normalize_technical_proposal_instruments
from cadence.music.technical_proposal_apply import normalize_technical_proposal_composition
from cadence.music.structure_catalog import resolve_proposal_structure
from cadence.music.style_profile import merge_proposal_genre_tags
from cadence.music.style_profile_det import build_style_profile_deterministic
from cadence.music.timbre_library import gm_name
from cadence.music.tonal_policy import apply_tonal_policy_to_proposal
from cadence.schemas.song_state import SongState


def prepare_pipeline_node(state: SongState) -> dict:
    """
    Ruta única tras technical_spec: intención y perfil deterministas,
    fusión de géneros y política tonal/estructura.
    """
    proposal = state.get("technical_proposal")
    if not proposal:
        raise ValueError("prepare requiere technical_proposal")

    raw = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            raw = msg.content
            break

    brief = state.get("creative_brief")
    intent = resolve_intent_from_prompt(
        raw,
        llm_style_tags=proposal.genre_tags,
        creative_brief=brief,
    )
    profile = build_style_profile_deterministic(
        intent, proposal_genres=proposal.genre_tags,
    )
    merged_tags = merge_proposal_genre_tags(proposal.genre_tags, profile)
    proposal = proposal.model_copy(update={"genre_tags": merged_tags})
    proposal = resolve_proposal_structure(
        proposal, intent, creative_brief=brief,
    )
    proposal = normalize_technical_proposal_instruments(proposal, intent)
    proposal = normalize_technical_proposal_composition(proposal)

    if proposal.instruments:
        inst_labels = [
            f"{item.instrument_id}:{gm_name(item.gm_program)}"
            for item in proposal.instruments
            if item.active
        ]
        profile = profile.model_copy(
            update={"instrumentation": inst_labels[:12]},
        )

    seed_text = combined_prompt_text(raw, brief)
    seed = compute_generation_seed(seed_text, 0)
    proposal, _ = apply_tonal_policy_to_proposal(proposal, intent, seed=seed)

    return {
        "intent": intent,
        "style_profile": profile,
        "technical_proposal": proposal,
        "generation_seed": seed,
    }
