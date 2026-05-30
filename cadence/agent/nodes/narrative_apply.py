"""Aplica SongNarrative a la generación determinista de eventos."""

from cadence.schemas.song_state import SectionIntent, SongNarrative, RhythmEvent


def section_intent_map(narrative: SongNarrative | None) -> dict[str, SectionIntent]:
    if not narrative:
        return {}
    return {s.id: s for s in narrative.sections}


def drum_velocities(
    section: str,
    intent: SectionIntent | None,
    defaults: dict[str, dict[str, int]],
) -> dict[str, int]:
    base = dict(defaults.get(section, defaults["default"]))
    if not intent:
        return base
    # density 0→70% vel, density 1→100% vel
    scale = 0.65 + intent.density * 0.35
    return {k: min(127, int(v * scale)) for k, v in base.items()}


def bass_should_play(section: str, intent: SectionIntent | None) -> bool:
    if intent is None:
        return section != "breakdown"
    if intent.narrative_role == "silence" or intent.density < 0.2:
        return False
    if intent.narrative_role == "reflection" and intent.density < 0.35:
        return False
    if section == "breakdown" and intent.density < 0.45:
        return False
    return True


def hihat_active(step: int, intent: SectionIntent | None) -> bool:
    """Filtra hi-hats según complejidad rítmica narrativa."""
    if intent is None or intent.rhythmic_complexity >= 0.45:
        return True
    return step % 2 == 0


def snare_ghost_velocity(base_vel: int, step: int, intent: SectionIntent | None) -> int | None:
    """Ghost note en off-beats cuando hay alta complejidad."""
    if intent is None or intent.rhythmic_complexity < 0.65:
        return None
    if step in (3, 7, 11, 15):
        return max(35, base_vel // 3)
    return None


def bar_variant_step(step: int, bar_idx: int, intent: SectionIntent | None) -> int:
    """Pequeña variación A/A'/B: acentúa snare en bar impar."""
    if intent is None or intent.rhythmic_complexity < 0.5:
        return step
    if bar_idx % 2 == 1 and step == 14:
        return 15  # desplazar último snare hit
    return step


def transition_events(
    t_bar_start: float,
    step_ms: float,
    transition_out: str,
    section: str,
    beat_index: int,
    drum_midi: dict[str, int],
) -> list[RhythmEvent]:
    """Eventos de transición en el último compás de una sección."""
    events: list[RhythmEvent] = []
    steps_per_bar = 16

    if transition_out == "riser":
        for step in range(8, steps_per_bar):
            vel = 55 + int((step - 8) / 8 * 70)
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["snare"],
                duration_ms=int(step_ms * 0.85),
                velocity=min(127, vel),
                beat_index=beat_index + step,
                section=section,
            ))
        for step in range(0, steps_per_bar, 2):
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["hihat"],
                duration_ms=int(step_ms * 0.7),
                velocity=40 + step * 3,
                beat_index=beat_index + step,
                section=section,
            ))

    elif transition_out == "pickup":
        for step in (12, 14, 15):
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["snare"],
                duration_ms=int(step_ms * 0.9),
                velocity=100,
                beat_index=beat_index + step,
                section=section,
            ))

    elif transition_out == "filter_sweep":
        for step in range(steps_per_bar):
            vel = 30 + int(step / steps_per_bar * 90)
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["hihat"],
                duration_ms=int(step_ms * 0.6),
                velocity=min(127, vel),
                beat_index=beat_index + step,
                section=section,
            ))

    elif transition_out == "fade":
        for step in range(8, steps_per_bar):
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["kick"],
                duration_ms=int(step_ms * 0.9),
                velocity=max(30, 90 - (step - 8) * 8),
                beat_index=beat_index + step,
                section=section,
            ))

    elif transition_out == "cut":
        # Silencio intencional en beats 3-4 del último compás (steps 8-15)
        pass

    elif transition_out == "breakdown":
        for step in (0, 8):
            events.append(RhythmEvent(
                t=int(t_bar_start + step * step_ms),
                type="drum_hit",
                pitch=drum_midi["kick"],
                duration_ms=int(step_ms * 1.2),
                velocity=50,
                beat_index=beat_index + step,
                section=section,
            ))

    return events


def melody_should_play(intent: SectionIntent | None) -> bool:
    if intent is None:
        return True
    if intent.narrative_role == "silence":
        return False
    return intent.density >= 0.2


def melody_rest_ratio(
    intent: SectionIntent | None,
    *,
    use_case: str = "game",
    composition_archetype: str | None = None,
    energy_level: int = 3,
    melody_texture: str = "balanced",
) -> float:
    """Proporción sugerida de silencios en el patrón melódico."""
    from cadence.music.melody_density_policy import melody_rest_ratio_for_intent

    return melody_rest_ratio_for_intent(
        intent,
        use_case=use_case,
        composition_archetype=composition_archetype,
        energy_level=energy_level,
        melody_texture=melody_texture,
    )


def narrative_melody_hint(intent: SectionIntent | None) -> str:
    if intent is None:
        return ""
    duration_hint = "notas cortas (1-2 steps)" if intent.density >= 0.7 else (
        "notas largas (4 steps)" if intent.density < 0.4 else "notas medias (2 steps)"
    )
    rest_pct = int(melody_rest_ratio(intent, use_case="game") * 100)
    return (
        f"role={intent.narrative_role}, emotion={intent.emotional_target}, "
        f"density={intent.density:.1f} → {duration_hint}, ~{rest_pct}% silencios"
    )
