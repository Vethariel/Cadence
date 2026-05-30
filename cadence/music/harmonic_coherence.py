"""Coherencia armónica cuando el stack tiene varias capas en tonos de acorde."""

from __future__ import annotations

from cadence.music.harmony_theory import chord_at_bar, chord_pitches, section_harmony_map
from cadence.music.layer_schedule import ms_per_bar
from cadence.schemas.song_state import (
    GenerationStrategies,
    HarmonyPlan,
    OrchestrationPlan,
    RhythmEvent,
    SongState,
    Track,
)

# Capas que anclan la armonía (excluye drums/perc/fx)
HARMONIC_SUPPORT_IDS = frozenset({
    "arp_synth", "countermelody", "synth_pluck", "chord_stab", "pad",
})

LEAD_SUPPORT_IDS = ("arp_synth", "countermelody", "synth_pluck", "chord_stab")
LEAD_SUPPORT_KEEP_ORDER = ("arp_synth", "countermelody", "synth_pluck", "chord_stab")
LEAD_SUPPORT_TRIM_ORDER = ("chord_stab", "synth_pluck", "echo_synth", "countermelody", "arp_synth")

LOW_HARMONY_AFFINITY_HIGH_ENERGY = frozenset({"classic", "modal", "cinematic"})


def active_instrument_ids_from_plan(plan: OrchestrationPlan | None) -> set[str]:
    if not plan:
        return set()
    return {a.instrument_id for a in plan.instruments if a.active}


def count_harmonic_support_layers(active_ids: set[str]) -> int:
    return sum(1 for iid in HARMONIC_SUPPORT_IDS if iid in active_ids)


def should_quantize_melody_to_chords(
    harmonic_support_count: int,
    energy_level: int,
    use_case: str,
) -> bool:
    """Varias capas en acordes + pieza intensa → melodía al acorde del compás."""
    uc = (use_case or "game").lower()
    return harmonic_support_count >= 2 and energy_level >= 4 and uc == "game"


def _nearest_chord_pitch(pitch: int, chord_tone_midis: list[int]) -> int:
    if not chord_tone_midis:
        return pitch
    candidates: list[int] = []
    for base in chord_tone_midis:
        for octave in range(-2, 4):
            candidates.append(base + octave * 12)
    return min(candidates, key=lambda c: abs(c - pitch))


