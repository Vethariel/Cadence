"""
Señales compositivas generales — energía, use_case, densidad de patrones y narrativa.

Sin listas de géneros/tags: el repertorio se infiere de cómo suena la estrategia
(pasos por compás, capas implicadas) y del rol de la pieza.
"""

from __future__ import annotations

from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.instrument_patterns import (
    COUNTER_STEP_PATTERNS,
    PERC_CLAP_PATTERNS,
    PLUCK_STEP_PATTERNS,
    STAB_STEP_PATTERNS,
)
from cadence.schemas.song_state import (
    GenerationStrategies,
    InstrumentAssignment,
    MusicalStyleProfile,
    OrchestrationPlan,
)

DENSE_STEPS_PER_BAR = 6
SPARSE_STEPS_PER_BAR = 3

_PATTERN_STEPS: dict[str, dict[str, tuple[int, ...]]] = {
    "stab": STAB_STEP_PATTERNS,
    "perc": PERC_CLAP_PATTERNS,
    "pluck": PLUCK_STEP_PATTERNS,
    "counter": COUNTER_STEP_PATTERNS,
}


def pattern_density(pattern_id: str | None, kind: str) -> int:
    """Pasos activos por compás (proxy de densidad rítmica)."""
    if not pattern_id:
        return 0
    if kind == "arp" and pattern_id == "sixteenth":
        return 16
    steps = _PATTERN_STEPS.get(kind, {}).get(pattern_id)
    if steps:
        return len(steps)
    if kind == "arp" and pattern_id in ARP_PATTERNS:
        return 4
    return 0


def is_dense_pattern(pattern_id: str | None, kind: str) -> bool:
    return pattern_density(pattern_id, kind) >= DENSE_STEPS_PER_BAR


def is_sparse_pattern(pattern_id: str | None, kind: str) -> bool:
    d = pattern_density(pattern_id, kind)
    return 0 < d <= SPARSE_STEPS_PER_BAR


def drum_pool_priority(
    energy_level: int,
    use_case: str,
    *,
    composition_archetype: str | None = None,
) -> list[str]:
    from cadence.music.strategy_pools import DRUM_POOL

    arch = composition_archetype or ""
    if arch == "chiptune_dance":
        return ["breakbeat", "dnb", "techno", "house"] + [
            p for p in DRUM_POOL if p not in ("breakbeat", "dnb", "techno", "house")
        ]
    if arch == "compact_action":
        return ["breakbeat", "techno", "house", "halftime"] + [
            p for p in DRUM_POOL if p not in ("breakbeat", "techno", "house", "halftime")
        ]
    if arch == "orchestral_boss":
        return ["breakbeat", "industrial", "dubstep", "techno"] + [
            p for p in DRUM_POOL if p not in ("breakbeat", "industrial", "dubstep", "techno")
        ]

    uc = (use_case or "game").lower()
    if uc == "loop" or energy_level <= 1:
        return ["default", "halftime", "house"] + [p for p in DRUM_POOL if p not in ("default", "halftime", "house")]
    if energy_level >= 5:
        return ["dubstep", "breakbeat", "dnb", "industrial", "techno"] + [
            p for p in DRUM_POOL if p not in ("dubstep", "breakbeat", "dnb", "industrial", "techno")
        ]
    if energy_level >= 4:
        return ["techno", "breakbeat", "dubstep", "house"] + [
            p for p in DRUM_POOL if p not in ("techno", "breakbeat", "dubstep", "house")
        ]
    return list(DRUM_POOL)


def harmony_pool_priority(
    energy_level: int,
    use_case: str,
    *,
    composition_archetype: str | None = None,
) -> list[str]:
    from cadence.music.strategy_pools import HARMONY_POOL

    arch = composition_archetype or ""
    if arch == "chiptune_dance":
        return ["dance", "aggressive", "game", "modal", "classic", "dark", "cinematic"]
    if arch == "compact_action":
        return ["game", "aggressive", "modal", "classic", "dance", "dark", "cinematic"]
    if arch == "orchestral_boss":
        return ["cinematic", "aggressive", "dark", "game", "modal", "dance", "classic"]

    uc = (use_case or "game").lower()
    if uc == "loop" or energy_level <= 1:
        order = ["modal", "classic", "game", "cinematic", "dark", "dance", "aggressive"]
    elif uc == "cutscene" or energy_level <= 2:
        order = ["cinematic", "modal", "dark", "classic", "game", "aggressive", "dance"]
    elif energy_level >= 5:
        order = ["aggressive", "dance", "game", "dark", "cinematic", "modal", "classic"]
    elif energy_level >= 4:
        order = ["aggressive", "dance", "game", "dark", "classic", "modal", "cinematic"]
    else:
        order = ["game", "classic", "modal", "dance", "cinematic", "dark", "aggressive"]
    return [p for p in order if p in HARMONY_POOL] + [p for p in HARMONY_POOL if p not in order]


