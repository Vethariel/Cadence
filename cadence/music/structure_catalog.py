"""
Catálogo de formas musicales — el LLM técnico elige form_id; el código expande y valida.
"""

from __future__ import annotations

import re
from cadence.music.narrative_contract import _normalize_section_id
from cadence.schemas.song_state import (
    CreativeBrief,
    NarrativeContract,
    TechnicalProposal,
    UserIntent,
)

GENERIC_POP_SECTIONS = ("intro", "verse", "chorus", "outro")

# IDs canónicos con guión (convención del pipeline; el normalizador _ usa guiones bajos)
_HYPHEN_CANONICAL: dict[str, str] = {
    "build_up": "build-up",
    "pre_chorus": "pre-chorus",
    "main_theme": "main-theme",
    "pad_layering": "pad_layering",
    "melodic_motif": "melodic_motif",
    "outro_loop": "outro_loop",
    "dialogue_bed": "dialogue_bed",
    "tension_swell": "tension_swell",
}


def canonical_section_id(section_id: str) -> str:
    """Id de sección estable para el grafo (prefiere forma con guión si aplica)."""
    norm = _normalize_section_id(section_id)
    if norm in _HYPHEN_CANONICAL:
        return _HYPHEN_CANONICAL[norm]
    raw = section_id.lower().strip().replace(" ", "-")
    return raw if raw else norm

_EXPLICIT_SECTION_RE = re.compile(
    r"\b(intro|outro|verse|chorus|bridge|drop|build[- ]?up|breakdown|"
    r"climax|loop|pre[- ]?chorus|main[- ]?theme|dialogue|tension|pad|"
    r"ambient|exploration|overworld|cutscene|swell|bed|motif)\b",
    re.IGNORECASE,
)


def is_generic_pop_structure(sections: list[str]) -> bool:
    if len(sections) != 4:
        return False
    return tuple(canonical_section_id(s) for s in sections) == GENERIC_POP_SECTIONS


def prompt_lists_explicit_sections(raw_prompt: str) -> bool:
    return extract_explicit_structure_from_prompt(raw_prompt) is not None


def prompt_requests_specific_form(raw_prompt: str) -> bool:
    p = (raw_prompt or "").lower()
    markers = (
        "loop", "overworld", "exploración", "exploration", "ambiente", "ambient",
        "cutscene", "diálogo", "dialogo", "narrativa", "boss", "jefe",
        "build-up", "drop", "climax", "chiptune", "eurobeat", "arcade",
    )
    return any(m in p for m in markers)


def extract_explicit_structure_from_prompt(raw_prompt: str) -> list[str] | None:
    p = (raw_prompt or "").strip()
    if not p:
        return None
    lower = p.lower()
    for sep in ("→", "->", "|", "/", ","):
        if sep in lower and "intro" in lower:
            parts = [x.strip() for x in re.split(re.escape(sep), lower) if x.strip()]
            if len(parts) >= 2 and all(_EXPLICIT_SECTION_RE.search(part) for part in parts):
                return [canonical_section_id(s) for s in parts]
    m = re.search(
        r"(?:estructura|structure|secciones?)\s*[:=]?\s*"
        r"([\w\s\-–—]+(?:intro|verse|chorus|outro|drop|build)[\w\s\-–—]*)",
        lower,
    )
    if m:
        chunk = re.split(r"\s+en\s+", m.group(1), maxsplit=1)[0]
        parts = re.split(r"[-–—]+", chunk)
        ids = [canonical_section_id(x.strip()) for x in parts if x.strip()]
        if len(ids) >= 2:
            return ids
    m = re.search(
        r"\b(intro\s*[-–—]\s*[\w]+(?:\s*[-–—]\s*[\w]+)*)\b",
        lower,
    )
    if m:
        chunk = re.split(r"\s+en\s+", m.group(0), maxsplit=1)[0]
        parts = [x.strip() for x in re.split(r"[-–—]+", chunk) if x.strip()]
        ids = [canonical_section_id(s) for s in parts]
        if len(ids) >= 2:
            return ids
    return None


