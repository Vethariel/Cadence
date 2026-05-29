"""Programación bar-a-bar de capas activas."""

from collections import defaultdict

from cadence.schemas.song_state import LayerSchedule, LayerScheduleEntry, SongStructure

CORE_LAYERS = frozenset({"drums", "bass", "melody"})
SCHEDULED_OPTIONAL = frozenset({
    "pad", "perc_aux", "countermelody", "echo_synth", "arp_synth", "fx_riser", "chord_stab",
})

# Umbrales de densidad narrativa (PR A — orquestación más densa)
DENSITY_PAD = 0.25
DENSITY_CHORD_STAB = 0.45
DENSITY_PERC = 0.45
DENSITY_COUNTER = 0.45
DENSITY_ECHO = 0.55
DENSITY_ARP = 0.60

# Entrada escalonada dentro de cada sección (compases desde el inicio)
LAYER_STAGGER: dict[str, int] = {
    "pad": 0,
    "chord_stab": 1,
    "perc_aux": 1,
    "countermelody": 2,
    "echo_synth": 2,
    "arp_synth": 4,
}

HIGH_ENERGY_SECTIONS = frozenset({"drop", "climax", "chorus", "build-up", "verse"})

# En climax las capas entran antes; en tension/build-up se escalonan más
CLIMAX_STAGGER: dict[str, int] = {
    "pad": 0,
    "chord_stab": 0,
    "perc_aux": 0,
    "countermelody": 0,
    "echo_synth": 0,
    "arp_synth": 1,
}


def _entry_stagger(layer_id: str, role: str) -> int:
    if role == "climax":
        return CLIMAX_STAGGER.get(layer_id, LAYER_STAGGER.get(layer_id, 0))
    return LAYER_STAGGER.get(layer_id, 0)


def ms_per_bar(bpm: int) -> float:
    return (60000 / bpm) * 4


def global_bar_from_ms(t_ms: int, bpm: int) -> int:
    return int(t_ms // ms_per_bar(bpm))


def section_start_bars(structure: SongStructure) -> dict[str, int]:
    """Compás global de inicio por sección."""
    starts: dict[str, int] = {}
    cursor = 0
    for section in structure.sections:
        starts[section] = cursor
        cursor += structure.bars_per_section.get(section, 4)
    return starts


def active_layers_at_bar(
    schedule: LayerSchedule,
    global_bar: int,
    available_layers: set[str],
) -> set[str]:
    """Capas activas en un compás dado, replay de entries."""
    active = set(schedule.core_layers) & available_layers
    for entry in sorted(schedule.entries, key=lambda e: e.bar):
        if entry.bar > global_bar:
            break
        for lid in entry.remove:
            active.discard(lid)
        for lid in entry.add:
            if lid in available_layers:
                active.add(lid)
    return active


def _plan_section_layers(
    *,
    density: float,
    role: str,
    section_id: str,
    global_bar: int,
    climax_bar: int,
    available: set[str],
    active: set[str],
) -> tuple[list[str], list[str]]:
    """Capas a quitar al inicio de sección y capas a añadir (stagger vía _entry_stagger)."""
    to_remove: list[str] = []
    to_add: list[str] = []

    if role in ("reflection", "silence") or density < DENSITY_PAD:
        for lid in ("perc_aux", "countermelody", "echo_synth", "arp_synth", "chord_stab"):
            if lid in active:
                to_remove.append(lid)

    if role in ("release",) or section_id == "outro":
        for lid in ("echo_synth", "perc_aux", "countermelody", "arp_synth", "chord_stab"):
            if lid in active:
                to_remove.append(lid)
        if density < 0.35 and "pad" in active:
            to_remove.append("pad")

    candidates: list[str] = []

    if density >= DENSITY_PAD and "pad" in available and "pad" not in active:
        candidates.append("pad")

    if (
        density >= DENSITY_CHORD_STAB
        and "chord_stab" in available
        and "chord_stab" not in active
    ):
        candidates.append("chord_stab")

    if (
        density >= DENSITY_PERC
        and role in ("tension", "climax", "transition")
        and section_id in HIGH_ENERGY_SECTIONS
        and "perc_aux" in available
        and "perc_aux" not in active
    ):
        candidates.append("perc_aux")

    if (
        density >= DENSITY_COUNTER
        and role in ("tension", "climax")
        and "countermelody" in available
        and "countermelody" not in active
    ):
        candidates.append("countermelody")

    if "echo_synth" in available and "echo_synth" not in active:
        if role == "climax" and density >= DENSITY_ECHO:
            candidates.append("echo_synth")
        elif global_bar >= climax_bar - 4 and density >= DENSITY_ECHO:
            candidates.append("echo_synth")

    if (
        density >= DENSITY_ARP
        and role in ("tension", "climax", "transition")
        and "arp_synth" in available
        and "arp_synth" not in active
    ):
        candidates.append("arp_synth")

    return to_remove, candidates


def build_layer_schedule(
    structure: SongStructure,
    layer_ids: list[str],
    narrative_sections: dict | None,
    generation_seed: int = 0,
) -> LayerSchedule:
    """
    Construye entradas/salidas de capas a lo largo de la pieza.
    Las capas opcionales entran escalonadas dentro de cada sección.
    """
    available = set(layer_ids)
    intent_map = narrative_sections or {}
    active: set[str] = set(CORE_LAYERS) & available

    global_bar = 0
    total_bars = structure.total_bars or sum(structure.bars_per_section.values())
    climax_bar = int(total_bars * 0.55) + (generation_seed % 4)

    pending: list[tuple[int, str, str]] = []

    for section_id in structure.sections:
        bars = structure.bars_per_section.get(section_id, 4)
        intent = intent_map.get(section_id)
        density = intent.density if intent else 0.5
        role = intent.narrative_role if intent else "establish"

        to_remove, candidates = _plan_section_layers(
            density=density,
            role=role,
            section_id=section_id,
            global_bar=global_bar,
            climax_bar=climax_bar,
            available=available,
            active=active,
        )

        section_end = global_bar + bars
        for lid in to_remove:
            pending.append((global_bar, "remove", lid))
            active.discard(lid)

        for lid in candidates:
            entry_bar = min(
                global_bar + _entry_stagger(lid, role),
                max(global_bar, section_end - 1),
            )
            pending.append((entry_bar, "add", lid))
            active.add(lid)

        global_bar += bars

    by_bar: dict[int, dict[str, list[str]]] = defaultdict(lambda: {"add": [], "remove": []})
    for bar, action, lid in sorted(pending, key=lambda x: (x[0], x[1] == "add")):
        by_bar[bar][action].append(lid)

    entries = [
        LayerScheduleEntry(bar=bar, add=ops["add"], remove=ops["remove"])
        for bar, ops in sorted(by_bar.items())
        if ops["add"] or ops["remove"]
    ]

    return LayerSchedule(
        entries=entries,
        core_layers=[l for l in schedule_core_list() if l in available],
    )


def schedule_core_list() -> list[str]:
    return list(CORE_LAYERS)


def filter_events_by_schedule(
    events: list,
    instrument_id: str,
    schedule: LayerSchedule | None,
    bpm: int,
    available_layers: set[str],
) -> list:
    """Elimina eventos en compases donde la capa no está activa."""
    if not schedule or instrument_id in schedule.core_layers:
        return events
    if instrument_id not in SCHEDULED_OPTIONAL:
        return events

    filtered = []
    for e in events:
        gbar = global_bar_from_ms(e.t, bpm)
        if instrument_id in active_layers_at_bar(schedule, gbar, available_layers):
            filtered.append(e)
    return filtered
