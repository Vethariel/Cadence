"""Fusión de OrchestrationPlan → GenerationStrategies (sin LLM)."""

from __future__ import annotations

from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.harmonic_coherence import (
    active_instrument_ids_from_plan,
    resolve_echo_source_for_stack,
)
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
)
from cadence.music.repertoire_signals import resolve_harmony_pool_choice
from cadence.music.strategy_pools import ECHO_SOURCE_POOL
from cadence.schemas.song_state import GenerationStrategies, OrchestrationPlan


def apply_plan_to_strategies(
    strategies: GenerationStrategies | None,
    plan: OrchestrationPlan,
    *,
    energy_level: int = 3,
    use_case: str = "game",
) -> GenerationStrategies:
    """Sincroniza patrones drum/bass y overrides de capas desde el plan de orquestación."""
    base = strategies or GenerationStrategies(
        generation_seed=0,
        drum_pattern=plan.drum_pattern,
        bass_pattern=plan.bass_pattern,
    )
    updates: dict = {
        "drum_pattern": plan.drum_pattern,
        "bass_pattern": plan.bass_pattern,
    }
    if plan.arp_pattern in ARP_PATTERNS:
        updates["arp_pattern"] = plan.arp_pattern
    updates["harmony_pool"] = resolve_harmony_pool_choice(
        plan.harmony_pool or None,
        base.harmony_pool,
        energy_level=energy_level,
        use_case=use_case,
    )
    if plan.stab_pattern in STAB_PATTERN_POOL:
        updates["stab_pattern"] = plan.stab_pattern
    if plan.perc_pattern in PERC_PATTERN_POOL:
        updates["perc_pattern"] = plan.perc_pattern
    if plan.pluck_pattern in PLUCK_PATTERN_POOL:
        updates["pluck_pattern"] = plan.pluck_pattern
    if plan.counter_pattern in COUNTER_PATTERN_POOL:
        updates["counter_pattern"] = plan.counter_pattern
    if plan.echo_source in ECHO_SOURCE_POOL:
        updates["echo_source"] = plan.echo_source

    active_ids = active_instrument_ids_from_plan(plan)
    updates["echo_source"] = resolve_echo_source_for_stack(
        base.model_copy(update=updates),
        active_ids,
        energy_level=energy_level,
        use_case=use_case,
    )
    return base.model_copy(update=updates)
