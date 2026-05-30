"""
Familias de instrumento duplicables (maderas, teclas, cuerdas, guitarras, metal).

Aplica cuando el estilo lo justifica — orquestal, cinematic, folk, jazz, boss, híbrido —
sin excluir game/dance/techno si los tags o la energía piden riqueza de conjunto.
"""

from __future__ import annotations

from cadence.schemas.song_state import InstrumentAssignment, SectionIntent

# IDs registrados en cadence.instruments.ensemble_voices
ENSEMBLE_INSTRUMENT_IDS: frozenset[str] = frozenset({
    "woodwind_a",
    "woodwind_b",
    "keys_piano",
    "keys_organ",
    "strings_ensemble",
    "guitar_acoustic",
    "guitar_electric",
    "brass_a",
})

# Capa genérica que sustituye la familia ensemble (evita dos guitarras pluck, etc.)
ENSEMBLE_REPLACES_OPTIONAL: dict[str, str] = {
    "guitar_acoustic": "synth_pluck",
    "guitar_electric": "echo_synth",
    "brass_a": "chord_stab",
}

ORCHESTRAL_TAG_TOKENS = frozenset({
    "orchestral", "orquesta", "symphonic", "symphony", "cinematic", "epic",
    "hybrid orchestral", "boss fight", "boss", "film", "trailer", "strings",
    "brass", "woodwind", "flute", "choir",
})

FOLK_JAZZ_TAG_TOKENS = frozenset({
    "folk", "acoustic", "jazz", "country", "bluegrass", "spanish", "flamenco",
    "nylon", "guitar", "piano", "organ", "church",
})

DANCE_ELECTRONIC_TAGS = frozenset({
    "techno", "house", "trance", "edm", "dubstep", "electro", "synthwave",
})


def _tags_lower(genre_tags: list[str] | None) -> set[str]:
    if not genre_tags:
        return set()
    out: set[str] = set()
    for t in genre_tags:
        low = t.lower().strip()
        out.add(low)
        for part in low.replace("-", " ").split():
            if len(part) > 2:
                out.add(part)
    return out


def _tag_overlap(tags: set[str], vocab: frozenset[str]) -> float:
    if not tags:
        return 0.0
    hits = sum(1 for v in vocab if any(v in t or t in v for t in tags))
    return min(1.0, hits / max(2, len(vocab) * 0.15))


def ensemble_score(
    *,
    genre_tags: list[str] | None,
    composition_archetype: str | None,
    use_case: str,
    energy_level: int,
    genre_mix: dict[str, float] | None = None,
) -> float:
    """0–1: conveniencia de activar familias ensemble."""
    tags = _tags_lower(genre_tags)
    arch = (composition_archetype or "").lower()
    uc = (use_case or "game").lower()

    score = 0.0
    orch = _tag_overlap(tags, ORCHESTRAL_TAG_TOKENS)
    folk = _tag_overlap(tags, FOLK_JAZZ_TAG_TOKENS)
    dance = _tag_overlap(tags, DANCE_ELECTRONIC_TAGS)

    if arch in ("orchestral_boss", "cinematic_cutscene"):
        score += 0.55
    if arch == "ambient_loop" and energy_level >= 3:
        score += 0.35
    if arch == "chiptune_dance" and orch >= 0.2:
        score += 0.4  # híbrido chiptune + orquesta

    score += orch * 0.45 + folk * 0.3

    if genre_mix:
        from cadence.music.genre_catalog import dominant_category

        dom = dominant_category(genre_mix)
        if dom in ("orchestral_cinematic", "jazz_blues_funk", "pop_world_folk"):
            score += 0.25

    if energy_level >= 4:
        score += 0.15
    elif energy_level >= 3:
        score += 0.08

    if uc in ("game", "animation", "cutscene"):
        score += 0.1
    if uc == "loop" and orch < 0.15:
        score *= 0.5

    # Techno puro sin señales orquestales/folk: no forzar ensemble
    if dance >= 0.35 and orch < 0.12 and folk < 0.12 and arch not in (
        "orchestral_boss", "cinematic_cutscene",
    ):
        score *= 0.45

    return min(1.0, score)


def ensemble_eligible(**kwargs) -> bool:
    return ensemble_score(**kwargs) >= 0.28


def max_ensemble_slots(
    energy_level: int,
    use_case: str,
    ensemble_score_value: float,
) -> int:
    uc = (use_case or "game").lower()
    base = 2
    if ensemble_score_value >= 0.55:
        base = 4
    elif ensemble_score_value >= 0.4:
        base = 3
    if energy_level >= 5:
        base += 1
    if energy_level >= 4 and uc in ("game", "animation"):
        base += 1
    if uc == "loop":
        base = min(base, 2)
    return min(6, max(1, base))


