from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import UserIntent, TechnicalProposal, SongNarrative, SectionIntent
from cadence.music.narrative_contract import build_narrative_contract
from cadence.agent.nodes.planner import structure_planner_node

def test_planner_non_technical():
    state = {
        "messages": [HumanMessage(content="canción oscura para jefe final")],
        "intent": UserIntent(
            raw_prompt="quiero una canción oscura y agresiva para un jefe final de videojuego",
            knowledge_level="non_technical",
            use_case="game",
            mood="dark, aggressive",
            style_tags=["techno", "dubstep", "dark"],
        ),
        "technical_proposal": TechnicalProposal(
            bpm=145,
            time_signature=[4, 4],
            key="F",
            mode="minor",
            genre_tags=["techno", "dubstep", "dark industrial"],
            energy_level=5,
            structure=["intro", "build-up", "drop", "breakdown", "climax", "outro"],
            reasoning="Un BPM de 145 aporta urgencia para un jefe final...",
        ),
        "structure": None,
        "narrative": SongNarrative(
            logline="boss fight",
            arc_type="rise-climax-fall",
            sections=[
                SectionIntent(
                    id=s,
                    narrative_role="establish" if s == "intro" else "tension",
                    emotional_target="urgency",
                    density=0.7,
                    harmonic_tension=0.6,
                    rhythmic_complexity=0.5,
                )
                for s in ["intro", "build-up", "drop", "breakdown", "climax", "outro"]
            ],
            global_motif=[0, 2, 4],
        ),
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    state["narrative_contract"] = build_narrative_contract(
        state["narrative"], state["intent"],
    )
    result = structure_planner_node(state)
    structure = result["structure"]

    print(f"sections         : {structure.sections}")
    print(f"bars_per_section : {structure.bars_per_section}")
    print(f"total_bars       : {structure.total_bars}")
    print(f"duration_ms      : {structure.estimated_duration_ms}")

    contract = state["narrative_contract"]
    assert structure.sections == contract.section_ids
    assert len(structure.sections) >= 2
    assert set(structure.sections) == set(structure.bars_per_section.keys()), \
        f"Mismatch secciones: {structure.sections} vs {list(structure.bars_per_section.keys())}"
    assert structure.total_bars == sum(structure.bars_per_section.values())
    assert structure.estimated_duration_ms > 0
    print("✓ test_planner_non_technical OK")

if __name__ == "__main__":
    test_planner_non_technical()
