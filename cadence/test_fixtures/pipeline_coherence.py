"""
Estado de pipeline alineado al contrato — base para tests intra-request.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from cadence.agent.nodes.align_sections import align_sections_node
from cadence.agent.nodes.composition_policy import composition_policy_node
from cadence.agent.nodes.narrative_contract_node import narrative_contract_node
from cadence.agent.nodes.strategy import strategy_planner_node
from cadence.music.narrative_contract import build_narrative_contract
from cadence.schemas.song_state import (
    SectionIntent,
    SongNarrative,
    SongStructure,
    TechnicalProposal,
    UserIntent,
)

CANONICAL_SECTION_IDS = ["intro", "build-up", "drop", "outro"]
PLANNER_SECTION_IDS = ["Intro", "Build-Up", "Drop", "Outro"]


def _boss_narrative() -> SongNarrative:
    specs = [
        ("intro", "establish", 0.3, 0.2),
        ("build-up", "tension", 0.7, 0.6),
        ("drop", "climax", 1.0, 0.85),
        ("outro", "release", 0.25, 0.1),
    ]
    return SongNarrative(
        logline="Boss fight escalates and releases",
        arc_type="rise-climax-fall",
        global_motif=[0, 2, 4],
        sections=[
            SectionIntent(
                id=sid,
                narrative_role=role,
                emotional_target="intense",
                density=density,
                harmonic_tension=tension,
                rhythmic_complexity=0.5,
                transition_out="cut",
            )
            for sid, role, density, tension in specs
        ],
    )


def _base_intent() -> UserIntent:
    return UserIntent(
        raw_prompt="boss fight techno dark",
        knowledge_level="non_technical",
        use_case="game",
        mood="dark",
        style_tags=["techno", "dubstep"],
    )


def build_pre_align_state() -> dict:
    """Estado tras narrative + contrato + structure_planner (IDs del planner)."""
    intent = _base_intent()
    narrative = _boss_narrative()
    contract = build_narrative_contract(narrative, intent)
    return {
        "messages": [HumanMessage(content=intent.raw_prompt)],
        "intent": intent,
        "narrative": narrative,
        "narrative_contract": contract,
        "technical_proposal": TechnicalProposal(
            bpm=140,
            key="F",
            mode="minor",
            genre_tags=["techno"],
            energy_level=5,
            structure=list(CANONICAL_SECTION_IDS),
            reasoning="test",
        ),
        "structure": SongStructure(
            sections=list(PLANNER_SECTION_IDS),
            bars_per_section={
                "Intro": 4,
                "Build-Up": 8,
                "Drop": 8,
                "Outro": 4,
            },
            total_bars=24,
            estimated_duration_ms=41143,
        ),
        "tracks": [],
        "retry_count": 0,
    }


def build_aligned_pipeline_state(
    *,
    generation_seed: int | None = None,
    include_strategy: bool = True,
) -> dict:
    """Pipeline hasta composition_policy (+ strategy opcional) con IDs canónicos."""
    state = build_pre_align_state()
    state.update(align_sections_node(state))
    if generation_seed is not None:
        state["generation_seed"] = generation_seed
    state.update(composition_policy_node(state))
    if include_strategy:
        state.update(strategy_planner_node(state))
    return state
