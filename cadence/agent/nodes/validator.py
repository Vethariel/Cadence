from cadence.schemas.song_state import (
    SongState,
    ValidationResult,
    Track,
    ArrangementPlan,
    NarrativeContract,
    NarrativeAnchors,
)
from cadence.music.narrative_validation import (
    check_global_motif_continuity,
    check_narrative_intensity_direction,
    check_narrative_key_section_coverage,
)
from cadence.music.track_metrics import (
    layers_active_stats,
    melody_leap_ratio,
    notes_per_bar_stdev,
    optional_layer_coverage,
)


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

def _check_drums_present(
    tracks: list[Track],
    sections: list[str],
    arrangement: ArrangementPlan | None = None,
) -> tuple[bool, str]:
    if arrangement and "drums" not in arrangement.required_layers:
        return True, ""
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


def _is_high_energy_game(
    energy_level: int,
    use_case: str,
) -> bool:
    return energy_level >= 4 and (use_case or "game").lower() in ("game", "animation")


def _check_instrumental_richness(
    tracks: list[Track],
    bpm: int,
    energy_level: int,
    use_case: str,
    composition_archetype: str | None = None,
) -> tuple[bool, str]:
    """Capas simultáneas y variación de densidad — relevante en game/energy alta."""
    arch = composition_archetype or ""
    layers_mean, layers_max = layers_active_stats(tracks, bpm)

    if arch == "compact_action":
        if layers_mean > 4.2:
            return False, (
                f"Stack demasiado denso para arquetipo compacto: μ={layers_mean:.1f} capas "
                "(máx ~4.2)."
            )
        return True, ""

    if not _is_high_energy_game(energy_level, use_case):
        return True, ""
    density_stdev = notes_per_bar_stdev(tracks, bpm)
    min_mean = 3.0 if energy_level == 4 else 3.5
    min_stdev = 8.0 if energy_level == 4 else 10.0

    issues = []
    if layers_mean < min_mean:
        issues.append(f"capas activas μ={layers_mean:.1f} (mín {min_mean})")
    if layers_max < 5 and energy_level >= 5:
        issues.append(f"capas activas máx={layers_max} (mín 5)")
    if density_stdev < min_stdev:
        issues.append(f"variación densidad σ={density_stdev:.1f} (mín {min_stdev})")

    if issues:
        return False, "Riqueza instrumental baja: " + "; ".join(issues)
    return True, ""


def _check_melody_leaps(
    tracks: list[Track],
    energy_level: int,
    use_case: str,
    composition_archetype: str | None = None,
) -> tuple[bool, str]:
    """Melodías de alta energía necesitan saltos amplios (estilo dance/arcade)."""
    arch = composition_archetype or ""
    if arch not in ("chiptune_dance", "default_game") and energy_level < 5:
        return True, ""
    if energy_level < 5 or (use_case or "game").lower() not in ("game", "animation"):
        if arch != "chiptune_dance":
            return True, ""

    ratio = melody_leap_ratio(tracks)
    min_ratio = 0.30 if arch == "chiptune_dance" else 0.25
    if ratio < min_ratio:
        return False, (
            f"Melodía demasiado conjunta: solo {ratio:.0%} de intervalos >4 semitonos "
            f"(se espera ≥{min_ratio:.0%} para {arch or 'energy 5'})."
        )
    return True, ""


def _check_melody_rest_density(
    tracks: list[Track],
    bpm: int,
    composition_archetype: str | None = None,
) -> tuple[bool, str]:
    """Chiptune/dance: penaliza melodías con demasiados silencios entre notas."""
    if composition_archetype != "chiptune_dance":
        return True, ""

    melody = next((t for t in tracks if t.id == "melody"), None)
    if not melody or len(melody.events) < 4:
        return True, ""

    sorted_ev = sorted(melody.events, key=lambda e: e.t)
    gaps = []
    for i in range(1, len(sorted_ev)):
        gap = sorted_ev[i].t - (sorted_ev[i - 1].t + sorted_ev[i - 1].duration_ms)
        if gap > 0:
            gaps.append(gap)
    if not gaps:
        return True, ""
    bar_ms = (60000 / max(bpm, 1)) * 4
    long_gaps = sum(1 for g in gaps if g >= bar_ms * 0.12)
    rest_ratio = long_gaps / len(gaps)
    if rest_ratio > 0.35:
        return False, (
            f"Melodía chiptune con demasiados silencios ({rest_ratio:.0%} huecos largos; máx 35%)."
        )
    return True, ""


def _check_orchestral_simultaneity(
    tracks: list[Track],
    bpm: int,
    energy_level: int,
    composition_archetype: str | None = None,
) -> tuple[bool, str]:
    if composition_archetype != "orchestral_boss" or energy_level < 5:
        return True, ""

    _, layers_max = layers_active_stats(tracks, bpm)
    if layers_max < 5:
        return False, (
            f"Boss orquestal: pocas capas simultáneas (máx {layers_max}; se espera ≥5)."
        )
    return True, ""


