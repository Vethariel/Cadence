"""Géneros compuestos con pesos — sin colapso a una sola rama."""

from cadence.music.style_profile import balance_genre_mix, build_genre_mix
from cadence.schemas.song_state import MusicalStyleProfile


def test_composite_techno_orchestral_boss_balanced():
    mix = build_genre_mix(
        style_profile=MusicalStyleProfile(
            genres=["techno", "orchestral", "boss fight"],
        ),
        raw_prompt="boss fight techno orchestral epic",
    )
    assert len(mix) >= 3
    assert max(mix.values()) <= 0.42
    assert mix.get("techno", 0) >= 0.08
    assert mix.get("orchestral", 0) >= 0.08
    assert mix.get("boss fight", 0) >= 0.08


def test_balance_caps_dominant_genre():
    raw = {"techno": 0.9, "orchestral": 0.08, "boss fight": 0.02}
    balanced = balance_genre_mix(raw)
    assert balanced["techno"] <= 0.4
    assert abs(sum(balanced.values()) - 1.0) < 0.03


if __name__ == "__main__":
    test_composite_techno_orchestral_boss_balanced()
    test_balance_caps_dominant_genre()
    print("All genre_mix tests passed.")
