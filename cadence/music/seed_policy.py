"""
Política de aleatoriedad por solicitud — semilla raíz y subsemillas por nodo.

Solo prompt_enhancer y technical_spec usan LLM; el resto del grafo es determinista.
"""

from __future__ import annotations

from cadence.schemas.song_state import NodeSeeds

# Temperatura LLM (solo nodos activos con modelo)
NODE_TEMPERATURE: dict[str, float] = {
    "prompt_enhancer": 0.72,
    "technical_spec": 0.35,
}

# Nodos cuyas subsemillas se guardan en NodeSeeds (grafo + composición)
GRAPH_SEED_NODES: tuple[str, ...] = (
    "prompt_enhancer",
    "technical_spec",
    "prepare",
    "narrative_planner",
    "structure_planner",
    "strategy_planner",
    "harmony_planner",
    "development_planner",
    "instrument_planner",
    "arrangement_planner",
    "melody",
    "melody_repair",
    "humanize",
    "layer_schedule",
)

LOW_VARIATION_NODES = frozenset({
    "prepare",
    "structure_planner",
    "strategy_planner",
    "harmony_planner",
    "development_planner",
    "composition_policy",
    "rhythm_engine",
    "pad",
    "melody_post",
})

HIGH_VARIATION_NODES = frozenset({
    "prompt_enhancer",
    "technical_spec",
    "arp_synth",
    "chord_stab",
    "countermelody",
    "perc_aux",
    "synth_pluck",
})

NODE_SALTS: dict[str, str] = {
    node: node for node in GRAPH_SEED_NODES
}
NODE_SALTS.update({
    "composition_policy": "composition_policy",
    "post_process": "post_process",
    "validator": "validator",
    "export": "export",
    "repair": "repair",
    "align_sections": "align_sections",
    "rhythm_engine": "rhythm",
    "pad": "pad",
    "melody_post": "melody_post",
    "arp_synth": "arp_synth",
    "chord_stab": "chord_stab",
    "countermelody": "countermelody",
    "fx_riser": "fx_riser",
    "perc_aux": "perc_aux",
    "synth_pluck": "synth_pluck",
})


def derive_node_seed(generation_seed: int, node: str) -> int:
    """Subsemilla determinista por nodo y solicitud."""
    salt = NODE_SALTS.get(node, node)
    return abs(hash(f"{generation_seed}:{salt}")) % 100_000


def build_node_seeds(generation_seed: int) -> NodeSeeds:
    """Deriva subsemillas documentadas para la solicitud (solo campos de NodeSeeds)."""
    data: dict[str, int] = {"generation_seed": generation_seed}
    for node in GRAPH_SEED_NODES:
        data[f"seed_{node}"] = derive_node_seed(generation_seed, node)
    return NodeSeeds(**data)


def node_temperature(node: str, *, repair_attempt: int = 0) -> float:
    """Temperatura LLM recomendada para el nodo."""
    return NODE_TEMPERATURE.get(node, 0.4)


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