def bass_pool_priority(energy_level: int, use_case: str) -> list[str]:
    from cadence.music.strategy_pools import BASS_POOL

    uc = (use_case or "game").lower()
    if uc in ("loop", "cutscene") or energy_level <= 2:
        return ["pulse", "root_fifth", "half_time"] + [p for p in BASS_POOL if p not in ("pulse", "root_fifth", "half_time")]
    if energy_level >= 5:
        return ["octave_pulse", "driving", "syncopated", "half_time"] + [
            p for p in BASS_POOL if p not in ("octave_pulse", "driving", "syncopated", "half_time")
        ]
    if energy_level >= 4:
        return ["driving", "octave_pulse", "syncopated", "root_fifth"] + [
            p for p in BASS_POOL if p not in ("driving", "octave_pulse", "syncopated", "root_fifth")
        ]
    return list(BASS_POOL)


def layer_pattern_bias(
    energy_level: int,
    use_case: str,
    generation_seed: int,
    *,
    composition_archetype: str | None = None,
) -> dict[str, list[str] | str]:
    """Candidatos de patrón por energía y rol — sin tags."""
    from cadence.music.instrument_patterns import (
        COUNTER_PATTERN_POOL,
        PERC_PATTERN_POOL,
        PLUCK_PATTERN_POOL,
        STAB_PATTERN_POOL,
    )

    uc = (use_case or "game").lower()
    arch = composition_archetype or ""
    bias: dict[str, list[str] | str] = {"echo_source": "auto"}

    if arch == "compact_action":
        bias["arp_candidates"] = ["broken", "up", "pingpong", "syncopated"] + list(ARP_PATTERNS)
        bias["counter_candidates"] = ["sparse", "backbeat", "offbeat_sync"] + list(COUNTER_PATTERN_POOL)
        bias["stab_candidates"] = ["sparse", "half_bar", "offbeat"] + list(STAB_PATTERN_POOL)
        bias["pluck_candidates"] = ["sparse", "eighth"] + list(PLUCK_PATTERN_POOL)
        bias["perc_candidates"] = ["backbeat", "sparse"] + list(PERC_PATTERN_POOL)
        bias["bass_candidates"] = ["pulse", "root_fifth", "half_time", "driving"]
        bias["echo_source"] = "melody"
        return bias

    if arch == "chiptune_dance":
        bias["arp_candidates"] = ["sixteenth", "cascade", "syncopated", "broken"] + list(ARP_PATTERNS)
        bias["stab_candidates"] = ["sixteenth", "four_on", "syncopated"] + list(STAB_PATTERN_POOL)
        bias["perc_candidates"] = ["syncopated", "four_clap", "backbeat"] + list(PERC_PATTERN_POOL)
        bias["pluck_candidates"] = ["sixteenth", "eighth", "syncopated"] + list(PLUCK_PATTERN_POOL)
        bias["counter_candidates"] = ["offbeat_sync", "sixteenth", "syncopated"] + list(COUNTER_PATTERN_POOL)
        bias["bass_candidates"] = ["octave_pulse", "driving", "syncopated"]
        return bias

    if arch == "orchestral_boss":
        bias["arp_candidates"] = ["broken", "up", "pingpong", "syncopated"] + list(ARP_PATTERNS)
        bias["stab_candidates"] = ["orchestral_sync", "half_bar", "offbeat"] + list(STAB_PATTERN_POOL)
        bias["counter_candidates"] = ["orchestral_sync", "offbeat_sync", "sparse"] + list(COUNTER_PATTERN_POOL)
        bias["pluck_candidates"] = ["sparse", "eighth"] + list(PLUCK_PATTERN_POOL)
        bias["perc_candidates"] = ["syncopated", "four_clap", "backbeat"] + list(PERC_PATTERN_POOL)
        bias["bass_candidates"] = ["driving", "octave_pulse", "half_time"]
        bias["echo_source"] = "chord_stab"
        return bias

    if energy_level <= 2 or uc == "loop":
        bias["arp_candidates"] = ["up", "broken", "pingpong"]
        bias["stab_candidates"] = ["sparse", "half_bar", "offbeat"]
        bias["counter_candidates"] = ["sparse", "backbeat"]
        bias["pluck_candidates"] = ["sparse", "eighth"]
        return bias

    if energy_level >= 4:
        bias["arp_candidates"] = ["sixteenth", "cascade", "broken", "syncopated"] + list(ARP_PATTERNS)
        bias["stab_candidates"] = ["sixteenth", "four_on", "syncopated", "offbeat"] + list(STAB_PATTERN_POOL)
        bias["perc_candidates"] = ["syncopated", "four_clap", "backbeat"] + list(PERC_PATTERN_POOL)
        bias["pluck_candidates"] = ["sixteenth", "eighth", "syncopated"] + list(PLUCK_PATTERN_POOL)
        bias["counter_candidates"] = ["offbeat_sync", "sixteenth", "syncopated"] + list(COUNTER_PATTERN_POOL)
        bias["bass_candidates"] = ["octave_pulse", "driving", "syncopated", "half_time"]
        # echo_source queda en auto; resolve_echo_source_for_stack elige capa consonante

    if uc == "cutscene" and energy_level >= 3:
        sc = list(bias.get("stab_candidates") or list(STAB_PATTERN_POOL))
        cc = list(bias.get("counter_candidates") or list(COUNTER_PATTERN_POOL))
        if "orchestral_sync" not in sc:
            sc.insert(0, "orchestral_sync")
        if "orchestral_sync" not in cc:
            cc.insert(0, "orchestral_sync")
        bias["stab_candidates"] = sc
        bias["counter_candidates"] = cc
        bias["echo_source"] = "chord_stab"

    return bias


