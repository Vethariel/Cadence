"""Capas y umbrales mínimos para arquetipo orchestral_boss."""

from __future__ import annotations

ORCHESTRAL_BOSS_MANDATORY = frozenset({
    "pad",
    "chord_stab",
    "countermelody",
    "arp_synth",
})

ORCHESTRAL_BOSS_REPAIR_LAYERS = frozenset({
    "pad",
    "chord_stab",
    "countermelody",
    "arp_synth",
    "synth_pluck",
    "perc_aux",
})


def orchestral_boss_active(energy_level: int, *, min_energy: int = 4) -> bool:
    return energy_level >= min_energy


def apply_orchestral_boss_instruments(chosen: set[str], energy_level: int) -> set[str]:
    """Garantiza cama armónica y contramelodía en boss orquestal."""
    if not orchestral_boss_active(energy_level):
        return chosen
    return set(chosen) | ORCHESTRAL_BOSS_MANDATORY


def orchestral_density_threshold(base: float, energy_level: int) -> float:
    """Umbrales más bajos para activar pads/stabs en secciones medias-altas."""
    if energy_level >= 5:
        return max(0.18, base - 0.12)
    if energy_level >= 4:
        return max(0.22, base - 0.08)
    return base


def orchestral_repair_layer_ids() -> list[str]:
    return sorted(ORCHESTRAL_BOSS_REPAIR_LAYERS)
