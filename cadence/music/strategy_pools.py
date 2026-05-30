"""Pools de estrategias compositivas — selección determinista por generation_seed."""

from cadence.schemas.song_state import GenerationStrategies
from cadence.music.arp_patterns import ARP_PATTERNS
from cadence.music.instrument_patterns import (
    COUNTER_PATTERN_POOL,
    PERC_PATTERN_POOL,
    PLUCK_PATTERN_POOL,
    STAB_PATTERN_POOL,
)
from cadence.music.repertoire_signals import (
    bass_pool_priority,
    drum_pool_priority,
    harmony_pool_priority,
    layer_pattern_bias,
)

# ── Patrones de batería (16 steps, 4/4) — sub-variantes _a/_b ─────

from cadence.music.pattern_variants import (
    BASS_PATTERN_ALIASES,
    BASS_VARIANT_PATTERNS,
    BASS_VARIANT_POOL,
    DRUM_PATTERN_ALIASES,
    DRUM_VARIANT_PATTERNS,
    DRUM_VARIANT_POOL,
)

DRUM_PATTERNS: dict[str, dict[str, list[int]]] = dict(DRUM_VARIANT_PATTERNS)
DRUM_POOL = list(DRUM_VARIANT_POOL)

DRUM_PATTERN_INFO: dict[str, str] = {
    "techno": "Kick four-on-the-floor, snare en 2 y 4, hi-hat en corcheas — industrial/techno oscuro.",
    "dubstep": "Kick syncopado con doble snare, hi-hat denso — brostep/agresivo.",
    "house": "Kick four-on-the-floor, snare clásico, hi-hat en off-beats — groove estable.",
    "breakbeat": "Kick y snare desplazados estilo break — tensión rítmica, boss fights.",
    "halftime": "Half-time: kick y snare espaciados — drops dubstep/trap.",
    "dnb": "Kick doble y hats continuos — drum and bass / neuro.",
    "industrial": "Kick y hats densos, snare seco — techno industrial / EBM.",
    "default": "Patrón equilibrado genérico — neutro si ningún estilo encaja.",
}

# ── Patrones de bajo (step, root|fifth) ───────────────────────

BassStep = tuple[int, str]

BASS_PATTERNS: dict[str, list[BassStep]] = dict(BASS_VARIANT_PATTERNS)
BASS_POOL = list(BASS_VARIANT_POOL)

BASS_PATTERN_INFO: dict[str, str] = {
    "root_fifth": "Raíz y quinta en compás — clásico, legible en juego.",
    "driving": "Raíz repetida con quintas en off-beats — impulso constante.",
    "syncopated": "Entradas desplazadas — groove más inquieto/tensión.",
    "pulse": "Solo raíz en 1 y 3 — mínimo, loops y cutscenes.",
    "half_time": "Raíz en 1 y 3 con quinta — half-time dubstep/trap.",
    "walk": "Caminata cromática en semicorcheas — jazz/funk game.",
    "octave_pulse": "Raíz en cada negra — sub presión constante.",
    "staccato": "Raíz y quinta cortas — groove seco, dance/chiptune.",
    "sub_drop": "Raíz espaciada con remate — drops de bass music.",
}

# ── Pools de progresiones armónicas ───────────────────────────