def default_structure_for_use_case(use_case: str, raw_prompt: str = "") -> list[str]:
    """Fallback legacy — delega en suggest_forms del catálogo."""
    explicit = extract_explicit_structure_from_prompt(raw_prompt)
    if explicit:
        return explicit
    form_hint = _form_from_prompt(raw_prompt)
    if form_hint:
        return expand_form(form_hint)
    tags: list[str] = []
    if prompt_requests_specific_form(raw_prompt):
        p = (raw_prompt or "").lower()
        for marker in (
            "exploración", "exploration", "overworld", "ambient", "ambiente",
            "pad", "dungeon", "exploration_bed",
        ):
            if marker in p:
                tags.append(marker)
    return expand_form(suggest_forms(use_case=use_case, genre_tags=tags, limit=1)[0])


def _form_from_prompt(raw_prompt: str) -> str | None:
    """Forma sugerida por palabras clave del prompt (sin LLM)."""
    from cadence.music.structure_forms_data import STRUCTURE_FORMS

    p = (raw_prompt or "").lower()
    hints: tuple[tuple[str, str], ...] = (
        ("exploración", "loop_exploration"),
        ("exploration", "loop_exploration"),
        ("overworld", "loop_exploration"),
        ("ambient", "loop_ambient"),
        ("ambiente", "loop_ambient"),
        ("pad", "loop_ambient"),
        ("dungeon", "loop_dungeon"),
    )
    for marker, form_id in hints:
        if marker in p and form_id in STRUCTURE_FORMS:
            return form_id
    return None

MIN_BARS_PER_SECTION = 2
MAX_BARS_PER_SECTION = 32
MAX_SECTIONS = 8

_DURATION_BY_USE_CASE: dict[str, tuple[int, int]] = {
    "loop": (24, 48),
    "cutscene": (16, 40),
    "game": (32, 72),
    "animation": (36, 80),
}


from cadence.music.structure_forms_data import (
    STRUCTURE_FORM_CATEGORIES,
    STRUCTURE_FORMS,
    StructureFormSpec,
)

_CATEGORY_LABELS: dict[str, str] = {
    "boss_combat": "Boss y combate",
    "edm_electronic": "EDM y electrónica",
    "loop_exploration": "Loops y exploración",
    "cutscene_cinematic": "Cutscene y cinemática",
    "game_ui": "UI y momentos de juego",
    "calm_tension": "Calma, puzzle y tensión",
    "action_racing": "Acción y carreras",
    "hybrid_styles": "Híbridos y estilos",
}

_EXTRA_SECTION_IDS = (
    "intro", "verse", "chorus", "outro", "bridge", "breakdown",
    "build-up", "drop", "climax", "pre-chorus", "main-theme",
    "pad_layering", "melodic_motif", "outro_loop",
    "dialogue_bed", "tension_swell",
    "stealth_bed", "chase", "menu_theme", "shop_bed",
    "victory_sting", "defeat_sting", "horror_bed",
    "exploration_bed", "dungeon_bed",
)

VALID_SECTION_IDS: frozenset[str] = frozenset({
    sid for spec in STRUCTURE_FORMS.values() for sid in spec["sections"]
} | set(_EXTRA_SECTION_IDS))

_ARC_FORM_HINTS: tuple[tuple[str, str], ...] = (
    ("loop-stable", "loop_ambient"),
    ("loop stable", "loop_ambient"),
    ("exploration", "loop_exploration"),
    ("overworld", "loop_exploration"),
    ("dungeon", "loop_dungeon"),
    ("underwater", "loop_underwater"),
    ("stealth", "loop_stealth"),
    ("dialogue-tension", "cutscene_arc"),
    ("dialogue", "cutscene_arc"),
    ("reveal", "cutscene_reveal"),
    ("betrayal", "cutscene_reveal"),
    ("chase", "chase_sequence"),
    ("pursuit", "cutscene_chase"),
    ("horror", "cutscene_horror"),
    ("rise-climax", "animation_climax"),
    ("trailer", "trailer_short"),
    ("montage", "montage_pop"),
    ("dread", "boss_orchestral"),
    ("triumph", "victory_fanfare"),
    ("victory", "victory_fanfare"),
    ("defeat", "defeat_sting"),
    ("game over", "game_over"),
    ("defiance", "boss_extended"),
    ("double drop", "edm_double_drop"),
    ("trance", "trance_journey"),
    ("house", "house_groove"),
    ("synthwave", "synthwave_arc"),
    ("hardstyle", "hardstyle_peak"),
    ("dnb", "boss_dnb"),
    ("dubstep", "boss_dubstep"),
    ("metal", "boss_metal"),
    ("menu", "menu_theme"),
    ("shop", "shop_theme"),
    ("puzzle", "puzzle_calm"),
    ("racing", "racing_high"),
    ("credits", "credits_roll"),
    ("title", "title_screen"),
    ("emotional", "emotional_piano"),
    ("hybrid", "orchestral_edm"),
    ("raid", "combat_raid"),
    ("survival", "combat_survival"),
    ("pre-battle", "pre_battle"),
)


