"""Composición melódica determinista desde motivo, desarrollo y armonía."""

from __future__ import annotations

from cadence.agent.nodes.melody import (
    MelodyNote,
    MelodyPhrase,
    _fix_section_phrases,
    _get_scale_pitches,
    _ms_per_step,
)
from cadence.agent.nodes.narrative_apply import melody_should_play
from cadence.music.development_theory import section_development_map
from cadence.music.melody_phrases import phrases_to_events
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.meter_theory import steps_per_bar
from cadence.schemas.song_state import SongState, Track


def _rhythm_steps_for_density(density: float, min_steps: int) -> int:
    if density >= 0.85:
        return max(min_steps, 1)
    if density >= 0.6:
        return max(min_steps, 2)
    return max(min_steps, 4)


def _phrase_from_motif(
    motif: list[int],
    bars: int,
    phrase_idx: int,
    *,
    density: float,
    min_steps: int,
    seed: int,
    bar_steps: int = 16,
) -> MelodyPhrase:
    """Frase 2–4 compases desde motivo y contorno determinista."""
    bars = max(2, min(4, bars))
    total_steps = bars * bar_steps
    step_dur = _rhythm_steps_for_density(density, min_steps)
    degrees = list(motif) if motif else [0, 2, 4, 2]
    if phrase_idx == 1:
        degrees = [(6 - d) % 7 for d in degrees] if seed % 2 else [(d + 2) % 7 for d in degrees]

    pattern: list[MelodyNote] = []
    acc = 0
    di = 0
    while acc < total_steps:
        remaining = total_steps - acc
        dur = min(step_dur, remaining)
        is_rest = (
            phrase_idx == 0
            and acc > total_steps * 0.75
            and density < 0.7
            and (seed + acc) % 5 == 0
        )
        vel = 88 if density >= 0.7 else 78
        oct_off = 1 if density >= 0.85 and phrase_idx == 1 else 0
        pattern.append(MelodyNote(
            scale_degree=degrees[di % len(degrees)],
            octave_offset=oct_off,
            duration_steps=dur,
            velocity=vel,
            is_rest=is_rest,
        ))
        acc += dur
        if not is_rest:
            di += 1

    return MelodyPhrase(bars=bars, pattern=pattern)


def build_section_phrases(
    section_id: str,
    bars: int,
    motif: list[int],
    *,
    density: float,
    min_steps: int,
    seed: int,
    phrase_length_bars: int = 2,
    bar_steps: int = 16,
) -> list[MelodyPhrase]:
    """Dos frases mínimo (pregunta/respuesta) cubriendo la sección."""
    phrase_bars = max(2, min(4, phrase_length_bars))
    p1 = _phrase_from_motif(
        motif, phrase_bars, 0, density=density, min_steps=min_steps, seed=seed, bar_steps=bar_steps,
    )
    p2 = _phrase_from_motif(
        motif, phrase_bars, 1,
        density=density, min_steps=min_steps, seed=seed + 17, bar_steps=bar_steps,
    )
    phrases = [p1, p2]
    covered = phrase_bars * 2
    if covered < bars and bars >= 4:
        phrases.append(_phrase_from_motif(
            motif, min(phrase_bars, bars - covered),
            2, density=density * 0.9, min_steps=min_steps, seed=seed + 31, bar_steps=bar_steps,
        ))
    return _fix_section_phrases(phrases, bar_steps)


def compose_melody_deterministic(state: SongState) -> Track:
    """Genera pista melody sin LLM."""
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    narrative = state.get("narrative")
    development = state.get("development")
    seed = state.get("generation_seed", 0)

    if not structure:
        raise ValueError("compose_melody_deterministic requiere structure")

    if proposal:
        bpm = proposal.bpm
        key = proposal.key
        mode = proposal.mode
        time_signature = list(proposal.time_signature or [4, 4])
    else:
        bpm, key, mode = 120, "C", "minor"
        time_signature = [4, 4]

    scale_pitches = _get_scale_pitches(key, mode)
    intent_map = section_intent_map_from_state(state, context="melody_det")
    dev_map = section_development_map(development)

    contract = state.get("narrative_contract")
    global_motif = (
        list(contract.global_motif)
        if contract
        else (list(narrative.global_motif) if narrative else [0, 2, 4, 2])
    )

    from cadence.music.voice_register_profile import profile_from_state

    voice_register = profile_from_state(state)
    min_steps = voice_register.min_melody_duration_steps
    energy = proposal.energy_level if proposal else 3

    all_events = []
    current_t = 0.0
    beat_index = 0
    step_ms = _ms_per_step(bpm, time_signature)
    bar_steps = steps_per_bar(time_signature)

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        section_intent = intent_map.get(section)

        if not melody_should_play(section_intent):
            current_t += bars * bar_steps * step_ms
            beat_index += bars * bar_steps
            continue

        dev = dev_map.get(section)
        motif = (dev.motif_variant if dev and dev.motif_variant else global_motif)
        density = section_intent.density if section_intent else 0.5
        phrase_len = dev.phrase_length_bars if dev else 2
        section_seed = seed + hash(section) % 9973

        phrases = build_section_phrases(
            section,
            bars,
            list(motif),
            density=density,
            min_steps=min_steps,
            seed=section_seed,
            phrase_length_bars=phrase_len,
            bar_steps=bar_steps,
        )
        section_events, current_t, beat_index = phrases_to_events(
            phrases=phrases,
            section=section,
            total_bars=bars,
            start_t=current_t,
            bpm=bpm,
            scale_pitches=scale_pitches,
            beat_index_start=beat_index,
            development=dev,
            time_signature=time_signature,
        )
        all_events.extend(section_events)

    from cadence.music.melody_identity import melody_instrument_from_state

    instrument_name, gm_program = melody_instrument_from_state(state)
    return Track(
        id="melody",
        instrument=instrument_name,
        instrument_id="melody",
        midi_channel=0,
        role="lead",
        gm_program=gm_program,
        events=all_events,
    )
