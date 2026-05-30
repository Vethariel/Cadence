"""Umbrales de densidad melódica — delegados en VoiceRegisterProfile."""

from __future__ import annotations

from cadence.schemas.song_state import SectionIntent, SongState

# Perfil benchmark dense_dance ≈ chiptune_dance + default_game denso en alta energía
DENSE_MELODY_ARCHETYPES = frozenset({"chiptune_dance"})


def _profile_from_kwargs(
    composition_archetype: str | None,
    energy_level: int,
    melody_texture: str,
    use_case: str,
    state: SongState | None = None,
):
    if state is not None:
        from cadence.music.voice_register_profile import profile_from_state
        return profile_from_state(state)
    from cadence.music.voice_register_profile import resolve_voice_register_profile

    return resolve_voice_register_profile(
        composition_archetype=composition_archetype or "default_game",
        energy_level=energy_level,
        use_case=use_case,
        melody_texture=melody_texture,
    )


def is_dense_melody_target(
    composition_archetype: str | None,
    *,
    energy_level: int = 3,
    melody_texture: str = "balanced",
    use_case: str = "game",
    state: SongState | None = None,
) -> bool:
    profile = _profile_from_kwargs(
        composition_archetype, energy_level, melody_texture, use_case, state,
    )
    return profile.is_dense_melody_target(energy_level, use_case)


def melody_notes_per_bar_target(
    composition_archetype: str | None,
    energy_level: int,
    *,
    narrative_role: str | None = None,
    melody_texture: str = "balanced",
    use_case: str = "game",
    state: SongState | None = None,
) -> int:
    profile = _profile_from_kwargs(
        composition_archetype, energy_level, melody_texture, use_case, state,
    )
    return profile.notes_per_bar_target(energy_level, narrative_role=narrative_role)


def melody_max_long_gap_ratio(
    composition_archetype: str | None,
    energy_level: int = 3,
    *,
    melody_texture: str = "balanced",
    use_case: str = "game",
    state: SongState | None = None,
) -> float | None:
    profile = _profile_from_kwargs(
        composition_archetype, energy_level, melody_texture, use_case, state,
    )
    return profile.melody_max_long_gap_ratio(energy_level)


def melody_min_notes_per_bar_validator(
    composition_archetype: str | None,
    energy_level: int,
    *,
    melody_texture: str = "balanced",
    use_case: str = "game",
    state: SongState | None = None,
) -> float | None:
    profile = _profile_from_kwargs(
        composition_archetype, energy_level, melody_texture, use_case, state,
    )
    return profile.melody_min_notes_per_bar_validator(energy_level)


def melody_rest_ratio_for_intent(
    intent: SectionIntent | None,
    *,
    use_case: str = "game",
    composition_archetype: str | None = None,
    energy_level: int = 3,
    melody_texture: str = "balanced",
    state: SongState | None = None,
) -> float:
    profile = _profile_from_kwargs(
        composition_archetype, energy_level, melody_texture, use_case, state,
    )
    return profile.melody_rest_ratio_for_intent(
        intent, use_case=use_case, energy_level=energy_level,
    )
