"""Catálogo de instrumentos registrados y timbres GM válidos para el agente."""

from __future__ import annotations

from cadence.instruments.registry import get_instrument, list_instruments
from cadence.music.repertoire_signals import (
    enrich_orchestration_from_strategies,
    instruments_implied_by_strategies,
    max_optional_budget,
    percussion_suppressed,
)
from cadence.music.strategy_pools import resolve_rhythm_patterns
from cadence.music.timbre_library import (
    BROWSER_SOUNDFONT,
    assert_browser_gm_program,
    extended_timbres_flat,
    filter_melody_timbres,
    gm_name,
    style_anchor_timbres_flat,
)
from cadence.schemas.song_state import (
    InstrumentAssignment,
    MusicalStyleProfile,
    OrchestrationPlan,
    Track,
)
from cadence.music.ensemble_policy import (
    ENSEMBLE_INSTRUMENT_IDS,
    ENSEMBLE_REPLACES_OPTIONAL,
    ensemble_optional_budget_bonus,
    ensemble_score,
    inject_ensemble_into_assignments,
)
from cadence.music.melody_identity import melody_instrument_from_state
from cadence.music.style_profile import programs_matching_avoid

CORE_INSTRUMENTS = frozenset({"drums", "bass", "melody"})
OPTIONAL_LEADS = frozenset({"countermelody", "echo_synth", "arp_synth", "chord_stab"})
OPTIONAL_SUPPORT = frozenset({"pad", "perc_aux", "fx_riser"})

MAX_OPTIONAL_BY_USE_CASE = {
    "loop": 0,
    "cutscene": 2,
    "game": 4,
    "animation": 4,
}

_TRIM_PRIORITY = (
    "fx_riser",
    "perc_aux",
    "chord_stab",
    "echo_synth",
    "arp_synth",
    "countermelody",
    "pad",
)

LEAD_OPTIONALS = frozenset({
    "countermelody", "echo_synth", "arp_synth", "chord_stab", "synth_pluck",
})

MAX_LEAD_OPTIONALS = {
    "loop": 0,
    "cutscene": 1,
    "game": 2,
    "animation": 2,
}

def is_drum(instrument_id: str, role: str) -> bool:
    return role == "rhythm" or instrument_id in ("drums", "perc_aux")


def _tags_lower(genre_tags: list[str]) -> set[str]:
    return {t.lower() for t in genre_tags}


def select_fallback_lead_layers(
    *,
    use_case: str,
    energy_level: int,
    genre_tags: list[str] | None = None,
    generation_seed: int,
    composition_archetype: str | None = None,
) -> set[str]:
    """Capas lead opcionales en fallback — género, energía y rol."""
    from cadence.music.genre_orchestration import select_lead_layers_genre_aware

    uc = (use_case or "game").lower()
    max_lead = MAX_LEAD_OPTIONALS.get(uc, 2)
    return select_lead_layers_genre_aware(
        use_case=use_case,
        energy_level=energy_level,
        generation_seed=generation_seed,
        composition_archetype=composition_archetype,
        genre_tags=genre_tags,
        max_lead=max_lead,
    )


# Timbres GM permitidos por instrument_id.
TIMBRES_BY_INSTRUMENT: dict[str, list[tuple[int, str]]] = {}


def _build_timbres_by_instrument() -> dict[str, list[tuple[int, str]]]:
    """Unión de anclas de estilo + biblioteca extendida; nombres canónicos GM."""
    by_id: dict[str, dict[int, str]] = {}
    for source in (style_anchor_timbres_flat(), extended_timbres_flat()):
        for iid, entries in source.items():
            for program, name in entries:
                assert_browser_gm_program(program)
                by_id.setdefault(iid, {})[program] = name
    return {
        iid: sorted(opts.items(), key=lambda x: x[0])
        for iid, opts in by_id.items()
    }


TIMBRES_BY_INSTRUMENT.update(_build_timbres_by_instrument())

# Alias histórico
GM_OPTIONS = TIMBRES_BY_INSTRUMENT


