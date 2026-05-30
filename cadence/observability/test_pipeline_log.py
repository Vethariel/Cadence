"""Tests de log estructurado y trace."""

import json
import logging

from cadence.observability.pipeline_log import (
    instrument_node,
    log_narrative_contract_fallback,
    log_section_reconciliation,
    section_ids_from_state,
)
from cadence.schemas.song_state import NarrativeContract, SongStructure


def test_section_ids_from_contract():
    state = {
        "narrative_contract": NarrativeContract(
            section_ids=["a", "b"],
            arc_type="x",
            global_motif=[0],
            prompt_intent_signature="s",
        ),
    }
    assert section_ids_from_state(state) == ["a", "b"]


def test_instrument_node_appends_trace():
    log = logging.getLogger("cadence.pipeline")
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Capture()
    handler.setLevel(logging.INFO)
    log.setLevel(logging.INFO)
    log.addHandler(handler)
    try:

        def dummy(state):
            return {
                "structure": SongStructure(
                    sections=["intro"],
                    bars_per_section={"intro": 4},
                    total_bars=4,
                    estimated_duration_ms=8000,
                ),
            }

        wrapped = instrument_node("strategy_planner", dummy)
        out = wrapped({
            "request_id": "rid-1",
            "generation_seed": 99,
            "pipeline_trace": [],
        })
    finally:
        log.removeHandler(handler)

    assert out["request_id"] == "rid-1"
    assert len(out["pipeline_trace"]) == 1
    assert out["pipeline_trace"][0]["event"] == "node_run"
    assert out["pipeline_trace"][0]["node"] == "strategy_planner"
    assert "duration_ms" in out["pipeline_trace"][0]
    if records:
        payload = json.loads(records[-1].getMessage())
        assert payload["request_id"] == "rid-1"
        assert payload.get("contract_section_ids_count", 0) >= 0
        assert "input_sections_count" in payload
        assert "output_sections_count" in payload


def test_section_reconciliation_trace():
    state = {"request_id": "rid-2", "pipeline_trace": []}
    extra = log_section_reconciliation(
        state,
        planner_section_ids=["intro_a"],
        canonical_section_ids=["intro"],
        mapping={"intro_a": "intro"},
        method="normalized",
        realigned=True,
    )
    assert extra["pipeline_trace"][0]["event"] == "section_reconciliation"
    assert extra["pipeline_trace"][0]["realigned"] is True
    assert extra["pipeline_trace"][0]["contract_section_ids_count"] == 1


def test_narrative_contract_fallback_trace():
    state = {"request_id": "rid-fb", "pipeline_trace": []}
    log_narrative_contract_fallback(state, node="melody")
    assert state["pipeline_trace"][0]["event"] == "narrative_contract_fallback"
    assert state["pipeline_trace"][0]["contract_section_ids_count"] == 0
    assert state["pipeline_trace"][0]["node"] == "melody"


if __name__ == "__main__":
    test_section_ids_from_contract()
    test_instrument_node_appends_trace()
    test_section_reconciliation_trace()
    test_narrative_contract_fallback_trace()
    print("All pipeline_log tests passed.")
