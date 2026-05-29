from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import UserIntent
from cadence.agent.nodes.proposal import technical_proposal_node

def test_proposal():
    state = {
        "messages": [HumanMessage(content="quiero una canción oscura y agresiva para un jefe final de videojuego")],
        "intent": UserIntent(
            raw_prompt="quiero una canción oscura y agresiva para un jefe final de videojuego",
            knowledge_level="non_technical",
            use_case="game",
            mood="dark, aggressive",
            style_tags=["techno", "dubstep", "dark"],
        ),
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    result = technical_proposal_node(state)
    proposal = result["technical_proposal"]

    print(f"bpm             : {proposal.bpm}")
    print(f"time_signature  : {proposal.time_signature}")
    print(f"key             : {proposal.key}")
    print(f"mode            : {proposal.mode}")
    print(f"genre_tags      : {proposal.genre_tags}")
    print(f"energy_level    : {proposal.energy_level}")
    print(f"structure       : {proposal.structure}")
    print(f"reasoning       :\n  {proposal.reasoning}")

    assert proposal.bpm > 0
    assert len(proposal.time_signature) == 2
    assert proposal.key != ""
    assert proposal.energy_level >= 1
    assert len(proposal.structure) >= 2
    assert proposal.reasoning != ""
    print("✓ test_proposal OK")

if __name__ == "__main__":
    test_proposal()
