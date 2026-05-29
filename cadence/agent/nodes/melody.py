from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import math

from cadence.config import settings
from cadence.schemas.song_state import SongNarrative, SongState, Track, RhythmEvent
from cadence.agent.nodes.repair import failed_check_names
from cadence.agent.nodes.narrative_apply import (
    melody_should_play,
    narrative_melody_hint,
    section_intent_map,
)
from cadence.music.harmony_theory import (
    chord_tones_as_degrees,
    harmony_summary_for_section,
    section_harmony_map,
)


# ── Escalas ───────────────────────────────────────────────────

SCALES = {
    "minor":    [0, 2, 3, 5, 7, 8, 10],
    "major":    [0, 2, 4, 5, 7, 9, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "dorian":   [0, 2, 3, 5, 7, 9, 10],
}

KEY_MIDI_ROOT = {
    "C": 60, "C#": 61, "D": 62, "D#": 63, "E": 64, "F": 65,
    "F#": 66, "G": 67, "G#": 68, "A": 69, "A#": 70, "B": 71,
}


# ── Salida estructurada del LLM ───────────────────────────────
# El LLM genera UN PATRÓN de exactamente 16 steps (1 bar)
# El código se encarga de repetirlo para cubrir todos los compases

class MelodyNote(BaseModel):
    scale_degree: int = Field(ge=0, le=6)
    octave_offset: int = Field(ge=-1, le=1, default=0)
    duration_steps: int = Field(
        description="Steps de 1/16 que ocupa esta nota. Valores: 1, 2, 4.",
        ge=1, le=4
    )
    velocity: int = Field(ge=40, le=127)
    is_rest: bool = Field(default=False)

class SectionPattern(BaseModel):
    section: str
    pattern: list[MelodyNote] = Field(
        description=(
            "Patrón de exactamente 1 bar (16 steps de 1/16). "
            "La suma de duration_steps de todas las notas debe ser exactamente 16. "
            "Mínimo 4 notas, máximo 16."
        )
    )

class MelodyComposerOutput(BaseModel):
    section_patterns: list[SectionPattern]


# ── Helpers ───────────────────────────────────────────────────

def _get_scale_pitches(key: str, mode: str) -> list[int]:
    root = KEY_MIDI_ROOT.get(key.split()[0].capitalize(), 65)
    intervals = SCALES.get(mode, SCALES["minor"])
    return [root + i for i in intervals]

def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4

def _fix_pattern_steps(pattern: list[MelodyNote]) -> list[MelodyNote]:
    """Ajusta el patrón para que sume exactamente 16 steps."""
    total = sum(n.duration_steps for n in pattern)
    if total == 16:
        return pattern
    if total < 16:
        # Agregar silencio al final
        pattern = list(pattern)
        pattern.append(MelodyNote(
            scale_degree=0,
            octave_offset=0,
            duration_steps=16 - total,
            velocity=80,
            is_rest=True,
        ))
    else:
        # Truncar hasta llegar a 16
        fixed = []
        acc = 0
        for note in pattern:
            remaining = 16 - acc
            if remaining <= 0:
                break
            if note.duration_steps > remaining:
                note = note.model_copy(update={"duration_steps": remaining})
            fixed.append(note)
            acc += note.duration_steps
        pattern = fixed
    return pattern

def _vary_pattern_for_bar(
    pattern: list[MelodyNote],
    bar_idx: int,
    global_motif: list[int],
) -> list[MelodyNote]:
    """Variación intra-sección A / A' / B usando el motivo global."""
    if bar_idx % 2 == 1:
        return [
            note.model_copy(update={"scale_degree": (note.scale_degree + 1) % 7})
            if not note.is_rest else note
            for note in pattern
        ]
    if global_motif and bar_idx % 4 == 2:
        varied = list(pattern)
        note_idx = 0
        for i, note in enumerate(varied):
            if note.is_rest:
                continue
            if note_idx < len(global_motif):
                varied[i] = note.model_copy(update={
                    "scale_degree": global_motif[note_idx] % 7,
                })
                note_idx += 1
        return varied
    return pattern

def _pattern_to_events(
    pattern: list[MelodyNote],
    section: str,
    bars: int,
    start_t: float,
    bpm: int,
    scale_pitches: list[int],
    beat_index_start: int,
    global_motif: list[int] | None = None,
) -> tuple[list[RhythmEvent], float, int]:
    """Repite el patrón de 1 bar para cubrir todos los compases de la sección."""
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16
    events = []
    current_t = start_t
    beat_index = beat_index_start
    motif = global_motif or []

    for bar in range(bars):
        bar_pattern = _vary_pattern_for_bar(pattern, bar, motif)
        for note in bar_pattern:
            duration_ms = int(note.duration_steps * step_ms * 0.92)
            if not note.is_rest:
                degree = max(0, min(6, note.scale_degree))
                pitch = scale_pitches[degree] + note.octave_offset * 12
                pitch = max(21, min(108, pitch))
                events.append(RhythmEvent(
                    t=int(current_t),
                    type="note",
                    pitch=pitch,
                    duration_ms=duration_ms,
                    velocity=note.velocity,
                    beat_index=beat_index,
                    section=section,
                ))
            current_t += note.duration_steps * step_ms
            beat_index += note.duration_steps

    return events, current_t, beat_index


# ── Nodo ─────────────────────────────────────────────────────

def compose_melody_track(state: SongState) -> Track:
    """Genera el track de melodía (LLM). Usado por registry y nodo legacy."""
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    validation = state.get("validation_result")
    narrative: SongNarrative | None = state.get("narrative")
    harmony = state.get("harmony")
    intent_map = section_intent_map(narrative)
    global_motif = list(narrative.global_motif) if narrative else []

    if proposal:
        bpm = proposal.bpm
        key = proposal.key
        mode = proposal.mode
        genre_tags = proposal.genre_tags
        energy_level = proposal.energy_level
    else:
        bpm = 120
        key = "C"
        mode = "minor"
        genre_tags = intent.style_tags
        energy_level = 3

    scale_pitches = _get_scale_pitches(key, mode)

    repair_context = ""
    temperature = 0.7
    variety_hint = ""

    if validation and not validation.passed and state.get("retry_count", 0) > 0:
        failed = failed_check_names(validation.errors)
        errors_str = "\n".join(f"  - {e}" for e in validation.errors)
        repair_context = (
            f"\n\nATENCIÓN — intento de reparación #{state['retry_count']}. "
            f"Errores anteriores:\n{errors_str}\nCorrige estos problemas."
        )
        if "melody_variety" in failed:
            temperature = min(1.0, 0.7 + state.get("retry_count", 0) * 0.12)
            variety_hint = (
                "\n- OBLIGATORIO: usa al menos 4 scale_degree distintos y "
                "varía octave_offset (-1, 0, 1) para crear contorno melódico."
            )
        if "melody_coverage" in failed:
            variety_hint += (
                "\n- OBLIGATORIO: cada patrón debe sumar exactamente 16 steps; "
                "el sistema lo repetirá en todos los compases de la sección."
            )
        if "pitch_range" in failed:
            variety_hint += (
                "\n- OBLIGATORIO: usa solo scale_degree 0-6 con octave_offset "
                "en rango -1 a 1; no generes notas fuera de la escala."
            )

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    ).with_structured_output(MelodyComposerOutput)

    narrative_block = ""
    if narrative:
        section_lines = []
        for s in narrative.sections:
            hint = narrative_melody_hint(s)
            section_lines.append(
                f"  - {s.id}: {hint}, transition_out={s.transition_out}"
            )
        motif_str = ", ".join(str(d) for d in global_motif) if global_motif else "none"
        narrative_block = (
            f"\nGuion narrativo:\n"
            f"  logline: {narrative.logline}\n"
            f"  arc: {narrative.arc_type}\n"
            f"  global_motif (scale degrees): [{motif_str}]\n"
            f"  Por sección:\n" + "\n".join(section_lines) + "\n"
            f"Usa global_motif como base melódica en intro/verse; "
            f"desarróllalo en climax/drop.\n"
        )

    harmony_block = ""
    if harmony:
        h_lines = []
        for section_id in structure.sections:
            summary = harmony_summary_for_section(harmony, section_id)
            if summary:
                sh = section_harmony_map(harmony).get(section_id)
                chord_degrees = []
                if sh:
                    for c in sh.progression:
                        chord_degrees.append(str(chord_tones_as_degrees(c)))
                h_lines.append(
                    f"  - {section_id}: progresión {summary} | "
                    f"grados por acorde: {', '.join(chord_degrees)}"
                )
        harmony_block = (
            f"\nPlan armónico ({harmony.key} {harmony.mode}):\n"
            + "\n".join(h_lines) + "\n"
            "Prioriza scale_degree que coincidan con los grados del acorde activo "
            "(root, third, fifth). La melodía debe sonar consonante con bajo y pad.\n"
        )

    system = SystemMessage(content=(
        "Eres un compositor experto en música electrónica para videojuegos.\n"
        "Tu tarea es componer UN PATRÓN DE 1 BAR (16 steps de 1/16) por sección.\n"
        "El sistema repetirá automáticamente ese patrón para cubrir toda la sección.\n\n"
        "REGLA CRÍTICA: la suma de duration_steps de todas las notas del patrón "
        "debe ser EXACTAMENTE 16.\n\n"
        "Guía por sección:\n"
        "- intro/outro: notas largas (duration_steps 4), pocas notas, melodía simple\n"
        "- build-up/verse: notas medias (duration_steps 2), patrón repetitivo\n"
        "- drop/climax: notas cortas (duration_steps 1-2), denso y agresivo\n"
        "- breakdown: mayoría silencios (is_rest=True), muy esparso\n"
        f"{harmony_block}"
        f"{narrative_block}"
        f"{variety_hint}\n"
        "Responde SOLO con el objeto estructurado, sin texto adicional."
    ))

    human = HumanMessage(content=(
        f"Canción: {key} {mode} | {bpm} BPM | Géneros: {', '.join(genre_tags)}\n"
        f"Mood: {intent.mood} | Energía: {energy_level}/5 | Uso: {intent.use_case}\n"
        f"Secciones: {structure.sections}\n"
        f"Grados disponibles (0-6): tónica=0, segunda=1, tercera=2, "
        f"cuarta=3, quinta=4, sexta=5, séptima=6\n"
        f"{repair_context}"
    ))

    result: MelodyComposerOutput = llm.invoke([system, human])

    # Construir eventos repitiendo cada patrón
    all_events = []
    current_t = 0.0
    beat_index = 0
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16

    pattern_map = {sp.section: sp.pattern for sp in result.section_patterns}

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        section_intent = intent_map.get(section)

        if not melody_should_play(section_intent):
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        if section in pattern_map:
            pattern = _fix_pattern_steps(pattern_map[section])
            section_events, current_t, beat_index = _pattern_to_events(
                pattern=pattern,
                section=section,
                bars=bars,
                start_t=current_t,
                bpm=bpm,
                scale_pitches=scale_pitches,
                beat_index_start=beat_index,
                global_motif=global_motif,
            )
            all_events.extend(section_events)
        else:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar

    return Track(
        id="melody",
        instrument="Lead Synth",
        instrument_id="melody",
        midi_channel=0,
        role="lead",
        events=all_events,
    )


def melody_composer_node(state: SongState) -> dict:
    melody_track = compose_melody_track(state)
    existing_tracks = [t for t in state.get("tracks", []) if t.id != "melody"]
    return {"tracks": existing_tracks + [melody_track]}
