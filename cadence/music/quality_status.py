"""
Estado de calidad explícito al exportar — sin ocultar degradaciones narrativas.
"""

from __future__ import annotations

from cadence.agent.nodes.repair import failed_check_names
from cadence.schemas.song_state import SongState

QualityStatus = str  # passed | degraded | failed_contract

NARRATIVE_QUALITY_CHECKS = frozenset({
    "narrative_key_coverage",
    "narrative_intensity",
    "narrative_motif",
})


def _contract_integrity_ok(state: SongState | dict) -> tuple[bool, str | None]:
    contract = state.get("narrative_contract") if isinstance(state, dict) else None
    structure = state.get("structure") if isinstance(state, dict) else None
    if not contract or not structure:
        return True, None
    if structure.sections != contract.section_ids:
        return False, (
            f"structure.sections {structure.sections!r} != "
            f"contract.section_ids {contract.section_ids!r}"
        )
    alignment = state.get("section_alignment")
    if alignment is not None and getattr(alignment, "realigned", False):
        return True, None
    return True, None


def compute_quality_metadata(state: SongState | dict) -> dict:
    """
    Metadatos de calidad y trazabilidad para .rsong.

    - passed: validación OK
    - degraded: exportado sin pass (p. ej. agotó reintentos) sin rotura de contrato
    - failed_contract: checks narrativos o desalineación contrato/structure
    """
    validation = state.get("validation_result") if isinstance(state, dict) else None
    retry_count = int(state.get("retry_count", 0) or 0)
    generation_seed = int(state.get("generation_seed", 0) or 0)
    request_id = state.get("request_id")

    failed: list[str] = []
    if validation and validation.errors:
        failed = sorted(failed_check_names(validation.errors))

    narrative_failed = [c for c in failed if c in NARRATIVE_QUALITY_CHECKS]
    contract_ok, contract_reason = _contract_integrity_ok(state)

    if not contract_ok or narrative_failed:
        status: QualityStatus = "failed_contract"
    elif validation and validation.passed:
        status = "passed"
    else:
        status = "degraded"

    trace = state.get("pipeline_trace") or []
    repair_events = [e for e in trace if e.get("event") == "repair_intervention"]
    reconcile_events = [e for e in trace if e.get("event") == "section_reconciliation"]

    return {
        "quality_status": status,
        "validation_passed": bool(validation.passed) if validation else False,
        "validation_score": round(validation.score, 3) if validation else 0.0,
        "retry_count": retry_count,
        "generation_seed": generation_seed,
        "request_id": request_id,
        "failed_checks": failed,
        "narrative_failed_checks": narrative_failed,
        "contract_integrity_ok": contract_ok,
        "contract_integrity_reason": contract_reason,
        "repair_interventions": len(repair_events),
        "section_reconciliations": len(reconcile_events),
        "pipeline_node_runs": sum(1 for e in trace if e.get("event") == "node_run"),
    }
