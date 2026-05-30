"""Tests de fallback rítmico por contexto y orquestación genre-aware."""

from cadence.music.genre_orchestration import (
    optional_layer_genre_score,
    select_lead_layers_genre_aware,
)
from cadence.music.instrument_catalog import get_timbres, select_fallback_lead_layers
from cadence.music.pattern_registry import pattern_family
from cadence.music.repertoire_signals import max_optional_budget
from cadence.music.rhythm_fallback_ladders import (
    fallback_bass_candidates,
    resolve_rhythm_context_key,
)
from cadence.music.strategy_pools import resolve_rhythm_patterns


def test_high_energy_bass_ladder_avoids_root_fifth_only():
    cands = fallback_bass_candidates(
        use_case="game",
        energy_level=5,
        genre_tags=["techno"],
        repertoire_priority=[],
    )
    families = {pattern_family(p) for p in cands}
    assert "root_fifth" not in families or families != {"root_fifth"}
    assert families & {"driving", "syncopated", "octave_pulse"}
    print("✓ test_high_energy_bass_ladder_avoids_root_fifth_only OK")


def test_dubstep_fallback_not_monotone_root_fifth():
    _, bass = resolve_rhythm_patterns(
        "invalid", "invalid",
        genre_tags=["dubstep"],
        energy_level=5,
        use_case="game",
        generation_seed=42,
    )
    fam = pattern_family(bass)
    assert fam in (
        "driving", "syncopated", "octave_pulse", "walk", "half_time",
        "pulse", "staccato", "sub_drop",
    )
    assert fam != "root_fifth"
    print(f"  dubstep bass fallback: {bass} ({fam})")
    print("✓ test_dubstep_fallback_not_monotone_root_fifth OK")


def test_loop_low_energy_bass_from_pulse_ladder():
    _, bass = resolve_rhythm_patterns(
        "techno", "invalid",
        genre_tags=[],
        energy_level=2,
        use_case="loop",
        generation_seed=0,
    )
    assert pattern_family(bass) in ("pulse", "half_time")
    print("✓ test_loop_low_energy_bass_from_pulse_ladder OK")


def test_boss_context_key():
    key = resolve_rhythm_context_key(
        use_case="game",
        energy_level=5,
        composition_archetype="orchestral_boss",
    )
    assert key == "boss"
    print("✓ test_boss_context_key OK")


def test_chiptune_lead_layers_prefer_arp():
    layers = select_lead_layers_genre_aware(
        use_case="game",
        energy_level=5,
        generation_seed=7,
        genre_tags=["chiptune", "dance"],
        max_lead=2,
    )
    assert layers
    score_arp = optional_layer_genre_score("arp_synth", genre_tags=["chiptune"])
    score_pad = optional_layer_genre_score("pad", genre_tags=["chiptune"])
    assert score_arp > score_pad
    print(f"  chiptune leads: {layers}")
    print("✓ test_chiptune_lead_layers_prefer_arp OK")


def test_orchestral_optional_budget_boost():
    base = max_optional_budget("game", 3, composition_archetype=None)
    boosted = max_optional_budget(
        "game", 4,
        composition_archetype=None,
        genre_tags=["orchestral", "cinematic"],
    )
    assert boosted[0] >= base[0]
    print("✓ test_orchestral_optional_budget_boost OK")


def test_bass_timbres_filtered_for_orchestral():
    all_bass = get_timbres("bass", genre_tags=None)
    orch = get_timbres(
        "bass",
        genre_tags=["orchestral", "cinematic"],
        composition_archetype="cinematic_cutscene",
    )
    assert len(orch) >= 3
    assert len(orch) <= len(all_bass)
    print("✓ test_bass_timbres_filtered_for_orchestral OK")


def test_techno_game_leads_not_empty():
    game = select_fallback_lead_layers(
        use_case="game",
        energy_level=5,
        genre_tags=["techno"],
        generation_seed=99,
    )
    assert len(game) <= 2
    assert game
    print("✓ test_techno_game_leads_not_empty OK")


if __name__ == "__main__":
    test_high_energy_bass_ladder_avoids_root_fifth_only()
    test_dubstep_fallback_not_monotone_root_fifth()
    test_loop_low_energy_bass_from_pulse_ladder()
    test_boss_context_key()
    test_chiptune_lead_layers_prefer_arp()
    test_orchestral_optional_budget_boost()
    test_bass_timbres_filtered_for_orchestral()
    test_techno_game_leads_not_empty()
    print("\n✓ All rhythm/genre orchestration tests passed")
