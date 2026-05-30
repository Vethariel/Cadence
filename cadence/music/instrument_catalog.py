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
    ProposalInstrument,
    TechnicalProposal,
    Track,
    UserIntent,
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

# Capas rítmicas/melódicas habituales (no obligatorias; solo clasificación y orden).
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
    from cadence.music.instrument_roles import is_percussion_role

    return is_percussion_role(role) or instrument_id in ("drums", "perc_aux")


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
    raw_prompt: str = "",
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
            raw_prompt=raw_prompt,
        )
    if instrument_id == "bass" and genre_tags is not None:
        from cadence.music.timbre_library import filter_bass_timbres

        return filter_bass_timbres(
            timbres,
            genre_tags=genre_tags,
            mood=mood,
            use_case=use_case,
            composition_archetype=composition_archetype,
            raw_prompt=raw_prompt,
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
    raw_prompt: str = "",
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
        raw_prompt=raw_prompt,
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
        f"Capas habituales (no obligatorias): {', '.join(sorted(CORE_INSTRUMENTS))}.",
    ]
    for iid in sorted(list_instruments()):
        defn = get_instrument(iid)
        req = "determinista" if not defn.requires_llm else "opcional-LLM"
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


_OPTIONAL_IDS_ORDER = (
    "countermelody", "echo_synth", "arp_synth", "chord_stab", "synth_pluck",
    "pad", "perc_aux", "fx_riser",
)

_DEFAULT_MIX = {"drums": -10.0, "bass": -6.0, "melody": -8.0, "pad": -14.0}


def format_orchestration_catalog_for_llm(
    *,
    use_case: str = "game",
    genre_tags: list[str] | None = None,
    mood: str = "",
    energy_level: int = 3,
    composition_archetype: str | None = None,
) -> str:
    """
    Catálogo compacto para technical_spec: capas + gm_program permitidos (filtrados por contexto).
    """
    from cadence.music.genre_orchestration import (
        adjust_optional_budget,
        lead_fallback_pool,
        select_lead_layers_genre_aware,
    )

    uc = (use_case or "game").lower()
    tags = list(genre_tags or [])
    max_opt, max_lead = adjust_optional_budget(
        MAX_OPTIONAL_BY_USE_CASE.get(uc, 4),
        MAX_LEAD_OPTIONALS.get(uc, 2),
        genre_tags=tags,
        composition_archetype=composition_archetype,
        energy_level=energy_level,
        use_case=uc,
    )
    suggested_leads = select_lead_layers_genre_aware(
        use_case=uc,
        energy_level=energy_level,
        generation_seed=0,
        composition_archetype=composition_archetype,
        genre_tags=tags,
        max_lead=max_lead,
    )
    fallback_pool = lead_fallback_pool(
        use_case=uc,
        energy_level=energy_level,
        composition_archetype=composition_archetype,
        genre_tags=tags,
    )

    lines = [
        "=== ORQUESTACIÓN Y TIMBRES (instruments en TechnicalProposal) ===",
        f"Capas habituales (referencia): {', '.join(sorted(CORE_INSTRUMENTS))}.",
        f"use_case={uc}: máx ~{max_opt + len(CORE_INSTRUMENTS)} capas totales, "
        f"máx {max_lead} leads (countermelody, echo_synth, arp_synth, chord_stab, synth_pluck).",
        f"Leads sugeridos: {', '.join(suggested_leads) or 'ninguno'}.",
        f"Pool: {', '.join(fallback_pool)}.",
        "Reglas:",
        "- instruments[]: solo las capas que quieras activar (puede ser solo pad, solo melody, etc.).",
        "- No hay núcleo obligatorio: omite drums/bass/melody si el brief no los necesita.",
        "- gm_program: número EXACTO de la lista de cada instrument_id.",
        "- drums y perc_aux: gm_program=0 (percusión GM, canal 9/10).",
        "- No repitas el mismo gm_program entre leads activos.",
        "- Cada entrada debe incluir role (lead|bass|rhythm|pad|fx).",
        "- ensemble_concept: 1–2 frases del color sonoro (variación creativa).",
        "- Si instruments=[] el sistema sugiere capas por contexto y seed.",
        "",
    ]
    from cadence.music.instrument_roles import format_roles_for_llm

    lines.append(format_roles_for_llm())
    lines.append("")
    show_ids = sorted(CORE_INSTRUMENTS) + [
        iid for iid in _OPTIONAL_IDS_ORDER if iid in set(list_instruments())
    ]
    for iid in show_ids:
        defn = get_instrument(iid)
        if is_drum(iid, defn.role):
            lines.append(
                f"[{iid}] role=rhythm (obligatorio) — active=true, gm_program=0",
            )
            continue
        lines.append(f"[{iid}] rol_sugerido={defn.role} — elige role + gm_program:")
        timbres = get_timbres(
            iid,
            genre_tags=tags,
            mood=mood,
            use_case=uc,
            composition_archetype=composition_archetype,
        )
        for program, name in timbres:
            lines.append(f"    {program}: {name}")
        lines.append("")
    return "\n".join(lines)


