"""Catálogo de instrumentos registrados y timbres GM válidos para el agente."""

from __future__ import annotations

from cadence.instruments.registry import get_instrument, list_instruments
from cadence.music.strategy_pools import resolve_rhythm_patterns
from cadence.music.timbre_library import (
    BROWSER_SOUNDFONT,
    assert_browser_gm_program,
    extended_timbres_flat,
    gm_name,
    style_anchor_timbres_flat,
)
from cadence.schemas.song_state import (
    InstrumentAssignment,
    MusicalStyleProfile,
    OrchestrationPlan,
    Track,
)
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

_ORCHESTRAL_RICH_TAGS = frozenset({
    "orchestral", "cinematic", "epic", "soundtrack", "film score",
})



def is_drum(instrument_id: str, role: str) -> bool:
    return role == "rhythm" or instrument_id in ("drums", "perc_aux")


def _tags_lower(genre_tags: list[str]) -> set[str]:
    return {t.lower() for t in genre_tags}


def select_fallback_lead_layers(
    *,
    use_case: str,
    energy_level: int,
    genre_tags: list[str],
    generation_seed: int,
) -> set[str]:
    """Capas lead opcionales en fallback sin plan del agente."""
    uc = (use_case or "game").lower()
    max_n = MAX_LEAD_OPTIONALS.get(uc, 2)
    if max_n == 0:
        return set()

    if uc == "cutscene" or energy_level <= 2:
        return {"countermelody"} if energy_level >= 2 else set()

    tags = _tags_lower(genre_tags)
    if tags & {"chiptune", "8-bit", "arcade"}:
        pool = ["arp_synth", "echo_synth"]
    elif tags & {"ambient", "drone", "ethereal", "space"}:
        return {"echo_synth"} if energy_level > 1 else set()
    elif tags & {"dubstep", "brostep", "bass music"}:
        pool = ["chord_stab", "synth_pluck", "perc_aux", "arp_synth"]
    elif tags & {"orchestral", "epic", "cinematic", "soundtrack"}:
        pool = ["countermelody", "echo_synth"]
    elif tags & {"techno", "industrial", "dark", "ebm"}:
        pool = ["chord_stab", "arp_synth", "synth_pluck"]
    elif tags & {"boss fight", "energetic", "battle", "combat", "aggressive"}:
        pool = ["arp_synth", "countermelody", "chord_stab", "echo_synth", "synth_pluck"]
    else:
        pool = ["arp_synth", "countermelody"]

    n = min(max_n, 2 if energy_level >= 4 else 1)
    chosen: list[str] = []
    for i in range(n):
        idx = (generation_seed // (29 * (i + 1))) % len(pool)
        candidate = pool[idx]
        if candidate not in chosen:
            chosen.append(candidate)
    return set(chosen)


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


def get_timbres(instrument_id: str) -> list[tuple[int, str]]:
    """Lista de (gm_program, nombre) disponibles para un instrument_id."""
    if instrument_id in TIMBRES_BY_INSTRUMENT:
        return list(TIMBRES_BY_INSTRUMENT[instrument_id])
    defn = get_instrument(instrument_id)
    return [(0, defn.display_name)]


def timbre_programs(instrument_id: str) -> set[int]:
    return {p for p, _ in get_timbres(instrument_id)}


def resolve_timbre(
    instrument_id: str,
    gm_program: int,
    *,
    generation_seed: int = 0,
) -> tuple[int, str]:
    """
    Resuelve timbre desde la lista permitida.
    Si gm_program no está en la lista, elige el más cercano;
    si gm_program es 0 y hay opciones, elige variante por seed (fallback).
    """
    allowed = get_timbres(instrument_id)
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
) -> InstrumentAssignment:
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
) -> int | None:
    options = [p for p in timbre_programs(instrument_id) if p not in avoid]
    if not options:
        return None
    salt = hash(instrument_id) % 97
    return options[(generation_seed // (41 + salt)) % len(options)]


def _separate_melody_chord_stab_programs(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
) -> None:
    """melody y chord_stab activos no pueden compartir gm_program."""
    mel = by_id.get("melody")
    stab = by_id.get("chord_stab")
    if not mel or not stab or not mel.active or not stab.active:
        return
    if mel.gm_program != stab.gm_program:
        return
    avoid = {mel.gm_program}
    alt = _pick_alternate_program("chord_stab", avoid, generation_seed + 31)
    if alt is None:
        alt = _pick_alternate_program("melody", avoid, generation_seed + 37)
        if alt is not None:
            prog, name = resolve_timbre("melody", alt, generation_seed=generation_seed)
            by_id["melody"] = mel.model_copy(update={"gm_program": prog, "display_name": name})
        return
    prog, name = resolve_timbre("chord_stab", alt, generation_seed=generation_seed)
    by_id["chord_stab"] = stab.model_copy(update={"gm_program": prog, "display_name": name})


def _apply_style_profile_avoids(
    by_id: dict[str, InstrumentAssignment],
    profile: MusicalStyleProfile | None,
    *,
    generation_seed: int,
) -> None:
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
        alt = _pick_alternate_program(iid, bad_programs, generation_seed + hash(iid))
        if alt is not None:
            prog, name = resolve_timbre(iid, alt, generation_seed=generation_seed)
            by_id[iid] = item.model_copy(update={"gm_program": prog, "display_name": name})


def validate_orchestration(
    plan: OrchestrationPlan,
    *,
    use_case: str,
    energy_level: int,
    genre_tags: list[str] | None = None,
    generation_seed: int = 0,
    style_profile: MusicalStyleProfile | None = None,
) -> OrchestrationPlan:
    """Corrige IDs, timbres GM, ritmo y presupuesto; garantiza núcleo drums/bass/melody."""
    uc = (use_case or "game").lower()
    tags = _tags_lower(genre_tags or [])
    max_optional = MAX_OPTIONAL_BY_USE_CASE.get(uc, 4)
    if tags & _ORCHESTRAL_RICH_TAGS and uc in ("game", "animation") and energy_level >= 4:
        max_optional = min(max_optional + 1, 5)
    if energy_level <= 2 and uc != "loop":
        max_optional = min(max_optional, 2)

    max_lead = MAX_LEAD_OPTIONALS.get(uc, 2)
    if tags & _ORCHESTRAL_RICH_TAGS and energy_level >= 4:
        max_lead = min(max_lead + 1, 3)

    known = set(list_instruments())
    by_id: dict[str, InstrumentAssignment] = {}

    for item in plan.instruments:
        if item.instrument_id not in known or not item.active:
            continue
        by_id[item.instrument_id] = _assignment_from_timbre(
            item, generation_seed=generation_seed,
        )

    default_mix = {"drums": -10.0, "bass": -6.0, "melody": -8.0}
    for core in CORE_INSTRUMENTS:
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
            )

    optionals = [iid for iid in by_id if iid not in CORE_INSTRUMENTS and iid in known]
    if len(optionals) > max_optional:
        to_remove: set[str] = set()
        for iid in _TRIM_PRIORITY:
            if len(optionals) - len(to_remove) <= max_optional:
                break
            if iid in optionals:
                to_remove.add(iid)
        for iid in to_remove:
            del by_id[iid]

    lead_present = [iid for iid in LEAD_OPTIONALS if iid in by_id]
    if len(lead_present) > max_lead:
        for iid in ("echo_synth", "synth_pluck", "countermelody", "chord_stab", "arp_synth"):
            if len(lead_present) <= max_lead:
                break
            if iid in by_id:
                del by_id[iid]
                lead_present.remove(iid)

    _apply_style_profile_avoids(
        by_id,
        style_profile,
        generation_seed=generation_seed,
    )
    _separate_melody_chord_stab_programs(
        by_id,
        generation_seed=generation_seed,
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
