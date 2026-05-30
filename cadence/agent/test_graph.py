"""
Tests E2E del grafo y regresiones de contrato / reproducibilidad / observabilidad.

Los tests con invoke() requieren API (Gemini). Los tests unitarios de contrato
y semilla corren sin red.
"""

from __future__ import annotations

import json
import os
import uuid

import httpx
from langchain_core.messages import HumanMessage

from cadence.agent.graph import cadence_graph
from cadence.agent.nodes.align_sections import align_sections_node
from cadence.music.narrative_contract import (
    SectionAlignmentError,
    align_structure_to_contract,
    section_intent_map_from_state,
)
from cadence.schemas.song_state import SongStructure
from cadence.test_fixtures.pipeline_coherence import (
    CANONICAL_SECTION_IDS,
    PLANNER_SECTION_IDS,
    build_aligned_pipeline_state,
    build_pre_align_state,
)

PROMPT_GAME = "quiero una canción oscura y agresiva para un jefe final de videojuego"
PROMPT_TECH = (
    "necesito una canción en D minor, 140 BPM, compás 4/4, "
    "estilo techno, estructura intro-verse-chorus-outro"
)
FIXED_SEED = 424242


def _graph_initial_state(prompt: str) -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "pipeline_trace": [],
        "messages": [HumanMessage(content=prompt)],
        "intent": None,
        "style_profile": None,
        "technical_proposal": None,
        "narrative": None,
        "narrative_contract": None,
        "section_alignment": None,
        "narrative_anchors": None,
        "creative_variation": None,
        "node_seeds": None,
        "composition_archetype": None,
        "harmony": None,
        "development": None,
        "strategies": None,
        "orchestration_plan": None,
        "style_coherence": None,
        "style_coherence_retries": 0,
        "arrangement": None,
        "generation_seed": 0,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "repair_target": None,
        "repair_layers": None,
        "repair_actions": None,
        "export_path": None,
        "rsong_data": None,
    }


def _network_unavailable(exc: BaseException) -> bool:
    """True si el entorno no puede alcanzar la API (DNS, timeout, reset remoto)."""
    transient = (
        httpx.ConnectError,
        httpx.RemoteProtocolError,
        httpx.ReadTimeout,
        httpx.TimeoutException,
        httpx.NetworkError,
    )
    if isinstance(exc, transient):
        return True
    cause = getattr(exc, "__cause__", None)
    return isinstance(cause, transient)


def _has_api_credentials() -> bool:
    if os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"):
        return True
    try:
        from cadence.config import settings
        return bool(settings.google_api_key)
    except Exception:
        return False


def assert_graph_pipeline_invariants(final_state: dict, *, label: str = "") -> None:
    """Falla si el pipeline pierde contrato, trazas, calidad o alineación de secciones."""
    prefix = f"{label}: " if label else ""

    contract = final_state.get("narrative_contract")
    structure = final_state.get("structure")
    assert contract is not None, f"{prefix}narrative_contract ausente"
    assert structure is not None, f"{prefix}structure ausente"
    assert structure.sections == contract.section_ids, (
        f"{prefix}structure {structure.sections!r} != contrato {contract.section_ids!r}"
    )

    narrative = final_state.get("narrative")
    assert narrative is not None, f"{prefix}narrative ausente"
    assert [s.id for s in narrative.sections] == contract.section_ids, (
        f"{prefix}narrative.sections desalineadas del contrato"
    )

    assert final_state.get("request_id"), f"{prefix}request_id ausente"
    trace = final_state.get("pipeline_trace") or []
    assert len(trace) > 0, f"{prefix}pipeline_trace vacío"

    node_runs = [e for e in trace if e.get("event") == "node_run"]
    assert len(node_runs) >= 5, f"{prefix}pocos node_run en trace ({len(node_runs)})"

    post_align = [
        e for e in trace
        if e.get("event") == "node_run"
        and e.get("node") in (
            "harmony_planner", "development_planner", "validator", "export",
        )
    ]
    for ev in post_align:
        assert ev.get("contract_section_ids_count", 0) > 0, (
            f"{prefix}nodo {ev.get('node')} sin contract_section_ids_count"
        )
        assert ev.get("seed") is not None, (
            f"{prefix}nodo {ev.get('node')} sin seed en trace (semilla no aplicada)"
        )

    seeds = final_state.get("node_seeds")
    assert seeds is not None, f"{prefix}node_seeds ausente"
    assert seeds.generation_seed > 0, f"{prefix}node_seeds.generation_seed inválido"

    rsong = final_state.get("rsong_data") or {}
    quality = rsong.get("quality") or {}
    assert quality.get("quality_status") in (
        "passed", "degraded", "failed_contract",
    ), f"{prefix}quality_status ausente o inválido: {quality!r}"
    assert quality.get("request_id") == final_state.get("request_id"), (
        f"{prefix}quality.request_id != state.request_id"
    )

    reconciliations = [e for e in trace if e.get("event") == "section_reconciliation"]
    assert len(reconciliations) >= 1, f"{prefix}sin section_reconciliation en trace"

    fallbacks = [e for e in trace if e.get("event") == "narrative_contract_fallback"]
    assert len(fallbacks) == 0, (
        f"{prefix}deriva narrativa: fallback sin contrato en nodos migrados: {fallbacks}"
    )


