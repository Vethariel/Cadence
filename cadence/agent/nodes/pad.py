"""Compositor determinista de pad — acordes sostenidos desde HarmonyPlan."""

from cadence.schemas.song_state import HarmonyPlan, SongState, Track, RhythmEvent
from cadence.music.harmony_theory import (
    chord_at_bar,
    chord_pitches,
    section_harmony_map,
)
from cadence.agent.nodes.narrative_apply import section_intent_map


def _ms_per_bar(bpm: int) -> float:
    return (60000 / bpm) * 4


def _pad_should_play(section: str, density: float) -> bool:
    if density < 0.2:
        return False
    return True


def _generate_pad_track(
    sections: list[str],
    bars_per_section: dict[str, int],
    bpm: int,
    harmony: HarmonyPlan,
    narrative=None,
) -> Track:
    harmony_map = section_harmony_map(harmony)
    intent_map = section_intent_map(narrative)
    ms_per_bar = _ms_per_bar(bpm)
    events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0
    steps_per_bar = 16

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

        base_vel = int(35 + density * 35)

        for bar_idx in range(bars):
            chord = chord_at_bar(section_h, bar_idx)
            pitches = chord_pitches(harmony.key, harmony.mode, chord, octave=3)
            duration_ms = int(ms_per_bar * 0.95)

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

    pad = _generate_pad_track(
        sections=structure.sections,
        bars_per_section=structure.bars_per_section,
        bpm=bpm,
        harmony=harmony,
        narrative=state.get("narrative"),
    )

    existing = [t for t in state.get("tracks", []) if t.id != "pad"]
    return {"tracks": existing + [pad]}
