"""Roles de instrumento desde technical_spec hasta Track."""

from cadence.agent.nodes.test_arrangement import _boss_fight_state
from cadence.instruments.registry import compose_layer, get_instrument
from cadence.instruments.context import build_compose_context
from cadence.music.instrument_roles import normalize_instrument_role
from cadence.music.orchestration_pick import pick_orchestration_plan
from cadence.schemas.song_state import (
    ArrangementPlan,
    GenerationStrategies,
    LayerSpec,
    ProposalInstrument,
)


def test_normalize_role_percussion():
    assert normalize_instrument_role("drums", "lead") == "rhythm"
    assert normalize_instrument_role("melody", "pad") == "pad"
    print("✓ test_normalize_role_percussion OK")


def test_pick_plan_preserves_llm_role():
    state = _boss_fight_state()
    state["strategies"] = GenerationStrategies(
        generation_seed=1, drum_pattern="techno", bass_pattern="driving",
    )
    state["generation_seed"] = 1
    state["technical_proposal"] = state["technical_proposal"].model_copy(
        update={
            "instruments": [
                ProposalInstrument(
                    instrument_id="pad", role="pad", gm_program=94, active=True,
                ),
                ProposalInstrument(
                    instrument_id="melody", role="lead", gm_program=4, active=True,
                ),
            ],
        },
    )
    plan = pick_orchestration_plan(state)
    by_id = {a.instrument_id: a for a in plan.instruments if a.active}
    assert by_id["pad"].role == "pad"
    assert by_id["melody"].role == "lead"
    assert "drums" not in by_id
    print("✓ test_pick_plan_preserves_llm_role OK")


def test_compose_uses_layer_role():
    state = _boss_fight_state()
    state["strategies"] = GenerationStrategies(
        generation_seed=1, drum_pattern="techno", bass_pattern="driving",
    )
    state["harmony"] = None
    from cadence.agent.nodes.harmony import harmony_planner_node
    state.update(harmony_planner_node(state))
    state["arrangement"] = ArrangementPlan(
        layers=[
            LayerSpec(
                instrument_id="pad",
                role="pad",
                active_sections=["*"],
                mix_level=-14,
            ),
        ],
        required_layers=["pad"],
    )
    import cadence.instruments  # noqa: F401

    layer = state["arrangement"].layers[0]
    ctx = build_compose_context(state, layer)
    track = compose_layer(ctx)
    assert track is not None
    assert track.role == "pad"
    print("✓ test_compose_uses_layer_role OK")


if __name__ == "__main__":
    test_normalize_role_percussion()
    test_pick_plan_preserves_llm_role()
    test_compose_uses_layer_role()
    print("\nAll instrument_roles tests passed.")
