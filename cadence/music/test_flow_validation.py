"""Regresión mínima del flujo composición LLM + pulido determinista."""

from cadence.analysis.benchmark_examples import (
    format_inspiration_profiles_for_llm,
    load_inspiration_profiles,
    validate_prompt_catalog,
)
from cadence.music.orchestration_pick import (
    build_orchestration_from_technical_proposal,
    pick_orchestration_plan,
)
from cadence.music.technical_proposal_apply import normalize_technical_proposal_composition
from cadence.schemas.song_state import (
    GenerationStrategies,
    ProposalInstrument,
    TechnicalProposal,
    UserIntent,
)


def _intent(*, use_case: str = "game") -> UserIntent:
    return UserIntent(
        raw_prompt="boss fight techno",
        knowledge_level="non_technical",
        use_case=use_case,  # type: ignore[arg-type]
        mood="intense",
        style_tags=["boss fight", "techno"],
    )


def _llm_proposal_with_instruments(*, use_case: str = "loop", energy_level: int = 2) -> TechnicalProposal:
    return TechnicalProposal(
        bpm=132,
        key="D",
        mode="minor",
        genre_tags=["techno", "boss fight"],
        energy_level=energy_level,
        ensemble_concept="technical_spec/llm",
        instruments=[
            ProposalInstrument(instrument_id="drums", role="rhythm", gm_program=0, active=True),
            ProposalInstrument(instrument_id="bass", role="bass", gm_program=43, active=True),
            ProposalInstrument(instrument_id="melody", role="lead", gm_program=81, active=True),
            ProposalInstrument(instrument_id="pad", role="pad", gm_program=89, active=True),
            ProposalInstrument(instrument_id="countermelody", role="lead", gm_program=82, active=True),
            ProposalInstrument(instrument_id="echo_synth", role="fx", gm_program=80, active=True),
            ProposalInstrument(instrument_id="arp_synth", role="lead", gm_program=98, active=True),
            ProposalInstrument(instrument_id="chord_stab", role="rhythm", gm_program=62, active=True),
            ProposalInstrument(instrument_id="synth_pluck", role="lead", gm_program=90, active=True),
        ],
        drum_pattern="techno",
        bass_pattern="driving",
        harmony_pool="aggressive",
        arp_pattern="sixteenth",
        stab_pattern="offbeat",
        perc_pattern="syncopated",
        pluck_pattern="eighth",
        counter_pattern="offbeat_sync",
        echo_source="melody",
        reasoning=f"flow test use_case={use_case}",
    )


def _state_from_proposal(
    proposal: TechnicalProposal,
    *,
    use_case: str = "loop",
) -> dict:
    return {
        "intent": _intent(use_case=use_case),
        "technical_proposal": proposal,
        "strategies": GenerationStrategies(
            generation_seed=7,
            drum_pattern="techno_a",
            bass_pattern="driving_a",
            harmony_pool="aggressive",
            arp_pattern="sixteenth_a",
            stab_pattern="offbeat_a",
            perc_pattern="syncopated_a",
            pluck_pattern="eighth_a",
            counter_pattern="offbeat_sync_a",
            echo_source="melody",
        ),
        "generation_seed": 7,
        "composition_archetype": "compact_action",
    }


def test_flow_preserves_llm_orchestration_decisions():
    proposal = _llm_proposal_with_instruments(use_case="loop", energy_level=2)
    state = _state_from_proposal(proposal, use_case="loop")
    plan = build_orchestration_from_technical_proposal(state)
    assert plan is not None
    active_ids = {a.instrument_id for a in plan.instruments if a.active}
    assert active_ids == {
        "drums",
        "bass",
        "melody",
        "pad",
        "countermelody",
        "echo_synth",
        "arp_synth",
        "chord_stab",
        "synth_pluck",
    }
    assert plan.harmony_pool == "aggressive"


def test_flow_uses_deterministic_fallback_when_llm_omits_orchestration():
    proposal = TechnicalProposal(
        bpm=138,
        key="F",
        mode="minor",
        genre_tags=["techno"],
        energy_level=4,
        instruments=[],
        reasoning="fallback flow test",
    )
    state = _state_from_proposal(proposal, use_case="game")
    plan = pick_orchestration_plan(state)
    ids = {a.instrument_id for a in plan.instruments if a.active}
    assert {"drums", "bass", "melody"} <= ids


def test_flow_normalizes_composition_without_dropping_llm_layers():
    proposal = _llm_proposal_with_instruments(use_case="game", energy_level=4)
    normalized = normalize_technical_proposal_composition(proposal)
    assert normalized.drum_pattern
    assert normalized.bass_pattern
    assert normalized.harmony_pool
    assert len(normalized.instruments) == len(proposal.instruments)


def test_flow_benchmark_catalog_is_complete_for_llm():
    errors = validate_prompt_catalog()
    assert not errors, "\n".join(errors)

    catalog = format_inspiration_profiles_for_llm()
    profiles = load_inspiration_profiles().get("profiles", {})
    for archetype in profiles.keys():
        assert archetype in catalog
    assert ".mid" not in catalog.lower()
