"""Tests del contrato narrativo y alineación de secciones."""

import json
import logging

from cadence.music.narrative_contract import (
    SectionAlignmentError,
    align_structure_to_contract,
    assert_sections_match_contract,
    build_narrative_contract,
    contract_section_intent_map,
    section_intent_map_from_state,
    compute_prompt_intent_signature,
    map_planner_sections_to_contract,
)
from cadence.schemas.song_state import (
    NarrativeContract,
    SectionIntent,
    SongNarrative,
    SongStructure,
    UserIntent,
)


def _narrative(section_ids: list[str]) -> SongNarrative:
    sections = [
        SectionIntent(
            id=sid,
            narrative_role="establish",
            emotional_target="calm",
            density=0.5,
            harmonic_tension=0.3,
            rhythmic_complexity=0.4,
        )
        for sid in section_ids
    ]
    return SongNarrative(
        logline="test",
        arc_type="loop-stable",
        sections=sections,
        global_motif=[0, 2, 4],
    )


def test_build_contract_from_narrative():
    intent = UserIntent(
        raw_prompt="loop ambiente",
        knowledge_level="non_technical",
        use_case="loop",
        mood="calm",
        style_tags=["ambient"],
    )
    narrative = _narrative(["intro", "main", "outro"])
    contract = build_narrative_contract(narrative, intent)
    assert contract.section_ids == ["intro", "main", "outro"]
    assert contract.arc_type == "loop-stable"
    assert contract.global_motif == [0, 2, 4]
    assert len(contract.prompt_intent_signature) == 16


def test_signature_differs_by_prompt():
    a = UserIntent(raw_prompt="a", knowledge_level="non_technical", use_case="game")
    b = UserIntent(raw_prompt="b", knowledge_level="non_technical", use_case="game")
    assert compute_prompt_intent_signature(a) != compute_prompt_intent_signature(b)


def test_map_positional_when_renamed():
    mapping, method = map_planner_sections_to_contract(
        ["Intro", "Main_Theme", "Outro"],
        ["intro", "main", "outro"],
    )
    assert method in ("normalized", "positional", "normalized_reorder")
    assert mapping["Intro"] == "intro"
    assert mapping["Main_Theme"] == "main"


def test_align_sections_rewrites_structure():
    contract = NarrativeContract(
        section_ids=["intro", "drop", "outro"],
        arc_type="rise-climax-fall",
        global_motif=[0, 3, 5],
        prompt_intent_signature="abc",
    )
    structure = SongStructure(
        sections=["Intro", "Drop", "Outro"],
        bars_per_section={"Intro": 4, "Drop": 16, "Outro": 8},
        total_bars=28,
        estimated_duration_ms=56000,
    )
    narrative = _narrative(["intro", "drop", "outro"])
    aligned_s, aligned_n, alignment = align_structure_to_contract(
        structure, narrative, contract,
    )
    assert aligned_s.sections == contract.section_ids
    assert aligned_s.bars_per_section == {"intro": 4, "drop": 16, "outro": 8}
    assert alignment.realigned is True
    assert_sections_match_contract(aligned_s, contract)


def test_align_fails_on_count_mismatch():
    contract = NarrativeContract(
        section_ids=["a", "b"],
        arc_type="x",
        global_motif=[0],
        prompt_intent_signature="x",
    )
    structure = SongStructure(
        sections=["a", "b", "c"],
        bars_per_section={"a": 4, "b": 4, "c": 4},
        total_bars=12,
        estimated_duration_ms=1000,
    )
    try:
        align_structure_to_contract(structure, _narrative(["a", "b"]), contract)
        assert False, "expected SectionAlignmentError"
    except SectionAlignmentError:
        pass


def test_assert_order_matters():
    contract = NarrativeContract(
        section_ids=["intro", "outro"],
        arc_type="x",
        global_motif=[],
        prompt_intent_signature="x",
    )
    structure = SongStructure(
        sections=["outro", "intro"],
        bars_per_section={"intro": 4, "outro": 4},
        total_bars=8,
        estimated_duration_ms=1000,
    )
    try:
        assert_sections_match_contract(structure, contract)
        assert False
    except AssertionError as exc:
        assert "orden" in str(exc).lower()


def test_contract_map_warns_without_contract():
    import logging as log_mod

    records: list[log_mod.LogRecord] = []

    class _Capture(log_mod.Handler):
        def emit(self, record: log_mod.LogRecord) -> None:
            records.append(record)

    logger = log_mod.getLogger("cadence.pipeline")
    handler = _Capture()
    handler.setLevel(log_mod.WARNING)
    logger.setLevel(log_mod.WARNING)
    logger.addHandler(handler)
    state = {"request_id": "warn-test", "pipeline_trace": []}
    try:
        narrative = _narrative(["intro", "outro"])
        contract_section_intent_map(
            narrative, None, context="test_no_contract", state=state,
        )
    finally:
        logger.removeHandler(handler)

    warnings = [json.loads(r.getMessage()) for r in records]
    fb = [w for w in warnings if w.get("event") == "narrative_contract_fallback"]
    assert fb
    assert fb[0].get("contract_section_ids_count") == 0
    assert fb[0].get("node") == "test_no_contract"
    trace_fb = [
        e for e in state["pipeline_trace"]
        if e.get("event") == "narrative_contract_fallback"
    ]
    assert len(trace_fb) == 1


def test_section_intent_map_from_state_uses_contract():
    intent = UserIntent(
        raw_prompt="game", knowledge_level="non_technical", use_case="game",
    )
    narrative = _narrative(["intro", "drop"])
    contract = build_narrative_contract(narrative, intent)
    state = {"narrative": narrative, "narrative_contract": contract}
    m = section_intent_map_from_state(state, context="test_state")
    assert list(m.keys()) == ["intro", "drop"]


if __name__ == "__main__":
    test_build_contract_from_narrative()
    test_signature_differs_by_prompt()
    test_map_positional_when_renamed()
    test_align_sections_rewrites_structure()
    test_align_fails_on_count_mismatch()
    test_assert_order_matters()
    test_contract_map_warns_without_contract()
    test_section_intent_map_from_state_uses_contract()
    print("All narrative_contract tests passed.")