PROGRESSIONS_CLASSIC_MINOR = {
    "default": [(0, "minor"), (5, "major"), (2, "major"), (6, "major")],
    "tension": [(0, "minor"), (3, "minor"), (5, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (0, "minor"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_MODAL_MINOR = {
    "default": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
    "tension": [(0, "minor"), (5, "major"), (6, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (6, "major"), (5, "major"), (0, "minor")],
    "sparse": [(0, "minor"), (5, "major")],
    "release": [(0, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_GAME_MINOR = {
    "default": [(0, "minor"), (6, "major"), (3, "minor"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (5, "major"), (6, "major")],
    "climax": [(0, "minor"), (5, "major"), (4, "dominant"), (0, "minor")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (3, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_CLASSIC_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (3, "major")],
    "tension": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "climax": [(0, "major"), (0, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_MODAL_MAJOR = {
    "default": [(0, "major"), (5, "minor"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (2, "minor"), (5, "minor"), (4, "major")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (3, "major"), (0, "major")],
}

PROGRESSIONS_GAME_MAJOR = {
    "default": [(0, "major"), (5, "major"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (6, "minor"), (4, "major"), (5, "major")],
    "climax": [(0, "major"), (4, "major"), (5, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_DARK_MINOR = {
    "default": [(0, "minor"), (3, "minor"), (6, "major"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (3, "minor"), (6, "major")],
    "climax": [(0, "minor"), (6, "major"), (4, "dominant"), (0, "minor")],
    "sparse": [(0, "minor"), (3, "minor")],
    "release": [(0, "minor"), (5, "major"), (0, "minor")],
}

PROGRESSIONS_DARK_MAJOR = {
    "default": [(0, "major"), (5, "minor"), (6, "minor"), (4, "major")],
    "tension": [(0, "major"), (4, "major"), (5, "minor"), (3, "minor")],
    "climax": [(0, "major"), (6, "minor"), (4, "major"), (0, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

PROGRESSIONS_CINEMATIC_MINOR = {
    "default": [(0, "minor"), (5, "major"), (3, "minor"), (4, "dominant")],
    "tension": [(0, "minor"), (6, "major"), (4, "dominant"), (5, "major")],
    "climax": [(0, "minor"), (5, "major"), (6, "major"), (0, "minor")],
    "sparse": [(0, "minor"), (5, "major")],
    "release": [(0, "minor"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_CINEMATIC_MAJOR = {
    "default": [(0, "major"), (4, "major"), (5, "minor"), (0, "major")],
    "tension": [(0, "major"), (2, "minor"), (5, "minor"), (4, "major")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (0, "major")],
    "sparse": [(0, "major"), (5, "major")],
    "release": [(0, "major"), (4, "major"), (0, "major")],
}

PROGRESSIONS_DANCE_MINOR = {
    "default": [(0, "minor"), (6, "major"), (5, "major"), (3, "minor")],
    "tension": [(0, "minor"), (5, "major"), (6, "major"), (4, "dominant")],
    "climax": [(0, "minor"), (6, "major"), (5, "major"), (6, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (3, "minor"), (0, "minor")],
}

PROGRESSIONS_DANCE_MAJOR = {
    "default": [(0, "major"), (5, "major"), (3, "minor"), (4, "major")],
    "tension": [(0, "major"), (4, "major"), (5, "major"), (3, "minor")],
    "climax": [(0, "major"), (5, "major"), (4, "major"), (5, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (3, "minor"), (0, "major")],
}

PROGRESSIONS_AGGRESSIVE_MINOR = {
    "default": [(0, "minor"), (6, "major"), (3, "minor"), (5, "major")],
    "tension": [(0, "minor"), (4, "dominant"), (5, "major"), (6, "major")],
    "climax": [(0, "minor"), (4, "dominant"), (6, "major"), (5, "major")],
    "sparse": [(0, "minor")],
    "release": [(0, "minor"), (5, "major"), (4, "dominant"), (0, "minor")],
}

PROGRESSIONS_AGGRESSIVE_MAJOR = {
    "default": [(0, "major"), (6, "minor"), (4, "major"), (5, "major")],
    "tension": [(0, "major"), (4, "major"), (6, "minor"), (5, "major")],
    "climax": [(0, "major"), (4, "major"), (5, "major"), (4, "major")],
    "sparse": [(0, "major")],
    "release": [(0, "major"), (5, "minor"), (0, "major")],
}

HARMONY_POOLS_MINOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MINOR,
    "modal": PROGRESSIONS_MODAL_MINOR,
    "game": PROGRESSIONS_GAME_MINOR,
    "dark": PROGRESSIONS_DARK_MINOR,
    "cinematic": PROGRESSIONS_CINEMATIC_MINOR,
    "dance": PROGRESSIONS_DANCE_MINOR,
    "aggressive": PROGRESSIONS_AGGRESSIVE_MINOR,
}

HARMONY_POOLS_MAJOR: dict[str, dict] = {
    "classic": PROGRESSIONS_CLASSIC_MAJOR,
    "modal": PROGRESSIONS_MODAL_MAJOR,
    "game": PROGRESSIONS_GAME_MAJOR,
    "dark": PROGRESSIONS_DARK_MAJOR,
    "cinematic": PROGRESSIONS_CINEMATIC_MAJOR,
    "dance": PROGRESSIONS_DANCE_MAJOR,
    "aggressive": PROGRESSIONS_AGGRESSIVE_MAJOR,
}

HARMONY_POOL = [
    "classic", "modal", "game", "dark", "cinematic", "dance", "aggressive",
]


def compute_generation_seed(raw_prompt: str, total_bars: int) -> int:
    return abs(hash(f"{raw_prompt}:{total_bars}")) % 100_000


def format_rhythm_patterns_for_llm() -> str:
    """Catálogo drum/bass para el instrument_planner."""
    from cadence.music.pattern_registry import pattern_family

    def _catalog_lines(
        pool: list[str],
        info: dict[str, str],
        label: str,
    ) -> list[str]:
        out = [label]
        seen: set[str] = set()
        for pid in pool:
            fam = pattern_family(pid)
            if fam in seen:
                continue
            seen.add(fam)
            variants = [p for p in pool if pattern_family(p) == fam]
            desc = info.get(fam, f"Patrón {fam}.")
            out.append(f"  • {', '.join(variants)}: {desc}")
        return out

    lines = _catalog_lines(
        DRUM_POOL,
        DRUM_PATTERN_INFO,
        "Patrones de batería (elige EXACTAMENTE uno — obligatorio):",
    )
    lines.extend(_catalog_lines(
        BASS_POOL,
        BASS_PATTERN_INFO,
        "\nPatrones de bajo (elige EXACTAMENTE uno — obligatorio):",
    ))
    lines.append(
        "\nElige drum y bass coherentes con género, energía y use_case. "
        "Varía respecto a un default genérico cuando el mood lo permita."
    )
    return "\n".join(lines)


ECHO_SOURCE_POOL = ("auto", "melody", "arp_synth", "chord_stab", "echo_synth")

_BATCH_PENALTY = 0.12
_RECENT_WINDOW = 4


def _node_jitter(seed: int, salt: int) -> int:
    """Desplazamiento determinista 0..9999 por nodo (evita correlación seed%len)."""
    return abs(hash((seed, salt, "cadence_pattern_jitter"))) % 10_000


def _ordered_candidates(
    priority: list[str] | None,
    pool: tuple[str, ...] | list[str],
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for pid in priority or []:
        if pid in pool and pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    for pid in pool:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    return ordered


def _batch_weight_factor(choice_id: str, field: str, recent: list[str]) -> float:
    if not recent:
        return 1.0
    token = f"{field}:{choice_id}"
    hits = sum(1 for sig in recent[-_RECENT_WINDOW:] if token in sig)
    if hits >= 2:
        return _BATCH_PENALTY
    if hits == 1:
        return 0.45
    return 1.0


def _weighted_pick(
    priority: list[str] | None,
    pool: tuple[str, ...] | list[str],
    seed: int,
    salt: int,
    *,
    field: str = "pattern",
    recent: list[str] | None = None,
) -> str:
    """Selección ponderada con jitter por nodo y penalización intra-batch."""
    pool_tuple = tuple(pool)
    candidates = _ordered_candidates(priority, pool_tuple)
    if not candidates:
        return pool_tuple[0]

    jitter = _node_jitter(seed, salt)
    batch_recent = recent or []
    weights: list[float] = []
    for rank, pid in enumerate(candidates):
        w = float(max(4, 18 - rank * 2))
        w *= _batch_weight_factor(pid, field, batch_recent)
        weights.append(w)

    total = sum(weights)
    if total <= 0:
        return candidates[jitter % len(candidates)]

    target = (jitter % 10_000) / 10_000.0 * total
    acc = 0.0
    for pid, w in zip(candidates, weights):
        acc += w
        if target < acc:
            return pid
    return candidates[-1]


def _pick_biased(
    candidates: list[str],
    pool: tuple[str, ...],
    seed: int,
    salt: int,
    *,
    field: str = "pattern",
    recent: list[str] | None = None,
) -> str:
    return _weighted_pick(candidates, pool, seed, salt, field=field, recent=recent)


def select_strategies(
    generation_seed: int,
    genre_tags: list[str] | None = None,
    mode: str = "minor",
    use_case: str = "game",
    energy_level: int = 3,
    *,
    composition_archetype: str | None = None,
    pattern_intent: object | None = None,
    pattern_selection_audit: object | None = None,
) -> GenerationStrategies:
    """Elige estrategias desde pattern_intent + seed (no mapeo directo tags→patrón)."""
    from cadence.music.pattern_batch_context import (
        get_batch_recent_patterns,
        record_strategy_patterns,
    )
    from cadence.music.pattern_intent import PatternIntent, derive_pattern_intent
    from cadence.music.style_profile import build_genre_mix

    arch = composition_archetype
    recent = get_batch_recent_patterns()

    intent: PatternIntent
    if isinstance(pattern_intent, PatternIntent):
        intent = pattern_intent
    else:
        mix = build_genre_mix(proposal_tags=genre_tags or [])
        intent = derive_pattern_intent(
            genre_mix=mix,
            use_case=use_case,
            energy_level=energy_level,
            composition_archetype=arch,
            generation_seed=generation_seed,
        )

    from cadence.music.genre_pattern_affinity import (
        ARP_GENRE_BOOST,
        BASS_GENRE_BOOST,
        COUNTER_GENRE_BOOST,
        DRUM_GENRE_BOOST,
        HARMONY_GENRE_BOOST,
        PERC_GENRE_BOOST,
        PLUCK_GENRE_BOOST,
        STAB_GENRE_BOOST,
    )
    from cadence.music.pattern_selection import weighted_pick_audited
    from cadence.music.pattern_selection_audit import rhythm_combo_signature
    from cadence.schemas.song_state import PatternSelectionAudit

    mix = intent.genre_mix or {}
    audit: PatternSelectionAudit | None = (
        pattern_selection_audit
        if isinstance(pattern_selection_audit, PatternSelectionAudit)
        else None
    )
    if audit is not None:
        audit.generation_seed = generation_seed
    mood = intent.mood or ""
    energy = intent.energy_level or energy_level

    from cadence.music.pattern_batch_context import (
        combo_in_recent_window,
        effective_combo_diversity_window,
    )

    drum_candidates = intent.drum_candidates or list(DRUM_POOL)
    layer_bias = intent.layer_bias or {}
    bass_candidates = layer_bias.get("bass_candidates")
    if not isinstance(bass_candidates, list):
        bass_candidates = intent.bass_candidates or list(BASS_POOL)
    harmony_candidates = intent.harmony_candidates or list(HARMONY_POOL)

    combo_window = effective_combo_diversity_window()
    if audit is not None:
        audit.combo_diversity_window = combo_window

    drum_pattern = ""
    bass_pattern = ""
    harmony_pool = ""
    combo_attempt = 0
    for attempt in range(12 if combo_window > 0 else 1):
        combo_attempt = attempt
        salt_off = attempt * 11
        drum_audit = weighted_pick_audited(
            generation_seed, 3 + salt_off, drum_candidates, DRUM_POOL,
            genre_mix=mix, genre_boost_table=DRUM_GENRE_BOOST,
            composition_archetype=arch, mood=mood, energy_level=energy,
            field="drum", recent=recent,
        )
        bass_audit = weighted_pick_audited(
            generation_seed, 7 + salt_off, bass_candidates, BASS_POOL,
            genre_mix=mix, genre_boost_table=BASS_GENRE_BOOST,
            composition_archetype=arch, mood=mood, energy_level=energy,
            field="bass", recent=recent,
        )
        harmony_audit = weighted_pick_audited(
            generation_seed, 13 + salt_off, harmony_candidates, tuple(HARMONY_POOL),
            genre_mix=mix, genre_boost_table=HARMONY_GENRE_BOOST,
            composition_archetype=arch, mood=mood, energy_level=energy,
            field="harmony", recent=recent,
        )
        drum_pattern = drum_audit.chosen
        bass_pattern = bass_audit.chosen
        harmony_pool = harmony_audit.chosen
        if audit is not None:
            audit.fields = [drum_audit, bass_audit, harmony_audit]
        if not combo_in_recent_window(
            drum=drum_pattern, bass=bass_pattern, harmony=harmony_pool,
        ):
            break

    if audit is not None:
        audit.combo_attempt = combo_attempt
        audit.combo_avoided_recent = combo_attempt > 0
        audit.rhythm_combo = rhythm_combo_signature(
            drum_pattern, bass_pattern, harmony_pool,
        )

    def _layer_pick(salt: int, cands: list[str], pool: tuple[str, ...] | list[str], table, fld: str) -> str:
        if audit is not None:
            fa = weighted_pick_audited(
                generation_seed, salt, cands, pool,
                genre_mix=mix, genre_boost_table=table,
                composition_archetype=arch, mood=mood, energy_level=energy,
                field=fld, recent=recent,
            )
            audit.fields.append(fa)
            return fa.chosen
        from cadence.music.pattern_selection import weighted_pick
        return weighted_pick(
            generation_seed, salt, cands, pool,
            genre_mix=mix, genre_boost_table=table,
            composition_archetype=arch, mood=mood, energy_level=energy,
            field=fld, recent=recent,
        )

    arp_cands = layer_bias.get("arp_candidates")
    if not isinstance(arp_cands, list):
        arp_cands = list(ARP_PATTERNS)
    arp_pattern = _layer_pick(17, arp_cands, ARP_PATTERNS, ARP_GENRE_BOOST, "arp")

    stab_cands = layer_bias.get("stab_candidates")
    if not isinstance(stab_cands, list):
        stab_cands = list(STAB_PATTERN_POOL)
    stab_pattern = _layer_pick(19, stab_cands, STAB_PATTERN_POOL, STAB_GENRE_BOOST, "stab")

    perc_cands = layer_bias.get("perc_candidates")
    if not isinstance(perc_cands, list):
        perc_cands = list(PERC_PATTERN_POOL)
    perc_pattern = _layer_pick(23, perc_cands, PERC_PATTERN_POOL, PERC_GENRE_BOOST, "perc")

    pluck_cands = layer_bias.get("pluck_candidates")
    if not isinstance(pluck_cands, list):
        pluck_cands = list(PLUCK_PATTERN_POOL)
    pluck_pattern = _layer_pick(29, pluck_cands, PLUCK_PATTERN_POOL, PLUCK_GENRE_BOOST, "pluck")

    counter_cands = layer_bias.get("counter_candidates")
    if not isinstance(counter_cands, list):
        counter_cands = list(COUNTER_PATTERN_POOL)
    counter_pattern = _layer_pick(
        37, counter_cands, COUNTER_PATTERN_POOL, COUNTER_GENRE_BOOST, "counter",
    )

    echo_source = layer_bias.get("echo_source", "auto")
    if echo_source not in ECHO_SOURCE_POOL:
        echo_source = "auto"

    record_strategy_patterns(
        drum=drum_pattern, bass=bass_pattern, harmony=harmony_pool,
    )

    return GenerationStrategies(
        generation_seed=generation_seed,
        drum_pattern=drum_pattern,
        bass_pattern=bass_pattern,
        harmony_pool=harmony_pool,
        arp_pattern=arp_pattern,
        stab_pattern=stab_pattern,
        perc_pattern=perc_pattern,
        pluck_pattern=pluck_pattern,
        counter_pattern=counter_pattern,
        echo_source=echo_source,
    )


def get_drum_pattern(pattern_id: str) -> dict[str, list[int]]:
    from cadence.music.pattern_registry import resolve_pattern_id

    rid = resolve_pattern_id(pattern_id, DRUM_PATTERN_ALIASES, default="default_a")
    return DRUM_PATTERNS.get(rid, DRUM_PATTERNS["default_a"])


def get_bass_pattern(pattern_id: str) -> list[BassStep]:
    from cadence.music.pattern_registry import resolve_pattern_id

    rid = resolve_pattern_id(pattern_id, BASS_PATTERN_ALIASES, default="root_fifth_a")
    return BASS_PATTERNS.get(rid, BASS_PATTERNS["root_fifth_a"])


def pattern_id_in_pool(pattern_id: str, pool: list[str], aliases: dict[str, str]) -> bool:
    from cadence.music.pattern_registry import resolve_pattern_id

    if pattern_id in pool:
        return True
    return resolve_pattern_id(pattern_id, aliases, default="") in pool


def resolve_rhythm_patterns(
    drum_pattern: str,
    bass_pattern: str,
    *,
    genre_tags: list[str],
    energy_level: int,
    use_case: str,
    generation_seed: int = 0,
    composition_archetype: str | None = None,
) -> tuple[str, str]:
    """Valida elección del agente; fallback ponderado si el id no es válido."""
    from cadence.music.pattern_batch_context import get_batch_recent_patterns

    recent = get_batch_recent_patterns()
    arch = composition_archetype
    from cadence.music.genre_pattern_affinity import BASS_GENRE_BOOST, DRUM_GENRE_BOOST
    from cadence.music.pattern_selection import weighted_pick

    drum = drum_pattern if pattern_id_in_pool(
        drum_pattern, DRUM_POOL, DRUM_PATTERN_ALIASES,
    ) else None
    bass = bass_pattern if pattern_id_in_pool(
        bass_pattern, BASS_POOL, BASS_PATTERN_ALIASES,
    ) else None

    from cadence.music.repertoire_signals import bass_pool_priority, drum_pool_priority
    from cadence.music.rhythm_fallback_ladders import (
        build_genre_mix_for_rhythm,
        fallback_bass_candidates,
        fallback_drum_candidates,
        resolve_rhythm_context_key,
    )

    genre_mix = build_genre_mix_for_rhythm(genre_tags)
    rhythm_key = resolve_rhythm_context_key(
        use_case=use_case,
        energy_level=energy_level,
        composition_archetype=arch,
        genre_tags=genre_tags,
        genre_mix=genre_mix,
    )
    strict_ladder = rhythm_key in ("loop", "cutscene", "game_low")

    if drum is None:
        rep = drum_pool_priority(
            energy_level, use_case, composition_archetype=arch,
        )
        candidates = fallback_drum_candidates(
            use_case=use_case,
            energy_level=energy_level,
            composition_archetype=arch,
            genre_tags=genre_tags,
            genre_mix=genre_mix,
            repertoire_priority=rep,
        )
        if strict_ladder and candidates:
            drum = candidates[generation_seed % len(candidates)]
        else:
            drum = weighted_pick(
                generation_seed, 3, candidates, DRUM_POOL,
                genre_mix=genre_mix,
                genre_boost_table=DRUM_GENRE_BOOST,
                composition_archetype=arch, energy_level=energy_level,
                field="drum", recent=recent,
            )

    if bass is None:
        rep = bass_pool_priority(
            energy_level, use_case, composition_archetype=arch,
        )
        candidates = fallback_bass_candidates(
            use_case=use_case,
            energy_level=energy_level,
            composition_archetype=arch,
            genre_tags=genre_tags,
            genre_mix=genre_mix,
            repertoire_priority=rep,
        )
        if strict_ladder and candidates:
            bass = candidates[generation_seed % len(candidates)]
        else:
            bass = weighted_pick(
                generation_seed, 7, candidates, BASS_POOL,
                genre_mix=genre_mix,
                genre_boost_table=BASS_GENRE_BOOST,
                composition_archetype=arch, energy_level=energy_level,
                field="bass", recent=recent,
            )

    return drum, bass


def get_harmony_templates(mode: str, pool_id: str) -> dict:
    from cadence.music.scale_theory import harmony_template_key

    pools = (
        HARMONY_POOLS_MINOR
        if harmony_template_key(mode) == "minor"
        else HARMONY_POOLS_MAJOR
    )
    return pools.get(pool_id, pools["classic"])


def resolve_harmony_pool(
    pool_id: str | None,
    generation_seed: int = 0,
    *,
    energy_level: int = 3,
    use_case: str = "game",
    composition_archetype: str | None = None,
) -> str:
    if pool_id and pool_id in HARMONY_POOL:
        return pool_id
    from cadence.music.pattern_batch_context import get_batch_recent_patterns

    candidates = harmony_pool_priority(
        energy_level, use_case, composition_archetype=composition_archetype,
    )
    return _weighted_pick(
        candidates, tuple(HARMONY_POOL), generation_seed, 13,
        field="harmony", recent=get_batch_recent_patterns(),
    )
