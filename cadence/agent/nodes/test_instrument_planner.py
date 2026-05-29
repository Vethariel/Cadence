"""Tests del catálogo y arreglo desde orchestration_plan del agente."""

from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.instrument_planner import _apply_plan_to_strategies
from cadence.music.instrument_catalog import (
    apply_orchestration_gm,
    get_timbres,
    resolve_timbre,
    timbre_programs,
    validate_orchestration,
)
from cadence.instruments.registry import get_instrument, list_instruments
from cadence.music.instrument_catalog import is_drum
from cadence.music.strategy_pools import resolve_rhythm_patterns
from cadence.schemas.song_state import (
    GenerationStrategies,
    InstrumentAssignment,
    MusicalStyleProfile,
    OrchestrationPlan,
    RhythmEvent,
    Track,
)


def _plan(**kwargs) -> OrchestrationPlan:
    defaults = {
        "drum_pattern": "techno",
        "bass_pattern": "driving",
    }
    defaults.update(kwargs)
    return OrchestrationPlan(**defaults)


def _minimal_state(orchestration: OrchestrationPlan | None = None) -> dict:
    from cadence.agent.nodes.test_arrangement import _boss_fight_state
    state = _boss_fight_state()
    if orchestration:
        state["orchestration_plan"] = orchestration
    return state


def test_validate_orchestration_enforces_core():
    plan = _plan(
        ensemble_concept="Synthwave duel",
        instruments=[
            InstrumentAssignment(instrument_id="arp_synth", gm_program=98, display_name="Crystal", active=True),
        ],
    )
    validated = validate_orchestration(plan, use_case="game", energy_level=4)
    ids = {a.instrument_id for a in validated.instruments if a.active}
    assert "drums" in ids and "bass" in ids and "melody" in ids
    assert "arp_synth" in ids
    assert validated.drum_pattern == "techno"
    assert validated.bass_pattern == "driving"
    print("✓ test_validate_orchestration_enforces_core OK")


def test_validate_trims_excess_optionals_for_loop():
    plan = _plan(
        instruments=[
            InstrumentAssignment(instrument_id=iid, gm_program=80, active=True)
            for iid in (
                "drums", "bass", "melody", "pad", "countermelody",
                "echo_synth", "arp_synth", "chord_stab",
            )
        ],
    )
    validated = validate_orchestration(plan, use_case="loop", energy_level=3)
    optionals = [
        a.instrument_id for a in validated.instruments
        if a.instrument_id not in ("drums", "bass", "melody") and a.active
    ]
    assert len(optionals) == 0
    print("✓ test_validate_trims_excess_optionals_for_loop OK")


def test_timbre_catalog_covers_melodic_instruments():
    import cadence.instruments  # noqa: F401
    for iid in list_instruments():
        defn = get_instrument(iid)
        if is_drum(iid, defn.role):
            continue
        timbres = get_timbres(iid)
        assert len(timbres) >= 1, f"{iid} sin timbres en catálogo"
        assert all(0 <= p <= 127 for p, _ in timbres)
    print("✓ test_timbre_catalog_covers_melodic_instruments OK")


def test_resolve_timbre_snaps_to_catalog():
    allowed = timbre_programs("melody")
    prog, name = resolve_timbre("melody", 999, generation_seed=0)
    assert prog in allowed
    assert name
    prog2, name2 = resolve_timbre("melody", 81, generation_seed=0)
    assert prog2 == 81
    assert name2 == "Lead Sawtooth"
    print("✓ test_resolve_timbre_snaps_to_catalog OK")


def test_validate_uses_catalog_display_name():
    plan = _plan(
        instruments=[
            InstrumentAssignment(
                instrument_id="melody", gm_program=48,
                display_name="Nombre inventado por LLM", active=True,
            ),
        ],
    )
    validated = validate_orchestration(plan, use_case="game", energy_level=4)
    melody = next(a for a in validated.instruments if a.instrument_id == "melody")
    assert melody.display_name == "String Ensemble 1"
    assert melody.gm_program == 48
    print("✓ test_validate_uses_catalog_display_name OK")


def test_agent_rhythm_patterns_applied_to_strategies():
    plan = _plan(drum_pattern="breakbeat", bass_pattern="syncopated")
    strategies = GenerationStrategies(
        generation_seed=42,
        drum_pattern="default",
        bass_pattern="root_fifth",
    )
    merged = _apply_plan_to_strategies(strategies, plan)
    assert merged.drum_pattern == "breakbeat"
    assert merged.bass_pattern == "syncopated"
    assert merged.generation_seed == 42
    print("✓ test_agent_rhythm_patterns_applied_to_strategies OK")


def test_agent_layer_patterns_applied_to_strategies():
    plan = _plan(
        stab_pattern="dubstep_off",
        perc_pattern="syncopated",
        pluck_pattern="sixteenth",
        arp_pattern="cascade",
        harmony_pool="aggressive",
    )
    merged = _apply_plan_to_strategies(
        GenerationStrategies(generation_seed=7, harmony_pool="classic"),
        plan,
        energy_level=5,
        use_case="game",
    )
    assert merged.stab_pattern == "dubstep_off"
    assert merged.perc_pattern == "syncopated"
    assert merged.pluck_pattern == "sixteenth"
    assert merged.arp_pattern == "cascade"
    assert merged.harmony_pool == "aggressive"
    invalid = _apply_plan_to_strategies(
        merged,
        _plan(stab_pattern="not_a_pattern", perc_pattern="", pluck_pattern=""),
    )
    assert invalid.stab_pattern == "dubstep_off"
    print("✓ test_agent_layer_patterns_applied_to_strategies OK")


