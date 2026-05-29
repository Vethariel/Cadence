from langgraph.graph import StateGraph, END

from cadence.schemas.song_state import SongState
from cadence.agent.nodes.router import music_knowledge_router
from cadence.agent.nodes.proposal import technical_proposal_node
from cadence.agent.nodes.technical_parser import technical_parser_node
from cadence.agent.nodes.planner import structure_planner_node
from cadence.agent.nodes.rhythm import rhythm_engine_node
from cadence.agent.nodes.melody import melody_composer_node
from cadence.agent.nodes.validator import validator_node
from cadence.agent.nodes.repair import repair_node, route_after_repair
from cadence.agent.nodes.exporter import export_node


# ── Edges condicionales ───────────────────────────────────────

def route_after_router(state: SongState) -> str:
    """Después del router: técnico pasa por parser, no técnico pasa por proposal."""
    if state["intent"].knowledge_level == "technical":
        return "technical"
    return "technical_proposal"

def route_after_validator(state: SongState) -> str:
    """Después del validator: si pasa va a export, si no y hay reintentos va a repair."""
    validation = state.get("validation_result")
    retry_count = state.get("retry_count", 0)

    if validation and validation.passed:
        return "export"
    if retry_count >= 3:
        return "export"
    return "repair"


# ── Nodo de reparación ────────────────────────────────────────
# Ver cadence/agent/nodes/repair.py


# ── Construcción del grafo ────────────────────────────────────

def build_graph():
    graph = StateGraph(SongState)

    # Registrar nodos
    graph.add_node("router",             music_knowledge_router)
    graph.add_node("technical_proposal", technical_proposal_node)
    graph.add_node("technical_parser",   technical_parser_node)
    graph.add_node("structure_planner",  structure_planner_node)
    graph.add_node("rhythm_engine",      rhythm_engine_node)
    graph.add_node("melody_composer",    melody_composer_node)
    graph.add_node("validator",          validator_node)
    graph.add_node("repair",             repair_node)
    graph.add_node("export",             export_node)

    # Entry point
    graph.set_entry_point("router")

    # Edges fijos
    graph.add_edge("technical_proposal", "structure_planner")
    graph.add_edge("technical_parser",   "structure_planner")
    graph.add_edge("structure_planner",  "rhythm_engine")
    graph.add_edge("rhythm_engine",      "melody_composer")
    graph.add_edge("melody_composer",    "validator")
    graph.add_edge("export",             END)

    # Repair loop: destino según tipo de error
    graph.add_conditional_edges(
        "repair",
        route_after_repair,
        {
            "melody_composer": "melody_composer",
            "rhythm_engine":   "rhythm_engine",
        },
    )

    # Edges condicionales
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "technical":          "technical_parser",
            "technical_proposal": "technical_proposal",
        }
    )
    graph.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "export": "export",
            "repair": "repair",
        }
    )

    return graph.compile()


# Instancia global del grafo
cadence_graph = build_graph()
