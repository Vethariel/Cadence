"""Validación del catálogo de prompts ↔ arquetipos MIDI."""

import pytest

pytestmark = pytest.mark.benchmark

from cadence.analysis.benchmark_examples import (
    export_title_for_prompt,
    load_benchmark_prompts,
    match_benchmark_id,
    validate_prompt_catalog,
    infer_archetype_for_benchmark_prompt,
)


def test_catalog_alignment():
    errors = validate_prompt_catalog()
    assert not errors, "\n".join(errors)
    print("✓ test_catalog_alignment OK")


def test_each_prompt_infers_expected_archetype():
    for bp in load_benchmark_prompts():
        inferred = infer_archetype_for_benchmark_prompt(bp)
        assert inferred == bp.archetype, (
            f"{bp.id}: got {inferred}, want {bp.archetype}"
        )
    print("✓ test_each_prompt_infers_expected_archetype OK")


def test_export_title_from_catalog_prompt():
    bp = load_benchmark_prompts()[0]
    assert match_benchmark_id(bp.prompt) == bp.id
    assert export_title_for_prompt(bp.prompt, "game", "x") == f"cadence_{bp.id}"
    assert export_title_for_prompt("prompt libre", "loop", "calm") == "cadence_loop_calm"
    print("✓ test_export_title_from_catalog_prompt OK")


def test_five_archetypes_covered():
    prompts = load_benchmark_prompts()
    assert len(prompts) == 5
    archetypes = {p.archetype for p in prompts}
    assert archetypes == {
        "sparse_loop",
        "moderate_cinematic",
        "dense_dance",
        "energetic_game",
        "boss_orchestral",
    }
    print("✓ test_five_archetypes_covered OK")


if __name__ == "__main__":
    test_catalog_alignment()
    test_each_prompt_infers_expected_archetype()
    test_export_title_from_catalog_prompt()
    test_five_archetypes_covered()
    print("\n✓ All benchmark example tests passed")
