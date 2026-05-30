"""Compositor determinista de pad — acordes sostenidos desde HarmonyPlan."""

from cadence.music.meter_theory import ms_per_bar as meter_ms_per_bar, steps_per_bar as meter_steps_per_bar
from cadence.schemas.song_state import HarmonyPlan, SongState, Track, RhythmEvent
from cadence.music.development_theory import section_development_map
from cadence.music.harmony_theory import (
    chord_at_bar,
    chord_pitches,
    section_harmony_map,
)
from cadence.music.layer_voice_variation import pad_octave_for_transform, pad_velocity_scale
from cadence.music.narrative_contract import contract_section_intent_map
from cadence.music.segment_variation import segment_at_bar
from cadence.schemas.song_state import SectionDevelopment, SectionIntent



def _pad_should_play(section: str, density: float) -> bool:
    if density < 0.2:
        return False
    return True


def _generate_pad_track(
    sections: list[str],
    bars_per_section: dict[str, int],
    bpm: int,
    harmony: HarmonyPlan,
    intent_map: dict[str, SectionIntent] | None = None,
    *,
    dev_map: dict[str, SectionDevelopment] | None = None,
    time_signature: list[int] | None = None,
) -> Track:
    harmony_map = section_harmony_map(harmony)
    intent_map = intent_map or {}
    ts = time_signature or [4, 4]
    ms_per_bar = meter_ms_per_bar(bpm, ts)
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0
    steps_per_bar = meter_steps_per_bar(ts)

    for section in sections:
        bars = bars_per_section.get(section, 4)
        intent = intent_map.get(section)
        density = intent.density if intent else 0.5

        if not _pad_should_play(section, density):
            current_t += bars * ms_per_bar
            beat_index += bars * steps_per_bar
            continue

        section_h = harmony_map.get(section)
        if not section_h:
            current_t += bars * ms_per_bar
            beat_index += bars * steps_per_bar
            continue

        role = intent.narrative_role if intent else "establish"
        sec_dev = dev_map.get(section) if dev_map else None

        for bar_idx in range(bars):
            transform = "introduce"
            if sec_dev and sec_dev.segments:
                seg = segment_at_bar(sec_dev, bar_idx)
                transform = seg.transform if seg else sec_dev.transform
            elif sec_dev:
                transform = sec_dev.transform

            octave = pad_octave_for_transform(transform, role)
            vel_scale = pad_velocity_scale(transform, role)
            base_vel = int((35 + density * 35) * vel_scale)
            chord = chord_at_bar(section_h, bar_idx)
            pitches = chord_pitches(harmony.key, harmony.mode, chord, octave=octave)
            sustain = 0.95 if transform not in ("sparse", "pedal", "resolve") else 0.65
            duration_ms = int(ms_per_bar * sustain)

            for pitch in pitches:
                events.append(RhythmEvent(
                    t=int(current_t),
                    type="chord",
                    pitch=pitch,
                    duration_ms=duration_ms,
                    velocity=base_vel,
                    beat_index=beat_index,
                    section=section,
                ))

            current_t += ms_per_bar
            beat_index += steps_per_bar

    return Track(
        id="pad",
        instrument="Warm Pad",
        midi_channel=2,
        role="pad",
        events=events,
    )


def pad_composer_node(state: SongState) -> dict:
    """Genera track de pad con acordes sostenidos alineados al HarmonyPlan."""
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    harmony: HarmonyPlan | None = state.get("harmony")

    if not harmony:
        existing = [t for t in state.get("tracks", []) if t.id != "pad"]
        return {"tracks": existing}

    bpm = proposal.bpm if proposal else 120
    time_signature = list(proposal.time_signature) if proposal else [4, 4]
    intent_map = contract_section_intent_map(
        state.get("narrative"),
        state.get("narrative_contract"),
        context="pad",
        state=state,
    )

    from cadence.music.development_theory import section_development_map

    pad = _generate_pad_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        harmony=harmony,
        intent_map=intent_map,
        dev_map=section_development_map(state.get("development")),
        time_signature=time_signature,
    )

    existing = [t for t in state.get("tracks", []) if t.id != "pad"]
    return {"tracks": existing + [pad]}
