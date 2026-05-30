"""
Cobertura de patrones: variedad mínima por prompts representativos y
no-regresión mismo prompt + seeds distintos.
"""

from __future__ import annotations

from cadence.analysis.benchmark_examples import load_benchmark_prompts
from cadence.music.instrument_catalog import select_fallback_lead_layers
from cadence.music.pattern_batch_context import PatternBatchContext, clear_service_combo_memory
from cadence.music.pattern_registry import pattern_family
from cadence.music.pattern_selection_audit import pattern_family_entropy, rhythm_combo_signature
from cadence.music.strategy_pools import select_strategies
from cadence.schemas.song_state import PatternSelectionAudit

# Mínimos por dimensión en la suite representativa
MIN_DRUM_FAMILIES = 3
MIN_BASS_FAMILIES = 3
MIN_HARMONY_POOLS = 2
MIN_LEAD_LAYER_SETS = 2

# Mismo prompt, M seeds → al menos K combos únicos
SAME_PROMPT_M_RUNS = 16
SAME_PROMPT_MIN_UNIQUE_COMBOS = 4


def _run_case(
    *,
    seed: int,
    tags: list[str],
    use_case: str,
    energy: int,
    archetype: str | None = None,
) -> tuple[object, PatternSelectionAudit]:
    audit = PatternSelectionAudit(generation_seed=seed)
    strategies = select_strategies(
        seed,
        tags,
        "minor",
        use_case,
        energy,
        composition_archetype=archetype,
        pattern_selection_audit=audit,
    )
    return strategies, audit


def test_representative_prompts_minimum_pattern_variety():
    """Benchmarks + casos sintéticos → diversidad mínima de familias."""
    clear_service_combo_memory()
    drum_fams: set[str] = set()
    bass_fams: set[str] = set()
    harmonies: set[str] = set()
    lead_sets: set[frozenset[str]] = set()

    cases: list[tuple[int, list[str], str, int, str | None]] = []
    for i, bp in enumerate(load_benchmark_prompts()):
        e_mid = (bp.expected_energy[0] + bp.expected_energy[1]) // 2
        cases.append((
            10_000 + i * 7919,
            list(bp.style_hints),
            bp.expected_use_case,
            e_mid,
            bp.archetype,
        ))
    cases.extend([
        (42, ["chiptune", "dance"], "game", 5, "chiptune_dance"),
        (43, ["orchestral", "boss fight"], "game", 5, "orchestral_boss"),
        (44, ["ambient", "loop"], "loop", 2, "ambient_loop"),
    ])

    with PatternBatchContext(combo_window=3):
        for seed, tags, uc, energy, arch in cases:
            s, _audit = _run_case(
                seed=seed, tags=tags, use_case=uc, energy=energy, archetype=arch,
            )
            drum_fams.add(pattern_family(s.drum_pattern))
            bass_fams.add(pattern_family(s.bass_pattern))
            harmonies.add(s.harmony_pool)
            leads = select_fallback_lead_layers(
                use_case=uc,
                energy_level=energy,
                genre_tags=tags,
                generation_seed=seed,
                composition_archetype=arch,
            )
            lead_sets.add(frozenset(leads))

    assert len(drum_fams) >= MIN_DRUM_FAMILIES, drum_fams
    assert len(bass_fams) >= MIN_BASS_FAMILIES, bass_fams
    assert len(harmonies) >= MIN_HARMONY_POOLS, harmonies
    assert len(lead_sets) >= MIN_LEAD_LAYER_SETS, lead_sets
    print(
        f"  drums={drum_fams} bass={bass_fams} "
        f"harmony={harmonies} lead_sets={len(lead_sets)}"
    )
    print("✓ test_representative_prompts_minimum_pattern_variety OK")


def test_same_prompt_different_seeds_unique_combos():
    """No-regresión: un prompt fijo con seeds distintos → K combos en M runs."""
    tags = ["techno", "dubstep", "dark"]
    combos: set[str] = set()
    with PatternBatchContext(combo_window=4):
        for i in range(SAME_PROMPT_M_RUNS):
            seed = 50_000 + i * 1337
            s, audit = _run_case(
                seed=seed,
                tags=tags,
                use_case="game",
                energy=5,
                archetype="default_game",
            )
            combos.add(rhythm_combo_signature(
                s.drum_pattern, s.bass_pattern, s.harmony_pool,
            ))
            assert audit.rhythm_combo
            assert any(f.field == "drum" and f.weights for f in audit.fields)

    assert len(combos) >= SAME_PROMPT_MIN_UNIQUE_COMBOS, (
        f"solo {len(combos)} combos únicos en {SAME_PROMPT_M_RUNS} runs: {combos}"
    )
    print(f"  unique_combos={len(combos)}/{SAME_PROMPT_M_RUNS}")
    print("✓ test_same_prompt_different_seeds_unique_combos OK")


def test_audit_export_shape():
    """Auditoría incluye candidatos, pesos y selection_reason."""
    _, audit = _run_case(
        seed=7,
        tags=["drum and bass"],
        use_case="game",
        energy=4,
        archetype="default_game",
    )
    dumped = audit.model_dump()
    assert dumped["rhythm_combo"]
    drum_field = next(f for f in dumped["fields"] if f["field"] == "drum")
    assert drum_field["candidates"]
    assert drum_field["weights"]
    assert drum_field["chosen"]
    assert "weighted_pick" in drum_field["selection_reason"]
    print("✓ test_audit_export_shape OK")


def test_exporter_includes_pattern_selection_audit():
    from cadence.agent.nodes.exporter import _build_rsong
    from cadence.test_fixtures.pipeline_coherence import build_aligned_pipeline_state
    from cadence.schemas.song_state import ValidationResult

    state = build_aligned_pipeline_state(generation_seed=4242)
    state["validation_result"] = ValidationResult(score=1.0, passed=True)
    assert state.get("pattern_selection_audit") is not None
    rsong = _build_rsong(state)
    audit = rsong["game_meta"].get("pattern_selection_audit")
    assert audit and audit.get("fields")
    assert audit.get("rhythm_combo")
    print("✓ test_exporter_includes_pattern_selection_audit OK")


def test_pattern_family_entropy_metric():
    drums = ["techno_a", "techno_b", "techno_a", "dnb_a"]
    ent = pattern_family_entropy(drums)
    assert ent < 1.5
    mixed = ["techno_a", "dnb_a", "breakbeat_a", "house_a"]
    assert pattern_family_entropy(mixed) > ent
    print("✓ test_pattern_family_entropy_metric OK")


if __name__ == "__main__":
    test_representative_prompts_minimum_pattern_variety()
    test_same_prompt_different_seeds_unique_combos()
    test_audit_export_shape()
    test_exporter_includes_pattern_selection_audit()
    test_pattern_family_entropy_metric()
    print("\n✓ All pattern_coverage tests passed")
