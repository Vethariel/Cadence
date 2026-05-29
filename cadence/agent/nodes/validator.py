from cadence.schemas.song_state import SongState, ValidationResult, Track, ArrangementPlan


# ── Checks individuales ───────────────────────────────────────
# Cada check retorna (passed: bool, message: str)

def _required_layer_ids(arrangement: ArrangementPlan | None) -> set[str]:
    if arrangement:
        return set(arrangement.required_layers)
    return {"drums", "bass", "melody"}


def _check_all_tracks_present(
    tracks: list[Track],
    arrangement: ArrangementPlan | None = None,
) -> tuple[bool, str]:
    ids = {t.id for t in tracks}
    required = _required_layer_ids(arrangement)
    missing = required - ids
    if missing:
        return False, f"Tracks faltantes: {missing}"
    return True, ""

def _check_melody_coverage(
    tracks: list[Track],
    estimated_duration_ms: int,
    sections: list[str],
) -> tuple[bool, str]:
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or not melody.events:
        return False, "Track de melodía vacío"

    last_t = max(e.t + e.duration_ms for e in melody.events)
    coverage = last_t / estimated_duration_ms if estimated_duration_ms > 0 else 0

    if coverage < 0.7:
        return False, (
            f"Melodía cubre solo {coverage:.0%} de la duración total. "
            f"Último evento en {last_t}ms de {estimated_duration_ms}ms esperados."
        )

    melody_sections = {e.section for e in melody.events}
    key_sections = {"drop", "climax", "chorus", "verse"}
    covered_key = key_sections & set(sections) & melody_sections
    expected_key = key_sections & set(sections)

    if expected_key and not covered_key:
        return False, f"Melodía no cubre secciones clave: {expected_key - melody_sections}"

    return True, ""

def _check_pitch_range(tracks: list[Track]) -> tuple[bool, str]:
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody:
        return True, ""

    out_of_range = [
        e.pitch for e in melody.events
        if not (21 <= e.pitch <= 108)
    ]
    if out_of_range:
        return False, f"{len(out_of_range)} notas fuera de rango MIDI (21-108): {out_of_range[:5]}"
    return True, ""

def _check_velocity_range(tracks: list[Track]) -> tuple[bool, str]:
    errors = []
    for track in tracks:
        bad = [e.velocity for e in track.events if not (0 <= e.velocity <= 127)]
        if bad:
            errors.append(f"{track.id}: {len(bad)} eventos con velocity inválida")
    if errors:
        return False, " | ".join(errors)
    return True, ""

def _check_timing_order(tracks: list[Track]) -> tuple[bool, str]:
    for track in tracks:
        times = [e.t for e in track.events]
        if times != sorted(times):
            return False, f"Track '{track.id}': eventos fuera de orden cronológico"
    return True, ""

def _check_drums_present(tracks: list[Track], sections: list[str]) -> tuple[bool, str]:
    drums = next((t for t in tracks if t.id == "drums"), None)
    if not drums or not drums.events:
        return False, "Track de drums vacío"

    drum_sections = {e.section for e in drums.events}
    active_sections = [s for s in sections if s != "breakdown"]
    missing = set(active_sections) - drum_sections

    if len(missing) > len(active_sections) * 0.3:
        return False, f"Drums ausentes en demasiadas secciones: {missing}"
    return True, ""

def _check_melody_variety(tracks: list[Track]) -> tuple[bool, str]:
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or len(melody.events) < 4:
        return True, ""

    unique_pitches = len({e.pitch for e in melody.events})
    if unique_pitches < 3:
        return False, (
            f"Melodía demasiado monótona: solo {unique_pitches} pitch(es) únicos. "
            "Necesita al menos 3 alturas diferentes."
        )
    return True, ""


def _check_melody_loop(tracks: list[Track], bpm: int) -> tuple[bool, str]:
    """Penaliza compases consecutivos con la misma secuencia de pitches."""
    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or len(melody.events) < 8:
        return True, ""

    ms_per_bar = (60000 / max(bpm, 1)) * 4
    bar_pitches: dict[int, list[int]] = {}
    for e in melody.events:
        bar = int(e.t / ms_per_bar)
        bar_pitches.setdefault(bar, []).append(e.pitch)

    bars = sorted(bar_pitches.keys())
    if len(bars) < 3:
        return True, ""

    identical = sum(
        1 for i in range(1, len(bars))
        if bar_pitches[bars[i]] == bar_pitches[bars[i - 1]]
    )
    ratio = identical / (len(bars) - 1)
    if ratio > 0.4:
        return False, (
            f"Melodía repite el mismo patrón en {ratio:.0%} de compases consecutivos."
        )
    return True, ""


