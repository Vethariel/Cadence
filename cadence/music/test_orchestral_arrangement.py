"""Boss orquestal — capas obligatorias en arreglo."""

from cadence.music.orchestral_arrangement import (
    ORCHESTRAL_BOSS_MANDATORY,
    apply_orchestral_boss_instruments,
)


def test_mandatory_layers_merged():
    chosen = apply_orchestral_boss_instruments({"melody", "bass", "drums"}, 5)
    assert ORCHESTRAL_BOSS_MANDATORY <= chosen


def test_low_energy_unchanged():
    chosen = apply_orchestral_boss_instruments({"melody"}, 2)
    assert chosen == {"melody"}


if __name__ == "__main__":
    test_mandatory_layers_merged()
    test_low_energy_unchanged()
    print("All orchestral_arrangement tests passed.")
