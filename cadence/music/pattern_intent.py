"""Capa intermedia: intención de patrones (género compuesto → pools), separada del seed."""

from __future__ import annotations

from cadence.music.genre_pattern_affinity import (
    layer_bias_from_genre_mix,
    rank_bass_candidates,
    rank_drum_candidates,
    rank_harmony_candidates,
)
from cadence.music.repertoire_signals import (
    bass_pool_priority,
    drum_pool_priority,
    harmony_pool_priority,
    layer_pattern_bias,
)
from cadence.music.style_profile import GenreMix, balance_genre_mix
from cadence.schemas.song_state import PatternIntent


def derive_pattern_intent(
    *,
    genre_mix: GenreMix | dict[str, float],
    use_case: str = "game",
    mood: str = "",
    energy_level: int = 3,
    composition_archetype: str | None = None,
    generation_seed: int = 0,
) -> PatternIntent:
    """Construye intención de patrón sin elegir ids finales (eso hace select_strategies + seed)."""
    mix = balance_genre_mix(dict(genre_mix))
    arch = composition_archetype

    drum_base = drum_pool_priority(
        energy_level, use_case, composition_archetype=arch,
    )
    bass_base = bass_pool_priority(
        energy_level, use_case, composition_archetype=arch,
    )
    harmony_base = harmony_pool_priority(
        energy_level, use_case, composition_archetype=arch,
    )
    layer_base = layer_pattern_bias(
        energy_level, use_case, generation_seed, composition_archetype=arch,
    )

    drum_candidates = rank_drum_candidates(drum_base, mix)
    bass_candidates = rank_bass_candidates(bass_base, mix)
    harmony_candidates = rank_harmony_candidates(harmony_base, mix)
    layer_bias = layer_bias_from_genre_mix(layer_base, mix)

    _apply_mood_echo_bias(layer_bias, mood, mix, arch)

    return PatternIntent(
        genre_mix=mix,
        drum_candidates=drum_candidates,
        bass_candidates=bass_candidates,
        harmony_candidates=harmony_candidates,
        layer_bias=layer_bias,
        mood=(mood or "").strip(),
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=arch,
    )


def _apply_mood_echo_bias(
    bias: dict[str, list[str] | str],
    mood: str,
    genre_mix: dict[str, float],
    archetype: str | None,
) -> None:
    m = (mood or "").lower()
    if bias.get("echo_source") not in (None, "", "auto"):
        return
    orch_w = sum(
        genre_mix.get(g, 0.0)
        for g in ("orchestral", "cinematic", "epic", "hybrid orchestral", "symphonic")
    )
    dance_w = sum(genre_mix.get(g, 0.0) for g in ("techno", "house", "dubstep", "dance"))
    if archetype == "orchestral_boss" or orch_w >= 0.35:
        bias["echo_source"] = "chord_stab"
    elif dance_w >= 0.4 and "dark" not in m and "epic" not in m:
        bias["echo_source"] = "melody"
    elif "tense" in m or "epic" in m:
        bias["echo_source"] = "chord_stab"
