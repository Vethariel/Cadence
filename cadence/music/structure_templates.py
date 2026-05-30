"""
Plantillas de macro-forma por use_case — evita intro-verse-chorus-outro por defecto.
"""

from __future__ import annotations

import re

from cadence.music.narrative_contract import _normalize_section_id
from cadence.schemas.song_state import NarrativeContract, TechnicalProposal, UserIntent

GENERIC_POP_SECTIONS = ("intro", "verse", "chorus", "outro")

# Orden fijo por use_case cuando el prompt no lista secciones explícitas
USE_CASE_STRUCTURE: dict[str, list[str]] = {
    "loop": ["intro", "pad_layering", "melodic_motif", "outro_loop"],
    "cutscene": ["intro", "dialogue_bed", "tension_swell", "outro"],
    "game": ["intro", "build-up", "drop", "outro"],
    "animation": ["intro", "build-up", "climax", "outro"],
}

_BOSS_MARKERS = (
    "boss", "jefe", "final boss", "confrontación", "confrontation",
    "boss fight", "pelea de jefe",
)
_ORCHESTRAL_EPIC_MARKERS = (
    "orquestal épico", "orquestal epico", "boss orquestal", "orchestral epic",
    "muchas capas", "capas simultáneas", "capas simultaneas", "masivas capas",
    "épico", "epico",
)
_EXPLICIT_SECTION_RE = re.compile(
    r"\b(intro|outro|verse|chorus|bridge|drop|build[- ]?up|breakdown|"
    r"climax|loop|pre[- ]?chorus|main[- ]?theme|dialogue|tension|pad|"
    r"ambient|exploration|overworld|cutscene|swell|bed|motif)\b",
    re.IGNORECASE,
)


def _normalized_ids(sections: list[str]) -> list[str]:
    return [_normalize_section_id(s) for s in sections]


def is_generic_pop_structure(sections: list[str]) -> bool:
    """True si la forma es exactamente intro-verse-chorus-outro (plantilla pop genérica)."""
    if len(sections) != 4:
        return False
    return tuple(_normalized_ids(sections)) == GENERIC_POP_SECTIONS


def prompt_lists_explicit_sections(raw_prompt: str) -> bool:
    """True si el prompt enumera secciones en orden (cadena intro-X-… o campo estructura)."""
    return extract_explicit_structure_from_prompt(raw_prompt) is not None


def prompt_requests_specific_form(raw_prompt: str) -> bool:
    """El brief pide una forma no-pop (loop, cutscene, boss, edm, etc.)."""
    p = (raw_prompt or "").lower()
    markers = (
        "loop", "overworld", "exploración", "exploration", "ambiente", "ambient",
        "cutscene", "diálogo", "dialogo", "narrativa", "pasillo", "tensión contenida",
        "boss", "jefe", "build-up", "build up", "drop", "breakdown", "climax",
        "chiptune", "eurobeat", "arcade", "plataforma", "platform", "sin edm",
        "sin climax de combate", "pads y drones", "pre-chorus", "main-theme",
    )
    return any(m in p for m in markers)


def extract_explicit_structure_from_prompt(raw_prompt: str) -> list[str] | None:
    """
    Extrae secciones si el prompt las enumera (ej. intro-verse-chorus-outro).
    Devuelve IDs canónicos o None si no hay lista clara.
    """
    p = (raw_prompt or "").strip()
    if not p:
        return None
    lower = p.lower()
    for sep in ("→", "->", "|", "/", ","):
        if sep in lower and "intro" in lower:
            parts = [x.strip() for x in re.split(re.escape(sep), lower) if x.strip()]
            if len(parts) >= 2 and all(_EXPLICIT_SECTION_RE.search(part) for part in parts):
                return _normalized_ids(parts)
    m = re.search(
        r"(?:estructura|structure|secciones?)\s*[:=]?\s*"
        r"([\w\s\-–—]+(?:intro|verse|chorus|outro|drop|build)[\w\s\-–—]*)",
        lower,
    )
    if m:
        chunk = re.split(r"\s+en\s+", m.group(1), maxsplit=1)[0]
        parts = re.split(r"[-–—]+", chunk)
        ids = [_normalize_section_id(x.strip()) for x in parts if x.strip()]
        if len(ids) >= 2:
            return ids
    m = re.search(
        r"\b(intro\s*[-–—]\s*[\w]+(?:\s*[-–—]\s*[\w]+)*)\b",
        lower,
    )
    if m:
        chunk = re.split(r"\s+en\s+", m.group(0), maxsplit=1)[0]
        parts = [x.strip() for x in re.split(r"[-–—]+", chunk) if x.strip()]
        ids = _normalized_ids(parts)
        if len(ids) >= 2:
            return ids
    return None


