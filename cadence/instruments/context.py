"""Contexto compartido para compositores de instrumentos."""

from dataclasses import dataclass, field

from cadence.music.narrative_contract import contract_section_intent_map
from cadence.schemas.song_state import LayerSpec, SongState


@dataclass
class ComposeContext:
    state: SongState
    layer: LayerSpec
    bpm: int = 120
    key: str = "C"
    mode: str = "minor"
    genre_tags: list[str] = field(default_factory=list)

    def active_sections(self) -> list[str]:
        """Secciones donde esta capa puede sonar (filtradas por layer spec)."""
        structure = self.state["structure"]
        intent_map = contract_section_intent_map(
            self.state.get("narrative"),
            self.state.get("narrative_contract"),
            context=f"compose_context:{self.layer.instrument_id}",
            state=self.state,
        )

        spec_sections = self.layer.active_sections
        all_sections = list(structure.sections)

        if spec_sections == ["*"]:
            candidates = all_sections
        else:
            candidates = [s for s in all_sections if s in spec_sections]

        result = []
        for section in candidates:
            intent = intent_map.get(section)
            density = intent.density if intent else 0.5
            if density >= self.layer.min_density:
                result.append(section)
        return result


def build_compose_context(state: SongState, layer: LayerSpec) -> ComposeContext:
    proposal = state.get("technical_proposal")
    intent = state["intent"]
    if proposal:
        return ComposeContext(
            state=state,
            layer=layer,
            bpm=proposal.bpm,
            key=proposal.key,
            mode=proposal.mode,
            genre_tags=proposal.genre_tags,
        )
    return ComposeContext(
        state=state,
        layer=layer,
        bpm=120,
        key="C",
        mode="minor",
        genre_tags=intent.style_tags,
    )
