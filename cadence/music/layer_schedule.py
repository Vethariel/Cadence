"""Programación bar-a-bar de capas activas."""

from collections import defaultdict

from cadence.schemas.song_state import LayerSchedule, LayerScheduleEntry, SongStructure

CORE_LAYERS = frozenset({"drums", "bass", "melody"})
SCHEDULED_OPTIONAL = frozenset({
    "pad", "perc_aux", "countermelody", "echo_synth", "arp_synth",
    "fx_riser", "chord_stab", "synth_pluck",
})

# Umbrales de densidad narrativa (PR A — orquestación más densa)
DENSITY_PAD = 0.25
DENSITY_CHORD_STAB = 0.45
DENSITY_PERC = 0.45
DENSITY_COUNTER = 0.45
DENSITY_ECHO = 0.55
DENSITY_ARP = 0.60
DENSITY_PLUCK = 0.50

# Entrada escalonada dentro de cada sección (compases desde el inicio)
LAYER_STAGGER: dict[str, int] = {
    "pad": 0,
    "chord_stab": 1,
    "synth_pluck": 1,
    "perc_aux": 1,
    "countermelody": 2,
    "echo_synth": 2,
    "arp_synth": 4,
}

HIGH_ENERGY_SECTIONS = frozenset({
    "drop", "climax", "chorus", "build-up", "buildup", "verse", "bridge",
})
FX_TRANSITIONS = frozenset({"riser", "filter_sweep", "pickup"})

# En climax las capas entran antes; en tension/build-up se escalonan más
CLIMAX_STAGGER: dict[str, int] = {
    "pad": 0,
    "chord_stab": 0,
    "synth_pluck": 0,
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


def _layer_thresholds(genre_adj: dict[str, float]) -> dict[str, float]:
    return {
        "pad": genre_adj.get("pad", DENSITY_PAD),
        "chord_stab": genre_adj.get("chord_stab", DENSITY_CHORD_STAB),
        "perc": genre_adj.get("perc", DENSITY_PERC),
        "counter": genre_adj.get("counter", DENSITY_COUNTER),
        "echo": genre_adj.get("echo", DENSITY_ECHO),
        "arp": genre_adj.get("arp", DENSITY_ARP),
        "pluck": genre_adj.get("pluck", DENSITY_PLUCK),
    }


def _plan_section_layers(
    *,
    density: float,
    role: str,
    section_id: str,
    global_bar: int,
    climax_bar: int,
    available: set[str],
    active: set[str],
    thresholds: dict[str, float] | None = None,
) -> tuple[list[str], list[str]]:
    """Capas a quitar al inicio de sección y capas a añadir (stagger vía _entry_stagger)."""
    th = thresholds or _layer_thresholds({})
    to_remove: list[str] = []
    to_add: list[str] = []

    if role in ("reflection", "silence") or density < th["pad"]:
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

    if density >= th["pad"] and "pad" in available and "pad" not in active:
        candidates.append("pad")

    if (
        density >= th["chord_stab"]
        and "chord_stab" in available
        and "chord_stab" not in active
    ):
        candidates.append("chord_stab")

    if (
        density >= th["perc"]
        and role in ("tension", "climax", "transition")
        and section_id in HIGH_ENERGY_SECTIONS
        and "perc_aux" in available
        and "perc_aux" not in active
    ):
        candidates.append("perc_aux")

    if (
        density >= th["counter"]
        and role in ("tension", "climax", "establish")
        and "countermelody" in available
        and "countermelody" not in active
    ):
        candidates.append("countermelody")

    if "echo_synth" in available and "echo_synth" not in active:
        if role == "climax" and density >= th["echo"]:
            candidates.append("echo_synth")
        elif global_bar >= climax_bar - 4 and density >= th["echo"]:
            candidates.append("echo_synth")

    if (
        density >= th["arp"]
        and role in ("tension", "climax", "transition")
        and "arp_synth" in available
        and "arp_synth" not in active
    ):
        candidates.append("arp_synth")

    if (
        density >= th["pluck"]
        and role in ("tension", "climax", "establish")
        and section_id in HIGH_ENERGY_SECTIONS
        and "synth_pluck" in available
        and "synth_pluck" not in active
    ):
        candidates.append("synth_pluck")

    return to_remove, candidates


def _density_thresholds_for_piece(
    energy_level: int,
    use_case: str | None,
) -> dict[str, float]:
    from cadence.music.repertoire_signals import schedule_density_thresholds

    return schedule_density_thresholds(energy_level, use_case or "game")


def build_layer_schedule(
    structure: SongStructure,
    layer_ids: list[str],
    narrative_sections: dict | None,
    generation_seed: int = 0,
    genre_tags: list[str] | None = None,
    energy_level: int = 3,
    use_case: str = "game",
) -> LayerSchedule:
    """
    Construye entradas/salidas de capas a lo largo de la pieza.
    Las capas opcionales entran escalonadas dentro de cada sección.
    """
    available = set(layer_ids)
    intent_map = narrative_sections or {}
    active: set[str] = set(CORE_LAYERS) & available
    del genre_tags  # compatibilidad; umbrales por energía/rol
    genre_adj = _density_thresholds_for_piece(energy_level, use_case)
    thresholds = _layer_thresholds(genre_adj)

    global_bar = 0
    total_bars = structure.total_bars or sum(structure.bars_per_section.values())
    climax_ratio = 0.50 if energy_level >= 5 else 0.55
    climax_bar = int(total_bars * climax_ratio) + (generation_seed % 4)

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
            thresholds=thresholds,
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

        transition_out = getattr(intent, "transition_out", None) if intent else None
        if (
            transition_out in FX_TRANSITIONS
            and "fx_riser" in available
        ):
            last_bar = max(global_bar, section_end - 1)
            pending.append((last_bar, "add", "fx_riser"))
            pending.append((section_end, "remove", "fx_riser"))
            active.discard("fx_riser")

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
