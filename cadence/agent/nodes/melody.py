from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from cadence.config import settings
from cadence.schemas.song_state import SongNarrative, SongState, Track, RhythmEvent
from cadence.agent.nodes.repair import failed_check_names
from cadence.agent.nodes.narrative_apply import (
    melody_rest_ratio,
    melody_should_play,
    narrative_melody_hint,
)
from cadence.music.narrative_contract import section_intent_map_from_state
from cadence.music.harmony_theory import (
    chord_tones_as_degrees,
    harmony_summary_for_section,
    section_harmony_map,
)
from cadence.music.development_theory import section_development_map
from cadence.music.melody_phrases import phrases_to_events, fix_phrase_steps
from cadence.music.narrative_anchors import format_anchors_for_llm
from cadence.music.creative_variation import format_variation_for_llm
from cadence.music.seed_policy import node_temperature, seed_for_state
from cadence.music.section_refs import format_section_ids_for_llm
from cadence.music.melody_density_policy import (
    is_dense_melody_target,
    melody_notes_per_bar_target,
)
from cadence.music.melody_identity import melody_instrument_from_state
from cadence.music.style_archetype import get_composition_archetype


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


# ── Salida estructurada del LLM — frases 2-4 compases ─────────

class MelodyNote(BaseModel):
    scale_degree: int = Field(ge=0, le=6)
    octave_offset: int = Field(ge=-1, le=1, default=0)
    duration_steps: int = Field(
        description="Steps de 1/16. Valores: 1, 2, 4.",
        ge=1, le=4,
    )
    velocity: int = Field(ge=40, le=127)
    is_rest: bool = Field(default=False)


class MelodyPhrase(BaseModel):
    bars: int = Field(
        ge=2, le=4,
        description="Duración de la frase en compases (2-4).",
    )
    pattern: list[MelodyNote] = Field(
        description=(
            "Patrón de la frase. La suma de duration_steps debe ser "
            "exactamente bars * 16."
        )
    )


class SectionPhrases(BaseModel):
    section: str
    phrases: list[MelodyPhrase] = Field(
        min_length=2,
        max_length=4,
        description=(
            "2-4 frases por sección. Frase 1 = pregunta, frase 2 = respuesta. "
            "Cada frase debe ser distinta (contorno complementario)."
        ),
    )


class MelodyComposerOutput(BaseModel):
    section_phrases: list[SectionPhrases]


# ── Helpers ───────────────────────────────────────────────────

def _get_scale_pitches(key: str, mode: str) -> list[int]:
    root = KEY_MIDI_ROOT.get(key.split()[0].capitalize(), 65)
    intervals = SCALES.get(mode, SCALES["minor"])
    return [root + i for i in intervals]


def _ms_per_step(bpm: int) -> float:
    return (60000 / bpm) / 4


def _fix_section_phrases(phrases: list[MelodyPhrase]) -> list[MelodyPhrase]:
    fixed = []
    for phrase in phrases:
        total_steps = phrase.bars * 16
        pattern = fix_phrase_steps(phrase.pattern, total_steps)
        fixed.append(phrase.model_copy(update={"pattern": pattern}))
    return fixed


def _development_hint(state: SongState) -> str:
    from cadence.music.development_theory import format_section_development_hint

    development = state.get("development")
    structure = state.get("structure")
    if not development:
        return ""
    bars_map = structure.bars_per_section if structure else {}
    lines = [
        "Plan de desarrollo motivico (subdivisiones = micro-arcos dentro de la sección):",
    ]
    for dev in development.sections:
        lines.append(format_section_development_hint(
            dev, bars_map.get(dev.section_id, 4),
        ))
    lines.append(
        "En secciones con varias subdivisiones, cambia el carácter melódico "
        "en cada bloque de compases (no un solo gesto durante toda la sección). "
        "Frase A presenta; frase B contrasta."
    )
    return "\n".join(lines) + "\n"


# ── Composición ───────────────────────────────────────────────

