"""
Aplica la composición del technical_spec (LLM) y deja al flujo determinista
solo validar, ajustar y generar notas.
"""

from __future__ import annotations

from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
)
from cadence.music.pattern_registry import pattern_family
from cadence.music.strategy_pools import (
    BASS_PATTERN_ALIASES,
    BASS_POOL,
    DRUM_PATTERN_ALIASES,
    DRUM_POOL,
    ECHO_SOURCE_POOL,
    HARMONY_POOL,
    format_rhythm_patterns_for_llm,
    pattern_id_in_pool,
)
from cadence.schemas.song_state import (
    GenerationStrategies,
    OrchestrationPlan,
    TechnicalProposal,
)

_TEXTURE_MODES = frozenset({"bedded", "staggered", "simultaneous", "compact"})
_AGENT_DRUM = frozenset({
    "techno", "dubstep", "house", "breakbeat", "halftime", "dnb", "industrial", "default",
})
_AGENT_BASS = frozenset({
    "root_fifth", "driving", "syncopated", "pulse", "half_time", "walk", "octave_pulse",
})


def proposal_has_composition_spec(proposal: TechnicalProposal) -> bool:
    """True si el LLM rellenó orquestación o patrones (no solo BPM/key)."""
    if proposal.instruments:
        return True
    return any(
        getattr(proposal, f, "") for f in (
            "drum_pattern", "bass_pattern", "harmony_pool", "arp_pattern",
            "stab_pattern", "perc_pattern", "pluck_pattern", "counter_pattern",
        )
    )


def _snap_in_pool(raw: str, pool: tuple[str, ...] | list[str], aliases: dict[str, str]) -> str:
    if not (raw or "").strip():
        return ""
    pid = (raw or "").strip().lower()
    if pattern_id_in_pool(pid, list(pool), aliases):
        from cadence.music.pattern_registry import resolve_pattern_id
        return resolve_pattern_id(pid, aliases, default=pid if pid in pool else "")
    fam = pattern_family(pid)
    for candidate in pool:
        if pattern_family(candidate) == fam:
            return candidate
    return ""


def snap_drum_pattern(raw: str) -> str:
    return _snap_in_pool(raw, DRUM_POOL, DRUM_PATTERN_ALIASES)


def snap_bass_pattern(raw: str) -> str:
    return _snap_in_pool(raw, BASS_POOL, BASS_PATTERN_ALIASES)


def snap_harmony_pool(raw: str) -> str:
    key = (raw or "").strip().lower()
    return key if key in HARMONY_POOL else ""


def snap_arp_pattern(raw: str) -> str:
    pid = (raw or "").strip().lower()
    if not pid:
        return ""
    if pid in ARP_PATTERNS:
        return pid
    fam = pattern_family(pid)
    for candidate in ARP_PATTERNS:
        if pattern_family(candidate) == fam:
            return candidate
    return ""


def snap_layer_pattern(raw: str, pool: tuple[str, ...], aliases: dict[str, str]) -> str:
    return _snap_in_pool(raw, pool, aliases)


def snap_echo_source(raw: str) -> str:
    key = (raw or "").strip().lower()
    return key if key in ECHO_SOURCE_POOL else ""


