"""
Tests de coherencia intra-request y heterogeneidad inter-request.

- Coherencia: section IDs alineados en todo el pipeline; narrativa y validator
  usan el mismo contrato.
- Heterogeneidad: mismo prompt + seeds distintas → timbres/patrones distintos;
  invariantes narrativas estables.
"""

from __future__ import annotations

from cadence.agent.nodes.arrangement import arrangement_planner_node
from cadence.agent.nodes.development import development_planner_node
from cadence.agent.nodes.harmony import harmony_planner_node
from cadence.agent.nodes.repair import failed_check_names
from cadence.agent.nodes.validator import validator_node
from cadence.music.instrument_catalog import validate_orchestration
from cadence.music.narrative_contract import (
    build_narrative_contract,
    contract_section_intent_map,
)
from cadence.music.section_refs import canonical_section_ids
from cadence.music.strategy_pools import select_strategies
from cadence.schemas.song_state import (
    InstrumentAssignment,
    OrchestrationPlan,
    RhythmEvent,
    SongStructure,
    Track,
    ValidationResult,
)
from cadence.test_fixtures.pipeline_coherence import (
    CANONICAL_SECTION_IDS,
    build_aligned_pipeline_state,
)


def _collect_section_ids_from_state(state: dict) -> dict[str, list[str]]:
    contract = state["narrative_contract"]
    canon = list(contract.section_ids)
    out: dict[str, list[str]] = {
        "contract": canon,
        "structure": list(state["structure"].sections),
        "narrative": [s.id for s in state["narrative"].sections],
        "canonical_helper": canonical_section_ids(state),
    }
    if state.get("harmony"):
        out["harmony"] = [s.section_id for s in state["harmony"].sections]
    if state.get("development"):
        out["development"] = [s.section_id for s in state["development"].sections]
    if state.get("arrangement"):
        sections_used: set[str] = set()
        for layer in state["arrangement"].layers:
            for sec in layer.active_sections:
                if sec != "*":
                    sections_used.add(sec)
        out["arrangement_active"] = sorted(sections_used)
    return out


def test_intra_request_section_ids_aligned_across_pipeline():
    state = build_aligned_pipeline_state(generation_seed=2024)
    state.update(harmony_planner_node(state))
    state.update(development_planner_node(state))
    state.update(arrangement_planner_node(state))

    ids = _collect_section_ids_from_state(state)
    canon = ids["contract"]
    for key in ("structure", "narrative", "canonical_helper", "harmony", "development"):
        assert ids[key] == canon, f"{key}: {ids[key]!r} != {canon!r}"

    for sid in ids.get("arrangement_active", []):
        assert sid in canon, f"arrangement usa sección no canónica: {sid!r}"

    intent_map = contract_section_intent_map(
        state["narrative"], state["narrative_contract"],
    )
    assert set(intent_map.keys()) == set(canon)
    print("✓ test_intra_request_section_ids_aligned_across_pipeline OK")


