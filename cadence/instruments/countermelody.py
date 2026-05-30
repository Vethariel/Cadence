"""Contramelodía determinista — segunda voz derivada del motivo en desarrollo."""

from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.agent.nodes.narrative_apply import melody_should_play
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.seed_policy import seed_for_state
from cadence.music.development_theory import development_for_bar, section_development_map
from cadence.music.harmony_theory import chord_at_bar, chord_tones_as_degrees, section_harmony_map
from cadence.music.instrument_patterns import COUNTER_PATTERN_POOL, counter_steps
from cadence.music.layer_voice_variation import counter_skip_step, pitch_shift_for_transform
from cadence.music.segment_variation import segment_at_bar, segment_index_at_bar, pattern_id_for_segment
from cadence.music.style_archetype import get_composition_archetype
from cadence.schemas.song_state import RhythmEvent, Track


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _compose_countermelody(ctx: ComposeContext) -> Track | None:
    structure = ctx.state["structure"]
    development = ctx.state.get("development")
    harmony = ctx.state.get("harmony")

    if not development:
        return None

    intent_map = section_intent_map_from_state(ctx.state, context="countermelody")
    dev_map = section_development_map(development)
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())

    from cadence.agent.nodes.melody import _get_scale_pitches
    scale_pitches = _get_scale_pitches(ctx.key, ctx.mode)

    strategies = ctx.state.get("strategies")
    seed = seed_for_state(ctx.state, "countermelody") or ctx.state.get("generation_seed", 0)
    base_counter = strategies.counter_pattern if strategies else None
    archetype = get_composition_archetype(ctx.state)
    texture_mode = (
        development.texture_mode if development else "staggered"
    )

    step_ms = _ms_per_step(ctx.bpm)
    steps_per_bar = 16
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        dev = dev_map.get(section)

        if section not in active or not melody_should_play(intent) or not dev:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        density = intent.density if intent else 0.5
        if density < 0.45:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        base_vel = int(42 + density * 32)
        if texture_mode == "bedded" or archetype == "cinematic_cutscene":
            base_vel = int(38 + density * 28)

        for bar_idx in range(bars):
            bar_dev = development_for_bar(dev, bar_idx)
            seg = segment_at_bar(dev, bar_idx) if dev.segments else None
            seg_idx = segment_index_at_bar(dev, bar_idx) if dev.segments else 0
            transform = bar_dev.transform
            motif = bar_dev.motif_variant or development.global_motif or [0, 2, 4]

            pat_id = pattern_id_for_segment(
                base_counter or "offbeat_sync_a",
                seg_idx,
                transform,
                seed + hash(section) % 9973,
                COUNTER_PATTERN_POOL,
            )
            step_pattern = counter_steps(pat_id, seed + seg_idx * 11)
            pitch_shift = pitch_shift_for_transform(transform, seg_idx)

            section_h = harmony_map.get(section)
            chord_degrees = motif
            if section_h:
                chord = chord_at_bar(section_h, bar_idx)
                chord_degrees = chord_tones_as_degrees(chord)

            for step_i, step in enumerate(step_pattern):
                if counter_skip_step(
                    step_i, transform,
                    texture_mode=texture_mode,
                    events_per_bar=len(step_pattern),
                ):
                    continue
                degree = chord_degrees[step_i % len(chord_degrees)] % 7
                if transform == "invert":
                    degree = (6 - degree) % 7
                pitch = scale_pitches[degree] + pitch_shift
                pitch = max(60, min(103, pitch))
                events.append(RhythmEvent(
                    t=int(current_t + step * step_ms),
                    type="note",
                    pitch=pitch,
                    duration_ms=int(step_ms * 1.2),
                    velocity=base_vel,
                    beat_index=beat_index + step,
                    section=section,
                ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id="countermelody",
        instrument_id="countermelody",
        instrument="Counter Melody",
        midi_channel=4,
        role="lead",
        events=events,
    )


register(InstrumentDefinition(
    instrument_id="countermelody",
    display_name="Counter Melody",
    role="lead",
    midi_channel=4,
    requires_llm=False,
    compose=_compose_countermelody,
))
