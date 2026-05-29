from typing import Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState


# ── Submodelos ────────────────────────────────────────────────

class UserIntent(BaseModel):
    """Resultado del nodo intent/router: qué quiere el usuario y qué sabe de música."""
    raw_prompt: str
    knowledge_level: Literal["technical", "non_technical"]
    use_case: Literal["game", "animation", "loop", "cutscene"] = "game"
    mood: str = ""
    style_tags: list[str] = Field(default_factory=list)

class TechnicalProposal(BaseModel):
    """Propuesta técnica generada cuando el usuario NO es técnico."""
    bpm: int
    time_signature: list[int] = Field(default=[4, 4])
    key: str
    mode: Literal["major", "minor"] = "minor"
    genre_tags: list[str] = Field(default_factory=list)
    energy_level: int = Field(ge=1, le=5, default=3)
    structure: list[str] = Field(default=["intro", "verse", "chorus", "outro"])
    reasoning: str = ""

class SongStructure(BaseModel):
    """Macro-forma de la canción: secciones y duración estimada."""
    sections: list[str]
    bars_per_section: dict[str, int]
    total_bars: int
    estimated_duration_ms: int

class RhythmEvent(BaseModel):
    """Un evento rítmico individual."""
    t: int                          # tiempo en ms desde inicio
    type: Literal["note", "rest", "chord", "drum_hit"]
    pitch: int = 60                 # número MIDI
    duration_ms: int = 250
    velocity: int = 100
    beat_index: int = 0
    section: str = ""

class Track(BaseModel):
    """Un track con su lista de eventos."""
    id: str
    instrument: str
    midi_channel: int = 0
    role: Literal["lead", "rhythm", "bass", "pad"]
    events: list[RhythmEvent] = Field(default_factory=list)

class ValidationResult(BaseModel):
    """Resultado del nodo validador."""
    score: float = Field(ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    passed: bool = False


# ── Estado principal del grafo ────────────────────────────────

class SongState(MessagesState):
    # — Router
    intent: Optional[UserIntent] = None
    
    # — Propuesta técnica (solo ruta non_technical)
    technical_proposal: Optional[TechnicalProposal] = None

    # — Planificación
    structure: Optional[SongStructure] = None

    # — Composición
    tracks: list[Track] = Field(default_factory=list)

    # — Validación
    validation_result: Optional[ValidationResult] = None
    retry_count: int = 0
    repair_target: Optional[str] = None

    # — Exportación
    export_path: Optional[str] = None
    rsong_data: Optional[dict] = None
