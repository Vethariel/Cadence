"""Validación del catálogo de prompts ↔ arquetipos MIDI."""

from pathlib import Path
import pytest

pytestmark = pytest.mark.benchmark

from cadence.music.composition_archetypes import COMPOSITION_ARCHETYPES
from cadence.analysis.benchmark_examples import (
    export_title_for_prompt,
    format_inspiration_profiles_for_llm,
    load_inspiration_profiles,
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


def test_llm_inspiration_catalog_includes_profiles():
    data = load_inspiration_profiles()
    assert data.get("profiles"), "inspiration_profiles.json no tiene perfiles"
    catalog = format_inspiration_profiles_for_llm()
    for archetype in data["profiles"].keys():
        assert archetype in catalog
    assert ".mid" not in catalog.lower()
    print("✓ test_llm_inspiration_catalog_includes_profiles OK")


def test_validate_prompt_catalog_without_midi_runtime_dependency(monkeypatch):
    def _fail_glob(self, pattern):  # noqa: ANN001
        raise AssertionError(f"validate_prompt_catalog no debe globear: {pattern}")

    monkeypatch.setattr(Path, "glob", _fail_glob, raising=True)
    errors = validate_prompt_catalog()
    assert not errors, "\n".join(errors)
    print("✓ test_validate_prompt_catalog_without_midi_runtime_dependency OK")


def test_inspiration_profiles_cover_all_composition_archetypes():
    data = load_inspiration_profiles()
    profiles = data.get("profiles", {})
    missing = sorted(set(COMPOSITION_ARCHETYPES) - set(profiles.keys()))
    assert not missing, f"Faltan arquetipos en inspiration_profiles: {missing}"
    assert "boss_orchestral" not in profiles, "Debe usarse id canónico orchestral_boss"
    print("✓ test_inspiration_profiles_cover_all_composition_archetypes OK")


def test_inspiration_profiles_include_extended_signals():
    data = load_inspiration_profiles()
    profiles = data.get("profiles", {})
    for archetype, p in profiles.items():
        rhythm = p.get("rhythm_signature_16")
        assert isinstance(rhythm, list) and len(rhythm) == 16, f"{archetype}: rhythm_signature_16 inválido"
        intervals = p.get("melody_interval_histogram", {})
        for k in ("step_1_2", "skip_3_4", "leap_5_7", "leap_8_plus", "ascending_ratio", "descending_ratio"):
            assert k in intervals, f"{archetype}: falta {k} en melody_interval_histogram"
        assert "cadence_tendencies" in p, f"{archetype}: falta cadence_tendencies"
        assert "layer_timeline_template" in p, f"{archetype}: falta layer_timeline_template"
        assert "role_register_ranges" in p, f"{archetype}: falta role_register_ranges"
        assert "harmonic_rhythm_deep" in p, f"{archetype}: falta harmonic_rhythm_deep"
        assert "dynamics_profile" in p, f"{archetype}: falta dynamics_profile"
        assert "motivicity_signature" in p, f"{archetype}: falta motivicity_signature"

        harmonic = p["harmonic_rhythm_deep"]
        assert harmonic.get("chord_hold_beats_mean", 0) > 0 or any(
            float(x) > 0 for x in harmonic.get("chord_change_density_curve_4q", [])
        ), f"{archetype}: harmonic_rhythm_deep sin señal útil"

        dynamics = p["dynamics_profile"]
        assert dynamics.get("velocity_mean", 0) > 0, f"{archetype}: dynamics_profile sin velocidad"

        motivic = p["motivicity_signature"]
        assert motivic.get("top_interval_ngrams_4"), f"{archetype}: motivicidad sin ngrams"

        layer_template = p["layer_timeline_template"]
        assert any(
            any(float(v) > 0 for v in vec)
            for vec in layer_template.values()
            if isinstance(vec, list)
        ), f"{archetype}: layer_timeline_template no aporta"

    catalog = format_inspiration_profiles_for_llm()
    assert "acentos_16" in catalog
    assert "intervalos:" in catalog
    assert "cadencias_tendencia:" in catalog
    assert "ritmo_armonico_profundo:" in catalog
    assert "dinamica:" in catalog
    assert "motivicidad:" in catalog
    print("✓ test_inspiration_profiles_include_extended_signals OK")


if __name__ == "__main__":
    test_catalog_alignment()
    test_each_prompt_infers_expected_archetype()
    test_export_title_from_catalog_prompt()
    test_five_archetypes_covered()
    test_llm_inspiration_catalog_includes_profiles()
    test_validate_prompt_catalog_without_midi_runtime_dependency()
    test_inspiration_profiles_cover_all_composition_archetypes()
    test_inspiration_profiles_include_extended_signals()
    print("\n✓ All benchmark example tests passed")
