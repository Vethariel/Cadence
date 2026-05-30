"""Tests de anclas, variación creativa y política de semillas."""

from cadence.music.creative_variation import (
    build_creative_variation_bounds,
    clamp_optional_layer_ids,
)
from cadence.music.narrative_anchors import build_narrative_anchors
from cadence.music.narrative_contract import build_narrative_contract
from cadence.music.seed_policy import (
    build_node_seeds,
    derive_node_seed,
    node_temperature,
)
from cadence.schemas.song_state import (
    CreativeVariationBounds,
    NarrativeContract,
    SectionIntent,
    SongNarrative,
    UserIntent,
)


def _fixture():
    intent = UserIntent(
        raw_prompt="boss fight denso",
        knowledge_level="non_technical",
        use_case="game",
        mood="intense",
        style_tags=["techno"],
    )
    narrative = SongNarrative(
        logline="confrontation",
        arc_type="rise-climax-fall",
        sections=[
            SectionIntent(
                id="intro",
                narrative_role="establish",
                emotional_target="tension",
                density=0.4,
                harmonic_tension=0.3,
                rhythmic_complexity=0.4,
            ),
            SectionIntent(
                id="climax",
                narrative_role="climax",
                emotional_target="triumph",
                density=0.9,
                harmonic_tension=0.85,
                rhythmic_complexity=0.8,
            ),
        ],
        global_motif=[0, 2, 5],
    )
    contract = build_narrative_contract(narrative, intent)
    anchors = build_narrative_anchors(narrative, contract)
    return intent, anchors


def test_anchors_key_section_and_curve():
    _, anchors = _fixture()
    assert "climax" in anchors.key_section_ids
    assert len(anchors.tension_release_curve) == 2
    assert anchors.tension_release_curve[-1] > anchors.tension_release_curve[0]


def test_creative_bounds_compact():
    _, anchors = _fixture()
    bounds = build_creative_variation_bounds(
        anchors, energy_level=4, use_case="game",
        composition_archetype="compact_action", generation_seed=42,
    )
    assert bounds.max_optional_layers <= 3
    assert bounds.max_lead_optionals == 1


def test_get_composition_archetype_cached():
    from cadence.music.style_archetype import get_composition_archetype

    state = {"composition_archetype": "chiptune_dance"}
    assert get_composition_archetype(state) == "chiptune_dance"


def test_clamp_optional_layers():
    bounds = CreativeVariationBounds(
        max_optional_layers=2,
        max_lead_optionals=1,
        allowed_optional_layers=["pad", "arp_synth", "echo_synth"],
        pattern_variance=0.5,
        micro_phrase_variance=0.5,
        fill_density=0.4,
        timbre_variance=0.5,
        secondary_motif_variance=0.4,
    )
    raw = {"drums", "bass", "melody", "arp_synth", "echo_synth", "countermelody", "pad"}
    out = clamp_optional_layer_ids(raw, bounds)
    assert "drums" in out and "melody" in out
    assert "countermelody" not in out
    assert len([x for x in out if x not in ("drums", "bass", "melody")]) <= 2


def test_node_seeds_stable_and_distinct():
    ns = build_node_seeds(12345)
    assert ns.generation_seed == 12345
    assert ns.seed_prompt_enhancer == derive_node_seed(12345, "prompt_enhancer")
    assert ns.seed_melody != ns.seed_prompt_enhancer


def test_temperature_policy():
    assert node_temperature("technical_spec") < node_temperature("prompt_enhancer")


if __name__ == "__main__":
    test_anchors_key_section_and_curve()
    test_creative_bounds_compact()
    test_clamp_optional_layers()
    test_node_seeds_stable_and_distinct()
    test_temperature_policy()
    test_get_composition_archetype_cached()
    print("All composition_policy tests passed.")