def proposal_has_orchestration(proposal: TechnicalProposal) -> bool:
    return bool(proposal.instruments)


def normalize_technical_proposal_instruments(
    proposal: TechnicalProposal,
    intent: UserIntent,
    *,
    composition_archetype: str | None = None,
) -> TechnicalProposal:
    """
    Valida ids y ajusta gm_program al catálogo (conserva elección LLM si es válida).
    """
    if not proposal.instruments:
        return proposal

    known = set(list_instruments())
    by_id: dict[str, InstrumentAssignment] = {}
    ctx = {
        "genre_tags": list(proposal.genre_tags),
        "mood": intent.mood,
        "use_case": intent.use_case,
        "composition_archetype": composition_archetype,
    }

    for item in proposal.instruments:
        iid = (item.instrument_id or "").strip().lower()
        if iid not in known:
            continue
        defn = get_instrument(iid)
        active = item.active
        from cadence.music.instrument_roles import normalize_instrument_role

        role = normalize_instrument_role(iid, item.role)
        if is_drum(iid, role):
            by_id[iid] = InstrumentAssignment(
                instrument_id=iid,
                role=role,
                gm_program=0,
                display_name=defn.display_name,
                mix_level=_DEFAULT_MIX.get(iid, -10.0),
                active=active,
            )
            continue
        prog, name = resolve_timbre(iid, item.gm_program, generation_seed=0, **ctx)
        by_id[iid] = InstrumentAssignment(
            instrument_id=iid,
            role=role,
            gm_program=prog,
            display_name=name,
            mix_level=_DEFAULT_MIX.get(iid, -10.0),
            active=active,
        )

    out: list[ProposalInstrument] = [
        ProposalInstrument(
            instrument_id=iid,
            role=assign.role,
            gm_program=assign.gm_program,
            active=assign.active,
        )
        for iid, assign in sorted(by_id.items())
    ]
    return proposal.model_copy(update={"instruments": out})


def proposal_instruments_to_assignments(
    proposal: TechnicalProposal,
    intent: UserIntent,
    *,
    composition_archetype: str | None = None,
) -> list[InstrumentAssignment]:
    """Convierte instruments del technical_spec a asignaciones validadas."""
    if not proposal.instruments:
        return []
    ctx = {
        "genre_tags": list(proposal.genre_tags),
        "mood": intent.mood,
        "use_case": intent.use_case,
        "composition_archetype": composition_archetype,
    }
    out: list[InstrumentAssignment] = []
    for item in proposal.instruments:
        iid = (item.instrument_id or "").strip().lower()
        if iid not in set(list_instruments()):
            continue
        defn = get_instrument(iid)
        active = item.active
        from cadence.music.instrument_roles import normalize_instrument_role

        role = normalize_instrument_role(iid, item.role)
        if is_drum(iid, role):
            out.append(InstrumentAssignment(
                instrument_id=iid,
                role=role,
                gm_program=0,
                display_name=defn.display_name,
                mix_level=_DEFAULT_MIX.get(iid, -10.0),
                active=active,
            ))
            continue
        prog, name = resolve_timbre(iid, item.gm_program, generation_seed=0, **ctx)
        out.append(InstrumentAssignment(
            instrument_id=iid,
            role=role,
            gm_program=prog,
            display_name=name,
            mix_level=_DEFAULT_MIX.get(iid, -10.0),
            active=active,
        ))
    return out


