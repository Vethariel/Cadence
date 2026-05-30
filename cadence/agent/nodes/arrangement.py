"""Planificador de arreglo — ejecuta el plan instrumental del agente o fallback determinista."""

from cadence.schemas.song_state import (
    ArrangementPlan,
    LayerSpec,
    OrchestrationPlan,
    SongState,
)
from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.instrument_catalog import active_instrument_ids, select_fallback_lead_layers
from cadence.music.repertoire_signals import (
    instruments_implied_by_strategies,
    percussion_suppressed,
)
from cadence.music.style_profile import effective_genre_tags
from cadence.music.layer_schedule import (
    DENSITY_ARP,
    DENSITY_CHORD_STAB,
    DENSITY_COUNTER,
    DENSITY_ECHO,
    DENSITY_PERC,
    DENSITY_PLUCK,
    build_layer_schedule,
)
from cadence.music.texture_policy import arrangement_required_layers

CORE_LAYERS = [
    LayerSpec(
        instrument_id="drums",
        active_sections=["*"],
        pattern_strategy="loop_1bar",
        mix_level=-10.0,
    ),
    LayerSpec(
        instrument_id="bass",
        active_sections=["*"],
        pattern_strategy="loop_1bar",
        mix_level=-6.0,
    ),
    LayerSpec(
        instrument_id="melody",
        active_sections=["*"],
        pattern_strategy="phrase_4bar",
        mix_level=-8.0,
        min_density=0.2,
    ),
]

HIGH_ENERGY_SECTIONS = {"drop", "climax", "chorus", "build-up", "buildup", "verse", "bridge", "main_theme"}
FX_TRANSITIONS = {"riser", "filter_sweep", "pickup"}

LEAD_OPTIONALS = ("countermelody", "echo_synth", "arp_synth", "chord_stab", "synth_pluck")

LAYER_DEFAULTS: dict[str, tuple[str, float, float]] = {
    "drums": ("loop_1bar", -10.0, 0.0),
    "bass": ("loop_1bar", -6.0, 0.0),
    "melody": ("phrase_4bar", -8.0, 0.2),
    "pad": ("chord_sustain", -14.0, 0.25),
    "chord_stab": ("loop_1bar", -13.0, DENSITY_CHORD_STAB),
    "perc_aux": ("loop_1bar", -12.0, DENSITY_PERC),
    "fx_riser": ("one_shot", -8.0, 0.0),
    "countermelody": ("phrase_4bar", -11.0, DENSITY_COUNTER),
    "echo_synth": ("generative_llm", -14.0, DENSITY_ECHO),
    "arp_synth": ("loop_1bar", -12.0, DENSITY_ARP),
    "synth_pluck": ("loop_1bar", -11.0, DENSITY_PLUCK),
}


def _mix_for(plan: OrchestrationPlan | None, instrument_id: str, default: float) -> float:
    if not plan:
        return default
    for a in plan.instruments:
        if a.instrument_id == instrument_id and a.active:
            return a.mix_level
    return default


def _layer_spec(
    instrument_id: str,
    active_sections: list[str],
    plan: OrchestrationPlan | None,
) -> LayerSpec:
    strategy, default_mix, min_density = LAYER_DEFAULTS.get(
        instrument_id,
        ("loop_1bar", -10.0, 0.0),
    )
    return LayerSpec(
        instrument_id=instrument_id,
        active_sections=active_sections,
        pattern_strategy=strategy,
        mix_level=_mix_for(plan, instrument_id, default_mix),
        min_density=min_density,
    )


def _effective_instruments(state: SongState, plan: OrchestrationPlan) -> set[str]:
    """Instrumentos activos del plan + strategies, con presupuesto lead general."""
    from cadence.music.harmonic_coherence import apply_lead_support_cap

    chosen = active_instrument_ids(plan)
    proposal = state.get("technical_proposal")
    intent = state["intent"]
    energy = proposal.energy_level if proposal else 3
    strategies = state.get("strategies")
    chosen |= instruments_implied_by_strategies(
        strategies,
        energy_level=energy,
        use_case=intent.use_case,
    )
    profile = state.get("style_profile")
    if percussion_suppressed(
        use_case=intent.use_case,
        energy_level=energy,
        style_profile=profile,
    ):
        chosen.discard("drums")

    return apply_lead_support_cap(
        chosen,
        energy_level=energy,
        use_case=intent.use_case,
    )


def _ensure_texture_bed_layers(
    layers: list[LayerSpec],
    structure,
    use_case: str,
) -> list[LayerSpec]:
    """Loop/cutscene: pad en todas las secciones para cama continua."""
    if (use_case or "game").lower() not in ("loop", "cutscene"):
        return layers
    ids = {l.instrument_id for l in layers}
    all_sections = list(structure.sections)
    out = list(layers)
    if "pad" not in ids:
        out.append(LayerSpec(
            instrument_id="pad",
            active_sections=all_sections or ["*"],
            pattern_strategy="chord_sustain",
            mix_level=-14.0,
            min_density=0.0,
        ))
    if "bass" not in ids:
        out.append(LayerSpec(
            instrument_id="bass",
            active_sections=["*"],
            pattern_strategy="loop_1bar",
            mix_level=-6.0,
            min_density=0.0,
        ))
    return out


