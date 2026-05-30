"""Tests del nodo technical_spec (prompt y catálogo de inspiración)."""

from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import CreativeBrief, TechnicalProposal


def _brief() -> CreativeBrief:
    return CreativeBrief(
        logline="Boss phase escalates",
        dramatic_objective="Drive urgency",
        emotional_arc="dread -> tension -> triumph",
        scene_and_context="Hero faces final form",
        listener_journey="Build pressure then release",
        mood_keywords=["intense", "dark"],
        use_case="game",
        style_hints=["boss fight", "techno"],
        enriched_prompt="Dark techno boss fight with strong climax.",
        reasoning="test",
    )


def test_technical_spec_prompt_includes_inspiration_profiles(monkeypatch):
    from cadence.agent.nodes import spec as spec_module

    captured: dict = {}

    class _FakeLLM:
        def with_structured_output(self, _schema):  # noqa: ANN001
            return self

        def invoke(self, messages):  # noqa: ANN001
            captured["messages"] = messages
            return TechnicalProposal(
                bpm=128,
                key="C",
                mode="minor",
                genre_tags=["techno"],
                energy_level=4,
                reasoning="fake",
            )

    class _FakeFactory:
        def __init__(self, **_kwargs):  # noqa: ANN003
            pass

        def with_structured_output(self, schema):  # noqa: ANN001
            return _FakeLLM().with_structured_output(schema)

    monkeypatch.setattr(spec_module, "ChatGoogleGenerativeAI", _FakeFactory)

    state = {
        "messages": [HumanMessage(content="boss fight techno 140 bpm")],
        "creative_brief": _brief(),
    }
    out = spec_module.technical_spec_node(state)  # type: ignore[arg-type]
    assert out["technical_proposal"].bpm == 128

    sys_msg = captured["messages"][0].content
    assert "PERFILES DE INSPIRACIÓN ESTILÍSTICA" in sys_msg
    assert ".mid" not in sys_msg.lower()
    assert "métricas objetivo:" in sys_msg

