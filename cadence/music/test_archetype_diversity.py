"""Tests de diversidad instrumental y estructural por arquetipo."""

from cadence.music.archetype_diversity import (
    archetype_form_score_bonus,
    optional_layer_pool_for_archetype,
    pick_optional_layers_for_archetype,
    pick_structure_form_for_archetype,
    valid_archetype_forms,
    variance_for_archetype,
)
from cadence.music.creative_variation import build_creative_variation_bounds
from cadence.music.structure_catalog import suggest_forms
from cadence.music.narrative_anchors import build_narrative_anchors
from cadence.music.narrative_contract import build_narrative_contract
from cadence.schemas.song_state import (
    NarrativeContract,
    SectionIntent,
    SongNarrative,
    UserIntent,
)


def _anchors():
    intent = UserIntent(
        raw_prompt="test",
        use_case="game",
        knowledge_level="non_technical",
    )
    narrative = SongNarrative(
        logline="x",
        arc_type="flat",
        sections=[
            SectionIntent(
                id="main",
                narrative_role="establish",
                emotional_target="calm",
                density=0.5,
                harmonic_tension=0.3,
                rhythmic_complexity=0.3,
            ),
        ],
        global_motif=[0, 2, 4],
    )
    contract = build_narrative_contract(narrative, intent)
    return build_narrative_anchors(narrative, contract)


def test_archetype_forms_valid_and_rotates():
    forms = valid_archetype_forms("orchestral_boss")
    assert "boss_orchestral" in forms
    a = pick_structure_form_for_archetype("orchestral_boss", 0)
    b = pick_structure_form_for_archetype("orchestral_boss", 1)
    assert a in forms and b in forms
    assert archetype_form_score_bonus("boss_orchestral", "orchestral_boss") > 0
    assert archetype_form_score_bonus("menu_theme", "orchestral_boss") == 0.0


def test_suggest_forms_prefers_archetype_pool():
    sparse = suggest_forms(
        use_case="loop",
        genre_tags=["ambient"],
        energy_level=2,
        raw_prompt="loop ambiente minimal",
        generation_seed=7,
        limit=3,
    )
    assert sparse[0] in valid_archetype_forms("sparse_loop")

    dance = suggest_forms(
        use_case="game",
        genre_tags=["edm"],
        energy_level=5,
        raw_prompt="chiptune dance arcade",
        generation_seed=3,
        limit=3,
    )
    pool = set(valid_archetype_forms("dense_dance"))
    assert any(f in pool for f in dance[:2])


def test_optional_layers_differ_by_archetype_and_seed():
    pool_sparse = optional_layer_pool_for_archetype("sparse_loop")
    pool_boss = optional_layer_pool_for_archetype("orchestral_boss")
    assert pool_sparse != pool_boss
    assert "pad" in pool_sparse

    a = pick_optional_layers_for_archetype(
        "dense_dance", generation_seed=10, max_layers=3,
    )
    b = pick_optional_layers_for_archetype(
        "dense_dance", generation_seed=99, max_layers=3,
    )
    assert len(a) == 3
    assert all(i in pool_boss or i in optional_layer_pool_for_archetype("dense_dance") for i in a)
    assert a != b or len(optional_layer_pool_for_archetype("dense_dance")) <= 3


def test_creative_bounds_use_archetype_variance():
    anchors = _anchors()
    sparse = build_creative_variation_bounds(
        anchors,
        energy_level=2,
        use_case="loop",
        composition_archetype="sparse_loop",
        generation_seed=1,
    )
    dance = build_creative_variation_bounds(
        anchors,
        energy_level=5,
        use_case="game",
        composition_archetype="dense_dance",
        generation_seed=1,
    )
    assert sparse.pattern_variance < dance.pattern_variance
    assert sparse.allowed_optional_layers != dance.allowed_optional_layers
    ref = variance_for_archetype("sparse_loop")
    assert abs(sparse.pattern_variance - ref["pattern"]) < 0.15