def _check_dynamic_range(
    tracks: list[Track],
    sections: list[str],
) -> tuple[bool, str]:
    """Velocity debe variar entre secciones (crescendo efectivo)."""
    note_tracks = [t for t in tracks if t.events and t.role in ("lead", "rhythm", "bass")]
    if not note_tracks or len(sections) < 2:
        return True, ""

    section_vel: dict[str, list[int]] = {s: [] for s in sections}
    for track in note_tracks:
        for e in track.events:
            if e.type in ("note", "drum_hit") and e.section in section_vel:
                section_vel[e.section].append(e.velocity)

    avgs = {
        s: sum(v) / len(v)
        for s, v in section_vel.items()
        if v
    }
    if len(avgs) < 2:
        return True, ""

    spread = max(avgs.values()) - min(avgs.values())
    if spread < 8:
        return False, (
            f"Dinámica plana entre secciones (spread={spread:.1f}). "
            "Se espera crescendo/decrescendo."
        )
    return True, ""


def _check_intensity_arc(
    tracks: list[Track],
    sections: list[str],
    narrative_sections: dict | None,
) -> tuple[bool, str]:
    """La sección más densa narrativamente no debe ser la más baja en velocity."""
    if not narrative_sections or len(sections) < 2:
        return True, ""

    target_density = {
        s: narrative_sections[s].density
        for s in sections
        if s in narrative_sections
    }
    if not target_density:
        return True, ""

    section_vel: dict[str, list[int]] = {s: [] for s in sections}
    for track in tracks:
        for e in track.events:
            if e.type in ("note", "drum_hit") and e.section in section_vel:
                section_vel[e.section].append(e.velocity)

    actual_avg = {
        s: sum(v) / len(v)
        for s, v in section_vel.items()
        if v
    }
    if len(actual_avg) < 2:
        return True, ""

    peak_target = max(target_density, key=target_density.get)
    peak_actual = max(actual_avg, key=actual_avg.get)
    if actual_avg.get(peak_target, 0) < actual_avg.get(peak_actual, 0) * 0.85:
        if peak_target != peak_actual and target_density[peak_target] >= 0.65:
            return False, (
                f"Sección clave '{peak_target}' (density={target_density[peak_target]:.2f}) "
                f"no alcanza la intensidad esperada vs '{peak_actual}'."
            )
    return True, ""


# Checks con su peso en el score final
CHECKS = [
    (_check_all_tracks_present,  0.22, "tracks_present"),
    (_check_melody_coverage,     0.22, "melody_coverage"),
    (_check_pitch_range,         0.13, "pitch_range"),
    (_check_velocity_range,      0.10, "velocity_range"),
    (_check_timing_order,        0.10, "timing_order"),
    (_check_drums_present,       0.10, "drums_present"),
    (_check_melody_variety,      0.05, "melody_variety"),
    (_check_melody_loop,         0.08, "melody_loop"),
    (_check_dynamic_range,       0.05, "dynamic_range"),
    (_check_intensity_arc,       0.05, "intensity_arc"),
]

def validator_node(state: SongState) -> dict:
    """
    Evalúa la calidad musical de los tracks generados.
    Retorna un ValidationResult con score 0-1 y lista de errores.
    """
    tracks = state.get("tracks", [])
    structure = state["structure"]
    arrangement = state.get("arrangement")
    narrative = state.get("narrative")
    proposal = state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120

    from cadence.agent.nodes.narrative_apply import section_intent_map
    intent_map = section_intent_map(narrative)

    errors = []
    warnings = []
    score = 1.0

    for check_fn, weight, name in CHECKS:
        if check_fn == _check_all_tracks_present:
            passed, msg = check_fn(tracks, arrangement)
        elif check_fn == _check_melody_coverage:
            passed, msg = check_fn(
                tracks,
                structure.estimated_duration_ms,
                structure.sections,
            )
        elif check_fn == _check_drums_present:
            passed, msg = check_fn(tracks, structure.sections)
        elif check_fn == _check_melody_loop:
            passed, msg = check_fn(tracks, bpm)
        elif check_fn == _check_dynamic_range:
            passed, msg = check_fn(tracks, structure.sections)
        elif check_fn == _check_intensity_arc:
            passed, msg = check_fn(tracks, structure.sections, intent_map)
        else:
            passed, msg = check_fn(tracks)

        if not passed:
            score -= weight
            errors.append(f"[{name}] {msg}")

    score = max(0.0, round(score, 3))
    passed = score >= 0.8

    validation = ValidationResult(
        score=score,
        errors=errors,
        warnings=warnings,
        passed=passed,
    )

    return {"validation_result": validation}