def select_ensemble_families(
    *,
    genre_tags: list[str] | None,
    composition_archetype: str | None,
    use_case: str,
    energy_level: int,
    generation_seed: int,
    genre_mix: dict[str, float] | None = None,
) -> set[str]:
    """Elige familias ensemble deterministas (coherentes con el estilo)."""
    if not ensemble_eligible(
        genre_tags=genre_tags,
        composition_archetype=composition_archetype,
        use_case=use_case,
        energy_level=energy_level,
        genre_mix=genre_mix,
    ):
        return set()

    tags = _tags_lower(genre_tags)
    arch = (composition_archetype or "").lower()
    score = ensemble_score(
        genre_tags=genre_tags,
        composition_archetype=composition_archetype,
        use_case=use_case,
        energy_level=energy_level,
        genre_mix=genre_mix,
    )
    n = max_ensemble_slots(energy_level, use_case, score)
    seed = generation_seed % 9973

    orch = _tag_overlap(tags, ORCHESTRAL_TAG_TOKENS)
    folk = _tag_overlap(tags, FOLK_JAZZ_TAG_TOKENS)

    priority: list[str] = []
    if orch >= 0.15 or arch == "orchestral_boss":
        priority.extend(["strings_ensemble", "woodwind_a", "keys_piano", "brass_a"])
    if folk >= 0.15 or arch == "cinematic_cutscene":
        priority.extend(["keys_piano", "guitar_acoustic", "woodwind_a"])
    if any(t in tags for t in ("organ", "church", "gothic", "cathedral")) or arch == "cinematic_cutscene":
        priority.append("keys_organ")
    if folk >= 0.2 or any(t in tags for t in ("rock", "metal", "distortion")):
        priority.append("guitar_electric")
    if n >= 3 and (orch >= 0.2 or energy_level >= 4):
        priority.append("woodwind_b")
    if n >= 4:
        priority.extend(["keys_organ", "guitar_acoustic"])
    if n >= 5 and orch >= 0.25:
        priority.append("brass_a")

    # Defaults si la lista quedó vacía pero somos elegibles
    if not priority:
        priority = ["keys_piano", "woodwind_a", "strings_ensemble"]

    seen: list[str] = []
    for i, pid in enumerate(priority):
        if pid in seen:
            continue
        if (seed + i * 17 + hash(pid)) % 5 == 0 and len(seen) >= n:
            continue
        seen.append(pid)
        if len(seen) >= n:
            break

    if len(seen) < min(2, n):
        for fallback in ("keys_piano", "strings_ensemble", "woodwind_a"):
            if fallback not in seen:
                seen.append(fallback)
            if len(seen) >= n:
                break

    return set(seen) & ENSEMBLE_INSTRUMENT_IDS


def resolve_ensemble_conflicts(chosen: set[str]) -> set[str]:
    """Quita capas genéricas sustituidas por una familia ensemble."""
    out = set(chosen)
    for ens, generic in ENSEMBLE_REPLACES_OPTIONAL.items():
        if ens in out and generic in out:
            out.discard(generic)
    return out


def ensemble_optional_budget_bonus(ensemble_score_value: float) -> tuple[int, int]:
    """(extra_optionals, extra_leads) cuando hay ensemble."""
    if ensemble_score_value < 0.28:
        return 0, 0
    if ensemble_score_value >= 0.55:
        return 2, 2
    if ensemble_score_value >= 0.4:
        return 1, 1
    return 1, 0


def inject_ensemble_into_assignments(
    by_id: dict[str, InstrumentAssignment],
    *,
    genre_tags: list[str] | None,
    composition_archetype: str | None,
    use_case: str,
    energy_level: int,
    generation_seed: int,
    timbre_context: dict,
    genre_mix: dict[str, float] | None = None,
) -> dict[str, InstrumentAssignment]:
    """Añade InstrumentAssignment por familia si el estilo lo pide."""
    from cadence.music.instrument_catalog import _assignment_from_timbre

    families = select_ensemble_families(
        genre_tags=genre_tags,
        composition_archetype=composition_archetype,
        use_case=use_case,
        energy_level=energy_level,
        generation_seed=generation_seed,
        genre_mix=genre_mix,
    )
    if not families:
        return by_id

    default_mix = {
        "woodwind_a": -12.0,
        "woodwind_b": -14.0,
        "keys_piano": -10.0,
        "keys_organ": -16.0,
        "strings_ensemble": -14.0,
        "guitar_acoustic": -11.0,
        "guitar_electric": -12.0,
        "brass_a": -10.0,
    }
    for iid in sorted(families):
        if iid in by_id:
            continue
        by_id[iid] = _assignment_from_timbre(
            InstrumentAssignment(
                instrument_id=iid,
                gm_program=0,
                mix_level=default_mix.get(iid, -12.0),
                active=True,
            ),
            generation_seed=generation_seed,
            default_mix=default_mix.get(iid, -12.0),
            timbre_context=timbre_context,
        )
    return by_id


def ensemble_min_density(instrument_id: str) -> float:
    return {
        "keys_organ": 0.28,
        "strings_ensemble": 0.32,
        "pad": 0.25,
    }.get(instrument_id, 0.42)


def format_ensemble_hint_for_llm(
    *,
    genre_tags: list[str] | None,
    composition_archetype: str | None,
    use_case: str,
    energy_level: int,
) -> str:
    if not ensemble_eligible(
        genre_tags=genre_tags,
        composition_archetype=composition_archetype,
        use_case=use_case,
        energy_level=energy_level,
    ):
        return ""
    ids = ", ".join(sorted(ENSEMBLE_INSTRUMENT_IDS))
    return (
        f"\nFamilias ensemble (opcionales, activa 2–4 coherentes con el estilo): {ids}.\n"
        "Puedes combinar p. ej. woodwind_a + woodwind_b (dos maderas), "
        "keys_piano + keys_organ, guitar_acoustic + guitar_electric.\n"
        "No sustituyas drums/bass/melody. Asigna gm_program distinto por familia.\n"
    )