def snap_texture_mode(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    return key if key in _TEXTURE_MODES else ""


def snap_archetype(raw: str) -> str:
    from cadence.music.composition_archetypes import is_valid_archetype, normalize_archetype

    key = (raw or "").strip().lower()
    if is_valid_archetype(key):
        return normalize_archetype(key)
    return ""


def snap_scale_mode(raw: str | None) -> str:
    from cadence.music.scale_theory import normalize_mode

    return normalize_mode(raw)


def snap_time_signature(raw: list[int] | None) -> list[int]:
    from cadence.music.meter_theory import normalize_time_signature

    return normalize_time_signature(raw)


def drum_pattern_for_plan(raw: str) -> str:
    """Familia de patrón para OrchestrationPlan (sin sufijo _a/_b)."""
    fam = pattern_family(snap_drum_pattern(raw) or raw)
    return fam if fam in _AGENT_DRUM else "default"


def bass_pattern_for_plan(raw: str) -> str:
    fam = pattern_family(snap_bass_pattern(raw) or raw)
    return fam if fam in _AGENT_BASS else "root_fifth"


def normalize_global_motif(degrees: list[int]) -> list[int]:
    if len(degrees) < 3:
        return []
    out = [max(0, min(6, int(d))) for d in degrees[:5]]
    return out if len(out) >= 3 else []


def format_composition_patterns_for_llm() -> str:
    """Catálogo de patrones para que technical_spec fije la composición rítmica/armónica."""
    from cadence.music.composition_archetypes import format_archetypes_for_llm

    lines = [
        "=== PATRONES DE COMPOSICIÓN (technical_spec — elige ids EXACTOS) ===",
        "Rellena drum_pattern, bass_pattern, harmony_pool y capas opcionales si las activas.",
        "Vacío en un campo = el sistema elige por seed (evitar si quieres control total).",
        "",
        format_rhythm_patterns_for_llm(),
        "",
        f"Pools armónicos (harmony_pool): {', '.join(HARMONY_POOL)}",
        "",
        "Patrones de capas (solo si activas arp_synth, chord_stab, perc_aux, synth_pluck, countermelody):",
        f"  arp_pattern — familias: {', '.join(sorted({pattern_family(p) for p in ARP_PATTERNS}))}",
        f"  stab_pattern — {', '.join(sorted({pattern_family(p) for p in STAB_PATTERN_POOL[:12]}))}…",
        f"  perc_pattern — {', '.join(sorted({pattern_family(p) for p in PERC_PATTERN_POOL[:8]}))}…",
        f"  pluck_pattern — {', '.join(sorted({pattern_family(p) for p in PLUCK_PATTERN_POOL[:8]}))}…",
        f"  counter_pattern — {', '.join(sorted({pattern_family(p) for p in COUNTER_PATTERN_POOL[:8]}))}…",
        f"  echo_source: {', '.join(ECHO_SOURCE_POOL)}",
        "",
        "texture_mode: bedded | staggered | simultaneous | compact",
        f"composition_archetype (opcional): {format_archetypes_for_llm()}",
        "global_motif (opcional): 3–5 enteros 0–6 (grados de escala del motivo principal).",
    ]
    return "\n".join(lines)


def normalize_technical_proposal_composition(proposal: TechnicalProposal) -> TechnicalProposal:
    """Ajusta patrones y metadatos compositivos del LLM al catálogo interno."""
    from cadence.music.instrument_patterns import (
        COUNTER_PATTERN_ALIASES,
        PERC_PATTERN_ALIASES,
        PLUCK_PATTERN_ALIASES,
        STAB_PATTERN_ALIASES,
    )

    updates: dict = {}
    drum = snap_drum_pattern(proposal.drum_pattern)
    if drum:
        updates["drum_pattern"] = drum
    bass = snap_bass_pattern(proposal.bass_pattern)
    if bass:
        updates["bass_pattern"] = bass
    harmony = snap_harmony_pool(proposal.harmony_pool)
    if harmony:
        updates["harmony_pool"] = harmony
    arp = snap_arp_pattern(proposal.arp_pattern)
    if arp:
        updates["arp_pattern"] = arp
    stab = snap_layer_pattern(proposal.stab_pattern, STAB_PATTERN_POOL, STAB_PATTERN_ALIASES)
    if stab:
        updates["stab_pattern"] = stab
    perc = snap_layer_pattern(proposal.perc_pattern, PERC_PATTERN_POOL, PERC_PATTERN_ALIASES)
    if perc:
        updates["perc_pattern"] = perc
    pluck = snap_layer_pattern(proposal.pluck_pattern, PLUCK_PATTERN_POOL, PLUCK_PATTERN_ALIASES)
    if pluck:
        updates["pluck_pattern"] = pluck
    counter = snap_layer_pattern(
        proposal.counter_pattern, COUNTER_PATTERN_POOL, COUNTER_PATTERN_ALIASES,
    )
    if counter:
        updates["counter_pattern"] = counter
    echo = snap_echo_source(proposal.echo_source)
    if echo:
        updates["echo_source"] = echo
    texture = snap_texture_mode(proposal.texture_mode)
    if texture:
        updates["texture_mode"] = texture  # type: ignore[assignment]
    arch = snap_archetype(proposal.composition_archetype)
    if arch:
        updates["composition_archetype"] = arch
    motif = normalize_global_motif(proposal.global_motif)
    if motif:
        updates["global_motif"] = motif
    mode = snap_scale_mode(proposal.mode)
    if mode:
        updates["mode"] = mode
    ts = snap_time_signature(proposal.time_signature)
    if ts:
        updates["time_signature"] = ts
    if not updates:
        return proposal
    return proposal.model_copy(update=updates)


def merge_strategies_from_proposal(
    strategies: GenerationStrategies,
    proposal: TechnicalProposal,
) -> GenerationStrategies:
    """Prioriza patrones del LLM; el resto queda del selector por seed."""
    updates: dict = {}

    drum = snap_drum_pattern(proposal.drum_pattern)
    if drum:
        updates["drum_pattern"] = drum
    bass = snap_bass_pattern(proposal.bass_pattern)
    if bass:
        updates["bass_pattern"] = bass
    harmony = snap_harmony_pool(proposal.harmony_pool)
    if harmony:
        updates["harmony_pool"] = harmony

    from cadence.music.instrument_patterns import (
        COUNTER_PATTERN_ALIASES,
        PERC_PATTERN_ALIASES,
        PLUCK_PATTERN_ALIASES,
        STAB_PATTERN_ALIASES,
    )

    arp = snap_arp_pattern(proposal.arp_pattern)
    if arp:
        updates["arp_pattern"] = arp
    stab = snap_layer_pattern(proposal.stab_pattern, STAB_PATTERN_POOL, STAB_PATTERN_ALIASES)
    if stab:
        updates["stab_pattern"] = stab
    perc = snap_layer_pattern(proposal.perc_pattern, PERC_PATTERN_POOL, PERC_PATTERN_ALIASES)
    if perc:
        updates["perc_pattern"] = perc
    pluck = snap_layer_pattern(proposal.pluck_pattern, PLUCK_PATTERN_POOL, PLUCK_PATTERN_ALIASES)
    if pluck:
        updates["pluck_pattern"] = pluck
    counter = snap_layer_pattern(
        proposal.counter_pattern, COUNTER_PATTERN_POOL, COUNTER_PATTERN_ALIASES,
    )
    if counter:
        updates["counter_pattern"] = counter
    echo = snap_echo_source(proposal.echo_source)
    if echo:
        updates["echo_source"] = echo

    if not updates:
        return strategies
    return strategies.model_copy(update=updates)


def apply_patterns_to_orchestration_plan(
    plan: OrchestrationPlan,
    proposal: TechnicalProposal,
    strategies: GenerationStrategies | None,
) -> OrchestrationPlan:
    """Sincroniza drum/bass/patrones de capas del plan con la propuesta LLM."""
    updates: dict = {}
    if proposal.drum_pattern:
        updates["drum_pattern"] = drum_pattern_for_plan(proposal.drum_pattern)  # type: ignore[arg-type]
    elif strategies:
        updates["drum_pattern"] = drum_pattern_for_plan(strategies.drum_pattern)  # type: ignore[arg-type]

    if proposal.bass_pattern:
        updates["bass_pattern"] = bass_pattern_for_plan(proposal.bass_pattern)  # type: ignore[arg-type]
    elif strategies:
        updates["bass_pattern"] = bass_pattern_for_plan(strategies.bass_pattern)  # type: ignore[arg-type]

    if proposal.arp_pattern and strategies:
        updates["arp_pattern"] = strategies.arp_pattern
    if proposal.stab_pattern and strategies:
        updates["stab_pattern"] = strategies.stab_pattern
    if proposal.perc_pattern and strategies:
        updates["perc_pattern"] = strategies.perc_pattern
    if proposal.pluck_pattern and strategies:
        updates["pluck_pattern"] = strategies.pluck_pattern
    if proposal.counter_pattern and strategies:
        updates["counter_pattern"] = strategies.counter_pattern
    if proposal.echo_source and strategies:
        updates["echo_source"] = strategies.echo_source
    if proposal.harmony_pool and strategies:
        updates["harmony_pool"] = strategies.harmony_pool

    if not updates:
        return plan
    return plan.model_copy(update=updates)
