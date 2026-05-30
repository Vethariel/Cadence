"""Tests de perfiles de benchmark por estilo."""

from cadence.analysis.benchmark_profiles import (
    ARCHETYPE_DEFS,
    build_style_profiles,
    infer_archetype,
    evaluate_against_style,
    compute_instrumental_richness,
)
from cadence.analysis.midi_benchmark import analyze_midi, EXAMPLES_DIR


def _ref_metrics():
    return {p.name: analyze_midi(p) for p in EXAMPLES_DIR.glob("*.mid")}


def test_infer_sparse_loop():
    assert infer_archetype(use_case="loop", energy_level=2, genre_tags=["ambient"]) == "sparse_loop"
    assert infer_archetype(title="cadence_loop_atmospheric") == "sparse_loop"
    print("✓ test_infer_sparse_loop OK")


def test_infer_dense_battle():
    assert infer_archetype(
        use_case="game", energy_level=5, title="cadence_game_aggressive",
        genre_tags=["techno", "dubstep"],
    ) == "energetic_game"
    assert infer_archetype(
        use_case="game", energy_level=5, title="cadence_dense_dance",
        genre_tags=["chiptune", "arcade", "eurobeat"],
    ) == "dense_dance"
    assert infer_archetype(
        use_case="game", energy_level=5, title="cadence_energetic_game",
        genre_tags=["boss fight", "combat", "platform"],
    ) == "energetic_game"
    print("✓ test_infer_dense_battle OK")


def test_energetic_game_profile_exists():
    metrics = _ref_metrics()
    profiles = build_style_profiles(metrics)
    assert "energetic_game" in profiles
    eg = profiles["energetic_game"]
    measured = [r for r in eg.references if r in metrics]
    assert measured, "energetic_game necesita al menos una referencia medida"
    assert eg.ranges.get("layers_active_mean")
    print("✓ test_energetic_game_profile_exists OK")


def test_profiles_have_ranges_from_refs():
    metrics = _ref_metrics()
    profiles = build_style_profiles(metrics)
    assert len(profiles) == len(ARCHETYPE_DEFS)
    for pid, profile in profiles.items():
        has_measured_ref = any(r in metrics for r in profile.references)
        if not has_measured_ref:
            continue
        assert profile.ranges, f"{pid} sin rangos"
        assert "layers_active_mean" in profile.ranges
    print("✓ test_profiles_have_ranges_from_refs OK")


def test_pizza_time_fits_sparse_loop():
    metrics = _ref_metrics()
    profiles = build_style_profiles(metrics)
    pizza = metrics["Its_Pizza_Time.mid"]
    ev = evaluate_against_style(pizza, profiles["sparse_loop"], metrics_by_file=metrics)
    assert ev.fit_ratio >= 0.5, f"Pizza Time debería encajar en sparse_loop: {ev.fit_ratio:.0%}"
    print(f"  Pizza Time fit sparse_loop: {ev.fit_ratio:.0%}")
    print("✓ test_pizza_time_fits_sparse_loop OK")


def test_instrumental_richness_score():
    metrics = _ref_metrics()
    profiles = build_style_profiles(metrics)
    asgore = metrics["ASGORE.mid"]
    sweden = metrics["Sweden_-_Minecraft.mid"]
    r_boss = compute_instrumental_richness(asgore, profiles["boss_orchestral"])
    r_sparse = compute_instrumental_richness(sweden, profiles["sparse_loop"])
    assert r_boss.score > r_sparse.score, (
        f"ASGORE ({r_boss.score}) debería ser más rico que Sweden ({r_sparse.score})"
    )
    print(f"  riqueza ASGORE={r_boss.score:.0f}  Sweden={r_sparse.score:.0f}")
    print("✓ test_instrumental_richness_score OK")


if __name__ == "__main__":
    test_infer_sparse_loop()
    test_infer_dense_battle()
    test_energetic_game_profile_exists()
    test_profiles_have_ranges_from_refs()
    test_pizza_time_fits_sparse_loop()
    test_instrumental_richness_score()
    print("\n✓ All benchmark profile tests passed")
