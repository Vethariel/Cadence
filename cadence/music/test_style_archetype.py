"""Tests de inferencia de arquetipo compositivo."""

from cadence.music.style_archetype import (
    infer_composition_archetype,
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
        raw_prompt="boss fight orquestal épico",
        use_case="game",
        energy_level=5,
    )
    assert arch == "orchestral_boss"


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
    test_drum_machines_avoid_does_not_suppress_drums()
    test_explicit_no_drums_suppresses()
    test_melody_texture_chiptune_dense()
    print("All style_archetype tests passed.")
