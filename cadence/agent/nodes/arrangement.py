"""Planificador determinista de arreglo — qué capas entran y cuándo."""

from cadence.schemas.song_state import ArrangementPlan, LayerSpec, SongState
from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.layer_schedule import (
    DENSITY_ARP,
    DENSITY_CHORD_STAB,
    DENSITY_COUNTER,
    DENSITY_ECHO,
    DENSITY_PERC,
    build_layer_schedule,
)

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

HIGH_ENERGY_SECTIONS = {"drop", "climax", "chorus", "build-up", "verse"}
FX_TRANSITIONS = {"riser", "filter_sweep", "pickup"}


def arrangement_planner_node(state: SongState) -> dict:
    """
    Decide qué instrumentos componen la pieza según narrativa,
    densidad y transiciones. Extensible vía LayerSpec.
    """
    narrative = state.get("narrative")
    structure = state["structure"]
    intent_map = section_intent_map(narrative)

    layers = list(CORE_LAYERS)

    pad_sections = []
    chord_stab_sections = []
    perc_sections = []
    fx_sections = []

    for section_id in structure.sections:
        intent = intent_map.get(section_id)
        density = intent.density if intent else 0.5

        if density >= 0.25:
            pad_sections.append(section_id)
        if density >= DENSITY_CHORD_STAB:
            chord_stab_sections.append(section_id)
        if density >= DENSITY_PERC and section_id in HIGH_ENERGY_SECTIONS:
            perc_sections.append(section_id)
        if intent and intent.transition_out in FX_TRANSITIONS:
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
            mix_level=-11.0,
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

    counter_sections = [
        s for s in structure.sections
        if (intent_map.get(s) and intent_map[s].density >= DENSITY_COUNTER)
    ]
    if counter_sections:
        layers.append(LayerSpec(
            instrument_id="countermelody",
            active_sections=counter_sections,
            pattern_strategy="phrase_4bar",
            mix_level=-10.0,
            min_density=DENSITY_COUNTER,
        ))

    echo_sections = [
        s for s in structure.sections
        if (intent_map.get(s) and intent_map[s].density >= DENSITY_ECHO)
    ]
    if echo_sections:
        layers.append(LayerSpec(
            instrument_id="echo_synth",
            active_sections=echo_sections,
            pattern_strategy="generative_llm",
            mix_level=-12.0,
            min_density=DENSITY_ECHO,
        ))

    arp_sections = [
        s for s in structure.sections
        if (intent_map.get(s) and intent_map[s].density >= DENSITY_ARP)
    ]
    if arp_sections:
        layers.append(LayerSpec(
            instrument_id="arp_synth",
            active_sections=arp_sections,
            pattern_strategy="loop_1bar",
            mix_level=-11.0,
            min_density=DENSITY_ARP,
        ))

    layer_ids = [l.instrument_id for l in layers]
    schedule = build_layer_schedule(
        structure,
        layer_ids,
        intent_map,
        generation_seed=state.get("generation_seed", 0),
    )

    arrangement = ArrangementPlan(
        layers=layers,
        layer_schedule=schedule,
        required_layers=["drums", "bass", "melody"],
    )

    return {"arrangement": arrangement}