_GENERIC_DISPLAY_NAMES = frozenset({
    "Melody", "Bass Synth", "Drum Kit", "Pad", "Chord Stab", "Synth Pluck",
    "Arp Synth", "Echo Synth", "Countermelody", "Percussion Aux", "FX Riser",
})


def _needs_archetype_timbre(instrument_id: str, item: InstrumentAssignment) -> bool:
    """True si el timbre viene del default genérico y puede diversificarse por arquetipo."""
    if is_drum(instrument_id, item.role):
        return False
    defn = get_instrument(instrument_id)
    if item.gm_program == 0:
        return True
    if item.display_name == defn.display_name:
        return True
    return item.display_name in _GENERIC_DISPLAY_NAMES


def pick_archetype_timbre(
    instrument_id: str,
    *,
    generation_seed: int,
    timbre_context: dict,
) -> tuple[int, str] | None:
    """
    Elige timbre entre las variantes de paleta del arquetipo, filtrado por estilo.
    Rotación determinista por generation_seed + instrument_id.
    """
    from cadence.music.timbre_library import gm_name, palette_candidate_programs

    arch = timbre_context.get("composition_archetype")
    allowed = get_timbres(instrument_id, **timbre_context)
    if not allowed:
        return None

    allowed_set = {p for p, _ in allowed}
    candidates = [
        p for p in palette_candidate_programs(instrument_id, arch)
        if p in allowed_set
    ]
    if not candidates:
        candidates = [p for p, _ in allowed]

    arch_key = arch or "default_game"
    idx = (
        generation_seed * 31
        + hash(instrument_id) % 997
        + hash(arch_key) % 503
    ) % len(candidates)
    prog = candidates[idx]
    name = next((n for p, n in allowed if p == prog), gm_name(prog))
    return prog, name


def apply_archetype_palette_diversity(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict,
) -> None:
    """Aplica timbres diversos del arquetipo a capas con nombre/GM genérico."""
    from cadence.music.instrument_roles import default_role_for_instrument

    for iid, existing in list(by_id.items()):
        if not existing.active or not _needs_archetype_timbre(iid, existing):
            continue
        picked = pick_archetype_timbre(
            iid,
            generation_seed=generation_seed + hash(iid) % 997,
            timbre_context=timbre_context,
        )
        if not picked:
            continue
        prog, name = picked
        role = existing.role or default_role_for_instrument(iid)
        by_id[iid] = existing.model_copy(update={
            "gm_program": prog,
            "display_name": name,
            "role": role,
        })


def apply_prompt_technical_constraints(
    by_id: dict[str, InstrumentAssignment],
    *,
    raw_prompt: str,
) -> None:
    """Fuerza timbres/capas pedidos explícitamente en el prompt del usuario."""
    from cadence.music.instrument_roles import default_role_for_instrument
    from cadence.music.prompt_technical_constraints import parse_prompt_instrument_requests

    requests = parse_prompt_instrument_requests(raw_prompt)
    if not requests:
        return

    for req in requests:
        existing = by_id.get(req.instrument_id)
        if existing and existing.active:
            by_id[req.instrument_id] = existing.model_copy(update={
                "gm_program": req.gm_program,
                "display_name": req.display_name,
            })
        else:
            by_id[req.instrument_id] = InstrumentAssignment(
                instrument_id=req.instrument_id,
                role=default_role_for_instrument(req.instrument_id),
                gm_program=req.gm_program,
                display_name=req.display_name,
                mix_level=_DEFAULT_MIX.get(req.instrument_id, -13.0),
                active=True,
            )