def _build_layers_from_orchestration(
    state: SongState,
    plan: OrchestrationPlan,
) -> list[LayerSpec]:
    """Materializa capas según el conjunto elegido por el agente."""
    structure = state["structure"]
    narrative = state.get("narrative")
    intent_map = section_intent_map(narrative)
    chosen = _effective_instruments(state, plan)

    layers: list[LayerSpec] = []
    for core in ("drums", "bass", "melody"):
        if core in chosen:
            layers.append(_layer_spec(core, ["*"], plan))

    pad_sections = []
    chord_stab_sections = []
    perc_sections = []
    fx_sections = []
    counter_sections = []
    echo_sections = []
    arp_sections = []

    for section_id in structure.sections:
        sec_intent = intent_map.get(section_id)
        density = sec_intent.density if sec_intent else 0.5

        if density >= 0.25 and "pad" in chosen:
            pad_sections.append(section_id)
        if density >= DENSITY_CHORD_STAB and "chord_stab" in chosen:
            chord_stab_sections.append(section_id)
        if density >= DENSITY_PERC and section_id in HIGH_ENERGY_SECTIONS and "perc_aux" in chosen:
            perc_sections.append(section_id)
        if sec_intent and sec_intent.transition_out in FX_TRANSITIONS and "fx_riser" in chosen:
            fx_sections.append(section_id)
        if density >= DENSITY_COUNTER and "countermelody" in chosen:
            counter_sections.append(section_id)
        if density >= DENSITY_ECHO and "echo_synth" in chosen:
            echo_sections.append(section_id)
        if density >= DENSITY_ARP and "arp_synth" in chosen:
            arp_sections.append(section_id)

    pluck_sections = []
    for section_id in structure.sections:
        sec_intent = intent_map.get(section_id)
        density = sec_intent.density if sec_intent else 0.5
        if (
            density >= DENSITY_PLUCK
            and section_id in HIGH_ENERGY_SECTIONS
            and "synth_pluck" in chosen
        ):
            pluck_sections.append(section_id)

    optional_sections = [
        ("pad", pad_sections),
        ("chord_stab", chord_stab_sections),
        ("perc_aux", perc_sections),
        ("fx_riser", fx_sections),
        ("countermelody", counter_sections),
        ("echo_synth", echo_sections),
        ("arp_synth", arp_sections),
        ("synth_pluck", pluck_sections),
    ]
    for iid, sections in optional_sections:
        if sections:
            layers.append(_layer_spec(iid, sections, plan))

    return _ensure_texture_bed_layers(
        layers, structure, state["intent"].use_case,
    )


