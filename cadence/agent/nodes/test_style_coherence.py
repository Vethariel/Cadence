"""Tests deterministas de style_coherence (sin LLM)."""

from cadence.agent.nodes.style_coherence import (
    apply_timbre_fixes,
    route_after_style_coherence,
    style_coherence_node,
)
from cadence.music.instrument_catalog import validate_orchestration
from cadence.schemas.song_state import (
    InstrumentAssignment,
    OrchestrationPlan,
    StyleCoherenceVerdict,
    TimbreFix,
)
from cadence.test_fixtures.pipeline_coherence import build_aligned_pipeline_state


def _minimal_plan(**kwargs) -> OrchestrationPlan:
    defaults = {
        "ensemble_concept": "Techno stack",
        "drum_pattern": "techno",
        "bass_pattern": "driving",
        "instruments": [
            InstrumentAssignment(
                instrument_id="drums", gm_program=0, active=True, mix_level=-10,
            ),
            InstrumentAssignment(
                instrument_id="bass", gm_program=38, active=True, mix_level=-6,
            ),
            InstrumentAssignment(
                instrument_id="melody", gm_program=81, active=True, mix_level=-8,
            ),
            InstrumentAssignment(
                instrument_id="chord_stab", gm_program=62, active=True, mix_level=-13,
            ),
        ],
    }
    defaults.update(kwargs)
    return OrchestrationPlan(**defaults)


def test_apply_timbre_fixes_snaps_to_catalog():
    plan = _minimal_plan()
    fixes = [TimbreFix(instrument_id="melody", gm_program=81, reason="ok")]
    fixed = apply_timbre_fixes(plan, fixes, generation_seed=99)
    melody = next(a for a in fixed.instruments if a.instrument_id == "melody")
    assert melody.gm_program == 81
    print("✓ test_apply_timbre_fixes_snaps_to_catalog OK")


def test_apply_timbre_fixes_separates_melody_and_stab():
    plan = _minimal_plan()
    fixes = [
        TimbreFix(instrument_id="melody", gm_program=80, reason="lead"),
        TimbreFix(instrument_id="chord_stab", gm_program=62, reason="stab"),
    ]
    fixed = apply_timbre_fixes(plan, fixes, generation_seed=7)
    gm = {a.instrument_id: a.gm_program for a in fixed.instruments if a.active}
    assert gm["melody"] != gm["chord_stab"]
    print("✓ test_apply_timbre_fixes_separates_melody_and_stab OK")


def test_route_retries_instrument_planner_without_fixes():
    state = {
        "style_coherence": StyleCoherenceVerdict(
            passed=False, issues=["incoherent"], timbre_fixes=[],
        ),
        "style_coherence_retries": 0,
    }
    assert route_after_style_coherence(state) == "instrument_planner"
    state["style_coherence_retries"] = 1
    assert route_after_style_coherence(state) == "arrangement_planner"
    print("✓ test_route_retries_instrument_planner_without_fixes OK")


def test_route_proceeds_when_passed_or_fixes_present():
    passed = {"style_coherence": StyleCoherenceVerdict(passed=True)}
    assert route_after_style_coherence(passed) == "arrangement_planner"
    with_fixes = {
        "style_coherence": StyleCoherenceVerdict(
            passed=False,
            timbre_fixes=[TimbreFix(instrument_id="melody", gm_program=80)],
        ),
        "style_coherence_retries": 0,
    }
    assert route_after_style_coherence(with_fixes) == "arrangement_planner"
    print("✓ test_route_proceeds_when_passed_or_fixes_present OK")


def test_style_coherence_node_without_plan():
    state = build_aligned_pipeline_state(generation_seed=10)
    state.pop("orchestration_plan", None)
    out = style_coherence_node(state)
    assert out["style_coherence"].passed is False
    assert "orchestration_plan" in out["style_coherence"].issues[0].lower()
    print("✓ test_style_coherence_node_without_plan OK")


def test_validate_orchestration_respects_contract_sections_in_state():
    """Tras align, validate no rompe el plan y mantiene núcleo."""
    state = build_aligned_pipeline_state(generation_seed=55)
    plan = _minimal_plan()
    validated = validate_orchestration(
        plan,
        use_case=state["intent"].use_case,
        energy_level=state["technical_proposal"].energy_level,
        generation_seed=state["generation_seed"],
        raw_prompt=state["intent"].raw_prompt,
        strategies=state.get("strategies"),
        composition_archetype=state.get("composition_archetype"),
    )
    active = {a.instrument_id for a in validated.instruments if a.active}
    assert {"drums", "bass", "melody"} <= active
    print("✓ test_validate_orchestration_respects_contract_sections_in_state OK")


if __name__ == "__main__":
    test_apply_timbre_fixes_snaps_to_catalog()
    test_apply_timbre_fixes_separates_melody_and_stab()
    test_route_retries_instrument_planner_without_fixes()
    test_route_proceeds_when_passed_or_fixes_present()
    test_style_coherence_node_without_plan()
    test_validate_orchestration_respects_contract_sections_in_state()
    print("\n✓ All style_coherence tests passed")