def ensure_core_assignments(
    by_id: dict[str, InstrumentAssignment],
    *,
    generation_seed: int,
    timbre_context: dict,
) -> None:
    """Garantiza drums/bass/melody con timbres diversos por arquetipo."""
    from cadence.instruments.registry import get_instrument as _get_inst

    for iid in CORE_INSTRUMENTS:
        existing = by_id.get(iid)
        if not existing or not existing.active:
            continue
        if iid == "drums":
            defn = _get_inst(iid)
            if not existing.display_name or existing.display_name == "Drum Kit":
                by_id[iid] = existing.model_copy(update={"display_name": defn.display_name})
            continue
        if not _needs_archetype_timbre(iid, existing):
            continue
        picked = pick_archetype_timbre(
            iid,
            generation_seed=generation_seed + hash(iid) % 997,
            timbre_context=timbre_context,
        )
        if not picked:
            continue
        prog, name = picked
        from cadence.music.instrument_roles import default_role_for_instrument

        by_id[iid] = existing.model_copy(update={
            "gm_program": prog,
            "display_name": name,
            "role": default_role_for_instrument(iid),
        })


def _assignment_from_timbre(
    item: InstrumentAssignment,
    *,
    generation_seed: int,
    default_mix: float | None = None,
    timbre_context: dict | None = None,
) -> InstrumentAssignment:
    from cadence.music.instrument_roles import normalize_instrument_role

    ctx = timbre_context or {}
    defn = get_instrument(item.instrument_id)
    mix = default_mix if default_mix is not None else item.mix_level
    role = normalize_instrument_role(item.instrument_id, item.role)
    active = item.active
    if is_drum(item.instrument_id, role):
        return InstrumentAssignment(
            instrument_id=item.instrument_id,
            role=role,
            gm_program=0,
            display_name=defn.display_name,
            mix_level=max(-24.0, min(0.0, mix)),
            active=active,
        )
    prog, name = resolve_timbre(
        item.instrument_id,
        item.gm_program,
        generation_seed=generation_seed,
        **ctx,
    )
    return InstrumentAssignment(
        instrument_id=item.instrument_id,
        role=role,
        gm_program=prog,
        display_name=name,
        mix_level=max(-24.0, min(0.0, mix)),
        active=active,
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
    lock_llm_ensemble: bool = False,
) -> OrchestrationPlan:
    """Corrige IDs/timbres y coherencia; puede preservar íntegro el plan del LLM."""
    from cadence.music.style_archetype import infer_composition_archetype
    from cadence.schemas.song_state import GenerationStrategies

    from cadence.music.composition_archetypes import normalize_archetype, suppresses_ensemble

    archetype = normalize_archetype(
        composition_archetype
        or infer_composition_archetype(
            style_profile=style_profile,
            raw_prompt=raw_prompt,
            use_case=use_case,
            energy_level=energy_level,
        )
    )
    timbre_context = {
        "genre_tags": genre_tags,
        "mood": "",
        "use_case": use_case,
        "composition_archetype": archetype,
        "raw_prompt": raw_prompt,
    }

    if not lock_llm_ensemble:
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
    if suppresses_ensemble(archetype):
        extra_opt, extra_lead = 0, 0
    else:
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

    from cadence.music.genre_orchestration import optional_layer_genre_score

    max_total = max_optional + len(CORE_INSTRUMENTS)
    if not lock_llm_ensemble and len(by_id) > max_total:
        trim_candidates = [
            iid for iid in by_id
            if iid not in protected and iid not in CORE_INSTRUMENTS
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
                iid in CORE_INSTRUMENTS,
            ),
        )
        while len(by_id) > max_total and trim_candidates:
            victim = trim_candidates.pop(0)
            if victim in by_id:
                del by_id[victim]

    from cadence.music.harmonic_coherence import apply_lead_support_cap

    if not lock_llm_ensemble:
        allowed_ids = apply_lead_support_cap(
            set(by_id.keys()),
            energy_level=energy_level,
            use_case=use_case,
            protected=protected,
            composition_archetype=archetype,
        )
        for iid in list(by_id.keys()):
            if iid not in allowed_ids and iid not in protected:
                del by_id[iid]
        if allowed_pool:
            for iid in list(by_id.keys()):
                if iid not in allowed_pool and iid not in protected:
                    del by_id[iid]

    lead_present = [iid for iid in LEAD_OPTIONALS if iid in by_id]
    if not lock_llm_ensemble and len(lead_present) > max_lead:
        for iid in ("fx_riser", "perc_aux", "synth_pluck", "chord_stab", "echo_synth", "countermelody", "arp_synth"):
            if len(lead_present) <= max_lead:
                break
            if iid in protected:
                continue
            if iid in by_id:
                del by_id[iid]
                if iid in lead_present:
                    lead_present.remove(iid)

    if not lock_llm_ensemble and not suppresses_ensemble(archetype):
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
    elif suppresses_ensemble(archetype):
        for eid in ENSEMBLE_INSTRUMENT_IDS:
            by_id.pop(eid, None)
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

    ensure_core_assignments(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    apply_archetype_palette_diversity(
        by_id,
        generation_seed=generation_seed,
        timbre_context=timbre_context,
    )
    apply_prompt_technical_constraints(by_id, raw_prompt=raw_prompt)

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


def apply_orchestration_gm(
    tracks: list[Track],
    plan: OrchestrationPlan,
    *,
    state: dict | None = None,
) -> list[Track]:
    """Asigna gm_program e instrument display desde timbres elegidos por el agente."""
    assign = {a.instrument_id: a for a in plan.instruments if a.active}
    if state is not None:
        assign = _merge_core_track_timbres(assign, state)
    result = []
    for track in tracks:
        iid = track.instrument_id or track.id
        entry = assign.get(iid)
        if not entry:
            result.append(track)
            continue
        updates: dict = {"instrument": entry.display_name}
        updates["role"] = entry.role
        if not is_drum(iid, entry.role):
            updates["gm_program"] = entry.gm_program
        result.append(track.model_copy(update=updates))
    return result


def _merge_core_track_timbres(
    assign: dict[str, InstrumentAssignment],
    state: dict,
) -> dict[str, InstrumentAssignment]:
    """Aplica paleta ancla a melody/bass en tracks aunque falten en el plan LLM."""
    from cadence.music.instrument_roles import default_role_for_instrument
    from cadence.music.style_archetype import get_composition_archetype

    proposal = state.get("technical_proposal")
    intent = state.get("intent")
    archetype = get_composition_archetype(state)
    ctx = {
        "genre_tags": list(proposal.genre_tags) if proposal else [],
        "mood": intent.mood if intent else "",
        "use_case": intent.use_case if intent else "game",
        "composition_archetype": archetype,
        "raw_prompt": intent.raw_prompt if intent else "",
    }
    seed = state.get("generation_seed", 0)
    merged = dict(assign)

    for iid in ("melody", "bass"):
        existing = merged.get(iid)
        defn = get_instrument(iid)
        needs = (
            existing is None
            or _needs_archetype_timbre(iid, existing)
        )
        if not needs:
            continue
        picked = pick_archetype_timbre(
            iid,
            generation_seed=seed + hash(iid) % 997,
            timbre_context=ctx,
        )
        if not picked:
            continue
        prog, name = picked
        role = default_role_for_instrument(iid)
        mix = existing.mix_level if existing else _DEFAULT_MIX.get(iid, -8.0)
        merged[iid] = InstrumentAssignment(
            instrument_id=iid,
            role=role,
            gm_program=prog,
            display_name=name,
            mix_level=mix,
            active=True,
        )
    return merged


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