def get_timbres(
    instrument_id: str,
    *,
    genre_tags: list[str] | None = None,
    mood: str = "",
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> list[tuple[int, str]]:
    """Lista de (gm_program, nombre) disponibles para un instrument_id."""
    if instrument_id in TIMBRES_BY_INSTRUMENT:
        timbres = list(TIMBRES_BY_INSTRUMENT[instrument_id])
    else:
        defn = get_instrument(instrument_id)
        timbres = [(0, defn.display_name)]
    if instrument_id == "melody" and genre_tags is not None:
        return filter_melody_timbres(
            timbres,
            genre_tags=genre_tags,
            mood=mood,
            use_case=use_case,
            composition_archetype=composition_archetype,
        )
    if instrument_id == "bass" and genre_tags is not None:
        from cadence.music.timbre_library import filter_bass_timbres

        return filter_bass_timbres(
            timbres,
            genre_tags=genre_tags,
            mood=mood,
            use_case=use_case,
            composition_archetype=composition_archetype,
        )
    return timbres


def timbre_programs(instrument_id: str, **timbre_context: object) -> set[int]:
    return {p for p, _ in get_timbres(instrument_id, **timbre_context)}  # type: ignore[arg-type]


def resolve_timbre(
    instrument_id: str,
    gm_program: int,
    *,
    generation_seed: int = 0,
    genre_tags: list[str] | None = None,
    mood: str = "",
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> tuple[int, str]:
    """
    Resuelve timbre desde la lista permitida.
    Si gm_program no está en la lista, elige el más cercano;
    si gm_program es 0 y hay opciones, elige variante por seed (fallback).
    """
    allowed = get_timbres(
        instrument_id,
        genre_tags=genre_tags,
        mood=mood,
        use_case=use_case,
        composition_archetype=composition_archetype,
    )
    programs = [p for p, _ in allowed]

    if gm_program in programs:
        for p, n in allowed:
            if p == gm_program:
                return p, n

    if gm_program == 0 and len(allowed) > 1:
        idx = (generation_seed // (37 + hash(instrument_id) % 97)) % len(allowed)
        return allowed[idx]

    if programs:
        closest = min(programs, key=lambda p: abs(p - gm_program))
        for p, n in allowed:
            if p == closest:
                return p, n

    return allowed[0]


def format_timbre_catalog_for_llm() -> str:
    """Catálogo explícito de timbres — el agente elige gm_program de aquí."""
    lines = [
        f"=== TIMBRES DISPONIBLES ({BROWSER_SOUNDFONT}.sf2 / General MIDI) ===",
        "Para cada capa activa, asigna gm_program EXACTAMENTE a uno de los listados.",
        "Todos los programas 0–127 son reproducibles en el navegador.",
        "El nombre display se deriva del gm_program; no inventes timbres fuera de lista.",
        "",
    ]
    for iid in sorted(list_instruments()):
        defn = get_instrument(iid)
        timbres = get_timbres(iid)
        if is_drum(iid, defn.role):
            lines.append(f"[{iid}] — percusión GM (canal {defn.midi_channel}), sin gm_program.")
            continue
        lines.append(f"[{iid}] — elige UN gm_program:")
        for program, name in timbres:
            lines.append(f"    {program}: {name}")
        lines.append("")
    return "\n".join(lines)


def format_catalog_for_llm() -> str:
    """Instrumentos del registro + referencia al catálogo de timbres."""
    lines = [
        "Instrumentos compositores registrados:",
        f"Obligatorios siempre activos: {', '.join(sorted(CORE_INSTRUMENTS))}.",
    ]
    for iid in sorted(list_instruments()):
        defn = get_instrument(iid)
        req = "requiere LLM" if defn.requires_llm else "determinista"
        n_timbres = len(get_timbres(iid))
        lines.append(
            f"  • {iid} — rol={defn.role}, canal={defn.midi_channel}, {req}, "
            f"{n_timbres} timbre(s) disponible(s)."
        )
    lines.append(
        "\nReglas de ensemble: no actives countermelody+echo_synth+arp_synth+chord_stab "
        "todas a la vez; elige un conjunto coherente. Varía timbres entre generaciones."
    )
    return "\n".join(lines)


def _assignment_from_timbre(
    item: InstrumentAssignment,
    *,
    generation_seed: int,
    default_mix: float | None = None,
    timbre_context: dict | None = None,
) -> InstrumentAssignment:
    ctx = timbre_context or {}
    defn = get_instrument(item.instrument_id)
    mix = default_mix if default_mix is not None else item.mix_level
    if is_drum(item.instrument_id, defn.role):
        return InstrumentAssignment(
            instrument_id=item.instrument_id,
            gm_program=0,
            display_name=defn.display_name,
            mix_level=max(-24.0, min(0.0, mix)),
            active=True,
        )
    prog, name = resolve_timbre(
        item.instrument_id,
        item.gm_program,
        generation_seed=generation_seed,
        **ctx,
    )
    return InstrumentAssignment(
        instrument_id=item.instrument_id,
        gm_program=prog,
        display_name=name,
        mix_level=max(-24.0, min(0.0, mix)),
        active=True,
    )


def _pick_alternate_program(
    instrument_id: str,
    avoid: set[int],
    generation_seed: int,
    *,
    timbre_context: dict | None = None,
) -> int | None:
    ctx = timbre_context or {}
    options = [
        p for p in timbre_programs(instrument_id, **ctx) if p not in avoid
    ]
    if not options:
        return None
    salt = hash(instrument_id) % 97
    return options[(generation_seed // (41 + salt)) % len(options)]


def _separate_lead_programs(
    by_id: dict[str, InstrumentAssignment],
    a: str,
    b: str,
    *,
    generation_seed: int,
    prefer_alt_on: str,
    timbre_context: dict | None = None,
) -> None:
    ctx = timbre_context or {}
    """Dos capas lead activas no comparten gm_program."""
    left = by_id.get(a)
    right = by_id.get(b)
    if not left or not right or not left.active or not right.active:
        return
    if left.gm_program != right.gm_program:
        return
    avoid = {left.gm_program}
    alt = _pick_alternate_program(
        prefer_alt_on, avoid, generation_seed + hash((a, b)), timbre_context=ctx,
    )
    if alt is None:
        other = b if prefer_alt_on == a else a
        alt = _pick_alternate_program(
            other, avoid, generation_seed + hash((b, a)), timbre_context=ctx,
        )
        if alt is None:
            return
        prog, name = resolve_timbre(other, alt, generation_seed=generation_seed, **ctx)
        by_id[other] = by_id[other].model_copy(update={"gm_program": prog, "display_name": name})
        return
    prog, name = resolve_timbre(prefer_alt_on, alt, generation_seed=generation_seed, **ctx)
    by_id[prefer_alt_on] = by_id[prefer_alt_on].model_copy(update={"gm_program": prog, "display_name": name})


def _separate_melody_chord_stab_programs(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict | None = None,
) -> None:
    """melody y chord_stab activos no pueden compartir gm_program."""
    _separate_lead_programs(
        by_id, "melody", "chord_stab",
        generation_seed=generation_seed,
        prefer_alt_on="chord_stab",
        timbre_context=timbre_context,
    )


def _separate_melody_countermelody_programs(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict | None = None,
) -> None:
    """melody y countermelody activos no pueden compartir gm_program."""
    _separate_lead_programs(
        by_id, "melody", "countermelody",
        generation_seed=generation_seed,
        prefer_alt_on="countermelody",
        timbre_context=timbre_context,
    )


def _separate_melody_echo_synth_programs(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict | None = None,
) -> None:
    """melody y echo_synth activos no pueden compartir gm_program (capa de eco)."""
    _separate_lead_programs(
        by_id, "melody", "echo_synth",
        generation_seed=generation_seed,
        prefer_alt_on="echo_synth",
        timbre_context=timbre_context,
    )


def _separate_ensemble_programs(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict | None = None,
) -> None:
    """Melodía y cada familia ensemble usan gm_program distintos entre sí."""
    ctx = timbre_context or {}
    melody = by_id.get("melody")
    if not melody or not melody.active:
        return
    used = {melody.gm_program}
    for eid in sorted(ENSEMBLE_INSTRUMENT_IDS):
        item = by_id.get(eid)
        if not item or not item.active:
            continue
        if item.gm_program not in used:
            used.add(item.gm_program)
            continue
        alt = _pick_alternate_program(
            eid, used, generation_seed + hash(eid), timbre_context=ctx,
        )
        if alt is not None:
            prog, name = resolve_timbre(eid, alt, generation_seed=generation_seed, **ctx)
            by_id[eid] = item.model_copy(update={"gm_program": prog, "display_name": name})
            used.add(prog)
        for other in sorted(ENSEMBLE_INSTRUMENT_IDS):
            if other == eid:
                continue
            o = by_id.get(other)
            if not o or not o.active:
                continue
            if o.gm_program == by_id[eid].gm_program:
                _separate_lead_programs(
                    by_id, eid, other,
                    generation_seed=generation_seed + hash((eid, other)),
                    prefer_alt_on=other,
                    timbre_context=ctx,
                )


def _apply_style_profile_avoids(
    by_id: dict[str, InstrumentAssignment],
    profile: MusicalStyleProfile | None,
    *,
    generation_seed: int,
    timbre_context: dict | None = None,
) -> None:
    ctx = timbre_context or {}
    """Evita gm_program que coinciden con la lista avoid del perfil LLM."""
    if not profile or not profile.avoid:
        return
    bad_programs = programs_matching_avoid(profile.avoid)
    if not bad_programs:
        return

    for iid, item in by_id.items():
        if is_drum(iid, get_instrument(iid).role):
            continue
        if item.gm_program not in bad_programs:
            continue
        alt = _pick_alternate_program(
            iid, bad_programs, generation_seed + hash(iid), timbre_context=ctx,
        )
        if alt is not None:
            prog, name = resolve_timbre(iid, alt, generation_seed=generation_seed, **ctx)
            by_id[iid] = item.model_copy(update={"gm_program": prog, "display_name": name})


def validate_orchestration(
    plan: OrchestrationPlan,
    *,
    use_case: str,
    energy_level: int,
    genre_tags: list[str] | None = None,
    generation_seed: int = 0,
    style_profile: MusicalStyleProfile | None = None,
    strategies: object | None = None,
    raw_prompt: str = "",
    creative_variation: object | None = None,
    composition_archetype: str | None = None,
) -> OrchestrationPlan:
    """Corrige IDs, timbres GM, ritmo y presupuesto; garantiza núcleo drums/bass/melody."""
    from cadence.music.style_archetype import infer_composition_archetype
    from cadence.schemas.song_state import GenerationStrategies

    archetype = composition_archetype or infer_composition_archetype(
        style_profile=style_profile,
        raw_prompt=raw_prompt,
        use_case=use_case,
        energy_level=energy_level,
    )
    timbre_context = {
        "genre_tags": genre_tags,
        "mood": "",
        "use_case": use_case,
        "composition_archetype": archetype,
    }

    plan = enrich_orchestration_from_strategies(
        plan,
        strategies if isinstance(strategies, GenerationStrategies) else None,
        energy_level=energy_level,
        use_case=use_case,
        generation_seed=generation_seed,
        style_profile=style_profile,
        raw_prompt=raw_prompt,
        composition_archetype=archetype,
    )
    from cadence.schemas.song_state import CreativeVariationBounds

    from cadence.music.style_profile import build_genre_mix

    genre_mix = build_genre_mix(proposal_tags=genre_tags) if genre_tags else {}
    max_optional, max_lead = max_optional_budget(
        use_case,
        energy_level,
        composition_archetype=archetype,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    e_score = ensemble_score(
        genre_tags=genre_tags,
        composition_archetype=archetype,
        use_case=use_case,
        energy_level=energy_level,
        genre_mix=genre_mix,
    )
    extra_opt, extra_lead = ensemble_optional_budget_bonus(e_score)
    max_optional = min(8, max_optional + extra_opt)
    max_lead = min(5, max_lead + extra_lead)
    allowed_pool: set[str] | None = None
    if isinstance(creative_variation, CreativeVariationBounds):
        max_optional = min(max_optional, creative_variation.max_optional_layers)
        max_lead = min(max_lead, creative_variation.max_lead_optionals)
        allowed_pool = set(creative_variation.allowed_optional_layers)
    protected = instruments_implied_by_strategies(
        strategies if isinstance(strategies, GenerationStrategies) else None,
        energy_level=energy_level,
        use_case=use_case,
        composition_archetype=archetype,
    )

    known = set(list_instruments())
    by_id: dict[str, InstrumentAssignment] = {}

    for item in plan.instruments:
        if item.instrument_id not in known or not item.active:
            continue
        by_id[item.instrument_id] = _assignment_from_timbre(
            item,
            generation_seed=generation_seed,
            timbre_context=timbre_context,
        )

    suppress_drums = percussion_suppressed(
        use_case=use_case,
        energy_level=energy_level,
        style_profile=style_profile,
    )
    default_mix = {"drums": -10.0, "bass": -6.0, "melody": -8.0}
    for core in CORE_INSTRUMENTS:
        if core == "drums" and suppress_drums:
            continue
        if core not in by_id:
            by_id[core] = _assignment_from_timbre(
                InstrumentAssignment(
                    instrument_id=core,
                    gm_program=0,
                    mix_level=default_mix[core],
                    active=True,
                ),
                generation_seed=generation_seed,
                default_mix=default_mix[core],
                timbre_context=timbre_context,
            )

    from cadence.music.genre_orchestration import optional_layer_genre_score

    optionals = [iid for iid in by_id if iid not in CORE_INSTRUMENTS and iid in known]
    if len(optionals) > max_optional:
        trim_candidates = [
            iid for iid in optionals
            if iid not in protected
        ]
        trim_candidates.sort(
            key=lambda iid: (
                optional_layer_genre_score(
                    iid,
                    genre_tags=genre_tags,
                    genre_mix=genre_mix,
                    composition_archetype=archetype,
                    energy_level=energy_level,
                ),
                _TRIM_PRIORITY.index(iid) if iid in _TRIM_PRIORITY else 99,
            ),
        )
        while len(optionals) > max_optional and trim_candidates:
            victim = trim_candidates.pop(0)
            if victim in by_id:
                del by_id[victim]
                optionals.remove(victim)

    from cadence.music.harmonic_coherence import apply_lead_support_cap

    allowed_ids = apply_lead_support_cap(
        set(by_id.keys()),
        energy_level=energy_level,
        use_case=use_case,
        protected=protected,
        composition_archetype=archetype,
    )
    for iid in list(by_id.keys()):
        if iid not in CORE_INSTRUMENTS and iid not in allowed_ids:
            del by_id[iid]
    if allowed_pool:
        for iid in list(by_id.keys()):
            if iid not in CORE_INSTRUMENTS and iid not in allowed_pool:
                del by_id[iid]

    lead_present = [iid for iid in LEAD_OPTIONALS if iid in by_id]
    if len(lead_present) > max_lead:
        for iid in ("fx_riser", "perc_aux", "synth_pluck", "chord_stab", "echo_synth", "countermelody", "arp_synth"):
            if len(lead_present) <= max_lead:
                break
            if iid in protected:
                continue
            if iid in by_id:
                del by_id[iid]
                lead_present.remove(iid)

    inject_ensemble_into_assignments(
        by_id,
        genre_tags=genre_tags,
        composition_archetype=archetype,
        use_case=use_case,
        energy_level=energy_level,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
        genre_mix=genre_mix,
    )
    for ens, generic in ENSEMBLE_REPLACES_OPTIONAL.items():
        if ens in by_id and generic in by_id:
            del by_id[generic]

    _apply_style_profile_avoids(
        by_id,
        style_profile,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    _separate_melody_chord_stab_programs(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    _separate_melody_countermelody_programs(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    _separate_melody_echo_synth_programs(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    _separate_ensemble_programs(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )

    ordered = [
        by_id[iid]
        for iid in sorted(by_id.keys(), key=lambda x: (x not in CORE_INSTRUMENTS, x))
    ]
    drum, bass = resolve_rhythm_patterns(
        plan.drum_pattern,
        plan.bass_pattern,
        genre_tags=genre_tags or [],
        energy_level=energy_level,
        use_case=use_case,
        generation_seed=generation_seed,
        composition_archetype=archetype,
    )
    return plan.model_copy(update={
        "instruments": ordered,
        "drum_pattern": drum,
        "bass_pattern": bass,
    })


def active_instrument_ids(plan: OrchestrationPlan) -> set[str]:
    return {a.instrument_id for a in plan.instruments if a.active}


def apply_orchestration_gm(tracks: list[Track], plan: OrchestrationPlan) -> list[Track]:
    """Asigna gm_program e instrument display desde timbres elegidos por el agente."""
    assign = {a.instrument_id: a for a in plan.instruments if a.active}
    result = []
    for track in tracks:
        iid = track.instrument_id or track.id
        entry = assign.get(iid)
        if not entry:
            result.append(track)
            continue
        updates: dict = {"instrument": entry.display_name}
        if not is_drum(iid, track.role):
            updates["gm_program"] = entry.gm_program
        result.append(track.model_copy(update=updates))
    return result


def build_fallback_orchestration(
    tracks: list[Track],
    *,
    use_case: str = "game",
    energy_level: int = 3,
    genre_tags: list[str] | None = None,
    generation_seed: int = 0,
    drum_pattern: str = "default",
    bass_pattern: str = "root_fifth",
    style_profile: MusicalStyleProfile | None = None,
) -> OrchestrationPlan:
    """
    Plan de orquestación determinista para tests y post_process sin agente.
    Timbres por seed desde TIMBRES_BY_INSTRUMENT.
    """
    seen: dict[str, InstrumentAssignment] = {}
    for track in tracks:
        iid = track.instrument_id or track.id
        if iid in seen:
            continue
        seed_prog = (generation_seed // (13 + hash(iid) % 47)) % 128
        seen[iid] = _assignment_from_timbre(
            InstrumentAssignment(
                instrument_id=iid,
                gm_program=seed_prog,
                mix_level=-10.0,
                active=True,
            ),
            generation_seed=generation_seed,
        )

    for core in CORE_INSTRUMENTS:
        if core not in seen:
            seen[core] = _assignment_from_timbre(
                InstrumentAssignment(
                    instrument_id=core,
                    gm_program=0,
                    mix_level=-10.0 if core == "drums" else (-6.0 if core == "bass" else -8.0),
                    active=True,
                ),
                generation_seed=generation_seed,
            )

    plan = OrchestrationPlan(
        ensemble_concept="fallback",
        instruments=list(seen.values()),
        drum_pattern=drum_pattern,  # type: ignore[arg-type]
        bass_pattern=bass_pattern,  # type: ignore[arg-type]
    )
    return validate_orchestration(
        plan,
        use_case=use_case,
        energy_level=energy_level,
        genre_tags=genre_tags or [],
        generation_seed=generation_seed,
        style_profile=style_profile,
    )


def orchestration_for_state(state: dict, tracks: list[Track]) -> OrchestrationPlan:
    """Plan del agente o fallback derivado de pistas y estado."""
    existing = state.get("orchestration_plan")
    if existing:
        return existing
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    strategies = state.get("strategies")
    seed = state.get("generation_seed", 0)
    return build_fallback_orchestration(
        tracks,
        use_case=intent.use_case,
        energy_level=proposal.energy_level if proposal else 3,
        genre_tags=proposal.genre_tags if proposal else intent.style_tags,
        generation_seed=seed,
        drum_pattern=strategies.drum_pattern if strategies else "default",
        bass_pattern=strategies.bass_pattern if strategies else "root_fifth",
        style_profile=state.get("style_profile"),
    )
