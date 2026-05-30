"""Tests de quality_status al exportar."""

from cadence.schemas.song_state import (
    NarrativeContract,
    SongStructure,
    ValidationResult,
)
from cadence.music.quality_status import compute_quality_metadata


def _base_state(**overrides):
    state = {
        "generation_seed": 4242,
        "retry_count": 0,
        "request_id": "req-test-1",
        "narrative_contract": NarrativeContract(
            section_ids=["intro", "drop"],
            arc_type="rise",
            global_motif=[0, 2, 4],
            prompt_intent_signature="sig",
        ),
        "structure": SongStructure(
            sections=["intro", "drop"],
            bars_per_section={"intro": 4, "drop": 8},
            total_bars=12,
            estimated_duration_ms=20000,
        ),
        "validation_result": ValidationResult(
            score=1.0, errors=[], warnings=[], passed=True,
        ),
    }
    state.update(overrides)
    return state


def test_quality_passed():
    meta = compute_quality_metadata(_base_state(
        validation_result=ValidationResult(
            score=1.0,
            errors=[],
            warnings=[],
            passed=True,
            passed_technical=True,
            passed_perceptual=True,
        ),
    ))
    assert meta["quality_status"] == "passed"
    assert meta["validation_passed_technical"] is True
    assert meta["validation_passed_perceptual"] is True
    assert meta["failed_checks"] == []
    assert meta["generation_seed"] == 4242


def test_quality_degraded_borderline_with_passed_true():
    meta = compute_quality_metadata(_base_state(
        retry_count=2,
        validation_result=ValidationResult(
            score=0.82,
            errors=[],
            warnings=[],
            passed=True,
            passed_technical=True,
            passed_perceptual=True,
        ),
    ))
    assert meta["quality_status"] == "degraded"
    assert meta["validation_borderline"] is True
    assert meta["validation_passed"] is True


def test_quality_degraded_perceptual_only():
    meta = compute_quality_metadata(_base_state(
        validation_result=ValidationResult(
            score=0.85,
            errors=["[melody_coverage] bajo"],
            warnings=[],
            passed=True,
            passed_technical=True,
            passed_perceptual=False,
        ),
    ))
    assert meta["quality_status"] == "degraded"
    assert meta["validation_passed_perceptual"] is False


def test_quality_degraded_after_retries():
    meta = compute_quality_metadata(_base_state(
        retry_count=3,
        validation_result=ValidationResult(
            score=0.72,
            errors=["[melody_coverage] bajo"],
            warnings=[],
            passed=False,
        ),
    ))
    assert meta["quality_status"] == "degraded"
    assert "melody_coverage" in meta["failed_checks"]


def test_quality_failed_contract_narrative():
    meta = compute_quality_metadata(_base_state(
        validation_result=ValidationResult(
            score=0.7,
            errors=["[narrative_intensity] Intensidad invertida"],
            warnings=[],
            passed=False,
        ),
    ))
    assert meta["quality_status"] == "failed_contract"
    assert meta["narrative_failed_checks"] == ["narrative_intensity"]


def test_quality_failed_contract_section_mismatch():
    st = SongStructure(
        sections=["intro", "verse"],
        bars_per_section={"intro": 4, "verse": 8},
        total_bars=12,
        estimated_duration_ms=20000,
    )
    meta = compute_quality_metadata(_base_state(structure=st))
    assert meta["quality_status"] == "failed_contract"
    assert meta["contract_integrity_ok"] is False


if __name__ == "__main__":
    test_quality_passed()
    test_quality_degraded_borderline_with_passed_true()
    test_quality_degraded_perceptual_only()
    test_quality_degraded_after_retries()
    test_quality_failed_contract_narrative()
    test_quality_failed_contract_section_mismatch()
    print("All quality_status tests passed.")
