from langchain_core.messages import HumanMessage
from cadence.agent.nodes.router import music_knowledge_router

def test_non_technical():
    state = {
        "messages": [HumanMessage(content="quiero una canción oscura y agresiva para un jefe final de videojuego")],
        "intent": None,
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }
    result = music_knowledge_router(state)
    intent = result["intent"]
    print(f"knowledge_level : {intent.knowledge_level}")
    print(f"use_case        : {intent.use_case}")
    print(f"mood            : {intent.mood}")
    print(f"style_tags      : {intent.style_tags}")
    assert intent.knowledge_level == "non_technical"
    print("✓ test_non_technical OK")

def test_technical():
    state = {
        "messages": [HumanMessage(content="necesito una canción en D minor, 140 BPM, compás 4/4, estilo techno, estructura intro-verse-chorus-outro")],
        "intent": None,
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }
    result = music_knowledge_router(state)
    intent = result["intent"]
    print(f"knowledge_level : {intent.knowledge_level}")
    print(f"use_case        : {intent.use_case}")
    print(f"mood            : {intent.mood}")
    print(f"style_tags      : {intent.style_tags}")
    assert intent.knowledge_level == "technical"
    print("✓ test_technical OK")

if __name__ == "__main__":
    test_non_technical()
    print("---")
    test_technical()
