"""Contrato de VoiceRegisterProfile — perfiles y presión de stack."""

from cadence.music.voice_register_profile import (
    resolve_voice_register_profile,
)
from cadence.schemas.song_state import SectionIntent


def test_orchestral_boss_legato_quarter_bass():
    p = resolve_voice_register_profile(
        composition_archetype="orchestral_boss",
        energy_level=5,
        use_case="game",
        texture_mode="simultaneous",
        harmonic_support_count=2,
        lead_support_count=2,
        active_optional_count=3,
    )
    assert p.lead_articulation == "legato"
    assert p.bass_grid_tier in ("half", "quarter")
    assert not p.allow_densify
    assert not p.quantize_lead_to_harmony
    assert p.stack_pressure
    assert p.normalize_bass_pattern_id("driving") == "half_time"
    assert p.normalize_bass_pattern_id("octave_pulse") == "root_fifth"


def test_chiptune_hyper_staccato():
    p = resolve_voice_register_profile(
        composition_archetype="chiptune_dance",
        energy_level=5,
        use_case="game",
        melody_texture="dense",
    )
    assert p.lead_density_tier == "hyper"
    assert p.lead_articulation == "staccato"
    assert p.allow_densify
    assert p.bass_grid_tier == "sixteenth"


def test_bedded_loop_sparse():
    p = resolve_voice_register_profile(
        composition_archetype="default_game",
        energy_level=2,
        use_case="loop",
        melody_texture="sparse",
        texture_mode="bedded",
    )
    assert p.lead_density_tier == "sparse"
    assert p.lead_articulation == "legato"
    assert not p.allow_densify


def test_moderate_notes_target():
    p = resolve_voice_register_profile(
        composition_archetype="orchestral_boss",
        energy_level=5,
        use_case="game",
    )
    assert p.notes_per_bar_target(5, narrative_role="climax") <= 5
    assert p.melody_rest_ratio_for_intent(
        SectionIntent(
            id="x",
            narrative_role="climax",
            emotional_target="",
            density=0.9,
            harmonic_tension=0.8,
            rhythmic_complexity=0.6,
        ),
        energy_level=5,
    ) >= 0.15


def test_bass_pool_respects_tier():
    p = resolve_voice_register_profile(
        composition_archetype="cinematic_cutscene",
        energy_level=3,
        use_case="cutscene",
    )
    top = p.bass_pool_priority()[:3]
    assert "half_time" in top or "pulse" in top


if __name__ == "__main__":
    test_orchestral_boss_legato_quarter_bass()
    test_chiptune_hyper_staccato()
    test_bedded_loop_sparse()
    test_moderate_notes_target()
    test_bass_pool_respects_tier()
    print("All voice_register_profile tests passed.")
