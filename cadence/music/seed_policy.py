"""
Política de aleatoriedad por solicitud — semilla raíz y subsemillas por nodo.

Alta variación: instrumentación fina, motivos secundarios, color melódico.
Baja variación: arco narrativo, secciones clave, tensión-release (nodos estructurales).
"""

from __future__ import annotations

from cadence.schemas.song_state import NodeSeeds

# Temperatura LLM por nodo (0 = determinista vía código, no LLM)
NODE_TEMPERATURE: dict[str, float] = {
    "router": 0.20,
    "tag_enricher": 0.35,
    "technical_proposal": 0.35,
    "technical_parser": 0.10,
    "narrative_planner": 0.35,
    "structure_planner": 0.25,
    "instrument_planner": 0.75,
    "style_coherence": 0.20,
    "melody": 0.85,
    "melody_repair": 0.92,
}

# Nodos de baja variación (deterministas o temperatura baja)
LOW_VARIATION_NODES = frozenset({
    "router",
    "technical_parser",
    "structure_planner",
    "strategy_planner",
    "harmony_planner",
    "development_planner",
    "align_sections",
    "composition_policy",
    "rhythm_engine",
    "pad",
    "melody_post",
})

HIGH_VARIATION_NODES = frozenset({
    "instrument_planner",
    "style_coherence",
    "melody",
    "melody_repair",
    "tag_enricher",
    "technical_proposal",
    "narrative_planner",
    "arp_synth",
    "chord_stab",
    "countermelody",
    "perc_aux",
    "synth_pluck",
})

NODE_SALTS: dict[str, str] = {
    "router": "router",
    "tag_enricher": "tag",
    "technical_proposal": "proposal",
    "technical_parser": "parser",
    "narrative_planner": "narrative",
    "structure_planner": "structure",
    "strategy_planner": "strategy",
    "harmony_planner": "harmony",
    "development_planner": "development",
    "instrument_planner": "instruments",
    "style_coherence": "coherence",
    "arrangement_planner": "arrangement",
    "melody": "melody",
    "melody_repair": "melody_repair",
    "melody_post": "melody_post",
    "rhythm_engine": "rhythm",
    "pad": "pad",
    "humanize": "humanize",
    "layer_schedule": "schedule",
    "align_sections": "align_sections",
    "composition_policy": "composition_policy",
    "post_process": "post_process",
    "validator": "validator",
    "export": "export",
    "repair": "repair",
    "arp_synth": "arp_synth",
    "chord_stab": "chord_stab",
    "countermelody": "countermelody",
    "fx_riser": "fx_riser",
    "perc_aux": "perc_aux",
    "synth_pluck": "synth_pluck",
}


def derive_node_seed(generation_seed: int, node: str) -> int:
    """Subsemilla determinista por nodo y solicitud."""
    salt = NODE_SALTS.get(node, node)
    return abs(hash(f"{generation_seed}:{salt}")) % 100_000


def build_node_seeds(generation_seed: int) -> NodeSeeds:
    """Deriva todas las subsemillas documentadas para la solicitud."""
    data: dict[str, int] = {"generation_seed": generation_seed}
    for node in NODE_SALTS:
        data[f"seed_{node}"] = derive_node_seed(generation_seed, node)
    return NodeSeeds(**data)


def node_temperature(node: str, *, repair_attempt: int = 0) -> float:
    """Temperatura LLM recomendada para el nodo."""
    base = NODE_TEMPERATURE.get(node, 0.4)
    if node == "melody" and repair_attempt > 0:
        return min(1.0, NODE_TEMPERATURE.get("melody_repair", 0.92))
    return base


def seed_for_state(state: dict, node: str) -> int:
    """Subsemilla del nodo desde estado (node_seeds o derivación)."""
    key = f"seed_{node}"
    ns = state.get("node_seeds")
    if ns is not None:
        val = getattr(ns, key, None)
        if isinstance(val, int) and val > 0:
            return val
    root = state.get("generation_seed", 0)
    return derive_node_seed(root, node) if root else 0
