"""Voces ensemble — maderas, teclas, cuerdas, guitarras y metal (canales 11–15 + 5/7/8)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cadence.agent.nodes.narrative_apply import melody_should_play
from cadence.instruments.context import ComposeContext
from cadence.instruments.registry import InstrumentDefinition, register
from cadence.music.development_theory import development_for_bar, section_development_map
from cadence.music.layer_voice_variation import counter_skip_step, pitch_shift_for_transform
from cadence.music.harmony_theory import chord_at_bar, chord_pitches, chord_tones_as_degrees, section_harmony_map
from cadence.music.arp_patterns import generate_bar_arp, resolve_arp_pattern
from cadence.music.instrument_patterns import counter_steps, pluck_steps
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.seed_policy import seed_for_state
from cadence.music.segment_variation import segment_index_at_bar
from cadence.schemas.song_state import RhythmEvent, Track


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _ms_per_bar(bpm: int) -> float:
    return (60000 / bpm) * 4


@dataclass(frozen=True)
class EnsembleVoiceSpec:
    instrument_id: str
    display_name: str
    midi_channel: int
    role: Literal["lead", "pad", "bass", "rhythm", "fx"]
    compose_kind: Literal["counter", "pad", "pluck", "arp"]
    pitch_shift: int = 12
    velocity_scale: float = 1.0
    invert_motif: bool = False
    octave_pad: int = 3


VOICE_SPECS: dict[str, EnsembleVoiceSpec] = {
    "woodwind_a": EnsembleVoiceSpec(
        "woodwind_a", "Woodwind A", 11, "lead", "counter", pitch_shift=12,
    ),
    "woodwind_b": EnsembleVoiceSpec(
        "woodwind_b", "Woodwind B", 12, "lead", "counter",
        pitch_shift=19, velocity_scale=0.9, invert_motif=True,
    ),
    "keys_piano": EnsembleVoiceSpec(
        "keys_piano", "Keys Piano", 13, "lead", "counter", pitch_shift=0, velocity_scale=1.05,
    ),
    "keys_organ": EnsembleVoiceSpec(
        "keys_organ", "Keys Organ", 14, "pad", "pad", octave_pad=2, velocity_scale=0.85,
    ),
    "strings_ensemble": EnsembleVoiceSpec(
        "strings_ensemble", "Strings Ensemble", 15, "pad", "pad", octave_pad=3,
    ),
    "guitar_acoustic": EnsembleVoiceSpec(
        "guitar_acoustic", "Guitar Acoustic", 8, "lead", "pluck", pitch_shift=0,
    ),
    "guitar_electric": EnsembleVoiceSpec(
        "guitar_electric", "Guitar Electric", 5, "lead", "arp", pitch_shift=7,
    ),
    "brass_a": EnsembleVoiceSpec(
        "brass_a", "Brass A", 7, "lead", "counter", pitch_shift=7, velocity_scale=1.1,
    ),
}


def _scale_pitches(ctx: ComposeContext) -> list[int]:
    from cadence.agent.nodes.melody import _get_scale_pitches
    return _get_scale_pitches(ctx.key, ctx.mode)


def _compose_ensemble_voice(ctx: ComposeContext, spec: EnsembleVoiceSpec) -> Track | None:
    structure = ctx.state["structure"]
    development = ctx.state.get("development")
    harmony = ctx.state.get("harmony")
    if not development and spec.compose_kind in ("counter", "arp"):
        return None
    if not harmony and spec.compose_kind in ("pad", "pluck", "arp"):
        return None

    intent_map = section_intent_map_from_state(
        ctx.state, context=f"ensemble:{spec.instrument_id}",
    )
    dev_map = section_development_map(development) if development else {}
    harmony_map = section_harmony_map(harmony)
    active = set(ctx.active_sections())
    scale = _scale_pitches(ctx)
    strategies = ctx.state.get("strategies")
    seed = seed_for_state(ctx.state, spec.instrument_id) or ctx.state.get("generation_seed", 0)

    step_ms = _ms_per_step(ctx.bpm)
    steps_per_bar = 16
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        dev = dev_map.get(section)

        if section not in active or not melody_should_play(intent):
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        density = intent.density if intent else 0.5
        if density < ctx.layer.min_density:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        section_h = harmony_map.get(section)
        motif = (
            (dev.motif_variant if dev else None)
            or (development.global_motif if development else [0, 2, 4])
        )

        if spec.compose_kind == "pad":
            if not section_h:
                current_t += bars * steps_per_bar * step_ms
                beat_index += bars * steps_per_bar
                continue
            base_vel = int((32 + density * 32) * spec.velocity_scale)
            ms_bar = _ms_per_bar(ctx.bpm)
            for bar_idx in range(bars):
                chord = chord_at_bar(section_h, bar_idx)
                pitches = chord_pitches(
                    harmony.key, harmony.mode, chord, octave=spec.octave_pad,
                )
                if spec.instrument_id == "keys_organ":
                    pitches = [p - 12 for p in pitches]
                dur = int(ms_bar * (0.92 if spec.instrument_id == "keys_organ" else 0.95))
                for pitch in pitches:
                    events.append(RhythmEvent(
                        t=int(current_t),
                        type="chord",
                        pitch=pitch,
                        duration_ms=dur,
                        velocity=base_vel,
                        beat_index=beat_index,
                        section=section,
                    ))
                current_t += ms_bar
                beat_index += steps_per_bar
            continue

        if spec.compose_kind == "pluck":
            if not section_h:
                current_t += bars * steps_per_bar * step_ms
                beat_index += bars * steps_per_bar
                continue
            steps = pluck_steps(
                strategies.pluck_pattern if strategies else None, seed + hash(spec.instrument_id),
            )
            base_vel = int((40 + density * 28) * spec.velocity_scale)
            for bar_idx in range(bars):
                chord = chord_at_bar(section_h, bar_idx)
                root = chord_pitches(ctx.key, ctx.mode, chord, octave=4)[0]
                for step in steps:
                    events.append(RhythmEvent(
                        t=int(current_t + step * step_ms),
                        type="note",
                        pitch=root + spec.pitch_shift,
                        duration_ms=int(step_ms * 0.4),
                        velocity=base_vel,
                        beat_index=beat_index + step,
                        section=section,
                    ))
                current_t += steps_per_bar * step_ms
                beat_index += steps_per_bar
            continue

        base_vel = int((44 + density * 38) * spec.velocity_scale)
        texture_mode = (
            development.texture_mode if development else "staggered"
        )
        counter_pat = strategies.counter_pattern if strategies else None
        arp_pat = resolve_arp_pattern(
            strategies.arp_pattern if strategies else None,
            seed + hash(spec.instrument_id),
        ) if spec.compose_kind == "arp" else None

        for bar_idx in range(bars):
            bar_dev = development_for_bar(dev, bar_idx) if dev else None
            transform = bar_dev.transform if bar_dev else "introduce"
            seg_idx = segment_index_at_bar(dev, bar_idx) if dev and dev.segments else 0
            if spec.compose_kind == "counter":
                pitch_shift = pitch_shift_for_transform(transform, seg_idx)
            else:
                pitch_shift = spec.pitch_shift

            if spec.compose_kind == "arp" and section_h and arp_pat:
                chord = chord_at_bar(section_h, bar_idx)
                tones = chord_pitches(ctx.key, ctx.mode, chord, octave=4)
                shifted = [p + spec.pitch_shift for p in tones]
                bar_ev = generate_bar_arp(
                    shifted,
                    arp_pat,
                    step_ms,
                    current_t,
                    beat_index,
                    section,
                    base_vel,
                )
                events.extend(bar_ev)
                current_t += steps_per_bar * step_ms
                beat_index += steps_per_bar
                continue

            steps = counter_steps(counter_pat, seed + hash(spec.instrument_id))
            chord_degrees = list(motif)
            if section_h:
                chord = chord_at_bar(section_h, bar_idx)
                chord_degrees = chord_tones_as_degrees(chord)
            if spec.invert_motif and dev and dev.transform == "invert":
                chord_degrees = [(6 - d) % 7 for d in chord_degrees]

            for step_i, step in enumerate(steps):
                if spec.compose_kind == "counter" and counter_skip_step(
                    step_i, transform,
                    texture_mode=texture_mode,
                    events_per_bar=len(steps),
                ):
                    continue
                degree = chord_degrees[step_i % len(chord_degrees)] % 7
                if transform == "invert":
                    degree = (6 - degree) % 7
                pitch = scale[degree] + pitch_shift
                pitch = max(48, min(108, pitch))
                events.append(RhythmEvent(
                    t=int(current_t + step * step_ms),
                    type="note",
                    pitch=pitch,
                    duration_ms=int(step_ms * 1.0),
                    velocity=base_vel,
                    beat_index=beat_index + step,
                    section=section,
                ))

            current_t += steps_per_bar * step_ms
            beat_index += steps_per_bar

    if not events:
        return None

    return Track(
        id=spec.instrument_id,
        instrument_id=spec.instrument_id,
        instrument=spec.display_name,
        midi_channel=spec.midi_channel,
        role=spec.role,
        events=events,
    )


def _make_compose(spec: EnsembleVoiceSpec):
    def _fn(ctx: ComposeContext) -> Track | None:
        return _compose_ensemble_voice(ctx, spec)
    return _fn


for _spec in VOICE_SPECS.values():
    register(InstrumentDefinition(
        instrument_id=_spec.instrument_id,
        display_name=_spec.display_name,
        role=_spec.role,
        midi_channel=_spec.midi_channel,
        requires_llm=False,
        compose=_make_compose(_spec),
    ))
