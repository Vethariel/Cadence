"""Tests Fase 4: ArrangementPlan + registry + compose_orchestra."""

from langchain_core.messages import HumanMessage

import cadence.instruments  # noqa: F401
from cadence.schemas.song_state import (
    ArrangementPlan,
    LayerSpec,
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)
from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.orchestra import compose_orchestra_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.instruments import list_instruments, get_instrument


def _boss_fight_state():
    narrative = SongNarrative(
        logline="Boss awakens and escalates to collapse",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id="intro", narrative_role="establish", emotional_target="mystery",
                density=0.3, harmonic_tension=0.2, rhythmic_complexity=0.3,
                transition_out="filter_sweep",
            ),
            SectionIntent(
                id="build-up", narrative_role="tension", emotional_target="urgency",
                density=0.7, harmonic_tension=0.6, rhythmic_complexity=0.6,
                transition_out="riser",
            ),
            SectionIntent(
                id="drop", narrative_role="climax", emotional_target="triumph",
                density=1.0, harmonic_tension=0.8, rhythmic_complexity=0.7,
                transition_out="cut",
            ),
            SectionIntent(
                id="breakdown", narrative_role="reflection", emotional_target="dread",
                density=0.15, harmonic_tension=0.3, rhythmic_complexity=0.2,
                transition_out="pickup",
            ),
            SectionIntent(
                id="outro", narrative_role="release", emotional_target="calm",
                density=0.3, harmonic_tension=0.1, rhythmic_complexity=0.2,
                transition_out="fade",
            ),
        ],
    )
    return {
        "messages": [HumanMessage(content="boss fight techno")],
        "intent": UserIntent(
            raw_prompt="boss fight", knowledge_level="non_technical",
            use_case="game", mood="dark", style_tags=["techno", "dubstep"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=140, key="F", mode="minor", genre_tags=["techno"],
            energy_level=5, structure=["intro", "build-up", "drop", "breakdown", "outro"],
        ),
        "structure": SongStructure(
            sections=["intro", "build-up", "drop", "breakdown", "outro"],
            bars_per_section={
                "intro": 4, "build-up": 8, "drop": 8, "breakdown": 4, "outro": 4,
            },
            total_bars=28,
            estimated_duration_ms=48000,
        ),
        "narrative": narrative,
        "tracks": [],
    }


def test_registry_has_core_instruments():
    ids = list_instruments()
    for required in ("drums", "bass", "melody", "pad", "fx_riser", "perc_aux", "countermelody", "echo_synth", "arp_synth", "chord_stab"):
        assert required in ids, f"{required} no registrado"
    assert get_instrument("drums").requires_llm is False
    assert get_instrument("melody").requires_llm is False
    print("✓ test_registry_has_core_instruments OK")


def test_arrangement_planner_adds_optional_layers():
    state = _boss_fight_state()
    arrangement = arrangement_planner_node(state)["arrangement"]
    layer_ids = [l.instrument_id for l in arrangement.layers]

    assert layer_ids[:3] == ["drums", "bass", "melody"]
    assert "pad" in layer_ids
    assert "perc_aux" in layer_ids
    assert "fx_riser" in layer_ids
    # Presupuesto lead: no todas las capas opcionales a la vez
    lead_optionals = {"countermelody", "echo_synth", "arp_synth", "chord_stab"}
    present = lead_optionals & set(layer_ids)
    assert 1 <= len(present) <= 2, f"expected 1-2 lead optionals, got {present}"
    assert len(layer_ids) < 10, "demasiadas capas simultáneas en el plan"
    assert arrangement.layer_schedule is not None
    assert len(arrangement.layer_schedule.entries) > 0
    assert set(arrangement.required_layers) == set(layer_ids)
    print(f"  layers: {layer_ids}")
    print("✓ test_arrangement_planner_adds_optional_layers OK")


def test_compose_orchestra_deterministic_layers():
    state = _boss_fight_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    full_arr = arrangement_planner_node(state)["arrangement"]
    # Solo capas deterministas (sin LLM)
    det_ids = {"drums", "bass", "pad", "fx_riser", "perc_aux"}
    state["arrangement"] = ArrangementPlan(
        layers=[l for l in full_arr.layers if l.instrument_id in det_ids],
        required_layers=["drums", "bass"],
    )

    result = compose_orchestra_node(state)
    tracks = result["tracks"]
    ids = {t.id for t in tracks}

    assert "drums" in ids
    assert "bass" in ids
    assert "pad" in ids
    assert "fx_riser" in ids
    assert "perc_aux" in ids
    assert result["repair_layers"] is None

    fx = next(t for t in tracks if t.id == "fx_riser")
    assert fx.role == "fx"
    assert len(fx.events) > 0
    print(f"  tracks: {sorted(ids)}")
    print("✓ test_compose_orchestra_deterministic_layers OK")


def test_repair_layers_partial_compose():
    state = _boss_fight_state()
    state["harmony"] = harmony_planner_node(state)["harmony"]
    state["arrangement"] = arrangement_planner_node(state)["arrangement"]

    # Primera pasada determinista
    det = ArrangementPlan(
        layers=[l for l in state["arrangement"].layers if l.instrument_id != "melody"],
        required_layers=["drums", "bass"],
    )
    state["arrangement"] = det
    first = compose_orchestra_node(state)
    state["tracks"] = first["tracks"]

    # Repair solo drums
    state["repair_layers"] = ["drums"]
    state["arrangement"] = det
    second = compose_orchestra_node(state)
    ids = [t.id for t in second["tracks"]]
    assert ids.count("drums") == 1
    assert "bass" in ids
    print("✓ test_repair_layers_partial_compose OK")


if __name__ == "__main__":
    test_registry_has_core_instruments()
    test_arrangement_planner_adds_optional_layers()
    test_compose_orchestra_deterministic_layers()
    test_repair_layers_partial_compose()
    print("\n✓ All phase 4 tests passed")