def test_align_sections_normalizes_misaligned_planner_ids():
    """Regresión contract-aware: IDs del planner → canónicos."""
    out = align_sections_node(build_pre_align_state())
    assert out["structure"].sections == CANONICAL_SECTION_IDS
    assert out["section_alignment"].realigned is True
    trace = out.get("pipeline_trace") or []
    assert any(e.get("event") == "section_reconciliation" for e in trace)
    print("✓ test_align_sections_normalizes_misaligned_planner_ids OK")


def test_align_sections_fails_explicitly_on_section_count_mismatch():
    """Estructura incompatible con el contrato debe fallar, no alinear en silencio."""
    state = build_pre_align_state()
    state["structure"] = SongStructure(
        sections=["Intro", "Drop", "Outro"],
        bars_per_section={"Intro": 4, "Drop": 8, "Outro": 4},
        total_bars=16,
        estimated_duration_ms=32000,
    )
    try:
        align_sections_node(state)
        raise AssertionError("se esperaba fallo por conteo de secciones")
    except ValueError as exc:
        assert "align_sections" in str(exc).lower() or "mapeo" in str(exc).lower()

    try:
        align_structure_to_contract(
            state["structure"],
            state["narrative"],
            state["narrative_contract"],
        )
        raise AssertionError("se esperaba SectionAlignmentError")
    except SectionAlignmentError:
        pass
    print("✓ test_align_sections_fails_explicitly_on_section_count_mismatch OK")


def test_same_prompt_same_seed_same_strategies():
    """Reproducibilidad mínima sin LLM: mismas strategies con mismo seed."""
    s1 = build_aligned_pipeline_state(generation_seed=FIXED_SEED)
    s2 = build_aligned_pipeline_state(generation_seed=FIXED_SEED)
    assert s1["narrative_contract"].section_ids == s2["narrative_contract"].section_ids
    assert s1["strategies"].model_dump() == s2["strategies"].model_dump()
    assert s1["generation_seed"] == s2["generation_seed"] == FIXED_SEED
    assert s1["node_seeds"].model_dump() == s2["node_seeds"].model_dump()
    print("✓ test_same_prompt_same_seed_same_strategies OK")


def test_different_seed_different_strategies_same_contract():
    """Mismo prompt, seed distinto → variación medible; contrato estable."""
    s1 = build_aligned_pipeline_state(generation_seed=1001)
    s2 = build_aligned_pipeline_state(generation_seed=9001)
    assert s1["narrative_contract"].section_ids == s2["narrative_contract"].section_ids
    differs = (
        s1["strategies"].drum_pattern != s2["strategies"].drum_pattern
        or s1["strategies"].bass_pattern != s2["strategies"].bass_pattern
        or s1["strategies"].harmony_pool != s2["strategies"].harmony_pool
    )
    assert differs, "se esperaba variación de strategies entre seeds"
    print("✓ test_different_seed_different_strategies_same_contract OK")


def test_narrative_fallback_records_in_pipeline_trace():
    """Regresión: sin contrato el fallback queda en trace (deriva narrativa detectable)."""
    state = build_aligned_pipeline_state(generation_seed=FIXED_SEED)
    state.pop("narrative_contract", None)
    state["pipeline_trace"] = []
    section_intent_map_from_state(state, context="melody")
    trace = state.get("pipeline_trace") or []
    fallbacks = [e for e in trace if e.get("event") == "narrative_contract_fallback"]
    assert len(fallbacks) == 1
    assert fallbacks[0]["node"] == "melody"
    assert fallbacks[0]["contract_section_ids_count"] == 0
    print("✓ test_narrative_fallback_records_in_pipeline_trace OK")


