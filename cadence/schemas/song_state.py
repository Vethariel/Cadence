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

class SectionIntent(BaseModel):
    """Intención dramática de una sección — guion narrativo musical."""
    id: str
    narrative_role: Literal[
        "establish", "tension", "release", "climax",
        "reflection", "transition", "silence",
    ]
    emotional_target: str = Field(
        description="Emoción objetivo en inglés. Ej: 'dread', 'urgency', 'triumph'."
    )
    density: float = Field(
        ge=0.0, le=1.0,
        description="Densidad de capas/energía. 0=sparse, 1=máxima.",
    )
    harmonic_tension: float = Field(
        ge=0.0, le=1.0,
        description="Tensión armónica. 0=estable, 1=muy tenso.",
    )
    rhythmic_complexity: float = Field(
        ge=0.0, le=1.0,
        description="Complejidad rítmica. 0=minimal, 1=muy denso.",
    )
    transition_out: Literal[
        "none", "riser", "cut", "filter_sweep",
        "breakdown", "pickup", "fade",
    ] = "none"

class SongNarrative(BaseModel):
    """Guion dramático de la pieza — qué cuenta y cómo evoluciona."""
    logline: str = Field(
        description="Una frase: qué historia musical cuenta esta pieza."
    )
    arc_type: str = Field(
        description="Tipo de arco. Ej: 'rise-climax-fall', 'loop-stable', 'cutscene-arc'."
    )
    sections: list[SectionIntent] = Field(
        description="Una entrada por cada sección, en el mismo orden que la estructura."
    )
    global_motif: list[int] = Field(
        default_factory=list,
        description="Grados de escala 0-6 del motivo principal (opcional, 3-5 grados).",
    )

class ChordSpec(BaseModel):
    """Un acorde expresado como grado de escala + calidad."""
    root_degree: int = Field(ge=0, le=6, description="Grado de escala 0-6 como raíz.")
    quality: Literal["minor", "major", "dim", "dominant"] = "minor"
    bars: int = Field(ge=1, le=8, default=1, description="Compases que dura el acorde.")

class SectionHarmony(BaseModel):
    """Progresión armónica de una sección."""
    section_id: str
    progression: list[ChordSpec]

class LayerSpec(BaseModel):
    """Capa instrumental en el arreglo — qué suena y cuándo."""
    instrument_id: str
    active_sections: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Secciones activas, o ['*'] para todas.",
    )
    pattern_strategy: Literal[
        "loop_1bar", "phrase_4bar", "one_shot", "generative_llm", "chord_sustain",
    ] = "loop_1bar"
    mix_level: float = Field(default=-10.0, description="Nivel de mezcla en dB.")
    min_density: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Densidad narrativa mínima para activar la capa en una sección.",
    )

class LayerScheduleEntry(BaseModel):
    """Cambio de capas activas en un compás global."""
    bar: int = Field(ge=0, description="Compás global 0-based donde aplica el cambio.")
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class LayerSchedule(BaseModel):
    """Programación bar-a-bar de qué capas suenan (estilo Pizza Time)."""
    entries: list[LayerScheduleEntry] = Field(default_factory=list)
    core_layers: list[str] = Field(
        default_factory=lambda: ["drums", "bass", "melody"],
        description="Capas siempre activas salvo remove explícito.",
    )


class ArrangementPlan(BaseModel):
    """Plan de orquestación — qué instrumentos entran y con qué estrategia."""
    layers: list[LayerSpec]
    layer_schedule: LayerSchedule | None = None
    required_layers: list[str] = Field(
        default_factory=lambda: ["drums", "bass", "melody"],
        description="Capas obligatorias para pasar validación.",
    )

class SectionDevelopment(BaseModel):
    """Cómo evoluciona el motivo en una sección."""
    section_id: str
    transform: Literal[
        "introduce", "sequence_up", "sequence_down", "invert",
        "fragment", "expand", "climax", "resolve", "sparse",
    ]
    phrase_length_bars: int = Field(ge=2, le=4, default=2)
    contour: Literal["ascending", "descending", "arch", "zigzag", "wave"] = "arch"
    motif_variant: list[int] = Field(
        default_factory=list,
        description="Motivo transformado (grados 0-6) para esta sección.",
    )

class DevelopmentPlan(BaseModel):
    """Plan de desarrollo motivico — variación sin repetición obvia."""
    global_motif: list[int] = Field(default_factory=list)
    sections: list[SectionDevelopment]
    generation_seed: int = 0


class GenerationStrategies(BaseModel):
    """Estrategias compositivas elegidas por generation_seed."""
    generation_seed: int = 0
    drum_pattern: str = "default"
    bass_pattern: str = "root_fifth"
    harmony_pool: str = "classic"
    arp_pattern: str = "up"


class HarmonyPlan(BaseModel):
    """Plan armónico compartido por bajo, melodía y pad."""
    key: str
    mode: Literal["major", "minor"]
    sections: list[SectionHarmony]
    bars_per_chord_default: int = 4

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
    instrument_id: str = ""
    midi_channel: int = 0
    role: Literal["lead", "rhythm", "bass", "pad", "fx"]
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
    narrative: Optional[SongNarrative] = None
    structure: Optional[SongStructure] = None
    harmony: Optional[HarmonyPlan] = None
    development: Optional[DevelopmentPlan] = None
    strategies: Optional[GenerationStrategies] = None
    arrangement: Optional[ArrangementPlan] = None
    generation_seed: int = 0

    # — Composición
    tracks: list[Track] = Field(default_factory=list)

    # — Validación
    validation_result: Optional[ValidationResult] = None
    retry_count: int = 0
    repair_target: Optional[str] = None
    repair_layers: Optional[list[str]] = None

    # — Exportación
    export_path: Optional[str] = None
    rsong_data: Optional[dict] = None