def all_form_ids() -> list[str]:
    return list(STRUCTURE_FORMS.keys())


def is_valid_form_id(form_id: str) -> bool:
    return (form_id or "").strip().lower() in STRUCTURE_FORMS


def expand_form(form_id: str) -> list[str]:
    """Expande form_id → lista de section_ids canónicos."""
    key = (form_id or "").strip().lower()
    spec = STRUCTURE_FORMS.get(key)
    if not spec:
        return []
    return [canonical_section_id(s) for s in spec["sections"]]


def default_bars_for_form(form_id: str) -> dict[str, int]:
    key = (form_id or "").strip().lower()
    spec = STRUCTURE_FORMS.get(key)
    if not spec:
        return {}
    return dict(spec["default_bars"])


def normalize_section_list(sections: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in sections:
        sid = canonical_section_id(s)
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out[:MAX_SECTIONS]


def validate_section_list(sections: list[str]) -> list[str]:
    """Filtra ids inválidos; conserva orden."""
    normalized = normalize_section_list(sections)
    if len(normalized) >= 2:
        return normalized
    return []


def score_form(
    form_id: str,
    *,
    use_case: str,
    genre_tags: list[str],
    energy_level: int,
) -> float:
    spec = STRUCTURE_FORMS.get(form_id)
    if not spec:
        return 0.0
    score = 1.0
    uc = (use_case or "game").lower()
    if uc in spec["use_cases"]:
        score += 3.0
    tags = {t.lower() for t in genre_tags}
    for hint in spec["genre_hints"]:
        hl = hint.lower()
        if any(hl in t or t in hl for t in tags):
            score += 2.0
    elow, ehigh = spec["energy_range"]
    if elow <= energy_level <= ehigh:
        score += 1.5
    return score


def suggest_forms(
    *,
    use_case: str,
    genre_tags: list[str] | None = None,
    energy_level: int = 3,
    brief: CreativeBrief | None = None,
    limit: int = 4,
) -> list[str]:
    """Formas recomendadas para el prompt del technical_spec."""
    uc = (brief.use_case if brief else use_case) or "game"
    tags = list(genre_tags or [])
    if brief:
        tags.extend(brief.style_hints)
        tags.extend(brief.mood_keywords)

    arc_form = _form_from_arc(brief.emotional_arc if brief else "")
    if arc_form:
        return [arc_form] + [
            f for f in sorted(
                STRUCTURE_FORMS.keys(),
                key=lambda fid: score_form(
                    fid, use_case=uc, genre_tags=tags, energy_level=energy_level,
                ),
                reverse=True,
            )
            if f != arc_form
        ][:limit]

    ranked = sorted(
        STRUCTURE_FORMS.keys(),
        key=lambda fid: score_form(
            fid, use_case=uc, genre_tags=tags, energy_level=energy_level,
        ),
        reverse=True,
    )
    return ranked[:limit]


def _form_from_arc(emotional_arc: str) -> str | None:
    arc = (emotional_arc or "").lower()
    for marker, form_id in _ARC_FORM_HINTS:
        if marker in arc:
            return form_id
    if "→" in arc or "->" in arc:
        parts = [p.strip() for p in arc.replace("->", "→").split("→") if p.strip()]
        if len(parts) >= 3:
            return "boss_orchestral"
        if len(parts) == 2:
            return "cutscene_arc"
    return None


def structure_from_brief(
    brief: CreativeBrief,
    *,
    genre_tags: list[str] | None = None,
    energy_level: int = 3,
) -> tuple[list[str], str]:
    """Deriva secciones y form_id desde el brief dramático."""
    arc_form = _form_from_arc(brief.emotional_arc)
    if arc_form:
        return expand_form(arc_form), arc_form

    suggested = suggest_forms(
        use_case=brief.use_case,
        genre_tags=genre_tags,
        energy_level=energy_level,
        brief=brief,
        limit=1,
    )
    if suggested:
        fid = suggested[0]
        return expand_form(fid), fid

    return expand_form("game_standard"), "game_standard"


def format_structure_catalog_for_llm(
    *,
    suggested: list[str] | None = None,
) -> str:
    lines = [
        "=== CATÁLOGO DE FORMAS (elige structure_form) ===",
        f"Total: {len(STRUCTURE_FORMS)} formas. Lista completa por categoría:",
    ]
    if suggested:
        lines.append(f"★ Sugeridas para este brief: {', '.join(suggested)}")
    for cat_key, form_ids in STRUCTURE_FORM_CATEGORIES.items():
        label = _CATEGORY_LABELS.get(cat_key, cat_key)
        lines.append(f"\n[{label}]")
        for fid in form_ids:
            spec = STRUCTURE_FORMS.get(fid)
            if not spec:
                continue
            secs = " → ".join(spec["sections"])
            dur = spec["duration_sec"]
            mark = "★ " if suggested and fid in suggested else ""
            lines.append(
                f"{mark}• {fid}: {spec['description']} | {secs} | "
                f"{', '.join(spec['use_cases'])} | ~{dur[0]}-{dur[1]}s",
            )
    uncategorized = sorted(set(STRUCTURE_FORMS) - {
        fid for ids in STRUCTURE_FORM_CATEGORIES.values() for fid in ids
    })
    if uncategorized:
        lines.append("\n[otras]")
        for fid in uncategorized:
            spec = STRUCTURE_FORMS[fid]
            secs = " → ".join(spec["sections"])
            lines.append(f"• {fid}: {spec['description']} | {secs}")
    lines.append(
        "\nReglas structure_form:\n"
        "- Elige UN form_id del catálogo que encaje con brief + géneros.\n"
        "- Si el usuario lista secciones explícitas, deja structure_form vacío y "
        "pon las secciones en structure.\n"
        "- Si no estás seguro, deja structure_form vacío y structure=[] "
        "(el sistema derivará forma).\n"
        "- bars_per_section: opcional, solo para ids que existan en la forma; "
        f"compases {MIN_BARS_PER_SECTION}-{MAX_BARS_PER_SECTION}.\n"
        "- target_total_bars o target_duration_sec: opcional (meta de duración)."
    )
    return "\n".join(lines)


def format_structure_hints_for_spec(
    *,
    use_case: str,
    genre_tags: list[str],
    energy_level: int,
    brief: CreativeBrief | None,
) -> str:
    suggested = suggest_forms(
        use_case=use_case,
        genre_tags=genre_tags,
        energy_level=energy_level,
        brief=brief,
    )
    uc = (brief.use_case if brief else use_case) or "game"
    dur = _DURATION_BY_USE_CASE.get(uc, (36, 72))
    lines = [
        "=== FORMAS RECOMENDADAS PARA ESTE BRIEF ===",
        f"Sugeridas (orden): {', '.join(suggested)}",
        f"Duración orientativa use_case={uc}: {dur[0]}-{dur[1]} s",
    ]
    if brief and brief.emotional_arc:
        arc_form = _form_from_arc(brief.emotional_arc)
        if arc_form:
            lines.append(f"Arco emocional sugiere forma: {arc_form}")
    return "\n".join(lines)


def _pick_form_id(
    proposal: TechnicalProposal,
    intent: UserIntent,
    brief: CreativeBrief | None,
) -> str | None:
    raw_form = (getattr(proposal, "structure_form", None) or "").strip().lower()
    if is_valid_form_id(raw_form):
        return raw_form

    if brief:
        _, fid = structure_from_brief(
            brief,
            genre_tags=proposal.genre_tags,
            energy_level=proposal.energy_level,
        )
        return fid

    suggested = suggest_forms(
        use_case=intent.use_case,
        genre_tags=proposal.genre_tags,
        energy_level=proposal.energy_level,
    )
    return suggested[0] if suggested else "game_standard"


def resolve_proposal_structure(
    proposal: TechnicalProposal,
    intent: UserIntent,
    *,
    narrative_contract: NarrativeContract | None = None,
    creative_brief: CreativeBrief | None = None,
) -> TechnicalProposal:
    """
    Resuelve section_ids finales: prompt explícito > LLM > form_id > brief > fallback.
    """
    if narrative_contract and narrative_contract.section_ids:
        structure = list(narrative_contract.section_ids)
        note = "structure from narrative_contract.section_ids"
        form_id = (proposal.structure_form or "").strip().lower() or None
    elif prompt_lists_explicit_sections(intent.raw_prompt):
        structure = list(extract_explicit_structure_from_prompt(intent.raw_prompt) or [])
        note = "structure from explicit prompt list"
        form_id = None
    else:
        explicit_sections = validate_section_list(proposal.structure)
        raw_form = (proposal.structure_form or "").strip().lower()

        if explicit_sections and not is_generic_pop_structure(explicit_sections):
            structure = explicit_sections
            note = "structure from technical_spec.structure"
            form_id = raw_form if is_valid_form_id(raw_form) else None
        elif is_valid_form_id(raw_form):
            structure = expand_form(raw_form)
            note = f"structure from structure_form={raw_form}"
            form_id = raw_form
        elif is_generic_pop_structure(proposal.structure) or not proposal.structure:
            form_id = _pick_form_id(proposal, intent, creative_brief)
            structure = expand_form(form_id or "game_standard")
            note = f"structure from catalog form={form_id}"
        else:
            structure = explicit_sections or expand_form("game_standard")
            note = "structure validated from proposal"
            form_id = raw_form if is_valid_form_id(raw_form) else None

    if len(structure) < 2:
        form_id = _pick_form_id(proposal, intent, creative_brief)
        structure = expand_form(form_id or "game_standard")
        note = f"structure fallback form={form_id}"

    updates: dict = {"structure": structure, "structure_form": form_id or ""}
    if structure != list(proposal.structure) or (form_id or "") != (proposal.structure_form or ""):
        reasoning = (
            f"{proposal.reasoning} | {note}: {', '.join(structure)}."
        ).strip()
        updates["reasoning"] = reasoning

    return proposal.model_copy(update=updates)


def clamp_bars(
    bars: int,
    *,
    section_id: str = "",
) -> int:
    return max(MIN_BARS_PER_SECTION, min(MAX_BARS_PER_SECTION, bars))


def resolve_bars_per_section(
    section_ids: list[str],
    proposal: TechnicalProposal,
    *,
    use_case: str = "game",
    default_density_bars: dict[str, int] | None = None,
) -> dict[str, int]:
    """
    Compases por sección: proposal.bars_per_section > forma > heurística density.
    """
    form_id = (proposal.structure_form or "").strip().lower()
    form_defaults = default_bars_for_form(form_id) if form_id else {}
    llm_bars = dict(proposal.bars_per_section or {})

    bars: dict[str, int] = {}
    for sid in section_ids:
        if sid in llm_bars:
            bars[sid] = clamp_bars(llm_bars[sid], section_id=sid)
        elif sid in form_defaults:
            bars[sid] = form_defaults[sid]
        elif default_density_bars and sid in default_density_bars:
            bars[sid] = default_density_bars[sid]
        else:
            bars[sid] = 8

    target = proposal.target_total_bars
    if target and target > 0 and bars:
        current = sum(bars.values())
        if current != target and current > 0:
            ratio = target / current
            scaled = {
                sid: clamp_bars(max(MIN_BARS_PER_SECTION, int(round(c * ratio))))
                for sid, c in bars.items()
            }
            diff = target - sum(scaled.values())
            if diff != 0:
                pivot = section_ids[-2] if len(section_ids) > 1 else section_ids[0]
                scaled[pivot] = clamp_bars(scaled.get(pivot, 8) + diff)
            bars = scaled

    return bars
