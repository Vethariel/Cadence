"""
Orquestación espaciada — capas por sección, exclusión mutua y silencios.

Evita que arp, contramelodía y eco suenen a la vez en toda la pieza;
asigna instrumentos solo a secciones narrativas concretas.
"""

from __future__ import annotations

from cadence.schemas.song_state import RhythmEvent, SectionIntent, SongStructure

CLIMAX_ROLES = frozenset({"climax", "tension", "drop", "chorus"})
SPARSE_ROLES = frozenset({"silence", "reflection", "release"})
BUILD_ROLES = frozenset({"establish", "transition"})

ORCHESTRAL_STAGGER: dict[str, int] = {
    "pad": 0,
    "chord_stab": 2,
    "perc_aux": 2,
    "countermelody": 4,
    "echo_synth": 6,
    "arp_synth": 8,
    "synth_pluck": 4,
}

# Una sola capa de este grupo por sección (rotación por índice de sección)
ROTATING_SUPPORTS = ("countermelody", "arp_synth", "echo_synth")


def orchestral_stack_active(
    composition_archetype: str | None,
    energy_level: int = 3,
) -> bool:
    from cadence.music.composition_archetypes import normalize_archetype

    return normalize_archetype(composition_archetype) == "orchestral_boss" and energy_level >= 4


def effective_texture_mode_for_schedule(
    texture_mode: str,
    *,
    composition_archetype: str | None,
    energy_level: int,
) -> str:
    """Boss orquestal: staggered real (no todo en bar 0)."""
    if orchestral_stack_active(composition_archetype, energy_level):
        if texture_mode == "simultaneous":
            return "staggered"
    return texture_mode


def schedule_thresholds_orchestral(
    base: dict[str, float],
    energy_level: int,
) -> dict[str, float]:
    """Sube umbrales de arp/counter para que no entren en todas las secciones."""
    from cadence.music.layer_schedule import (
        DENSITY_ARP,
        DENSITY_CHORD_STAB,
        DENSITY_COUNTER,
        DENSITY_ECHO,
        DENSITY_PAD,
        DENSITY_PERC,
        DENSITY_PLUCK,
    )

    if not base:
        base = {
            "arp": DENSITY_ARP,
            "pad": DENSITY_PAD,
            "pluck": DENSITY_PLUCK,
            "counter": DENSITY_COUNTER,
            "chord_stab": DENSITY_CHORD_STAB,
            "perc": DENSITY_PERC,
            "echo": DENSITY_ECHO,
        }
    bump = 0.14 if energy_level >= 5 else 0.10
    return {
        **base,
        "arp": min(0.92, base.get("arp", 0.55) + bump),
        "counter": min(0.88, base.get("counter", 0.45) + bump * 0.8),
        "echo": max(0.38, base.get("echo", 0.45) - 0.06),
        "chord_stab": max(0.28, base.get("chord_stab", 0.42) - 0.06),
    }


def entry_stagger_orchestral(layer_id: str, narrative_role: str) -> int:
    if narrative_role == "climax":
        return max(0, ORCHESTRAL_STAGGER.get(layer_id, 2) - 1)
    if narrative_role in SPARSE_ROLES:
        return ORCHESTRAL_STAGGER.get(layer_id, 4)
    return ORCHESTRAL_STAGGER.get(layer_id, 2)


def rotating_support_for_section(
    section_index: int,
    role: str,
    *,
    chosen: set[str],
) -> str | None:
    """Elige como mucho un soporte lead rotatorio por sección."""
    if role not in CLIMAX_ROLES and role not in BUILD_ROLES:
        return None
    pool = [lid for lid in ROTATING_SUPPORTS if lid in chosen]
    if not pool:
        return None
    if role in SPARSE_ROLES:
        return None
    if role in BUILD_ROLES:
        return pool[section_index % len(pool)] if role == "establish" else None
    # climax/tension: alternar counter vs arp
    if "countermelody" in pool and "arp_synth" in pool:
        return "countermelody" if section_index % 2 == 0 else "arp_synth"
    return pool[section_index % len(pool)]


