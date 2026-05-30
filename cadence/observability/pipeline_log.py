"""
Log estructurado del grafo Cadence — variación sana vs deriva narrativa.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

from cadence.music.seed_policy import node_temperature, seed_for_state
from cadence.schemas.song_state import SongState

logger = logging.getLogger("cadence.pipeline")

TRACE_CAP = 120
LLM_NODES = frozenset({
    "router",
    "tag_enricher",
    "technical_proposal",
    "technical_parser",
    "narrative_planner",
    "structure_planner",
    "instrument_planner",
    "style_coherence",
    "melody",
})


def ensure_request_id(state: SongState | dict) -> str:
    rid = state.get("request_id") if isinstance(state, dict) else None
    if rid:
        return str(rid)
    return str(uuid.uuid4())


def contract_section_ids_count(state: SongState | dict) -> int:
    contract = state.get("narrative_contract") if isinstance(state, dict) else None
    if contract is not None:
        return len(contract.section_ids)
    return 0


def section_ids_from_state(state: SongState | dict) -> list[str]:
    """IDs de sección canónicos o de structure/proposal."""
    contract = state.get("narrative_contract") if isinstance(state, dict) else None
    structure = state.get("structure") if isinstance(state, dict) else None
    proposal = state.get("technical_proposal") if isinstance(state, dict) else None
    if contract is not None:
        return list(contract.section_ids)
    if structure is not None:
        return list(structure.sections)
    if proposal is not None:
        return list(proposal.structure)
    return []


def _emit(event: dict[str, Any]) -> None:
    logger.info(json.dumps(event, ensure_ascii=False, default=str))


def _trace_base(state: SongState | dict, result: dict | None = None) -> list[dict]:
    if result and result.get("pipeline_trace"):
        return list(result["pipeline_trace"])
    return list(state.get("pipeline_trace") or [])


def _append_trace(
    state: SongState | dict,
    event: dict[str, Any],
    result: dict | None = None,
) -> list[dict]:
    trace = _trace_base(state, result)
    trace.append(event)
    return trace[-TRACE_CAP:]


def _merge_output(
    state: SongState | dict,
    result: dict | None,
    extra: dict | None = None,
) -> dict:
    out: dict = dict(result or {})
    if extra:
        out.update(extra)
    rid = state.get("request_id") if isinstance(state, dict) else None
    if not rid:
        out.setdefault("request_id", ensure_request_id(state))
    return out


def log_narrative_contract_fallback(state: SongState | dict, *, node: str) -> None:
    """Warning + trace cuando un nodo usa narrativa sin narrative_contract."""
    event = {
        "event": "narrative_contract_fallback",
        "request_id": ensure_request_id(state),
        "node": node,
        "context": node,
        "contract_section_ids_count": 0,
        "message": (
            "narrative_contract ausente; usando section_intent_map "
            "(compatibilidad legacy)"
        ),
    }
    logger.warning(json.dumps(event, ensure_ascii=False, default=str))
    if isinstance(state, dict):
        state["pipeline_trace"] = _append_trace(state, event, None)


def log_section_reconciliation(
    state: SongState | dict,
    *,
    planner_section_ids: list[str],
    canonical_section_ids: list[str],
    mapping: dict[str, str],
    method: str,
    realigned: bool,
) -> dict:
    """Registra reconciliación structure_planner ↔ narrative_contract."""
    event = {
        "event": "section_reconciliation",
        "request_id": ensure_request_id(state),
        "node": "align_sections",
        "seed": seed_for_state(state, "align_sections") or state.get("generation_seed") or None,
        "contract_section_ids_count": len(canonical_section_ids),
        "input_sections_count": len(planner_section_ids),
        "output_sections_count": len(canonical_section_ids),
        "planner_section_ids": planner_section_ids,
        "canonical_section_ids": canonical_section_ids,
        "mapping": mapping,
        "method": method,
        "realigned": realigned,
        "input_section_ids": planner_section_ids,
        "output_section_ids": canonical_section_ids,
    }
    _emit(event)
    return {"pipeline_trace": _append_trace(state, event, None)}


def log_repair_intervention(
    state: SongState | dict,
    *,
    retry_count: int,
    failed_checks: list[str],
    repair_target: str,
    repair_layers: list[str] | None,
    repair_actions: list[str],
    validation_score: float | None = None,
) -> dict:
    """Registra una vuelta del repair loop."""
    event = {
        "event": "repair_intervention",
        "request_id": ensure_request_id(state),
        "node": "repair",
        "retry_count": retry_count,
        "failed_checks": failed_checks,
        "repair_target": repair_target,
        "repair_layers": repair_layers or [],
        "repair_actions": repair_actions,
        "validation_score": validation_score,
        "input_section_ids": section_ids_from_state(state),
    }
    _emit(event)
    return {"pipeline_trace": _append_trace(state, event, None)}


def instrument_node(node_name: str, fn: Callable[[SongState], dict]) -> Callable[[SongState], dict]:
    """Envuelve un nodo del grafo con log estructurado y acumulación de trace."""

    def wrapped(state: SongState) -> dict:
        request_id = ensure_request_id(state)
        t0 = time.perf_counter()
        input_section_ids = section_ids_from_state(state)
        seed = seed_for_state(state, node_name) if state.get("generation_seed") else 0
        llm_temp = node_temperature(node_name) if node_name in LLM_NODES else None
        error_msg: str | None = None
        result: dict | None = None
        exc_to_raise: BaseException | None = None

        try:
            result = fn(state)
            if result is None:
                result = {}
            elif not isinstance(result, dict):
                result = {}
        except BaseException as exc:
            exc_to_raise = exc
            error_msg = str(exc)
        finally:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            merged = {**state, **(result or {})}
            output_section_ids = section_ids_from_state(merged)
            input_contract_count = contract_section_ids_count(state)
            output_contract_count = contract_section_ids_count(merged)
            event = {
                "event": "node_run",
                "request_id": request_id,
                "node": node_name,
                "duration_ms": duration_ms,
                "llm_temp": llm_temp,
                "seed": seed if seed else None,
                "has_narrative_contract": input_contract_count > 0,
                "contract_section_ids_count": (
                    output_contract_count or input_contract_count
                ),
                "input_sections_count": len(input_section_ids),
                "output_sections_count": len(output_section_ids),
                "input_section_ids": input_section_ids,
                "output_section_ids": output_section_ids,
                "section_ids_changed": input_section_ids != output_section_ids,
                "error": error_msg,
            }
            _emit(event)
            trace = _append_trace(state, event, result)
            if exc_to_raise is not None:
                raise exc_to_raise

        return _merge_output(
            state,
            result,
            {"pipeline_trace": trace, "request_id": request_id},
        )

    wrapped.__name__ = getattr(fn, "__name__", node_name)
    wrapped.__doc__ = fn.__doc__
    return wrapped


def failed_check_names_from_state(state: SongState | dict) -> list[str]:
    from cadence.agent.nodes.repair import failed_check_names

    validation = state.get("validation_result") if isinstance(state, dict) else None
    if not validation or not validation.errors:
        return []
    return sorted(failed_check_names(validation.errors))
