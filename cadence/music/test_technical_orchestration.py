"""Orquestación desde technical_spec.instruments (LLM)."""

from cadence.agent.nodes.test_arrangement import _boss_fight_state
from cadence.music.orchestration_pick import (
    build_orchestration_from_technical_proposal,
    pick_orchestration_plan,
    pick_orchestration_plan_deterministic,
)
from cadence.schemas.song_state import GenerationStrategies, ProposalInstrument


def _state_with_strategies():
    state = _boss_fight_state()
    state["strategies"] = GenerationStrategies(
        generation_seed=42,
        drum_pattern="techno",
        bass_pattern="driving",
    )
    state["generation_seed"] = 42
    return state


def test_build_plan_from_technical_proposal():
    state = _state_with_strategies()
    state["technical_proposal"] = state["technical_proposal"].model_copy(
        update={
            "ensemble_concept": "Industrial saw lead + synth bass",
            "instruments": [
                ProposalInstrument(instrument_id="drums", role="rhythm", gm_program=0, active=True),
                ProposalInstrument(instrument_id="bass", role="bass", gm_program=38, active=True),
                ProposalInstrument(instrument_id="melody", role="lead", gm_program=81, active=True),
                ProposalInstrument(instrument_id="arp_synth", role="lead", gm_program=98, active=True),
            ],
            "melody_texture": "dense",
        },
    )
    plan = build_orchestration_from_technical_proposal(state)
    assert plan is not None
    by_id = {a.instrument_id: a for a in plan.instruments if a.active}
    assert by_id["melody"].gm_program == 81
    assert by_id["bass"].gm_program == 38
    assert by_id["arp_synth"].gm_program == 98
    assert plan.ensemble_concept.startswith("Industrial")
    assert plan.melody_texture == "dense"
    print("✓ test_build_plan_from_technical_proposal OK")


def test_pick_prefers_llm_over_seed():
    state = _state_with_strategies()
    state["technical_proposal"] = state["technical_proposal"].model_copy(
        update={
            "instruments": [
                ProposalInstrument(instrument_id="drums", role="rhythm", gm_program=0, active=True),
                ProposalInstrument(instrument_id="bass", role="bass", gm_program=38, active=True),
                ProposalInstrument(instrument_id="melody", role="lead", gm_program=81, active=True),
            ],
        },
    )
    plan = pick_orchestration_plan(state)
    melody = next(a for a in plan.instruments if a.instrument_id == "melody")
    assert melody.gm_program == 81
    assert "technical_spec" in plan.ensemble_concept or plan.ensemble_concept
    print("✓ test_pick_prefers_llm_over_seed OK")


def test_empty_instruments_falls_back_deterministic():
    state = _state_with_strategies()
    state["technical_proposal"] = state["technical_proposal"].model_copy(
        update={"instruments": []},
    )
    assert build_orchestration_from_technical_proposal(state) is None
    plan = pick_orchestration_plan(state)
    assert any(a.instrument_id == "melody" for a in plan.instruments)
    print("✓ test_empty_instruments_falls_back_deterministic OK")


if __name__ == "__main__":
    test_build_plan_from_technical_proposal()
    test_pick_prefers_llm_over_seed()
    test_empty_instruments_falls_back_deterministic()
    print("\nAll technical_orchestration tests passed.")