def test_validator_uses_same_contract_as_narrative():
    state = build_aligned_pipeline_state(generation_seed=99)
    contract = state["narrative_contract"]
    intent_map = contract_section_intent_map(
        state["narrative"], contract,
    )

    ms_per_bar = (60000 / 140) * 4

    def note(t: int, section: str, vel: int = 90, pitch: int = 65):
        return RhythmEvent(
            t=t, type="note", pitch=pitch, duration_ms=200,
            velocity=vel, beat_index=0, section=section,
        )

    def drum(t: int, section: str, vel: int = 100):
        return RhythmEvent(
            t=t, type="drum_hit", pitch=36, duration_ms=100,
            velocity=vel, beat_index=0, section=section,
        )

    melody_events = []
    drum_events = []
    cursor = 0
    for sid in contract.section_ids:
        bars = state["structure"].bars_per_section[sid]
        dur = int(bars * ms_per_bar)
        n_notes = max(12, bars * 4)
        for i in range(n_notes):
            t = cursor + i * max(80, dur // n_notes)
            melody_events.append(
                note(t, sid, vel=70 + int(intent_map[sid].density * 40), pitch=60 + (i % 5)),
            )
            drum_events.append(drum(t, sid))
        cursor += dur

    tracks = [
        Track(id="melody", instrument="Lead", role="lead", events=melody_events),
        Track(id="drums", instrument="Drums", role="rhythm", events=drum_events),
        Track(id="bass", instrument="Bass", role="bass", events=melody_events[:40]),
    ]
    state["tracks"] = tracks
    state["validation_result"] = None

    result = validator_node(state)
    v = result["validation_result"]
    assert state["structure"].sections == contract.section_ids
    assert v is not None
    narrative_errors = [
        e for e in v.errors
        if failed_check_names([e]) & {
            "narrative_key_coverage",
            "narrative_intensity",
            "narrative_motif",
        }
    ]
    assert not narrative_errors, narrative_errors
    print("✓ test_validator_uses_same_contract_as_narrative OK")


def test_inter_request_narrative_invariants_same_prompt_different_seeds():
    seeds = (1001, 4242, 9001)
    contracts = []
    anchors_list = []
    signatures = []

    for seed in seeds:
        state = build_aligned_pipeline_state(generation_seed=seed)
        contracts.append(state["narrative_contract"])
        anchors_list.append(state["narrative_anchors"])
        signatures.append(state["narrative_contract"].prompt_intent_signature)

    first_ids = contracts[0].section_ids
    for c in contracts[1:]:
        assert c.section_ids == first_ids == CANONICAL_SECTION_IDS
        assert c.arc_type == contracts[0].arc_type
        assert c.global_motif == contracts[0].global_motif

    assert len(set(signatures)) == 1, "misma solicitud → misma firma de prompt"

    first_keys = anchors_list[0].key_section_ids
    for a in anchors_list[1:]:
        assert a.key_section_ids == first_keys
        assert a.section_ids == anchors_list[0].section_ids
    print("✓ test_inter_request_narrative_invariants_same_prompt_different_seeds OK")


def test_inter_request_measurable_strategy_diversity():
    """Mismo contexto musical; seeds distintas → patrones distintos."""
    tags = ["techno", "dubstep"]
    sigs: set[tuple[str, str, str]] = set()
    for seed in range(0, 64):
        s = select_strategies(
            seed, tags, "minor", "game", 5,
            composition_archetype="default_game",
        )
        sigs.add((s.drum_pattern, s.bass_pattern, s.harmony_pool))
    assert len(sigs) >= 3, f"poca diversidad de estrategias: {len(sigs)} firmas"

    a = select_strategies(17, tags, "minor", "game", 5)
    b = select_strategies(17017, tags, "minor", "game", 5)
    assert (a.drum_pattern, a.bass_pattern) != (b.drum_pattern, b.bass_pattern) or (
        a.harmony_pool != b.harmony_pool
    )
    print("✓ test_inter_request_measurable_strategy_diversity OK")


def test_inter_request_measurable_timbre_diversity_by_seed():
    plan = OrchestrationPlan(
        ensemble_concept="seed test",
        drum_pattern="techno",
        bass_pattern="driving",
        instruments=[
            InstrumentAssignment(instrument_id="drums", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="bass", gm_program=0, active=True),
            InstrumentAssignment(instrument_id="melody", gm_program=0, active=True),
        ],
    )
    gms: set[int] = set()
    for seed in (3, 19, 87, 503, 2003):
        validated = validate_orchestration(
            plan,
            use_case="game",
            energy_level=5,
            generation_seed=seed,
            raw_prompt="boss fight techno dark",
        )
        melody = next(
            a for a in validated.instruments if a.instrument_id == "melody"
        )
        gms.add(melody.gm_program)
    assert len(gms) >= 2, f"gm_program melodía no varía con seed: {gms}"
    print("✓ test_inter_request_measurable_timbre_diversity_by_seed OK")


def test_inter_request_strategy_planner_differs_by_seed_same_contract():
    state_a = build_aligned_pipeline_state(generation_seed=11)
    state_b = build_aligned_pipeline_state(generation_seed=9911)
    assert (
        state_a["narrative_contract"].section_ids
        == state_b["narrative_contract"].section_ids
    )
    sa = state_a["strategies"]
    sb = state_b["strategies"]
    assert sa is not None and sb is not None
    differs = (
        sa.drum_pattern != sb.drum_pattern
        or sa.bass_pattern != sb.bass_pattern
        or sa.harmony_pool != sb.harmony_pool
        or sa.arp_pattern != sb.arp_pattern
    )
    assert differs, "se esperaba variación medible entre seeds"
    print("✓ test_inter_request_strategy_planner_differs_by_seed_same_contract OK")


def test_contract_signature_stable_across_seeds():
    intent = build_aligned_pipeline_state(generation_seed=1)["intent"]
    narrative = build_aligned_pipeline_state(generation_seed=2)["narrative"]
    c1 = build_narrative_contract(narrative, intent)
    c2 = build_narrative_contract(narrative, intent)
    assert c1.prompt_intent_signature == c2.prompt_intent_signature
    print("✓ test_contract_signature_stable_across_seeds OK")


if __name__ == "__main__":
    test_intra_request_section_ids_aligned_across_pipeline()
    test_validator_uses_same_contract_as_narrative()
    test_inter_request_narrative_invariants_same_prompt_different_seeds()
    test_inter_request_measurable_strategy_diversity()
    test_inter_request_measurable_timbre_diversity_by_seed()
    test_inter_request_strategy_planner_differs_by_seed_same_contract()
    test_contract_signature_stable_across_seeds()
    print("\n✓ All coherence_diversity tests passed")
