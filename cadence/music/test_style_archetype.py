"""Tests de inferencia de arquetipo compositivo."""

from cadence.analysis.benchmark_examples import load_benchmark_prompts
from cadence.music.style_archetype import (
    infer_composition_archetype,
    infer_composition_archetype_with_reason,
    melody_texture_for_archetype,
)
from cadence.music.repertoire_signals import percussion_suppressed
from cadence.schemas.song_state import MusicalStyleProfile


def test_compact_from_prompt():
    arch = infer_composition_archetype(
        style_profile=MusicalStyleProfile(genres=["action", "platform"]),
        raw_prompt="Pelea compacta, pocos instrumentos a la vez, sin orquesta",
        use_case="game",
        energy_level=4,
    )
    assert arch == "compact_action"


def test_chiptune_from_genres():
    arch = infer_composition_archetype(
        style_profile=MusicalStyleProfile(genres=["chiptune", "eurobeat", "arcade"]),
        raw_prompt="combate arcade denso",
        use_case="game",
        energy_level=5,
    )
    assert arch == "chiptune_dance"


def test_orchestral_boss():
    arch = infer_composition_archetype(
        style_profile=MusicalStyleProfile(
            genres=["orchestral", "symphonic", "epic", "boss fight"],
        ),
        raw_prompt="boss fight orquestal épico con muchas capas simultáneas",
        use_case="game",
        energy_level=5,
    )
    assert arch == "orchestral_boss"


def test_precedence_compact_platform_over_orchestral_tags():
    """Regresión energetic_game: tags orquestales + prompt plataforma compacta."""
    bp = next(p for p in load_benchmark_prompts() if p.id == "energetic_game")
    decision = infer_composition_archetype_with_reason(
        style_profile=MusicalStyleProfile(
            genres=["orchestral", "boss fight", "combat", "platformer"],
        ),
        raw_prompt=bp.prompt,
        use_case=bp.expected_use_case,
        energy_level=4,
    )
    assert decision.archetype == "compact_action"
    assert "precedence_matrix" in decision.reason or "compact" in decision.reason


def test_reconcile_llm_orchestral_overridden_by_compact_prompt():
    from cadence.music.style_archetype import reconcile_llm_archetype

    bp = next(p for p in load_benchmark_prompts() if p.id == "energetic_game")
    decision = reconcile_llm_archetype(
        "orchestral_boss",
        style_profile=MusicalStyleProfile(
            genres=["orchestral", "boss fight", "eurobeat"],
        ),
        raw_prompt=bp.prompt,
        use_case="game",
        energy_level=4,
    )
    assert decision.archetype == "compact_action"
    assert "guardrail" in decision.reason or "precedence" in decision.reason


def test_archetype_reason_exported():
    decision = infer_composition_archetype_with_reason(
        raw_prompt="loop ambiente",
        use_case="loop",
        energy_level=1,
    )
    assert decision.archetype == "ambient_loop"
    assert decision.reason


def test_drum_machines_avoid_does_not_suppress_drums():
    profile = MusicalStyleProfile(
        genres=["orchestral"],
        avoid=["synthesizers", "drum machines", "electronic dance music"],
    )
    assert percussion_suppressed(
        use_case="game", energy_level=5, style_profile=profile,
    ) is False


def test_explicit_no_drums_suppresses():
    profile = MusicalStyleProfile(avoid=["no drums", "lush pads"])
    assert percussion_suppressed(
        use_case="game", energy_level=5, style_profile=profile,
    ) is True


def test_melody_texture_chiptune_dense():
    assert melody_texture_for_archetype("chiptune_dance", 5, "game") == "dense"


if __name__ == "__main__":
    test_compact_from_prompt()
    test_chiptune_from_genres()
    test_orchestral_boss()
    test_precedence_compact_platform_over_orchestral_tags()
    test_reconcile_llm_orchestral_overridden_by_compact_prompt()
    test_archetype_reason_exported()
    test_drum_machines_avoid_does_not_suppress_drums()
    test_explicit_no_drums_suppresses()
    test_melody_texture_chiptune_dense()
    print("All style_archetype tests passed.")
