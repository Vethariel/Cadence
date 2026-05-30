"""
Requisitos técnicos explícitos en el prompt del usuario.

Principio: si el usuario nombra un instrumento o timbre, eso gana sobre
paletas por arquetipo/género. No inferimos estilo por tags — solo lo que
dice el prompt.

Para añadir instrumentos: extender _ALIAS_SPECS (alias, capa, GM, familia).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from cadence.music.timbre_library import gm_name


@dataclass(frozen=True)
class PromptInstrumentRequest:
    """Un instrumento pedido explícitamente en el prompt."""
    instrument_id: str
    gm_program: int
    display_name: str


@dataclass(frozen=True)
class _AliasSpec:
    alias: str
    instrument_id: str
    gm_program: int
    family: str


# alias (substring) → capa destino + GM + familia (deduplicación multi-instrumento)
# Orden: más específico primero; el buscador prioriza coincidencias largas en la misma posición.
_ALIAS_SPECS: tuple[_AliasSpec, ...] = (
    # ── guitarra ──
    _AliasSpec("nylon guitar", "melody", 24, "guitar"),
    _AliasSpec("jazz guitar", "melody", 26, "guitar"),
    _AliasSpec("clean guitar", "melody", 27, "guitar"),
    _AliasSpec("distortion guitar", "melody", 30, "guitar"),
    _AliasSpec("overdriven guitar", "melody", 29, "guitar"),
    _AliasSpec("muted guitar", "melody", 28, "guitar"),
    _AliasSpec("steel guitar", "melody", 25, "guitar"),
    _AliasSpec("guitarra acústica", "melody", 24, "guitar"),
    _AliasSpec("guitarra acustica", "melody", 24, "guitar"),
    _AliasSpec("guitarra eléctrica", "melody", 27, "guitar"),
    _AliasSpec("guitarra electrica", "melody", 27, "guitar"),
    _AliasSpec("guitarra", "melody", 26, "guitar"),
    _AliasSpec("guitar", "melody", 26, "guitar"),
    # ── piano / teclado ──
    _AliasSpec("electric piano", "melody", 4, "piano"),
    _AliasSpec("piano eléctrico", "melody", 4, "piano"),
    _AliasSpec("piano electrico", "melody", 4, "piano"),
    _AliasSpec("grand piano", "melody", 0, "piano"),
    _AliasSpec("piano acústico", "melody", 0, "piano"),
    _AliasSpec("piano acustico", "melody", 0, "piano"),
    _AliasSpec("honky tonk", "melody", 3, "piano"),
    _AliasSpec("honky-tonk", "melody", 3, "piano"),
    _AliasSpec("clavinet", "melody", 7, "keys"),
    _AliasSpec("clavinete", "melody", 7, "keys"),
    _AliasSpec("teclado", "melody", 4, "piano"),
    _AliasSpec("keyboard", "melody", 4, "piano"),
    _AliasSpec("piano", "melody", 4, "piano"),
    # ── órgano / acordeón ──
    _AliasSpec("church organ", "melody", 19, "organ"),
    _AliasSpec("órgano de iglesia", "melody", 19, "organ"),
    _AliasSpec("organo de iglesia", "melody", 19, "organ"),
    _AliasSpec("rock organ", "melody", 18, "organ"),
    _AliasSpec("órgano", "melody", 19, "organ"),
    _AliasSpec("organo", "melody", 19, "organ"),
    _AliasSpec("organ", "melody", 19, "organ"),
    _AliasSpec("acordeón", "melody", 21, "organ"),
    _AliasSpec("acordeon", "melody", 21, "organ"),
    _AliasSpec("accordion", "melody", 21, "organ"),
    _AliasSpec("harmonica", "melody", 22, "organ"),
    _AliasSpec("armónica", "melody", 22, "organ"),
    _AliasSpec("armonica", "melody", 22, "organ"),
    # ── cuerdas melódicas ──
    _AliasSpec("violonchelo", "melody", 42, "cello"),
    _AliasSpec("violoncello", "melody", 42, "cello"),
    _AliasSpec("cello", "melody", 42, "cello"),
    _AliasSpec("chelo", "melody", 42, "cello"),
    _AliasSpec("viola", "melody", 41, "viola"),
    _AliasSpec("violín", "melody", 40, "violin"),
    _AliasSpec("violin", "melody", 40, "violin"),
    _AliasSpec("contrabajo", "bass", 43, "contrabass"),
    _AliasSpec("contrabass", "bass", 43, "contrabass"),
    _AliasSpec("double bass", "bass", 43, "contrabass"),
    # ── viento madera ──
    _AliasSpec("flauta de pan", "melody", 75, "flute"),
    _AliasSpec("pan flute", "melody", 75, "flute"),
    _AliasSpec("flauta dulce", "melody", 74, "flute"),
    _AliasSpec("recorder", "melody", 74, "flute"),
    _AliasSpec("flauta", "melody", 73, "flute"),
    _AliasSpec("flute", "melody", 73, "flute"),
    _AliasSpec("clarinete", "melody", 71, "clarinet"),
    _AliasSpec("clarinet", "melody", 71, "clarinet"),
    _AliasSpec("oboe", "melody", 68, "oboe"),
    _AliasSpec("obúa", "melody", 68, "oboe"),
    _AliasSpec("obua", "melody", 68, "oboe"),
    _AliasSpec("piccolo", "melody", 72, "piccolo"),
    _AliasSpec("flautín", "melody", 72, "piccolo"),
    _AliasSpec("flautin", "melody", 72, "piccolo"),
    _AliasSpec("ocarina", "melody", 79, "ocarina"),
    # ── viento metal / sax ──
    _AliasSpec("saxofón tenor", "melody", 66, "sax"),
    _AliasSpec("saxofon tenor", "melody", 66, "sax"),
    _AliasSpec("tenor sax", "melody", 66, "sax"),
    _AliasSpec("saxofón alto", "melody", 65, "sax"),
    _AliasSpec("saxofon alto", "melody", 65, "sax"),
    _AliasSpec("alto sax", "melody", 65, "sax"),
    _AliasSpec("saxofón", "melody", 66, "sax"),
    _AliasSpec("saxofon", "melody", 66, "sax"),
    _AliasSpec("saxophone", "melody", 66, "sax"),
    _AliasSpec("sax", "melody", 66, "sax"),
    _AliasSpec("trompeta", "melody", 56, "trumpet"),
    _AliasSpec("trumpet", "melody", 56, "trumpet"),
    _AliasSpec("trombón", "melody", 57, "trombone"),
    _AliasSpec("trombon", "melody", 57, "trombone"),
    _AliasSpec("trombone", "melody", 57, "trombone"),
    _AliasSpec("trompa", "melody", 60, "horn"),
    _AliasSpec("french horn", "melody", 60, "horn"),
    _AliasSpec("corno francés", "melody", 60, "horn"),
    _AliasSpec("corno frances", "melody", 60, "horn"),
    # ── bajo ──
    _AliasSpec("fretless bass", "bass", 35, "bass"),
    _AliasSpec("bajo sin trastes", "bass", 35, "bass"),
    _AliasSpec("bajo fretless", "bass", 35, "bass"),
    _AliasSpec("slap bass", "bass", 36, "bass"),
    _AliasSpec("bajo slap", "bass", 36, "bass"),
    _AliasSpec("pick bass", "bass", 34, "bass"),
    _AliasSpec("bajo con pua", "bass", 34, "bass"),
    _AliasSpec("bajo con púa", "bass", 34, "bass"),
    _AliasSpec("finger bass", "bass", 33, "bass"),
    _AliasSpec("synth bass", "bass", 38, "bass"),
    _AliasSpec("bajo sintetizador", "bass", 38, "bass"),
    _AliasSpec("bajo sintético", "bass", 38, "bass"),
    _AliasSpec("bajo sintetico", "bass", 38, "bass"),
    _AliasSpec("acoustic bass", "bass", 32, "bass"),
    _AliasSpec("bajo acústico", "bass", 32, "bass"),
    _AliasSpec("bajo acustico", "bass", 32, "bass"),
    _AliasSpec("bajo", "bass", 34, "bass"),
    _AliasSpec("bass", "bass", 34, "bass"),
    # ── pads / cuerdas de fondo ──
    _AliasSpec("string ensemble", "pad", 48, "pad_strings"),
    _AliasSpec("cuerdas de fondo", "pad", 48, "pad_strings"),
    _AliasSpec("string pad", "pad", 48, "pad_strings"),
    _AliasSpec("cuerdas", "pad", 48, "pad_strings"),
    _AliasSpec("strings", "pad", 48, "pad_strings"),
    _AliasSpec("tremolo strings", "pad", 44, "pad_strings"),
    _AliasSpec("synth strings", "pad", 50, "pad_strings"),
    _AliasSpec("choir aahs", "pad", 52, "pad_choir"),
    _AliasSpec("coro", "pad", 52, "pad_choir"),
    _AliasSpec("coros", "pad", 52, "pad_choir"),
    _AliasSpec("choir", "pad", 52, "pad_choir"),
    _AliasSpec("halo pad", "pad", 94, "pad_synth"),
    _AliasSpec("pad etéreo", "pad", 94, "pad_synth"),
    _AliasSpec("pad etereo", "pad", 94, "pad_synth"),
    _AliasSpec("pad", "pad", 89, "pad_synth"),
    # ── arpeggios / campanas / arpa ──
    _AliasSpec("orchestral harp", "arp_synth", 46, "harp"),
    _AliasSpec("arpa orquestal", "arp_synth", 46, "harp"),
    _AliasSpec("arpa", "arp_synth", 46, "harp"),
    _AliasSpec("harp", "arp_synth", 46, "harp"),
    _AliasSpec("glockenspiel", "arp_synth", 9, "bells"),
    _AliasSpec("campanas", "arp_synth", 9, "bells"),
    _AliasSpec("tubular bells", "arp_synth", 14, "bells"),
    _AliasSpec("campanas tubulares", "arp_synth", 14, "bells"),
    _AliasSpec("vibraphone", "arp_synth", 11, "mallet"),
    _AliasSpec("vibráfono", "arp_synth", 11, "mallet"),
    _AliasSpec("vibrafono", "arp_synth", 11, "mallet"),
    _AliasSpec("marimba", "arp_synth", 12, "mallet"),
    _AliasSpec("xilófono", "arp_synth", 13, "mallet"),
    _AliasSpec("xilofono", "arp_synth", 13, "mallet"),
    _AliasSpec("xylophone", "arp_synth", 13, "mallet"),
    _AliasSpec("celesta", "arp_synth", 8, "bells"),
    _AliasSpec("music box", "arp_synth", 10, "bells"),
    _AliasSpec("caja de música", "arp_synth", 10, "bells"),
    _AliasSpec("caja de musica", "arp_synth", 10, "bells"),
    _AliasSpec("harpsichord", "melody", 6, "harpsichord"),
    _AliasSpec("clavicémbalo", "melody", 6, "harpsichord"),
    _AliasSpec("clavicembalo", "melody", 6, "harpsichord"),
    # ── synth leads ──
    _AliasSpec("lead square", "melody", 80, "synth"),
    _AliasSpec("square lead", "melody", 80, "synth"),
    _AliasSpec("onda cuadrada", "melody", 80, "synth"),
    _AliasSpec("square wave", "melody", 80, "synth"),
    _AliasSpec("chiptune lead", "melody", 80, "synth"),
    _AliasSpec("saw lead", "melody", 81, "synth"),
    _AliasSpec("sawtooth", "melody", 81, "synth"),
    _AliasSpec("onda diente de sierra", "melody", 81, "synth"),
    _AliasSpec("lead synth", "melody", 81, "synth"),
    _AliasSpec("sintetizador lead", "melody", 81, "synth"),
    _AliasSpec("synth lead", "melody", 81, "synth"),
)

# Pares frecuentes con capas fijas (familia → capa override)
_PAIR_LAYER_OVERRIDES: dict[frozenset[str], dict[str, str]] = {
    frozenset({"guitar", "piano"}): {"guitar": "melody", "piano": "chord_stab"},
    frozenset({"violin", "piano"}): {"violin": "melody", "piano": "chord_stab"},
    frozenset({"violin", "cello"}): {"violin": "melody", "cello": "countermelody"},
}

_INSTRUMENT_ALIASES: tuple[tuple[str, str, int], ...] = tuple(
    (s.alias, s.instrument_id, s.gm_program) for s in _ALIAS_SPECS
)
_FAMILY: dict[str, str] = {s.alias: s.family for s in _ALIAS_SPECS}


def _normalize_prompt(raw_prompt: str) -> str:
    return " ".join((raw_prompt or "").lower().split())


def _alias_in_prompt(prompt: str, alias: str) -> int:
    """Índice del alias como palabra completa, o -1 si no aparece."""
    pattern = re.compile(
        rf"(?<![a-záéíóúüñ0-9]){re.escape(alias)}(?![a-záéíóúüñ0-9])",
    )
    match = pattern.search(prompt)
    return match.start() if match else -1


def _find_alias_matches(prompt: str) -> list[_AliasSpec]:
    """Alias encontrados en orden de aparición en el prompt."""
    found: list[tuple[int, int, _AliasSpec]] = []
    for spec in _ALIAS_SPECS:
        idx = _alias_in_prompt(prompt, spec.alias)
        if idx >= 0:
            found.append((idx, -len(spec.alias), spec))
    found.sort()

    seen_alias: set[str] = set()
    seen_span: list[tuple[int, int]] = []
    ordered: list[_AliasSpec] = []

    for idx, _neg_len, spec in found:
        if spec.alias in seen_alias:
            continue
        end = idx + len(spec.alias)
        overlap = any(not (end <= start or idx >= end2) for start, end2 in seen_span)
        if overlap:
            continue
        seen_alias.add(spec.alias)
        seen_span.append((idx, end))
        ordered.append(spec)

    return ordered


def _layer_for_family(
    family: str,
    spec: _AliasSpec,
    families_present: set[str],
) -> str:
    for fam_set, mapping in _PAIR_LAYER_OVERRIDES.items():
        if families_present >= fam_set and family in mapping:
            return mapping[family]
    return spec.instrument_id


def parse_prompt_instrument_requests(raw_prompt: str) -> list[PromptInstrumentRequest]:
    """
    Instrumentos nombrados explícitamente en el prompt, en orden de aparición.
    Cada alias define su capa destino; familias duplicadas se ignoran.
    """
    prompt = _normalize_prompt(raw_prompt)
    if not prompt:
        return []

    matches = _find_alias_matches(prompt)
    if not matches:
        return []

    families_present = {spec.family for spec in matches}
    used_families: set[str] = set()
    used_layers: set[str] = set()
    requests: list[PromptInstrumentRequest] = []

    for spec in matches:
        if spec.family in used_families:
            continue
        layer = _layer_for_family(spec.family, spec, families_present)
        if layer in used_layers:
            continue
        used_families.add(spec.family)
        used_layers.add(layer)
        requests.append(PromptInstrumentRequest(
            layer, spec.gm_program, gm_name(spec.gm_program),
        ))

    return requests


def prompt_requests_melody_gm(raw_prompt: str) -> int | None:
    """GM program forzado para melody si el prompt lo pide."""
    for req in parse_prompt_instrument_requests(raw_prompt):
        if req.instrument_id == "melody":
            return req.gm_program
    return None


def prompt_context_tokens(raw_prompt: str) -> set[str]:
    """Tokens de contexto derivados solo de menciones explícitas en el prompt."""
    tokens: set[str] = set()
    prompt = _normalize_prompt(raw_prompt)
    for spec in _find_alias_matches(prompt):
        tokens.add(spec.family)
        tokens.add(spec.alias.replace(" ", "_"))
        if spec.instrument_id == "bass":
            tokens.add("bass")
        if spec.family == "guitar":
            tokens.update({"guitar", "guitarra"})
        if spec.family == "piano":
            tokens.add("piano")
    return tokens
