from langchain_core.messages import HumanMessage

from cadence.schemas.song_state import CreativeBrief


def _fake_brief() -> CreativeBrief:
    return CreativeBrief(
        logline="A pilot defends the city and discovers a hidden betrayal.",
        dramatic_objective="Sustain urgency while preserving hope.",
        central_conflict="Escape civilians before the station collapses after an ally betrayal.",
        emotional_arc="dread -> resistance -> resolve",
        scene_and_context="Final escape sequence in a collapsing station.",
        listener_journey="The player feels pressure, then clarity, then determination.",
        mood_keywords=["urgent", "tense", "resolute"],
        dominant_tone="Urgent survival pressure",
        secondary_tone="Defiant determination",
        negative_constraints=["no comic relief", "no celebratory victory lap"],
        scenario_assumption="",
        use_case="game",
        style_hints=["heroic but strained", "city-under-siege pulse"],
        enriched_prompt=(
            "The pilot races through a collapsing station while civilians depend on a final "
            "route to safety. A trusted ally's betrayal reframes the mission, forcing a "
            "hard choice before a determined push toward survival."
        ),
        reasoning="The conflict, arc, and objective align around urgent survival with resolve.",
        coherence_notes="Logline, conflict, objective and arc all point to urgent survival with resolve.",
    )


def test_prompt_enhancer_prompt_has_narrative_guardrails(monkeypatch):
    from cadence.agent.nodes import prompt_enhancer as enhancer_module

    captured: dict = {}

    class _FakeLLM:
        def invoke(self, messages):  # noqa: ANN001
            captured["messages"] = messages
            return _fake_brief()

    class _FakeFactory:
        def __init__(self, **_kwargs):  # noqa: ANN003
            pass

        def with_structured_output(self, _schema):  # noqa: ANN001
            return _FakeLLM()

    monkeypatch.setattr(enhancer_module, "ChatGoogleGenerativeAI", _FakeFactory)

    state = {
        "messages": [HumanMessage(content="Necesito música para boss final tenso.")],
    }
    out = enhancer_module.prompt_enhancer_node(state)  # type: ignore[arg-type]
    assert out["creative_brief"].use_case == "game"

    sys_msg = captured["messages"][0].content
    assert "logline: una sola frase con protagonista, objetivo, obstáculo y giro final." in sys_msg
    assert "central_conflict: conflicto central único" in sys_msg
    assert "scenario_assumption:" in sys_msg
    assert "negative_constraints:" in sys_msg
    assert "coherence_notes:" in sys_msg
    assert "emotional_arc: exactamente 3 hitos emocionales en formato A → B → C." in sys_msg
    assert "Reglas de calidad:" in sys_msg
    assert "No incluyas BPM, tonalidad, compás" in sys_msg
