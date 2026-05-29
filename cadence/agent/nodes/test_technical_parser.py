from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import UserIntent
from cadence.agent.nodes.technical_parser import technical_parser_node

TECHNICAL_PROMPT = (
    "necesito una canción en D minor, 140 BPM, compás 4/4, "
    "estilo techno, estructura intro-verse-chorus-outro"
)


def test_technical_parser():
    state = {
        "messages": [HumanMessage(content=TECHNICAL_PROMPT)],
        "intent": UserIntent(
            raw_prompt=TECHNICAL_PROMPT,
            knowledge_level="technical",
            use_case="game",
            mood="energetic",
            style_tags=["techno"],
        ),
        "technical_proposal": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    result = technical_parser_node(state)
    proposal = result["technical_proposal"]

    print(f"bpm             : {proposal.bpm}")
    print(f"time_signature  : {proposal.time_signature}")
    print(f"key             : {proposal.key}")
    print(f"mode            : {proposal.mode}")
    print(f"genre_tags      : {proposal.genre_tags}")
    print(f"structure       : {proposal.structure}")
    print(f"reasoning       :\n  {proposal.reasoning}")

    assert proposal.bpm == 140, f"BPM esperado 140, got {proposal.bpm}"
    assert proposal.key.upper().startswith("D"), f"Key esperada D, got {proposal.key}"
    assert proposal.mode == "minor"
    assert proposal.time_signature == [4, 4]
    assert "techno" in [t.lower() for t in proposal.genre_tags]
    assert "intro" in proposal.structure
    assert "chorus" in proposal.structure
    print("✓ test_technical_parser OK")


if __name__ == "__main__":
    test_technical_parser()