def compose_melody_track(state: SongState) -> Track:
    """Genera melodía por frases 2-4 compases con desarrollo motivico."""
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    validation = state.get("validation_result")
    narrative: SongNarrative | None = state.get("narrative")
    harmony = state.get("harmony")
    development = state.get("development")
    seed = seed_for_state(state, "melody") or state.get("generation_seed", 0)
    intent_map = section_intent_map_from_state(state, context="melody")
    phrase_variant = seed % 8
    dev_map = section_development_map(development)

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
    retry_n = state.get("retry_count", 0)
    temperature = node_temperature("melody", repair_attempt=retry_n)
    variety_hint = (
        "\n- OBLIGATORIO: cada frase debe sumar exactamente bars*16 steps.\n"
        "- OBLIGATORIO: frase 2 (respuesta) debe diferir de frase 1 en "
        "al menos 3 notas o contorno inverso.\n"
        "- Prefiere movimiento conjunto (±1 grado); saltos máx 2 grados "
        "(≤4 semitonos) salvo en climax.\n"
        f"- En drop/climax/build-up: máximo {int((0.05 if dense_target else 0.10) * 100)}% silencios (is_rest).\n"
        f"- Objetivo global: ≥{notes_target} notas por compás en secciones activas densas.\n"
        "- En secciones density>=0.7: frases de 2 compases, notas de 1-2 steps.\n"
        "- Registro objetivo C4–C6 (octave_offset 0 o +1 en climax)."
        f"\n- Variante melódica (subsemilla {phrase_variant}): "
        f"contorno {'ascendente' if phrase_variant % 2 else 'ondulante'} en frases de respuesta."
    )

    if validation and not validation.passed and state.get("retry_count", 0) > 0:
        failed = failed_check_names(validation.errors)
        errors_str = "\n".join(f"  - {e}" for e in validation.errors)
        repair_context = (
            f"\n\nATENCIÓN — intento de reparación #{state['retry_count']}.\n"
            f"Errores:\n{errors_str}\n"
        )
        if "melody_variety" in failed or "melody_loop" in failed:
            temperature = node_temperature("melody", repair_attempt=retry_n + 1)
            variety_hint += (
                "\n- OBLIGATORIO: mínimo 5 scale_degree distintos por sección."
            )
        if "melody_coverage" in failed:
            variety_hint += "\n- OBLIGATORIO: cubre todas las secciones activas."

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
            dev = dev_map.get(s.id)
            dev_str = f"transform={dev.transform}" if dev else ""
            section_lines.append(f"  - {s.id}: {hint}, {dev_str}")
        motif_str = ", ".join(str(d) for d in narrative.global_motif) if narrative.global_motif else "none"
        narrative_block = (
            f"\nGuion narrativo:\n"
            f"  logline: {narrative.logline}\n"
            f"  global_motif: [{motif_str}]\n"
            + "\n".join(section_lines) + "\n"
        )

    harmony_block = ""
    if harmony:
        h_lines = []
        for section_id in structure.sections:
            summary = harmony_summary_for_section(harmony, section_id)
            if summary:
                sh = section_harmony_map(harmony).get(section_id)
                degrees = [str(chord_tones_as_degrees(c)) for c in sh.progression] if sh else []
                h_lines.append(f"  - {section_id}: {summary} | acordes: {', '.join(degrees)}")
        harmony_block = (
            f"\nPlan armónico ({harmony.key} {harmony.mode}):\n"
            + "\n".join(h_lines) + "\n"
        )

    dev_block = _development_hint(state)

    archetype = get_composition_archetype(state)
    plan = state.get("orchestration_plan")
    melody_texture = (
        getattr(plan, "melody_texture", "balanced") if plan is not None else "balanced"
    ) or "balanced"
    dense_target = is_dense_melody_target(
        archetype,
        energy_level=energy_level,
        melody_texture=melody_texture,
        use_case=intent.use_case,
    )
    notes_target = melody_notes_per_bar_target(
        archetype, energy_level, melody_texture=melody_texture, use_case=intent.use_case,
    )
    archetype_hint = ""
    if archetype == "chiptune_dance" or dense_target:
        label = "CHIPTUNE/DANCE" if archetype == "chiptune_dance" else "DENSE DANCE"
        archetype_hint = (
            f"\nArquetipo {label}: melodía muy densa (≥{notes_target} notas/compás en climax), "
            "notas cortas (1-2 steps), saltos de hasta 7 semitonos, silencios ≤5%.\n"
        )
    elif archetype == "compact_action":
        archetype_hint = (
            "\nArquetipo COMPACTO: melodía directa y urgente, pocos silencios (≤10%), "
            "frases cortas; no rellenes con arpegios orquestales.\n"
        )
    elif archetype == "orchestral_boss":
        archetype_hint = (
            "\nArquetipo ORQUESTAL: melodía protagonista con densidad moderada, "
            "frases expresivas; silencios ≤15% en climax.\n"
        )

    harmonic_stack_hint = ""
    if plan and proposal:
        from cadence.music.harmonic_coherence import (
            active_instrument_ids_from_plan,
            count_harmonic_support_layers,
            should_quantize_melody_to_chords,
        )
        active = active_instrument_ids_from_plan(plan)
        if should_quantize_melody_to_chords(
            count_harmonic_support_layers(active),
            proposal.energy_level,
            intent.use_case,
        ):
            harmonic_stack_hint = (
                "\nStack armónico denso (arp/contramelodía/pluck): "
                "usa SOLO scale_degree que pertenezcan al acorde indicado "
                "para cada sección (grados del plan armónico). "
                "Evita notas fuera del acorde en drops y climax.\n"
            )

    # phrase length hints per section (primer segmento o resumen)
    phrase_hints = []
    for section_id in structure.sections:
        dev = dev_map.get(section_id)
        section_intent = intent_map.get(section_id)
        if dev:
            active_dev = dev.segments[0] if dev.segments else dev
            bars = active_dev.phrase_length_bars
            if section_intent and section_intent.density >= 0.7:
                bars = min(bars, 2)
            rest_pct = int(melody_rest_ratio(
                section_intent,
                use_case=intent.use_case,
                composition_archetype=archetype,
                energy_level=energy_level,
                melody_texture=melody_texture,
            ) * 100)
            seg_note = (
                f", {len(dev.segments)} micro-arcos" if dev.segments else ""
            )
            phrase_hints.append(
                f"  - {section_id}: frases de {bars} compases{seg_note}, rests ≤{rest_pct}%"
            )

    system = SystemMessage(content=(
        "Eres un compositor experto en música electrónica para videojuegos.\n"
        "Compones FRASES de 2-4 compases (NO loops de 1 compás).\n"
        "Por sección: 2 frases mínimo — frase A (pregunta) y frase B (respuesta).\n\n"
        "REGLA CRÍTICA: suma de duration_steps = bars * 16 por cada frase.\n\n"
        "Estilo de fraseo:\n"
        "- Pregunta: ascendente o arco, termina en silencio o nota tensa\n"
        "- Respuesta: desciende o resuelve a tónica/grado 0\n"
        "- Drop/climax: notas cortas (1-2 steps), denso, pocos silencios\n"
        "- Breakdown: silencios permitidos pero no más del 30%\n"
        f"{harmony_block}{dev_block}{narrative_block}{archetype_hint}\n"
        f"{format_section_ids_for_llm(state)}\n"
        f"{format_anchors_for_llm(state.get('narrative_anchors'))}\n"
        f"{format_variation_for_llm(state.get('creative_variation'))}\n"
        f"{harmonic_stack_hint}"
        f"Longitud sugerida:\n" + "\n".join(phrase_hints) + "\n"
        f"{variety_hint}\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Canción: {key} {mode} | {bpm} BPM | Géneros: {', '.join(genre_tags)}\n"
        f"Mood: {intent.mood} | Energía: {energy_level}/5\n"
        f"{format_section_ids_for_llm(state, include_instruction=False)}\n"
        f"Grados 0-6 (tónica=0 … séptima=6)\n"
        f"{repair_context}"
    ))

    result: MelodyComposerOutput = llm.invoke([system, human])

    all_events: list[RhythmEvent] = []
    current_t = 0.0
    beat_index = 0
    step_ms = _ms_per_step(bpm)
    steps_per_bar = 16

    phrase_map = {sp.section: sp.phrases for sp in result.section_phrases}

    for section in structure.sections:
        bars = structure.bars_per_section.get(section, 4)
        section_intent = intent_map.get(section)

        if not melody_should_play(section_intent):
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar
            continue

        if section in phrase_map:
            phrases = _fix_section_phrases(phrase_map[section])
            dev = dev_map.get(section)
            section_events, current_t, beat_index = phrases_to_events(
                phrases=phrases,
                section=section,
                total_bars=bars,
                start_t=current_t,
                bpm=bpm,
                scale_pitches=scale_pitches,
                beat_index_start=beat_index,
                development=dev,
            )
            all_events.extend(section_events)
        else:
            current_t += bars * steps_per_bar * step_ms
            beat_index += bars * steps_per_bar

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


def melody_composer_node(state: SongState) -> dict:
    melody_track = compose_melody_track(state)
    existing_tracks = [t for t in state.get("tracks", []) if t.id != "melody"]
    return {"tracks": existing_tracks + [melody_track]}
