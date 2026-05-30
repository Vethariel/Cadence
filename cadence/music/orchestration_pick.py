"""Selección de orquestación: prioridad technical_spec (LLM) → fallback determinista."""

from __future__ import annotations

from cadence.music.genre_orchestration import adjust_optional_budget
from cadence.music.instrument_catalog import (
    proposal_has_orchestration,
    proposal_instruments_to_assignments,
    resolve_timbre,
    select_fallback_lead_layers,
    validate_orchestration,
)
from cadence.music.pattern_variants import BASS_PATTERN_ALIASES, DRUM_PATTERN_ALIASES
from cadence.music.strategy_pools import resolve_rhythm_patterns
from cadence.music.style_archetype import melody_texture_for_archetype
from cadence.music.style_profile import build_genre_mix
from cadence.music.technical_proposal_apply import (
    apply_patterns_to_orchestration_plan,
    drum_pattern_for_plan,
    bass_pattern_for_plan,
)
from cadence.schemas.song_state import (
    GenerationStrategies,
    InstrumentAssignment,
    OrchestrationPlan,
    SongState,
)

_AGENT_DRUM_IDS = frozenset({
    "techno", "dubstep", "house", "breakbeat", "halftime", "dnb", "industrial", "default",
})
_AGENT_BASS_IDS = frozenset({
    "root_fifth", "driving", "syncopated", "pulse", "half_time", "walk", "octave_pulse",
})

_DEFAULT_MIX = {"drums": -10.0, "bass": -6.0, "melody": -8.0, "pad": -14.0}


def _agent_rhythm_id(pool_id: str, aliases: dict[str, str], allowed: frozenset[str]) -> str:
    for family, variant in aliases.items():
        if pool_id in (family, variant):
            return family if family in allowed else "default"
    base = pool_id.rsplit("_", 1)[0] if pool_id.endswith(("_a", "_b")) else pool_id
    return base if base in allowed else "default"


def _assignment(
    instrument_id: str,
    *,
    generation_seed: int,
    genre_tags: list[str],
    mood: str,
    use_case: str,
    archetype: str | None,
    mix_level: float | None = None,
) -> InstrumentAssignment:
    prog, name = resolve_timbre(
        instrument_id,
        0,
        generation_seed=generation_seed,
        genre_tags=genre_tags,
        mood=mood,
        use_case=use_case,
        composition_archetype=archetype,
    )
    from cadence.music.instrument_roles import default_role_for_instrument

    return InstrumentAssignment(
        instrument_id=instrument_id,
        role=default_role_for_instrument(instrument_id),
        gm_program=prog,
        display_name=name,
        mix_level=mix_level if mix_level is not None else _DEFAULT_MIX.get(instrument_id, -10.0),
        active=True,
    )


def _rhythm_patterns_from_state(state: SongState) -> tuple[str, str]:
    intent = state["intent"]
    proposal = state["technical_proposal"]
    strategies: GenerationStrategies | None = state.get("strategies")
    if not proposal or not strategies:
        raise ValueError("_rhythm_patterns_from_state requiere technical_proposal y strategies")

    if proposal.drum_pattern:
        drum_pat = drum_pattern_for_plan(proposal.drum_pattern)
    else:
        seed = state.get("generation_seed", 0)
        archetype = state.get("composition_archetype")
        drum_pool, _ = resolve_rhythm_patterns(
            strategies.drum_pattern,
            strategies.bass_pattern,
            genre_tags=list(proposal.genre_tags),
            energy_level=proposal.energy_level,
            use_case=intent.use_case,
            generation_seed=seed,
            composition_archetype=archetype,
        )
        drum_pat = _agent_rhythm_id(drum_pool, DRUM_PATTERN_ALIASES, _AGENT_DRUM_IDS)

    if proposal.bass_pattern:
        bass_pat = bass_pattern_for_plan(proposal.bass_pattern)
    else:
        seed = state.get("generation_seed", 0)
        archetype = state.get("composition_archetype")
        _, bass_pool = resolve_rhythm_patterns(
            strategies.drum_pattern,
            strategies.bass_pattern,
            genre_tags=list(proposal.genre_tags),
            energy_level=proposal.energy_level,
            use_case=intent.use_case,
            generation_seed=seed,
            composition_archetype=archetype,
        )
        bass_pat = _agent_rhythm_id(bass_pool, BASS_PATTERN_ALIASES, _AGENT_BASS_IDS)

    return drum_pat, bass_pat


def _validate_plan(state: SongState, plan: OrchestrationPlan) -> OrchestrationPlan:
    intent = state["intent"]
    proposal = state["technical_proposal"]
    strategies = state.get("strategies")
    return validate_orchestration(
        plan,
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        genre_tags=list(proposal.genre_tags),
        generation_seed=state.get("generation_seed", 0),
        style_profile=state.get("style_profile"),
        strategies=strategies,
        raw_prompt=intent.raw_prompt,
        creative_variation=state.get("creative_variation"),
        composition_archetype=state.get("composition_archetype"),
        lock_llm_ensemble="technical_spec" in (plan.ensemble_concept or "").lower(),
    )