def test_resolve_rhythm_patterns_fallback_by_genre():
    drum, bass = resolve_rhythm_patterns(
        "invalid", "invalid",
        genre_tags=["dubstep"],
        energy_level=5,
        use_case="game",
        generation_seed=0,
    )
    assert drum == "dubstep"
    assert bass in ("root_fifth", "driving", "syncopated", "pulse")
    print("✓ test_resolve_rhythm_patterns_fallback_by_genre OK")


def test_loop_energy_uses_pulse_bass_fallback():
    _, bass = resolve_rhythm_patterns(
        "techno", "invalid",
        genre_tags=[],
        energy_level=2,
        use_case="loop",
        generation_seed=0,
    )
    assert bass == "pulse"
    print("✓ test_loop_energy_uses_pulse_bass_fallback OK")


def test_arrangement_from_orchestration_plan():
    plan = _plan(
        ensemble_concept="Industrial stack",
        drum_pattern="techno",
        bass_pattern="driving",
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True, mix_level=-10),
            InstrumentAssignment(instrument_id="bass", gm_program=38, active=True, mix_level=-6),
            InstrumentAssignment(instrument_id="melody", gm_program=81, active=True, mix_level=-8),
            InstrumentAssignment(instrument_id="chord_stab", gm_program=62, active=True, mix_level=-13),
            InstrumentAssignment(instrument_id="arp_synth", gm_program=98, active=True, mix_level=-12),
        ],
    )
    state = _minimal_state(plan)
    state["strategies"] = _apply_plan_to_strategies(state.get("strategies"), plan)
    arrangement = arrangement_planner_node(state)["arrangement"]
    ids = {l.instrument_id for l in arrangement.layers}
    assert "chord_stab" in ids
    assert "arp_synth" in ids
    assert "echo_synth" in ids
    assert "countermelody" in ids
    assert state["strategies"].drum_pattern == "techno"
    print("✓ test_arrangement_from_orchestration_plan OK")


def test_apply_orchestration_gm():
    plan = _plan(
        instruments=[
            InstrumentAssignment(
                instrument_id="melody", gm_program=48,
                display_name="String Ensemble", active=True,
            ),
        ],
    )
    tracks = [
        Track(id="melody", instrument_id="melody", instrument="Lead", role="lead", events=[
            RhythmEvent(t=0, type="note", pitch=60, duration_ms=500, velocity=90, beat_index=0),
        ]),
    ]
    out = apply_orchestration_gm(tracks, plan)
    assert out[0].gm_program == 48
    assert out[0].instrument == "String Ensemble"
    print("✓ test_apply_orchestration_gm OK")


def test_melody_chord_stab_cannot_share_gm_program():
    plan = _plan(
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=39, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=81, active=True),
            InstrumentAssignment(instrument_id="chord_stab", gm_program=81, active=True),
        ],
    )
    validated = validate_orchestration(
        plan,
        use_case="game",
        energy_level=5,
        generation_seed=42,
    )
    by_id = {a.instrument_id: a for a in validated.instruments}
    assert by_id["melody"].gm_program != by_id["chord_stab"].gm_program
    print("✓ test_melody_chord_stab_cannot_share_gm_program OK")


def test_style_profile_avoids_incoherent_timbres():
    profile = MusicalStyleProfile(
        avoid=["calliope", "music box", "orchestral strings"],
    )
    plan = _plan(
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=39, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=82, active=True),
            InstrumentAssignment(instrument_id="pad", gm_program=50, active=True),
        ],
    )
    validated = validate_orchestration(
        plan,
        use_case="game",
        energy_level=5,
        generation_seed=42,
        style_profile=profile,
    )
    by_id = {a.instrument_id: a for a in validated.instruments}
    assert by_id["melody"].gm_program != 82
    assert by_id["pad"].gm_program != 50
    print("✓ test_style_profile_avoids_incoherent_timbres OK")


def test_style_profile_no_avoid_keeps_programs():
    plan = _plan(
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=39, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=81, active=True),
        ],
    )
    validated = validate_orchestration(
        plan,
        use_case="game",
        energy_level=4,
        generation_seed=12345,
    )
    mel = next(a for a in validated.instruments if a.instrument_id == "melody")
    assert mel.gm_program == 81
    print("✓ test_style_profile_no_avoid_keeps_programs OK")


if __name__ == "__main__":
    test_validate_orchestration_enforces_core()
    test_validate_trims_excess_optionals_for_loop()
    test_timbre_catalog_covers_melodic_instruments()
    test_resolve_timbre_snaps_to_catalog()
    test_validate_uses_catalog_display_name()
    test_agent_rhythm_patterns_applied_to_strategies()
    test_agent_layer_patterns_applied_to_strategies()
    test_resolve_rhythm_patterns_fallback_by_genre()
    test_loop_energy_uses_pulse_bass_fallback()
    test_arrangement_from_orchestration_plan()
    test_apply_orchestration_gm()
    test_melody_chord_stab_cannot_share_gm_program()
    test_style_profile_avoids_incoherent_timbres()
    test_style_profile_no_avoid_keeps_programs()
    print("\nAll instrument planner tests passed.")