def test_node_run_trace_includes_seed_and_contract_counts():
    """Observabilidad: node_run expone seed y conteos de contrato."""
    import logging

    from cadence.observability.pipeline_log import instrument_node

    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    log = logging.getLogger("cadence.pipeline")
    handler = _Capture()
    handler.setLevel(logging.INFO)
    log.setLevel(logging.INFO)
    log.addHandler(handler)

    state = build_aligned_pipeline_state(generation_seed=FIXED_SEED)
    state["request_id"] = "trace-test-req"

    def dummy(s):
        return {}

    try:
        instrument_node("strategy_planner", dummy)(state)
    finally:
        log.removeHandler(handler)

    payloads = [json.loads(r.getMessage()) for r in records if r.name == "cadence.pipeline"]
    node_run = next(p for p in payloads if p.get("event") == "node_run")
    assert node_run["request_id"] == "trace-test-req"
    assert node_run["node"] == "strategy_planner"
    assert node_run["seed"] is not None
    assert node_run["contract_section_ids_count"] == len(CANONICAL_SECTION_IDS)
    assert node_run["has_narrative_contract"] is True
    print("✓ test_node_run_trace_includes_seed_and_contract_counts OK")


def test_graph_non_technical():
    if not _has_api_credentials():
        print("⊘ test_graph_non_technical SKIP (sin GOOGLE_API_KEY)")
        return

    print("\n── test_graph_non_technical ──")
    try:
        final_state = cadence_graph.invoke(_graph_initial_state(PROMPT_GAME))
    except Exception as exc:
        if _network_unavailable(exc):
            print(f"⊘ test_graph_non_technical SKIP (red: {exc})")
            return
        raise

    print(f"knowledge_level  : {final_state['intent'].knowledge_level}")
    print(f"bpm              : {final_state['technical_proposal'].bpm}")
    print(f"sections         : {final_state['structure'].sections}")
    print(f"quality_status   : {(final_state.get('rsong_data') or {}).get('quality', {}).get('quality_status')}")
    print(f"trace events     : {len(final_state.get('pipeline_trace') or [])}")
    print(f"export_path      : {final_state['export_path']}")

    assert final_state["intent"].knowledge_level == "non_technical"
    assert final_state["technical_proposal"] is not None
    assert final_state["harmony"] is not None
    assert final_state["development"] is not None
    assert final_state["strategies"] is not None
    assert final_state["generation_seed"] > 0
    assert final_state["arrangement"] is not None
    assert len(final_state["tracks"]) >= 4
    assert {"drums", "bass", "melody"}.issubset({t.id for t in final_state["tracks"]})

    assert_graph_pipeline_invariants(final_state, label="non_technical")
    print("✓ test_graph_non_technical OK")


def test_graph_technical():
    if not _has_api_credentials():
        print("⊘ test_graph_technical SKIP (sin GOOGLE_API_KEY)")
        return

    print("\n── test_graph_technical ──")
    try:
        final_state = cadence_graph.invoke(_graph_initial_state(PROMPT_TECH))
    except Exception as exc:
        if _network_unavailable(exc):
            print(f"⊘ test_graph_technical SKIP (red: {exc})")
            return
        raise

    print(f"knowledge_level  : {final_state['intent'].knowledge_level}")
    print(f"bpm              : {final_state['technical_proposal'].bpm}")
    print(f"sections         : {final_state['structure'].sections}")

    assert final_state["intent"].knowledge_level == "technical"
    assert final_state["technical_proposal"].bpm == 140
    assert final_state["technical_proposal"].key.upper().startswith("D")
    assert final_state["harmony"] is not None
    assert len(final_state["tracks"]) >= 4

    assert_graph_pipeline_invariants(final_state, label="technical")
    print("✓ test_graph_technical OK")


if __name__ == "__main__":
    test_align_sections_normalizes_misaligned_planner_ids()
    test_align_sections_fails_explicitly_on_section_count_mismatch()
    test_same_prompt_same_seed_same_strategies()
    test_different_seed_different_strategies_same_contract()
    test_node_run_trace_includes_seed_and_contract_counts()
    test_narrative_fallback_records_in_pipeline_trace()
    test_graph_non_technical()
    print("---")
    test_graph_technical()
    print("\n✓ graph tests finished")
