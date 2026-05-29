from langchain_core.messages import HumanMessage
from cadence.agent.graph import cadence_graph

def test_graph_non_technical():
    print("\n── test_graph_non_technical ──")
    initial_state = {
        "messages": [HumanMessage(content=(
            "quiero una canción oscura y agresiva para un jefe final de videojuego"
        ))],
        "intent": None,
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    final_state = cadence_graph.invoke(initial_state)

    print(f"knowledge_level  : {final_state['intent'].knowledge_level}")
    print(f"bpm              : {final_state['technical_proposal'].bpm}")
    print(f"sections         : {final_state['structure'].sections}")
    print(f"tracks           : {[t.id for t in final_state['tracks']]}")
    print(f"validation score : {final_state['validation_result'].score}")
    print(f"validation passed: {final_state['validation_result'].passed}")
    print(f"retry_count      : {final_state['retry_count']}")
    print(f"export_path      : {final_state['export_path']}")

    assert final_state["intent"].knowledge_level == "non_technical"
    assert final_state["technical_proposal"] is not None
    assert final_state["structure"] is not None
    assert len(final_state["tracks"]) == 3
    assert final_state["validation_result"] is not None
    assert final_state["export_path"] is not None
    print("✓ test_graph_non_technical OK")

def test_graph_technical():
    print("\n── test_graph_technical ──")
    initial_state = {
        "messages": [HumanMessage(content=(
            "necesito una canción en D minor, 140 BPM, compás 4/4, "
            "estilo techno, estructura intro-verse-chorus-outro"
        ))],
        "intent": None,
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    final_state = cadence_graph.invoke(initial_state)

    print(f"knowledge_level  : {final_state['intent'].knowledge_level}")
    print(f"bpm              : {final_state['technical_proposal'].bpm}")
    print(f"key              : {final_state['technical_proposal'].key} {final_state['technical_proposal'].mode}")
    print(f"sections         : {final_state['structure'].sections}")
    print(f"tracks           : {[t.id for t in final_state['tracks']]}")
    print(f"validation score : {final_state['validation_result'].score}")
    print(f"validation passed: {final_state['validation_result'].passed}")
    print(f"retry_count      : {final_state['retry_count']}")

    assert final_state["intent"].knowledge_level == "technical"
    assert final_state["technical_proposal"] is not None
    assert final_state["technical_proposal"].bpm == 140
    assert final_state["technical_proposal"].key.upper().startswith("D")
    assert final_state["technical_proposal"].mode == "minor"
    assert final_state["structure"] is not None
    assert len(final_state["tracks"]) == 3
    print("✓ test_graph_technical OK")

if __name__ == "__main__":
    test_graph_non_technical()
    print("---")
    test_graph_technical()
    print("\n✓ todos los tests del grafo OK")