def instruments_implied_by_strategies(
    strategies: GenerationStrategies | None,
    *,
    energy_level: int = 3,
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> set[str]:
    """Capas que la estrategia ya compromete (deben materializarse en el arreglo)."""
    if not strategies:
        return set()

    implied: set[str] = set()
    uc = (use_case or "game").lower()
    arch = composition_archetype or ""

    if arch == "compact_action":
        if energy_level >= 3 and uc != "loop":
            implied.add("pad")
        if strategies.counter_pattern and not is_sparse_pattern(
            strategies.counter_pattern, "counter",
        ):
            implied.add("countermelody")
        echo = strategies.echo_source or "auto"
        if echo in ("melody", "arp_synth", "chord_stab"):
            implied.add("echo_synth")
        return implied

    if arch == "orchestral_boss":
        implied.add("pad")
        if strategies.counter_pattern and strategies.counter_pattern in COUNTER_STEP_PATTERNS:
            implied.add("countermelody")
        if strategies.stab_pattern and not is_sparse_pattern(strategies.stab_pattern, "stab"):
            implied.add("chord_stab")
        if strategies.perc_pattern and not is_sparse_pattern(strategies.perc_pattern, "perc"):
            implied.add("perc_aux")
        echo = strategies.echo_source or "auto"
        if echo in ("melody", "arp_synth", "chord_stab"):
            implied.add("echo_synth")
        if is_dense_pattern(strategies.arp_pattern, "arp") and energy_level >= 5:
            implied.add("arp_synth")
        return implied

    if is_dense_pattern(strategies.arp_pattern, "arp") or (
        strategies.arp_pattern == "sixteenth"
    ):
        implied.add("arp_synth")

    if strategies.counter_pattern and strategies.counter_pattern in COUNTER_STEP_PATTERNS:
        if not is_sparse_pattern(strategies.counter_pattern, "counter") or energy_level >= 3:
            implied.add("countermelody")

    if strategies.stab_pattern and not is_sparse_pattern(strategies.stab_pattern, "stab"):
        implied.add("chord_stab")

    if strategies.pluck_pattern and is_dense_pattern(strategies.pluck_pattern, "pluck"):
        has_dense_arp = is_dense_pattern(strategies.arp_pattern, "arp")
        has_counter = (
            strategies.counter_pattern
            and strategies.counter_pattern in COUNTER_STEP_PATTERNS
            and not is_sparse_pattern(strategies.counter_pattern, "counter")
        )
        if energy_level >= 4 and uc == "game" and has_dense_arp and has_counter:
            pass
        else:
            implied.add("synth_pluck")

    if strategies.perc_pattern and not is_sparse_pattern(strategies.perc_pattern, "perc"):
        if energy_level >= 3 and uc != "loop":
            implied.add("perc_aux")

    echo = strategies.echo_source or "auto"
    if echo in ("melody", "arp_synth", "chord_stab"):
        implied.add("echo_synth")
    elif echo == "auto" and energy_level >= 4 and uc == "game":
        if arch != "compact_action":
            implied.add("echo_synth")

    if energy_level >= 3 and uc not in ("loop",) and not is_sparse_piece(energy_level, uc):
        implied.add("pad")

    if arch == "chiptune_dance" and energy_level >= 4:
        implied.add("arp_synth")
        implied.add("perc_aux")

    return implied


def is_sparse_piece(energy_level: int, use_case: str) -> bool:
    return (use_case or "game").lower() == "loop" or energy_level <= 1


def percussion_suppressed(
    *,
    use_case: str,
    energy_level: int,
    style_profile: MusicalStyleProfile | None = None,
) -> bool:
    """Piezas muy tranquilas o que evitan percusión explícitamente."""
    if (use_case or "game").lower() == "loop" and energy_level <= 2:
        return True
    if energy_level <= 1:
        return True
    if not style_profile or not style_profile.avoid:
        return False
    avoid_l = " ".join(style_profile.avoid).lower()
    explicit_no = (
        "no drums", "without drums", "no drum kit", "no percussion", "without percussion",
        "no kick", "no snare", "no beat", "no rhythm", "sin batería", "sin percusión",
        "no drum", "without drum", "avoid drums", "avoid percussion",
        "no percussive drums", "percussive drums",
        "sin bateria", "sin percusion",
    )
    if any(phrase in avoid_l for phrase in explicit_no):
        return True
    import re

    if re.search(
        r"\b(?:no|without|avoid|sin)\s+(?:drums?|percussion|kick|snare|beat|rhythm)\b",
        avoid_l,
    ):
        return True
    # "drum machines" / kits electrónicos ≠ prohibir batería acústica/taiko
    stripped = re.sub(r"\bdrum\s+machines?\b", "", avoid_l)
    if re.search(r"\b(?:no|without|avoid|sin)\s+drums?\b", stripped):
        return True
    return False


def schedule_density_thresholds(energy_level: int, use_case: str) -> dict[str, float]:
    """Umbrales de capas opcionales por energía y rol."""
    from cadence.music.layer_schedule import (
        DENSITY_ARP,
        DENSITY_CHORD_STAB,
        DENSITY_COUNTER,
        DENSITY_ECHO,
        DENSITY_PAD,
        DENSITY_PERC,
        DENSITY_PLUCK,
    )

    uc = (use_case or "game").lower()
    if is_sparse_piece(energy_level, uc):
        return {
            "arp": 0.85,
            "pad": 0.12,
            "pluck": 0.7,
            "counter": 0.7,
            "chord_stab": 0.7,
            "perc": 0.7,
            "echo": 0.7,
        }
    if uc == "cutscene" or energy_level <= 2:
        return {
            "arp": 0.68,
            "pad": 0.18,
            "pluck": 0.42,
            "counter": 0.38,
            "chord_stab": 0.38,
            "perc": 0.42,
            "echo": 0.45,
        }
    if energy_level >= 5:
        return {
            "arp": 0.52,
            "pad": 0.30,
            "pluck": 0.40,
            "counter": 0.40,
            "chord_stab": 0.40,
            "perc": 0.40,
            "echo": 0.45,
        }
    if energy_level >= 4:
        return {
            "arp": 0.55,
            "pluck": 0.42,
            "pad": 0.32,
            "echo": 0.48,
            "counter": 0.42,
            "chord_stab": 0.42,
            "perc": 0.42,
        }
    return {}


def default_melody_texture(
    energy_level: int,
    use_case: str,
    requested: str = "balanced",
) -> str:
    if requested != "balanced":
        return requested
    uc = (use_case or "game").lower()
    if uc == "loop" or energy_level <= 2:
        return "sparse"
    if energy_level >= 5:
        return "dense"
    if energy_level >= 4 and uc == "game":
        return "dense"
    return "balanced"


def resolve_harmony_pool_choice(
    plan_pool: str | None,
    strategies_pool: str | None,
    *,
    energy_level: int,
    use_case: str,
) -> str:
    """Elige pool con afinidad a energía/rol; en stacks intensos evita pools planos del agente."""
    from cadence.music.harmonic_coherence import harmony_pool_for_dense_stack

    return harmony_pool_for_dense_stack(
        plan_pool, strategies_pool,
        energy_level=energy_level, use_case=use_case,
    )


def max_optional_budget(
    use_case: str,
    energy_level: int,
    *,
    composition_archetype: str | None = None,
) -> tuple[int, int]:
    """(max_optionals, max_lead_optionals) por rol y energía."""
    uc = (use_case or "game").lower()
    from cadence.music.instrument_catalog import (
        MAX_LEAD_OPTIONALS,
        MAX_OPTIONAL_BY_USE_CASE,
    )

    max_opt = MAX_OPTIONAL_BY_USE_CASE.get(uc, 4)
    max_lead = MAX_LEAD_OPTIONALS.get(uc, 2)

    arch = composition_archetype or ""
    if arch == "compact_action":
        return min(max_opt, 3), 1
    if arch == "orchestral_boss" and energy_level >= 4:
        return min(max_opt + 1, 5), min(max_lead + 1, 3)

    if energy_level <= 2 and uc != "loop":
        max_opt = min(max_opt, 2)
        max_lead = min(max_lead, 1)
    elif energy_level >= 5 and uc in ("game", "animation"):
        max_opt = min(max_opt + 1, 5)
        max_lead = min(max_lead + 1, 3)
    elif energy_level >= 4 and uc in ("game", "animation"):
        max_lead = min(max_lead + 1, 3)

    return max_opt, max_lead


def enrich_orchestration_from_strategies(
    plan: OrchestrationPlan,
    strategies: GenerationStrategies | None,
    *,
    energy_level: int,
    use_case: str,
    generation_seed: int = 0,
    style_profile: MusicalStyleProfile | None = None,
    raw_prompt: str = "",
    composition_archetype: str | None = None,
) -> OrchestrationPlan:
    """Añade capas que la estrategia ya define pero el agente omitió."""
    from cadence.music.style_archetype import infer_composition_archetype

    arch = composition_archetype or infer_composition_archetype(
        style_profile=style_profile,
        raw_prompt=raw_prompt,
        use_case=use_case,
        energy_level=energy_level,
    )
    implied = instruments_implied_by_strategies(
        strategies,
        energy_level=energy_level,
        use_case=use_case,
        composition_archetype=arch,
    )
    if percussion_suppressed(
        use_case=use_case, energy_level=energy_level, style_profile=style_profile,
    ):
        implied.discard("perc_aux")

    by_id = {a.instrument_id: a for a in plan.instruments if a.active}
    default_mix = {
        "pad": -14.0, "arp_synth": -12.0, "echo_synth": -14.0,
        "countermelody": -11.0, "chord_stab": -13.0, "perc_aux": -12.0,
        "synth_pluck": -11.0,
    }

    for iid in implied:
        if iid not in by_id:
            by_id[iid] = InstrumentAssignment(
                instrument_id=iid,
                gm_program=0,
                mix_level=default_mix.get(iid, -12.0),
                active=True,
            )

    if percussion_suppressed(
        use_case=use_case, energy_level=energy_level, style_profile=style_profile,
    ):
        if "drums" in by_id:
            by_id["drums"] = by_id["drums"].model_copy(update={"active": False})

    from cadence.music.style_archetype import (
        infer_composition_archetype,
        melody_texture_for_archetype,
    )

    texture = melody_texture_for_archetype(
        arch, energy_level, use_case, plan.melody_texture,
    )

    instruments = list(by_id.values())
    return plan.model_copy(update={
        "instruments": instruments,
        "melody_texture": texture,
    })


def lead_layers_for_fallback(energy_level: int, use_case: str, generation_seed: int) -> set[str]:
    """Capas lead opcionales en fallback — solo energía y rol."""
    uc = (use_case or "game").lower()
    from cadence.music.instrument_catalog import MAX_LEAD_OPTIONALS

    max_n = MAX_LEAD_OPTIONALS.get(uc, 2)
    if max_n == 0:
        return set()

    if uc == "cutscene" or energy_level <= 2:
        return {"countermelody"} if energy_level >= 2 else set()

    if energy_level >= 5:
        pool = ["arp_synth", "echo_synth", "countermelody", "chord_stab", "synth_pluck"]
    elif energy_level >= 4:
        pool = ["arp_synth", "echo_synth", "countermelody", "chord_stab"]
    else:
        pool = ["arp_synth", "countermelody"]

    n = min(max_n, 2 if energy_level >= 4 else 1)
    chosen: list[str] = []
    for i in range(n):
        idx = (generation_seed // (29 * (i + 1))) % len(pool)
        c = pool[idx]
        if c not in chosen:
            chosen.append(c)
    return set(chosen)
