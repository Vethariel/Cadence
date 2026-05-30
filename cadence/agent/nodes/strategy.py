"""Nodo determinista: selección de estrategias desde generation_seed."""

from cadence.schemas.song_state import PatternSelectionAudit, SongState
from cadence.music.seed_policy import derive_node_seed
from cadence.music.strategy_pools import compute_generation_seed, select_strategies
from cadence.music.creative_variation import build_creative_variation_bounds
from cadence.music.pattern_intent import derive_pattern_intent
from cadence.music.style_archetype import reconcile_llm_archetype
from cadence.music.style_profile import build_genre_mix_from_state, effective_genre_tags
from cadence.music.technical_proposal_apply import (
    merge_strategies_from_proposal,
    snap_archetype,
)


def strategy_planner_node(state: SongState) -> dict:
    """
    Pools por seed; los campos de TechnicalProposal del LLM tienen prioridad.
    """
    intent = state["intent"]
    structure = state["structure"]
    proposal = state.get("technical_proposal")

    root_seed = state.get("generation_seed") or compute_generation_seed(
        intent.raw_prompt,
        structure.total_bars,
    )
    pool_seed = derive_node_seed(root_seed, "strategy_planner")
    mode = proposal.mode if proposal else "minor"
    genre_tags = effective_genre_tags(state)
    energy = proposal.energy_level if proposal else 3

    llm_arch = snap_archetype(proposal.composition_archetype) if proposal else ""
    arch_decision = reconcile_llm_archetype(
        llm_arch or None,
        style_profile=state.get("style_profile"),
        raw_prompt=intent.raw_prompt,
        use_case=intent.use_case,
        energy_level=energy,
    )
    archetype = arch_decision.archetype
    arch_reason = arch_decision.reason

    genre_mix = build_genre_mix_from_state(state)
    pattern_intent = derive_pattern_intent(
        genre_mix=genre_mix,
        use_case=intent.use_case,
        mood=intent.mood,
        energy_level=energy,
        composition_archetype=archetype,
        generation_seed=pool_seed or root_seed,
    )
    pattern_selection_audit = PatternSelectionAudit(
        generation_seed=pool_seed or root_seed,
    )
    strategies = select_strategies(
        pool_seed or root_seed,
        genre_tags,
        mode,
        intent.use_case,
        energy,
        composition_archetype=archetype,
        pattern_intent=pattern_intent,
        pattern_selection_audit=pattern_selection_audit,
    )
    if proposal:
        strategies = merge_strategies_from_proposal(strategies, proposal)

    out: dict = {
        "generation_seed": root_seed,
        "strategies": strategies,
        "genre_mix": genre_mix,
        "pattern_intent": pattern_intent,
        "pattern_selection_audit": pattern_selection_audit,
        "composition_archetype": archetype,
        "archetype_reason": arch_reason,
    }
    anchors = state.get("narrative_anchors")
    if anchors:
        out["creative_variation"] = build_creative_variation_bounds(
            anchors,
            energy_level=energy,
            use_case=intent.use_case,
            composition_archetype=archetype,
            generation_seed=root_seed,
        )
    return out
