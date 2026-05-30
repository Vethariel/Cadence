"""Tests de section IDs canónicos."""

from cadence.music.section_refs import canonical_section_ids, format_section_ids_for_llm
from cadence.schemas.song_state import NarrativeContract, SongStructure


def test_canonical_from_contract():
    state = {
        "narrative_contract": NarrativeContract(
            section_ids=["intro", "drop"],
            arc_type="x",
            global_motif=[0],
            prompt_intent_signature="a",
        ),
        "structure": SongStructure(
            sections=["wrong"],
            bars_per_section={"intro": 4, "drop": 8},
            total_bars=12,
            estimated_duration_ms=1000,
        ),
    }
    assert canonical_section_ids(state) == ["intro", "drop"]
    text = format_section_ids_for_llm(state)
    assert "intro" in text and "drop" in text
    assert "EXACTAMENTE" in text


if __name__ == "__main__":
    test_canonical_from_contract()
    print("All section_refs tests passed.")