def build_orchestration_from_technical_proposal(state: SongState) -> OrchestrationPlan | None:
    """Plan desde instruments[] del technical_spec (variación elegida por el LLM técnico)."""
    proposal = state["technical_proposal"]
    if not proposal or not proposal_has_orchestration(proposal):
        return None

    intent = state["intent"]
    strategies: GenerationStrategies | None = state.get("strategies")
    if not strategies:
        raise ValueError("build_orchestration_from_technical_proposal requiere strategies")

    archetype = state.get("composition_archetype")
    instruments = proposal_instruments_to_assignments(
        proposal, intent, composition_archetype=archetype,
    )
    if not instruments:
        return None

    texture = proposal.melody_texture or melody_texture_for_archetype(
        archetype or "default",
        proposal.energy_level,
        intent.use_case,
        "balanced",
    )
    drum_pat, bass_pat = _rhythm_patterns_from_state(state)
    concept = (proposal.ensemble_concept or "").strip() or "technical_spec/llm"

    plan = OrchestrationPlan(
        ensemble_concept=concept,
        instruments=instruments,
        melody_texture=texture,  # type: ignore[arg-type]
        drum_pattern=drum_pat,  # type: ignore[arg-type]
        bass_pattern=bass_pat,  # type: ignore[arg-type]
        arp_pattern=strategies.arp_pattern,
        harmony_pool=strategies.harmony_pool,
        stab_pattern=strategies.stab_pattern,
        perc_pattern=strategies.perc_pattern,
        pluck_pattern=strategies.pluck_pattern,
        counter_pattern=strategies.counter_pattern,
        echo_source=strategies.echo_source,
    )
    plan = apply_patterns_to_orchestration_plan(plan, proposal, strategies)
    return _validate_plan(state, plan)


def pick_orchestration_plan_deterministic(state: SongState) -> OrchestrationPlan:
    """Fallback: core + leads por género + patrones de strategies (seed)."""
    intent = state["intent"]
    proposal = state["technical_proposal"]
    strategies: GenerationStrategies | None = state.get("strategies")
    if not proposal or not strategies:
        raise ValueError("pick_orchestration_plan_deterministic requiere technical_proposal y strategies")

    seed = state.get("generation_seed", 0)
    archetype = state.get("composition_archetype")
    genre_tags = list(proposal.genre_tags)
    genre_mix = build_genre_mix(
        style_profile=state.get("style_profile"),
        proposal_tags=genre_tags,
        intent_tags=intent.style_tags,
        raw_prompt=intent.raw_prompt,
    )

    from cadence.music.instrument_catalog import max_optional_budget

    max_opt, max_lead = max_optional_budget(
        intent.use_case,
        proposal.energy_level,
        composition_archetype=archetype,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    max_opt, max_lead = adjust_optional_budget(
        max_opt,
        max_lead,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
        composition_archetype=archetype,
        energy_level=proposal.energy_level,
        use_case=intent.use_case,
    )

    lead_ids = select_fallback_lead_layers(
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        genre_tags=genre_tags,
        generation_seed=seed,
        composition_archetype=archetype,
    )
    if max_lead <= 0:
        lead_ids = set()
    elif len(lead_ids) > max_lead:
        lead_ids = set(sorted(lead_ids)[:max_lead])

    optional_support = []
    if max_opt > 0 and proposal.energy_level >= 3:
        if "pad" not in lead_ids and max_opt >= 1:
            optional_support.append("pad")
        if proposal.energy_level >= 4 and len(optional_support) + len(lead_ids) < max_opt:
            optional_support.append("perc_aux")

    from cadence.music.instrument_catalog import percussion_suppressed
    from cadence.music.texture_policy import schedule_core_layers

    suppress_drums = percussion_suppressed(
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        style_profile=state.get("style_profile"),
    )
    default_ids = schedule_core_layers(
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        percussion_suppressed=suppress_drums,
    )

    instruments: list[InstrumentAssignment] = []
    for iid in default_ids:
        instruments.append(_assignment(
            iid,
            generation_seed=seed + hash(iid) % 97,
            genre_tags=genre_tags,
            mood=intent.mood,
            use_case=intent.use_case,
            archetype=archetype,
            mix_level=_DEFAULT_MIX.get(iid),
        ))

    active_optional = sorted(lead_ids | set(optional_support))
    for iid in active_optional:
        instruments.append(_assignment(
            iid,
            generation_seed=seed + hash(iid) % 997,
            genre_tags=genre_tags,
            mood=intent.mood,
            use_case=intent.use_case,
            archetype=archetype,
        ))

    texture = melody_texture_for_archetype(
        archetype or "default",
        proposal.energy_level,
        intent.use_case,
        "balanced",
    )
    drum_pat, bass_pat = _rhythm_patterns_from_state(state)

    plan = OrchestrationPlan(
        ensemble_concept=f"deterministic/{archetype or 'default'}",
        instruments=instruments,
        melody_texture=texture,  # type: ignore[arg-type]
        drum_pattern=drum_pat,  # type: ignore[arg-type]
        bass_pattern=bass_pat,  # type: ignore[arg-type]
        arp_pattern=strategies.arp_pattern,
        harmony_pool=strategies.harmony_pool,
        stab_pattern=strategies.stab_pattern,
        perc_pattern=strategies.perc_pattern,
        pluck_pattern=strategies.pluck_pattern,
        counter_pattern=strategies.counter_pattern,
        echo_source=strategies.echo_source,
    )
    return _validate_plan(state, plan)


def pick_orchestration_plan(state: SongState) -> OrchestrationPlan:
    """
    Orquestación final: prioriza instruments del technical_spec (LLM);
    si instruments=[] usa fallback determinista por seed.
    """
    llm_plan = build_orchestration_from_technical_proposal(state)
    if llm_plan is not None:
        return llm_plan
    return pick_orchestration_plan_deterministic(state)