def _build_layers_deterministic(state: SongState) -> list[LayerSpec]:
    """Fallback sin plan del agente — capas opcionales por género y seed."""
    narrative = state.get("narrative")
    structure = state["structure"]
    intent_map = section_intent_map(narrative)
    intent = state["intent"]
    proposal = state.get("technical_proposal")

    use_case = intent.use_case
    energy = proposal.energy_level if proposal else 3
    genre_tags = effective_genre_tags(state)
    seed = state.get("generation_seed", 0)

    allowed_leads = select_fallback_lead_layers(
        use_case=use_case,
        energy_level=energy,
        genre_tags=genre_tags,
        generation_seed=seed,
    )

    profile = state.get("style_profile")
    if percussion_suppressed(
        use_case=use_case,
        energy_level=energy,
        style_profile=profile,
    ):
        layers = [
            LayerSpec(
                instrument_id="bass",
                active_sections=["*"],
                pattern_strategy="loop_1bar",
                mix_level=-6.0,
            ),
            LayerSpec(
                instrument_id="melody",
                active_sections=["*"],
                pattern_strategy="phrase_4bar",
                mix_level=-8.0,
                min_density=0.2,
            ),
        ]
    else:
        layers = list(CORE_LAYERS)

    pad_sections = []
    chord_stab_sections = []
    perc_sections = []
    fx_sections = []

    for section_id in structure.sections:
        sec_intent = intent_map.get(section_id)
        density = sec_intent.density if sec_intent else 0.5

        if density >= 0.25:
            pad_sections.append(section_id)
        if density >= DENSITY_CHORD_STAB and "chord_stab" in allowed_leads:
            chord_stab_sections.append(section_id)
        if density >= DENSITY_PERC and section_id in HIGH_ENERGY_SECTIONS:
            perc_sections.append(section_id)
        if sec_intent and sec_intent.transition_out in FX_TRANSITIONS:
            fx_sections.append(section_id)

    if pad_sections:
        layers.append(LayerSpec(
            instrument_id="pad",
            active_sections=pad_sections,
            pattern_strategy="chord_sustain",
            mix_level=-14.0,
            min_density=0.25,
        ))

    if chord_stab_sections:
        layers.append(LayerSpec(
            instrument_id="chord_stab",
            active_sections=chord_stab_sections,
            pattern_strategy="loop_1bar",
            mix_level=-13.0,
            min_density=DENSITY_CHORD_STAB,
        ))

    if perc_sections:
        layers.append(LayerSpec(
            instrument_id="perc_aux",
            active_sections=perc_sections,
            pattern_strategy="loop_1bar",
            mix_level=-12.0,
            min_density=DENSITY_PERC,
        ))

    if fx_sections:
        layers.append(LayerSpec(
            instrument_id="fx_riser",
            active_sections=fx_sections,
            pattern_strategy="one_shot",
            mix_level=-8.0,
            min_density=0.0,
        ))

    if "countermelody" in allowed_leads:
        counter_sections = [
            s for s in structure.sections
            if (intent_map.get(s) and intent_map[s].density >= DENSITY_COUNTER)
        ]
        if counter_sections:
            layers.append(LayerSpec(
                instrument_id="countermelody",
                active_sections=counter_sections,
                pattern_strategy="phrase_4bar",
                mix_level=-11.0,
                min_density=DENSITY_COUNTER,
            ))

    if "echo_synth" in allowed_leads:
        echo_sections = [
            s for s in structure.sections
            if (intent_map.get(s) and intent_map[s].density >= DENSITY_ECHO)
        ]
        if echo_sections:
            layers.append(LayerSpec(
                instrument_id="echo_synth",
                active_sections=echo_sections,
                pattern_strategy="generative_llm",
                mix_level=-14.0,
                min_density=DENSITY_ECHO,
            ))

    if "arp_synth" in allowed_leads:
        arp_sections = [
            s for s in structure.sections
            if (intent_map.get(s) and intent_map[s].density >= DENSITY_ARP)
        ]
        if arp_sections:
            layers.append(LayerSpec(
                instrument_id="arp_synth",
                active_sections=arp_sections,
                pattern_strategy="loop_1bar",
                mix_level=-12.0,
                min_density=DENSITY_ARP,
            ))

    if "synth_pluck" in allowed_leads:
        pluck_sections = [
            s for s in structure.sections
            if (
                intent_map.get(s)
                and intent_map[s].density >= DENSITY_PLUCK
                and s in HIGH_ENERGY_SECTIONS
            )
        ]
        if pluck_sections:
            layers.append(LayerSpec(
                instrument_id="synth_pluck",
                active_sections=pluck_sections,
                pattern_strategy="loop_1bar",
                mix_level=-11.0,
                min_density=DENSITY_PLUCK,
            ))

    return _ensure_texture_bed_layers(layers, structure, use_case)


def arrangement_planner_node(state: SongState) -> dict:
    """
    Construye ArrangementPlan a partir del orchestration_plan del agente
    (cuándo entra cada capa según narrativa) o fallback determinista.
    """
    structure = state["structure"]
    narrative = state.get("narrative")
    intent_map = section_intent_map(narrative)
    seed = state.get("generation_seed", 0)
    orchestration = state.get("orchestration_plan")
    proposal = state.get("technical_proposal")
    energy = proposal.energy_level if proposal else 3
    intent = state.get("intent")
    use_case = intent.use_case if intent else "game"

    profile = state.get("style_profile")
    suppress_drums = percussion_suppressed(
        use_case=use_case,
        energy_level=energy,
        style_profile=profile,
    )

    if orchestration:
        layers = _build_layers_from_orchestration(state, orchestration)
    else:
        layers = _build_layers_deterministic(state)

    layers = _ensure_texture_bed_layers(layers, structure, use_case)

    development = state.get("development")
    texture_mode = development.texture_mode if development else "staggered"
    layer_ids = [l.instrument_id for l in layers]
    optional_count = len([i for i in layer_ids if i not in ("drums", "bass", "melody")])
    if (
        development
        and use_case == "game"
        and energy >= 4
        and optional_count >= 4
        and texture_mode != "bedded"
    ):
        texture_mode = "simultaneous"
    schedule = build_layer_schedule(
        structure,
        layer_ids,
        intent_map,
        generation_seed=seed,
        energy_level=energy,
        use_case=use_case,
        development=development,
        texture_mode=texture_mode,
        percussion_suppressed=suppress_drums,
    )

    arrangement = ArrangementPlan(
        layers=layers,
        layer_schedule=schedule,
        required_layers=arrangement_required_layers(use_case, suppress_drums),
    )

    return {"arrangement": arrangement}