def _check_planned_optional_layers(
    tracks: list[Track],
    arrangement: ArrangementPlan | None,
    duration_ms: int,
) -> tuple[bool, str]:
    """Capas opcionales en el plan deben tener presencia audible."""
    if not arrangement or duration_ms <= 0:
        return True, ""

    core = {"drums", "bass", "melody"}
    thin = []
    for layer in arrangement.layers:
        iid = layer.instrument_id
        if iid in core:
            continue
        cov = optional_layer_coverage(tracks, iid, duration_ms)
        if cov < 0.15:
            thin.append(f"{iid} ({cov:.0%})")

    if len(thin) >= 2:
        return False, f"Capas planificadas casi inaudibles: {', '.join(thin)}"
    return True, ""


def _check_narrative_key_coverage(
    tracks: list[Track],
    structure,
    contract: NarrativeContract | None,
    anchors: NarrativeAnchors | None,
    intent_map: dict | None,
) -> tuple[bool, str]:
    if not intent_map:
        return True, ""
    return check_narrative_key_section_coverage(
        tracks, structure, contract, anchors, intent_map,
    )


def _check_narrative_intensity_direction(
    tracks: list[Track],
    sections: list[str],
    intent_map: dict | None,
    contract: NarrativeContract | None,
) -> tuple[bool, str]:
    if not intent_map:
        return True, ""
    return check_narrative_intensity_direction(
        tracks, sections, intent_map, contract,
    )


def _check_narrative_motif_continuity(
    tracks: list[Track],
    contract: NarrativeContract | None,
    anchors: NarrativeAnchors | None,
    intent_map: dict | None,
    key: str,
    mode: str,
) -> tuple[bool, str]:
    if not intent_map:
        return True, ""
    return check_global_motif_continuity(
        tracks, contract, anchors, intent_map, key=key, mode=mode,
    )


# Checks con su peso en el score final
CHECKS = [
    (_check_all_tracks_present,  0.20, "tracks_present"),
    (_check_melody_coverage,     0.20, "melody_coverage"),
    (_check_pitch_range,         0.10, "pitch_range"),
    (_check_velocity_range,      0.08, "velocity_range"),
    (_check_timing_order,        0.08, "timing_order"),
    (_check_drums_present,       0.08, "drums_present"),
    (_check_melody_variety,      0.05, "melody_variety"),
    (_check_melody_loop,         0.06, "melody_loop"),
    (_check_dynamic_range,       0.04, "dynamic_range"),
    (_check_intensity_arc,       0.04, "intensity_arc"),
    (_check_instrumental_richness, 0.04, "instrumental_richness"),
    (_check_melody_leaps,        0.03, "melody_leaps"),
    (_check_planned_optional_layers, 0.03, "planned_layers"),
    (_check_melody_rest_density, 0.03, "melody_rest_density"),
    (_check_orchestral_simultaneity, 0.03, "orchestral_layers"),
    (_check_narrative_key_coverage, 0.03, "narrative_key_coverage"),
    (_check_narrative_intensity_direction, 0.03, "narrative_intensity"),
    (_check_narrative_motif_continuity, 0.03, "narrative_motif"),
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
    energy = proposal.energy_level if proposal else 3
    use_case = state["intent"].use_case

    from cadence.music.narrative_contract import contract_section_intent_map
    from cadence.music.section_refs import canonical_section_ids
    from cadence.music.style_archetype import get_composition_archetype

    contract = state.get("narrative_contract")
    anchors = state.get("narrative_anchors")
    intent_map = contract_section_intent_map(
        narrative, contract, context="validator", state=state,
    )
    archetype = get_composition_archetype(state)
    key = proposal.key if proposal else "C"
    mode = proposal.mode if proposal else "minor"
    canonical = canonical_section_ids(state)
    if structure and canonical and structure.sections != canonical:
        raise AssertionError(
            f"validator: structure.sections {structure.sections!r} != "
            f"canónicas {canonical!r}",
        )

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
            passed, msg = check_fn(tracks, structure.sections, arrangement)
        elif check_fn == _check_melody_loop:
            passed, msg = check_fn(tracks, bpm)
        elif check_fn == _check_dynamic_range:
            passed, msg = check_fn(tracks, structure.sections)
        elif check_fn == _check_intensity_arc:
            passed, msg = check_fn(tracks, structure.sections, intent_map)
        elif check_fn == _check_instrumental_richness:
            passed, msg = check_fn(tracks, bpm, energy, use_case, archetype)
        elif check_fn == _check_melody_leaps:
            passed, msg = check_fn(tracks, energy, use_case, archetype)
        elif check_fn == _check_melody_rest_density:
            passed, msg = check_fn(tracks, bpm, archetype)
        elif check_fn == _check_orchestral_simultaneity:
            passed, msg = check_fn(tracks, bpm, energy, archetype)
        elif check_fn == _check_planned_optional_layers:
            passed, msg = check_fn(
                tracks, arrangement, structure.estimated_duration_ms,
            )
        elif check_fn == _check_narrative_key_coverage:
            passed, msg = check_fn(
                tracks, structure, contract, anchors, intent_map,
            )
        elif check_fn == _check_narrative_intensity_direction:
            passed, msg = check_fn(tracks, structure.sections, intent_map, contract)
        elif check_fn == _check_narrative_motif_continuity:
            passed, msg = check_fn(
                tracks, contract, anchors, intent_map, key, mode,
            )
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