def _bar_index_in_section(t_ms: int, bar_ms: float, section_bars: int) -> int:
    if bar_ms <= 0 or section_bars <= 0:
        return 0
    local = int(t_ms // bar_ms) % section_bars
    return local


def quantize_melody_events_to_harmony(
    events: list[RhythmEvent],
    *,
    harmony: HarmonyPlan,
    structure_sections: list[str],
    bars_per_section: dict[str, int],
    key: str,
    mode: str,
    bpm: int,
) -> list[RhythmEvent]:
    """Ajusta cada nota melódica al tono de acorde más cercano en su compás."""
    if not events or not harmony:
        return events

    harmony_map = section_harmony_map(harmony)
    bar_ms = ms_per_bar(bpm)
    section_start_ms: dict[str, float] = {}
    cursor = 0.0
    for sid in structure_sections:
        section_start_ms[sid] = cursor
        cursor += bars_per_section.get(sid, 4) * bar_ms

    out: list[RhythmEvent] = []
    for e in events:
        if e.type != "note":
            out.append(e)
            continue
        section_h = harmony_map.get(e.section)
        if not section_h:
            out.append(e)
            continue
        section_bars = bars_per_section.get(e.section, 4)
        rel_t = e.t - section_start_ms.get(e.section, 0)
        bar_idx = _bar_index_in_section(int(rel_t), bar_ms, section_bars)
        chord = chord_at_bar(section_h, bar_idx)
        tones = chord_pitches(key, mode, chord, octave=4)
        snapped = _nearest_chord_pitch(e.pitch, tones)
        out.append(e.model_copy(update={"pitch": snapped}))
    return out


def resolve_echo_source_for_stack(
    strategies: GenerationStrategies | None,
    active_ids: set[str],
    *,
    energy_level: int,
    use_case: str,
) -> str:
    """
    Eco desde capa consonante si hay stack armónico denso.
    auto + ≥2 soportes → arp_synth si existe; si no, melody.
    """
    explicit = strategies.echo_source if strategies else "auto"
    if explicit and explicit != "auto":
        if (
            explicit == "melody"
            and should_quantize_melody_to_chords(
                count_harmonic_support_layers(active_ids),
                energy_level,
                use_case,
            )
            and "arp_synth" in active_ids
        ):
            return "arp_synth"
        return explicit

    if should_quantize_melody_to_chords(
        count_harmonic_support_layers(active_ids),
        energy_level,
        use_case,
    ):
        if "arp_synth" in active_ids:
            return "arp_synth"
        if "chord_stab" in active_ids:
            return "chord_stab"
    return "melody"


def max_lead_support_slots(energy_level: int, use_case: str) -> int:
    uc = (use_case or "game").lower()
    if uc in ("loop", "cutscene") or energy_level <= 2:
        return 0 if energy_level <= 1 else 1
    if energy_level >= 4 and uc == "game":
        return 2
    return 1


def apply_lead_support_cap(
    active_ids: set[str],
    *,
    energy_level: int,
    use_case: str,
    protected: set[str] | None = None,
) -> set[str]:
    """
    melody + hasta N soportes (arp > counter > pluck > stab).
    echo_synth solo si hay stack armónico denso (≥2 soportes o E≥4 game).
    """
    protected = protected or set()
    max_supports = max_lead_support_slots(energy_level, use_case)

    supports = [i for i in LEAD_SUPPORT_KEEP_ORDER if i in active_ids]
    kept: list[str] = []
    for iid in supports:
        if len(kept) >= max_supports:
            break
        if iid in protected or iid not in kept:
            kept.append(iid)

    result = {iid for iid in active_ids if iid in ("drums", "bass", "melody", "pad", "perc_aux", "fx_riser")}
    result |= set(kept)

    uc = (use_case or "game").lower()
    if "echo_synth" in active_ids:
        if len(kept) >= 2 or (energy_level >= 4 and uc == "game"):
            result.add("echo_synth")

    return result


def deactivate_trimmed_instruments(
    plan: OrchestrationPlan,
    allowed_ids: set[str],
) -> OrchestrationPlan:
    """Marca inactive las capas opcionales fuera del presupuesto lead."""
    core = {"drums", "bass", "melody"}
    updated = []
    for a in plan.instruments:
        if a.instrument_id in core:
            updated.append(a)
        elif a.instrument_id in allowed_ids:
            updated.append(a)
        else:
            updated.append(a.model_copy(update={"active": False}))
    return plan.model_copy(update={"instruments": updated})


def _harmony_pool_by_score(
    plan_pool: str | None,
    strategies_pool: str | None,
    *,
    energy_level: int,
    use_case: str,
) -> str:
    from cadence.music.repertoire_signals import harmony_pool_priority
    from cadence.music.strategy_pools import HARMONY_POOL, resolve_harmony_pool

    priority = harmony_pool_priority(energy_level, use_case)

    def score(pool: str | None) -> int:
        if not pool or pool not in HARMONY_POOL:
            return -1
        try:
            return len(priority) - priority.index(pool)
        except ValueError:
            return 0

    plan_score = score(plan_pool)
    strat_score = score(strategies_pool)
    if plan_pool in HARMONY_POOL and strategies_pool in HARMONY_POOL:
        if strat_score > plan_score:
            return strategies_pool
        return plan_pool
    if strategies_pool in HARMONY_POOL:
        return strategies_pool
    if plan_pool in HARMONY_POOL:
        return plan_pool
    return resolve_harmony_pool(strategies_pool or plan_pool, 0)


def harmony_pool_for_dense_stack(
    plan_pool: str | None,
    strategies_pool: str | None,
    *,
    energy_level: int,
    use_case: str,
) -> str:
    """Si energía alta y el agente elige pool de baja tensión, prioriza strategies."""
    uc = (use_case or "game").lower()
    if (
        energy_level >= 4
        and uc == "game"
        and plan_pool in LOW_HARMONY_AFFINITY_HIGH_ENERGY
        and strategies_pool
        and strategies_pool not in LOW_HARMONY_AFFINITY_HIGH_ENERGY
    ):
        return strategies_pool
    return _harmony_pool_by_score(
        plan_pool, strategies_pool,
        energy_level=energy_level, use_case=use_case,
    )


def apply_harmonic_coherence_to_state(state: SongState) -> dict:
    """Post-orquesta: cuantiza melodía si el stack lo requiere."""
    tracks = state.get("tracks", [])
    if not tracks:
        return {}

    proposal = state.get("technical_proposal")
    structure = state.get("structure")
    harmony = state.get("harmony")
    plan = state.get("orchestration_plan")
    intent = state.get("intent")

    if not proposal or not structure or not harmony:
        return {}

    energy = proposal.energy_level
    use_case = intent.use_case if intent else "game"
    active = active_instrument_ids_from_plan(plan)
    n_harmonic = count_harmonic_support_layers(active)

    if not should_quantize_melody_to_chords(n_harmonic, energy, use_case):
        return {}

    result = []
    for track in tracks:
        if track.id != "melody" or not track.events:
            result.append(track)
            continue
        events = quantize_melody_events_to_harmony(
            track.events,
            harmony=harmony,
            structure_sections=structure.sections,
            bars_per_section=structure.bars_per_section,
            key=proposal.key,
            mode=proposal.mode,
            bpm=proposal.bpm,
        )
        result.append(track.model_copy(update={"events": events}))
    return {"tracks": result}
