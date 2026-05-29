from langchain_core.messages import HumanMessage
from cadence.schemas.song_state import UserIntent, TechnicalProposal
from cadence.agent.nodes.narrative import narrative_planner_node

BOSS_PROMPT = (
    "quiero una canción oscura y agresiva para un jefe final de videojuego"
)


def test_narrative_boss_fight():
    state = {
        "messages": [HumanMessage(content=BOSS_PROMPT)],
        "intent": UserIntent(
            raw_prompt=BOSS_PROMPT,
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
            reasoning="test",
        ),
        "narrative": None,
        "structure": None,
        "tracks": [],
        "validation_result": None,
        "retry_count": 0,
        "export_path": None,
        "rsong_data": None,
    }

    result = narrative_planner_node(state)
    narrative = result["narrative"]

    print(f"logline         : {narrative.logline}")
    print(f"arc_type        : {narrative.arc_type}")
    print(f"global_motif    : {narrative.global_motif}")
    print(f"sections        : {[s.id for s in narrative.sections]}")

    for s in narrative.sections:
        print(
            f"  {s.id:12} role={s.narrative_role:12} "
            f"density={s.density:.1f} tension={s.harmonic_tension:.1f} "
            f"rhythm={s.rhythmic_complexity:.1f} out→{s.transition_out} "
            f"({s.emotional_target})"
        )

    expected = state["technical_proposal"].structure
    assert len(narrative.sections) == len(expected)
    assert [s.id for s in narrative.sections] == expected
    assert narrative.logline != ""
    assert len(narrative.global_motif) >= 2

    # Boss fight: drop o climax deben tener alta densidad
    peak = [s for s in narrative.sections if s.id in ("drop", "climax")]
    assert any(s.density >= 0.7 for s in peak), "Secciones pico deben tener density >= 0.7"

    # build-up debe tender a riser o filter_sweep
    buildup = next((s for s in narrative.sections if s.id == "build-up"), None)
    if buildup:
        assert buildup.narrative_role in ("tension", "transition", "climax")

    print("✓ test_narrative_boss_fight OK")


if __name__ == "__main__":
    test_narrative_boss_fight()