def default_structure_for_use_case(
    use_case: str,
    raw_prompt: str = "",
) -> list[str]:
    """Estructura base cuando no hay lista explícita en el prompt."""
    uc = (use_case or "game").lower()
    prompt = (raw_prompt or "").lower()

    explicit = extract_explicit_structure_from_prompt(raw_prompt)
    if explicit:
        return explicit

    if any(m in prompt for m in _BOSS_MARKERS):
        if any(m in prompt for m in _ORCHESTRAL_EPIC_MARKERS):
            return [
                "intro", "verse", "pre-chorus", "main-theme", "bridge", "climax", "outro",
            ]
        if any(m in prompt for m in ("build-up", "build up", "drop", "edm", "techno")):
            return ["intro", "build-up", "drop", "outro"]
        return ["intro", "build-up", "drop", "bridge", "outro"]

    if uc == "loop" or any(
        x in prompt for x in ("overworld", "exploración", "exploration", "loop de")
    ):
        return list(USE_CASE_STRUCTURE["loop"])
    if uc == "cutscene" or "cutscene" in prompt or "diálogo" in prompt:
        return list(USE_CASE_STRUCTURE["cutscene"])
    if any(x in prompt for x in ("chiptune", "eurobeat", "arcade", "combate arcade")):
        return ["intro", "verse", "chorus", "outro"]
    return list(USE_CASE_STRUCTURE.get(uc, USE_CASE_STRUCTURE["game"]))


def resolve_proposal_structure(
    proposal: TechnicalProposal,
    intent: UserIntent,
    *,
    narrative_contract: NarrativeContract | None = None,
) -> TechnicalProposal:
    """
    Sustituye plantilla pop genérica por forma derivada de use_case / prompt / contrato.
    """
    if narrative_contract and narrative_contract.section_ids:
        structure = list(narrative_contract.section_ids)
        note = "structure from narrative_contract.section_ids"
    elif prompt_lists_explicit_sections(intent.raw_prompt):
        structure = list(extract_explicit_structure_from_prompt(intent.raw_prompt) or [])
        note = "structure from explicit prompt list"
    elif is_generic_pop_structure(proposal.structure):
        structure = default_structure_for_use_case(intent.use_case, intent.raw_prompt)
        note = f"structure defaulted from use_case={intent.use_case!r} (avoided generic pop)"
    else:
        structure = [_normalize_section_id(s) for s in proposal.structure]
        note = "structure kept from proposal"

    if structure == list(proposal.structure):
        return proposal

    reasoning = (
        f"{proposal.reasoning} | {note}: {', '.join(structure)}."
    ).strip()
    return proposal.model_copy(update={"structure": structure, "reasoning": reasoning})


def structure_planner_penalty_hint(state: dict) -> str:
    """Bloque para structure_planner: penaliza plantilla genérica si el prompt pide otra forma."""
    intent = state.get("intent")
    contract = state.get("narrative_contract")
    if not intent or not contract:
        return ""

    raw = intent.raw_prompt or ""
    if not prompt_requests_specific_form(raw):
        return ""

    if not is_generic_pop_structure(contract.section_ids):
        return ""

    suggested = default_structure_for_use_case(intent.use_case, raw)
    return (
        "\n=== PENALIZACIÓN ESTRUCTURA GENÉRICA ===\n"
        "El contrato aún refleja intro-verse-chorus-outro pero el prompt pide otra forma "
        f"({intent.use_case}, términos del brief).\n"
        f"Los section_ids del contrato son INMUTABLES en este nodo, pero asigna compases "
        f"como si la pieza fuera {', '.join(suggested)} — densidad acorde al rol narrativo, "
        "no a un pop estándar.\n"
        "En futuras rutas, la propuesta técnica debería evitar la plantilla pop.\n"
    )
