"""Programación bar-a-bar de capas activas."""

from cadence.schemas.song_state import LayerSchedule, LayerScheduleEntry, SongStructure

CORE_LAYERS = frozenset({"drums", "bass", "melody"})
SCHEDULED_OPTIONAL = frozenset({
    "pad", "perc_aux", "countermelody", "echo_synth", "arp_synth", "fx_riser",
})


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


def build_layer_schedule(
    structure: SongStructure,
    layer_ids: list[str],
    narrative_sections: dict | None,
    generation_seed: int = 0,
) -> LayerSchedule:
    """
    Construye entradas/salidas de capas a lo largo de la pieza.
    Inspirado en arreglos tipo Pizza Time: capas entran y salen en el tiempo.
    """
    available = set(layer_ids)
    entries: list[LayerScheduleEntry] = []
    active: set[str] = set(CORE_LAYERS) & available
    intent_map = narrative_sections or {}

    global_bar = 0
    total_bars = structure.total_bars or sum(structure.bars_per_section.values())
    climax_bar = int(total_bars * 0.55) + (generation_seed % 4)

    for section_id in structure.sections:
        bars = structure.bars_per_section.get(section_id, 4)
        intent = intent_map.get(section_id)
        density = intent.density if intent else 0.5
        role = intent.narrative_role if intent else "establish"

        to_add: list[str] = []
        to_remove: list[str] = []

        if density >= 0.25 and "pad" in available and "pad" not in active:
            to_add.append("pad")

        if (
            density >= 0.55
            and role in ("tension", "climax", "transition")
            and "perc_aux" in available
            and "perc_aux" not in active
        ):
            to_add.append("perc_aux")

        if (
            density >= 0.55
            and role in ("tension", "climax")
            and "countermelody" in available
            and "countermelody" not in active
        ):
            to_add.append("countermelody")

        if (
            role == "climax"
            and density >= 0.65
            and "echo_synth" in available
            and "echo_synth" not in active
        ):
            to_add.append("echo_synth")
        elif (
            global_bar >= climax_bar - 4
            and density >= 0.65
            and "echo_synth" in available
            and "echo_synth" not in active
        ):
            to_add.append("echo_synth")

        if (
            density >= 0.7
            and role in ("tension", "climax", "transition")
            and "arp_synth" in available
            and "arp_synth" not in active
        ):
            to_add.append("arp_synth")

        if role in ("reflection", "silence") or density < 0.25:
            for lid in ("perc_aux", "countermelody", "echo_synth", "arp_synth"):
                if lid in active:
                    to_remove.append(lid)

        if role in ("release",) or section_id == "outro":
            for lid in ("echo_synth", "perc_aux", "countermelody", "arp_synth"):
                if lid in active:
                    to_remove.append(lid)
            if density < 0.35 and "pad" in active:
                to_remove.append("pad")

        if to_add or to_remove:
            entries.append(LayerScheduleEntry(
                bar=global_bar,
                add=to_add,
                remove=to_remove,
            ))
            active.update(to_add)
            for lid in to_remove:
                active.discard(lid)

        global_bar += bars

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