def assign_orchestral_layer_sections(
    structure: SongStructure,
    intent_map: dict[str, SectionIntent],
    chosen: set[str],
    *,
    energy_level: int,
    pad_floor: float,
    stab_floor: float,
    counter_floor: float,
    arp_floor: float,
    echo_floor: float,
    perc_floor: float,
) -> dict[str, list[str]]:
    """
    Listas de section_id por capa opcional — sin pisarse en la misma sección.
    """
    pad_sections: list[str] = []
    chord_stab_sections: list[str] = []
    perc_sections: list[str] = []
    counter_sections: list[str] = []
    echo_sections: list[str] = []
    arp_sections: list[str] = []
    pluck_sections: list[str] = []

    for idx, section_id in enumerate(structure.sections):
        intent = intent_map.get(section_id)
        density = intent.density if intent else 0.5
        role = intent.narrative_role if intent else "establish"

        if role in SPARSE_ROLES or density < 0.28:
            if density >= pad_floor * 0.8 and "pad" in chosen:
                pad_sections.append(section_id)
            continue

        if density >= pad_floor and "pad" in chosen:
            pad_sections.append(section_id)

        if density >= stab_floor and role in (*BUILD_ROLES, *CLIMAX_ROLES) and "chord_stab" in chosen:
            if role != "transition" or density >= 0.5:
                chord_stab_sections.append(section_id)

        if (
            density >= perc_floor
            and role in ("tension", "climax", "transition")
            and "perc_aux" in chosen
        ):
            perc_sections.append(section_id)

        rot = rotating_support_for_section(idx, role, chosen=chosen)
        if rot == "countermelody" and density >= counter_floor:
            counter_sections.append(section_id)
        elif rot == "arp_synth" and density >= arp_floor:
            arp_sections.append(section_id)
        elif rot == "echo_synth" and density >= echo_floor and role in (
            *CLIMAX_ROLES, "tension", "transition",
        ):
            echo_sections.append(section_id)

        if (
            rot is None
            and role in CLIMAX_ROLES
            and density >= counter_floor
            and "countermelody" in chosen
            and section_id not in counter_sections
            and section_id not in arp_sections
        ):
            if idx % 3 != 1 and density >= 0.62:
                counter_sections.append(section_id)

        if "synth_pluck" in chosen and role in CLIMAX_ROLES and density >= 0.55:
            if idx % 4 == 0:
                pluck_sections.append(section_id)

    return {
        "pad": pad_sections,
        "chord_stab": chord_stab_sections,
        "perc_aux": perc_sections,
        "countermelody": counter_sections,
        "echo_synth": echo_sections,
        "arp_synth": arp_sections,
        "synth_pluck": pluck_sections,
    }


def segment_support_cap(
    *,
    composition_archetype: str | None,
    texture_mode: str,
    segment_index: int,
) -> int:
    if not orchestral_stack_active(composition_archetype):
        if texture_mode == "simultaneous":
            return 3 if segment_index >= 2 else 2
        if texture_mode == "compact":
            return 1
        return 2
    return 1 if segment_index == 0 else 2


def segment_layer_delta_orchestral(
    transform: str,
    *,
    available: set[str],
    segment_index: int,
    section_role: str,
) -> tuple[list[str], list[str]]:
    """Máximo 1–2 soportes por micro-arco; sin arp+counter juntos."""
    add: list[str] = []
    remove: list[str] = []

    sparse_like = transform in ("sparse", "fragment", "resolve", "pedal")
    dense_like = transform in ("climax", "augment", "call_response", "sequence_up")

    if sparse_like:
        for lid in ROTATING_SUPPORTS:
            if lid in available:
                remove.append(lid)
        return remove, add

    if not dense_like:
        if transform in ("expand", "introduce", "ostinato") and "pad" in available:
            add.append("pad")
        return remove, add

    cap = 2 if section_role == "climax" else 1
    order = ("pad", "chord_stab", "countermelody", "arp_synth", "echo_synth")
    for lid in order:
        if lid not in available:
            continue
        if lid in ROTATING_SUPPORTS and section_role in SPARSE_ROLES:
            continue
        if len(add) >= cap:
            break
        if lid == "arp_synth" and "countermelody" in add:
            continue
        if lid == "countermelody" and "arp_synth" in add:
            continue
        add.append(lid)

    add = list(dict.fromkeys(add))
    remove = [lid for lid in remove if lid not in add]
    return remove, add


def counter_skip_orchestral(
    step_index: int,
    transform: str,
    *,
    events_per_bar: int,
) -> bool:
    from cadence.music.layer_voice_variation import counter_skip_step

    if counter_skip_step(
        step_index, transform, texture_mode="staggered", events_per_bar=events_per_bar,
    ):
        return True
    if transform in ("sparse", "fragment", "pedal", "resolve"):
        return step_index % 2 == 1
    if events_per_bar > 4:
        return step_index % 2 == 1
    return step_index % 3 == 2


def arp_min_density_orchestral() -> float:
    return 0.72


def arp_stride_bonus_orchestral() -> int:
    """Más espacio entre notas de arp."""
    return 2


def apply_orchestral_melody_breaths(
    events: list[RhythmEvent],
    *,
    bpm: int,
    structure: SongStructure,
    intent_map: dict[str, SectionIntent],
    bars_per_rest: int = 2,
    time_signature: list[int] | None = None,
) -> list[RhythmEvent]:
    """
    Inserta compases de respiro al final de secciones sparse/reflection
    (quita notas en el último 25% de la sección si density < 0.45).
    """
    if not events:
        return events

    from cadence.music.meter_theory import ms_per_bar as meter_ms_per_bar

    bar_ms = meter_ms_per_bar(bpm, time_signature)
    from cadence.music.layer_schedule import section_start_bars

    starts = section_start_bars(structure)
    drop_ranges: list[tuple[int, int]] = []

    for section_id in structure.sections:
        intent = intent_map.get(section_id)
        if not intent:
            continue
        role = intent.narrative_role
        density = intent.density
        if role not in SPARSE_ROLES and density >= 0.45:
            continue
        start = starts.get(section_id, 0)
        bars = structure.bars_per_section.get(section_id, 4)
        rest_bars = min(bars_per_rest, max(1, bars // 4))
        if rest_bars <= 0:
            continue
        drop_start = (start + bars - rest_bars) * bar_ms
        drop_end = (start + bars) * bar_ms
        drop_ranges.append((int(drop_start), int(drop_end)))

    if not drop_ranges:
        return events

    kept: list[RhythmEvent] = []
    for e in events:
        if any(lo <= e.t < hi for lo, hi in drop_ranges):
            continue
        kept.append(e)
    return sorted(kept, key=lambda e: e.t)
