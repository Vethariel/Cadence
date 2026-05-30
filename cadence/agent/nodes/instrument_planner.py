"""Nodo agente: conjunto instrumental, timbres GM y patrones drum/bass."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from cadence.config import settings
from cadence.music.narrative_anchors import format_anchors_for_llm
from cadence.music.creative_variation import format_variation_for_llm
from cadence.music.section_refs import format_section_ids_for_llm
from cadence.music.style_profile import effective_genre_tags
from cadence.music.style_archetype import get_composition_archetype
from cadence.music.seed_policy import node_temperature, seed_for_state
from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.instrument_catalog import (
    CORE_INSTRUMENTS,
    format_catalog_for_llm,
    format_timbre_catalog_for_llm,
    validate_orchestration,
)
from cadence.music.style_profile import format_profile_for_llm
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
    format_layer_patterns_for_llm,
)
from cadence.music.harmonic_coherence import (
    active_instrument_ids_from_plan,
    resolve_echo_source_for_stack,
)
from cadence.music.repertoire_signals import resolve_harmony_pool_choice
from cadence.music.strategy_pools import ECHO_SOURCE_POOL
from cadence.music.strategy_pools import (
    BASS_POOL,
    DRUM_POOL,
    HARMONY_POOL,
    format_rhythm_patterns_for_llm,
)
from cadence.schemas.song_state import (
    GenerationStrategies,
    OrchestrationPlan,
    SongState,
)


class _AgentOrchestrationOutput(OrchestrationPlan):
    """Mismo schema que OrchestrationPlan — salida estructurada del LLM."""


def _apply_plan_to_strategies(
    strategies: GenerationStrategies | None,
    plan: OrchestrationPlan,
    *,
    energy_level: int = 3,
    use_case: str = "game",
) -> GenerationStrategies:
    """Drum/bass siempre vienen del agente; arp/harmony solo si el agente los override."""
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


def instrument_planner_node(state: SongState) -> dict:
    """
    El agente elige ensemble, timbres GM y patrones drum/bass
    desde los catálogos registrados.
    """
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    profile = state.get("style_profile")
    narrative = state.get("narrative")
    strategies = state.get("strategies")
    seed = seed_for_state(state, "instrument_planner") or state.get("generation_seed", 0)
    coherence = state.get("style_coherence")
    retries = state.get("style_coherence_retries", 0)

    extra: dict = {}
    if coherence and not coherence.passed and retries < 1:
        extra["style_coherence_retries"] = retries + 1

    if not proposal:
        raise ValueError("instrument_planner requiere technical_proposal")

    genre_tags = ", ".join(proposal.genre_tags)
    structure = state.get("structure")
    contract = state.get("narrative_contract")
    logline = narrative.logline if narrative else ""
    arc = (
        contract.arc_type if contract
        else (narrative.arc_type if narrative else "")
    )
    archetype = get_composition_archetype(state)

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=node_temperature("instrument_planner"),
    ).with_structured_output(_AgentOrchestrationOutput)

    from cadence.music.ensemble_policy import format_ensemble_hint_for_llm

    energy = proposal.energy_level
    ensemble_hint = format_ensemble_hint_for_llm(
        genre_tags=effective_genre_tags(state),
        composition_archetype=archetype,
        use_case=intent.use_case,
        energy_level=energy,
    )

    catalog = format_catalog_for_llm()
    timbre_catalog = format_timbre_catalog_for_llm()
    rhythm_catalog = format_rhythm_patterns_for_llm()
    layer_catalog = format_layer_patterns_for_llm()
    arp_opts = ", ".join(ARP_PATTERNS)
    harmony_opts = ", ".join(HARMONY_POOL)

    system = SystemMessage(content=(
        "Eres un arreglista de videojuegos. Diseña el CONJUNTO INSTRUMENTAL "
        "y la base rítmica de una pieza.\n\n"
        "Reglas:\n"
        f"- Siempre incluye y activa: {', '.join(sorted(CORE_INSTRUMENTS))}.\n"
        "- Elige capas opcionales (pad, countermelody, echo_synth, arp_synth, "
        "chord_stab, synth_pluck, perc_aux, fx_riser) según mood, género y use_case.\n"
        "- TIMBRE OBLIGATORIO: para cada instrumento activo (excepto drums/perc), "
        "asigna gm_program de la lista TIMBRES DISPONIBLES de ese instrument_id. "
        "No uses valores fuera de catálogo.\n"
        "- El conjunto de timbres debe ser coherente con el perfil de estilo y el prompt.\n"
        "- Respeta la lista EVITAR del perfil (no calliope en dubstep, etc.).\n"
        "- mix_level en dB aproximado (-24 a 0): drums ~-10, bass ~-6, melody ~-8, "
        "pads/FX más bajo.\n"
        "- melody_texture: sparse | balanced | dense | percussive.\n"
        f"- drum_pattern OBLIGATORIO: uno de [{', '.join(DRUM_POOL)}].\n"
        f"- bass_pattern OBLIGATORIO: uno de [{', '.join(BASS_POOL)}].\n"
        "- drum y bass deben ser coherentes entre sí y con el género/energía.\n"
        "- Varía ensemble y ritmo respecto a defaults genéricos.\n"
        "- arp_pattern y harmony_pool: opcional; vacío o elige de "
        f"arp [{arp_opts}], harmony [{harmony_opts}].\n"
        "- stab_pattern, perc_pattern, pluck_pattern, counter_pattern: opcional; vacío "
        "si no activas esa capa, o elige del catálogo de patrones de capas.\n"
        "- echo_source: auto | melody | arp_synth | chord_stab (eco de esa capa; "
        "auto = primera con notas).\n"
        "- Si activas chord_stab → stab_pattern. perc_aux → perc_pattern. "
        "synth_pluck → pluck_pattern. countermelody → counter_pattern.\n"
        "- active_sections y planificación: usa EXACTAMENTE los section IDs canónicos "
        "indicados en el mensaje humano.\n"
        f"{ensemble_hint}\n"
        "Responde SOLO con el objeto estructurado."
    ))

    dev = state.get("development")
    dev_hint = ""
    if dev:
        seg_lines = []
        for sd in dev.sections:
            if sd.segments:
                seg_lines.append(
                    f"  {sd.section_id}: {len(sd.segments)} micro-arcos de orquestación"
                )
        if seg_lines:
            dev_hint = (
                f"\nDesarrollo ({dev.texture_mode}): el schedule añadirá/quitará capas "
                f"por segmento:\n" + "\n".join(seg_lines) + "\n"
            )

    human_parts = [
        f"Prompt: {intent.raw_prompt}",
        f"Uso: {intent.use_case} | Mood: {intent.mood}",
        f"Géneros: {genre_tags} | Energía: {proposal.energy_level}/5",
        f"Key: {proposal.key} {proposal.mode} | BPM: {proposal.bpm}",
        f"Arquetipo compositivo: {archetype}",
        f"Narrativa: {logline} (arco: {arc})",
        dev_hint,
        "",
        format_section_ids_for_llm(state),
        "",
        format_anchors_for_llm(state.get("narrative_anchors")),
        "",
        format_variation_for_llm(state.get("creative_variation")),
        "",
        format_profile_for_llm(profile),
        "",
        rhythm_catalog,
        "",
        layer_catalog,
        "",
        timbre_catalog,
        "",
        catalog,
        "",
        "Define el plan completo: ensemble, drum_pattern, bass_pattern, "
        "patrones de capas activas y gm_program por instrumento.",
    ]
    if coherence and not coherence.passed:
        human_parts.insert(
            7,
            "REVISIÓN — coherencia anterior falló:\n"
            + "\n".join(f"- {i}" for i in coherence.issues),
        )

    human = HumanMessage(content="\n".join(human_parts))

    raw: OrchestrationPlan = llm.invoke([system, human])
    plan = validate_orchestration(
        raw,
        use_case=intent.use_case,
        energy_level=proposal.energy_level,
        genre_tags=proposal.genre_tags,
        generation_seed=seed,
        style_profile=profile,
        strategies=strategies,
        raw_prompt=intent.raw_prompt,
        creative_variation=state.get("creative_variation"),
        composition_archetype=archetype,
    )

    return {
        "orchestration_plan": plan,
        "strategies": _apply_plan_to_strategies(
            strategies,
            plan,
            energy_level=proposal.energy_level,
            use_case=intent.use_case,
        ),
        **extra,
    }
