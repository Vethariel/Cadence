"""Regresión de decisiones compositivas extendidas del technical_spec."""

from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.development import development_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.music.harmony_theory import section_harmony_map
from cadence.music.technical_proposal_apply import normalize_technical_proposal_composition
from cadence.schemas.song_state import (
    GenerationStrategies,
    InstrumentAssignment,
    OrchestrationPlan,
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)


def _state() -> dict:
    proposal = TechnicalProposal(
        bpm=128,
        key="C",
        mode="minor",
        genre_tags=["techno", "boss fight"],
        energy_level=4,
        structure=["intro", "build-up", "drop", "outro"],
        section_intensity_curve={"intro": 0.25, "build-up": 0.75, "drop": 1.0, "outro": 0.35},
        rhythmic_density_curve={"intro": 0.2, "build-up": 0.8, "drop": 0.95, "outro": 0.3},
        motif_transform_plan={"intro": "introduce", "build-up": "sequence_up", "drop": "climax", "outro": "resolve"},
        cadence_plan={"intro": "half", "build-up": "deceptive", "drop": "authentic", "outro": "plagal"},
        lead_hierarchy=["melody", "countermelody", "arp_synth", "echo_synth"],
        call_response_map={"build-up": "melody:countermelody"},
        silence_breaks=[7],
        tension_points=[11],
        reasoning="extended composition decisions",
    )
    return {
        "intent": UserIntent(
            raw_prompt="boss fight techno",
            knowledge_level="non_technical",
            use_case="game",
            mood="intense",
            style_tags=["techno", "boss fight"],
        ),
        "technical_proposal": proposal,
        "narrative": SongNarrative(
            logline="Boss escalation arc",
            arc_type="rise-climax-fall",
            global_motif=[0, 2, 4, 2],
            sections=[
                SectionIntent(id="intro", narrative_role="establish", emotional_target="dark", density=0.3, harmonic_tension=0.3, rhythmic_complexity=0.3),
                SectionIntent(id="build-up", narrative_role="tension", emotional_target="urgent", density=0.7, harmonic_tension=0.7, rhythmic_complexity=0.7, transition_out="riser"),
                SectionIntent(id="drop", narrative_role="climax", emotional_target="epic", density=1.0, harmonic_tension=0.9, rhythmic_complexity=0.8),
                SectionIntent(id="outro", narrative_role="release", emotional_target="calm", density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.2),
            ],
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "outro"],
            bars_per_section={"intro": 4, "build-up": 4, "drop": 4, "outro": 4},
            total_bars=16,
            estimated_duration_ms=30000,
        ),
        "generation_seed": 123,
        "strategies": GenerationStrategies(generation_seed=123),
        "orchestration_plan": OrchestrationPlan(
            ensemble_concept="technical_spec/llm",
            drum_pattern="techno",
            bass_pattern="driving",
            instruments=[
                InstrumentAssignment(instrument_id="drums", role="rhythm", gm_program=0, active=True),
                InstrumentAssignment(instrument_id="bass", role="bass", gm_program=43, active=True),
                InstrumentAssignment(instrument_id="melody", role="lead", gm_program=81, active=True),
                InstrumentAssignment(instrument_id="countermelody", role="lead", gm_program=82, active=True),
                InstrumentAssignment(instrument_id="fx_riser", role="fx", gm_program=119, active=True),
            ],
        ),
        "tracks": [],
    }


def test_normalize_extended_composition_fields():
    proposal = TechnicalProposal(
        bpm=120,
        key="D",
        mode="minor",
        genre_tags=["techno"],
        energy_level=4,
        section_intensity_curve={"Drop ": 1.5},
        rhythmic_density_curve={"Build-Up": -1.0},
        motif_transform_plan={"drop": "CLIMAX", "bad": "nope"},
        cadence_plan={"drop": "authentic"},
        lead_hierarchy=["Melody", "melody", "echo_synth", "invalid"],
        register_plan={"melody": "high"},
        call_response_map={"drop": "melody:CounterMelody", "x": "bad"},
        silence_breaks=[-1, 3, 3],
        tension_points=[2, 2, 7],
        reasoning="test",
    )
    norm = normalize_technical_proposal_composition(proposal)
    assert norm.section_intensity_curve == {"drop": 1.0}
    assert norm.rhythmic_density_curve == {"build-up": 0.0}
    assert norm.motif_transform_plan == {"drop": "climax"}
    assert norm.cadence_plan == {"drop": "authentic"}
    assert norm.lead_hierarchy == ["melody", "echo_synth"]
    assert norm.register_plan == {"melody": "high"}
    assert norm.call_response_map == {"drop": "melody:countermelody"}
    assert norm.silence_breaks == [0, 3]
    assert norm.tension_points == [2, 7]


def test_development_respects_motif_transform_plan():
    state = _state()
    dev = development_planner_node(state)["development"]
    by_id = {s.section_id: s for s in dev.sections}
    assert by_id["drop"].transform == "climax"
    assert by_id["outro"].transform == "resolve"


def test_harmony_respects_cadence_plan():
    state = _state()
    harmony = harmony_planner_node(state)["harmony"]
    drop = section_harmony_map(harmony)["drop"].progression
    assert drop[-1].root_degree == 0


def test_arrangement_applies_call_response_and_schedule_markers():
    state = _state()
    arr = arrangement_planner_node(state)["arrangement"]
    by_id = {l.instrument_id: l for l in arr.layers}
    assert "build-up" in by_id["countermelody"].active_sections or by_id["countermelody"].active_sections == ["*"]
    assert arr.layer_schedule is not None
    entries = {e.bar: e for e in arr.layer_schedule.entries}
    assert 7 in entries and "melody" in entries[7].remove
    assert any("fx_riser" in e.add for e in arr.layer_schedule.entries if e.bar >= 10)
