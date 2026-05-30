from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
from langgraph.graph import MessagesState

from cadence.music.scale_theory import ScaleMode, normalize_mode
from cadence.music.meter_theory import normalize_time_signature


# ── Submodelos ────────────────────────────────────────────────

class UserIntent(BaseModel):
    """Intención resuelta en prepare (determinista) a partir del prompt y el brief."""
    raw_prompt: str
    knowledge_level: Literal["technical", "non_technical"]
    use_case: Literal["game", "animation", "loop", "cutscene"] = "game"
    mood: str = ""
    style_tags: list[str] = Field(
        default_factory=list,
        description="Pistas de estilo del catálogo y del brief creativo.",
    )


class MusicalStyleProfile(BaseModel):
    """Perfil de estilo construido por LLM — fuente de verdad para timbres y género."""
    genres: list[str] = Field(
        default_factory=list,
        description=(
            "3–8 géneros del catálogo cadence.music.genre_catalog "
            "(techno, dubstep, boss fight, orchestral…)."
        ),
    )
    references: list[str] = Field(
        default_factory=list,
        description="Solo nombres propios del prompt; vacío si no hay referentes literales.",
    )
    instrumentation: list[str] = Field(
        default_factory=list,
        description="Timbres/roles deseados (saw lead, wobble bass, brass stab…).",
    )
    avoid: list[str] = Field(
        default_factory=list,
        description="Estilos o timbres a evitar (calliope, music box, orchestral strings pad…).",
    )
    drum_character: str = Field(
        default="",
        description="Carácter rítmico esperado (four-on-floor, dubstep half-time…).",
    )
    reasoning: str = Field(
        default="",
        description="Por qué se eligieron estos tags y no otros (ej. no chiptune si piden SNES party).",
    )


class CreativeBrief(BaseModel):
    """
    Brief dramático ampliado — salida del prompt_enhancer.
    El technical_spec lo convierte en parámetros musicales concretos.
    """
    logline: str = Field(
        description="Una frase: qué historia cuenta la música.",
    )
    dramatic_objective: str = Field(
        description="Qué debe lograr la pieza en el juego/animación (función dramática).",
    )
    emotional_arc: str = Field(
        description="Cómo evoluciona la emoción de inicio a fin (ej. dread → defiance → triumph).",
    )
    scene_and_context: str = Field(
        description="Escena, personaje o situación narrativa que inspira la música.",
    )
    listener_journey: str = Field(
        description="Qué debe sentir el jugador/espectador momento a momento.",
    )
    mood_keywords: list[str] = Field(
        default_factory=list,
        description="3–6 palabras de mood en inglés (dark, urgent, triumphant…).",
    )
    use_case: Literal["game", "animation", "loop", "cutscene"] = Field(
        default="game",
        description="Contexto de uso inferido del brief.",
    )
    style_hints: list[str] = Field(
        default_factory=list,
        description="Pistas de estilo en lenguaje natural (no sustituyen genre_tags del catálogo).",
    )
    enriched_prompt: str = Field(
        description=(
            "Párrafo(s) que integran objetivo, arco, escena y emoción — "
            "entrada principal para el nodo técnico."
        ),
    )
    reasoning: str = Field(
        default="",
        description="Por qué elegiste este enfoque dramático respecto al prompt original.",
    )


InstrumentRole = Literal["lead", "bass", "rhythm", "pad", "fx"]
CadenceType = Literal["authentic", "half", "deceptive", "plagal", "suspended"]
RegisterBand = Literal["low", "mid", "high", "wide"]


class ProposalInstrument(BaseModel):
    """Capa + timbre GM elegidos por technical_spec (antes de validación de orquestación)."""
    instrument_id: str = Field(
        description="Id del registro (drums, bass, melody, pad, arp_synth, …).",
    )
    role: InstrumentRole = Field(
        description="Función musical de la capa: lead | bass | rhythm | pad | fx.",
    )
    gm_program: int = Field(
        ge=0, le=127,
        description="Programa GM del catálogo para este instrument_id.",
    )
    active: bool = Field(
        default=True,
        description="False para desactivar una capa opcional explícitamente.",
    )


class TechnicalProposal(BaseModel):
    """Propuesta técnica: parámetros concretos derivados del brief creativo."""
    bpm: int
    time_signature: list[int] = Field(
        default=[4, 4],
        description="Compás [numerador, denominador]: 4/4, 3/4, 6/8, 5/4…",
    )
    key: str
    mode: ScaleMode = Field(
        default="minor",
        description="Modo de escala: major | minor | dorian | phrygian.",
    )
    genre_tags: list[str] = Field(default_factory=list)
    energy_level: int = Field(ge=1, le=5, default=3)
    structure_form: str = Field(
        default="",
        description="Id de forma en structure_catalog (ej. boss_edm, loop_ambient). Vacío = derivar.",
    )
    structure: list[str] = Field(
        default_factory=list,
        description="Section ids; vacío si solo structure_form. Prioridad si el usuario listó secciones.",
    )
    bars_per_section: dict[str, int] = Field(
        default_factory=dict,
        description="Compases opcionales por section_id (validados en prepare/structure_det).",
    )
    target_total_bars: int | None = Field(
        default=None,
        description="Meta de compases totales; escala proporcional si se define.",
    )
    target_duration_sec: int | None = Field(
        default=None,
        description="Duración objetivo en segundos (orientación; no obligatoria).",
    )
    ensemble_concept: str = Field(
        default="",
        description="Concepto del ensemble en 1–2 frases (variación timbral creativa).",
    )
    instruments: list[ProposalInstrument] = Field(
        default_factory=list,
        description=(
            "Capas activas con gm_program del catálogo TIMBRES_BY_INSTRUMENT. "
            "Vacío = el sistema elige por seed. Si se rellena, define la variación principal."
        ),
    )
    melody_texture: Literal["sparse", "balanced", "dense", "percussive"] | None = Field(
        default=None,
        description="Densidad melódica; vacío = derivar del arquetipo.",
    )
    drum_pattern: str = Field(
        default="",
        description="Patrón de batería (catálogo strategy_pools). Vacío = derivar por seed.",
    )
    bass_pattern: str = Field(
        default="",
        description="Patrón de bajo (catálogo strategy_pools). Vacío = derivar por seed.",
    )
    harmony_pool: str = Field(
        default="",
        description="Pool armónico: classic, modal, game, dark, cinematic, dance, aggressive.",
    )
    arp_pattern: str = Field(default="", description="Si arp_synth activo.")
    stab_pattern: str = Field(default="", description="Si chord_stab activo.")
    perc_pattern: str = Field(default="", description="Si perc_aux activo.")
    pluck_pattern: str = Field(default="", description="Si synth_pluck activo.")
    counter_pattern: str = Field(default="", description="Si countermelody activo.")
    echo_source: str = Field(
        default="",
        description="auto | melody | arp_synth | chord_stab | echo_synth.",
    )
    texture_mode: Literal["bedded", "staggered", "simultaneous", "compact"] | None = Field(
        default=None,
        description="Entrada de capas en el tiempo; vacío = derivar.",
    )
    composition_archetype: str = Field(
        default="",
        description="Arquetipo compositivo; vacío = inferir en strategy_planner.",
    )
    global_motif: list[int] = Field(
        default_factory=list,
        description="3–5 grados 0–6 del motivo principal; vacío = derivar.",
    )
    section_intensity_curve: dict[str, float] = Field(
        default_factory=dict,
        description="Intensidad por sección (0–1). Claves: section_id canónico.",
    )
    rhythmic_density_curve: dict[str, float] = Field(
        default_factory=dict,
        description="Densidad rítmica por sección (0–1).",
    )
    motif_transform_plan: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Transformación motívica por sección: introduce|sequence_up|sequence_down|"
            "invert|fragment|expand|climax|resolve|sparse|ostinato|augment|"
            "call_response|pedal."
        ),
    )
    cadence_plan: dict[str, CadenceType] = Field(
        default_factory=dict,
        description="Tipo de cadencia por sección: authentic|half|deceptive|plagal|suspended.",
    )
    lead_hierarchy: list[str] = Field(
        default_factory=list,
        description=(
            "Prioridad de capas lead (instrument_id), de más protagonista a menos."
        ),
    )
    register_plan: dict[str, RegisterBand] = Field(
        default_factory=dict,
        description="Registro objetivo por capa (low|mid|high|wide).",
    )
    call_response_map: dict[str, str] = Field(
        default_factory=dict,
        description="Mapa sección->'caller:responder' usando instrument_id.",
    )
    silence_breaks: list[int] = Field(
        default_factory=list,
        description="Compases globales (0-based) donde forzar micro-silencio expresivo.",
    )
    tension_points: list[int] = Field(
        default_factory=list,
        description="Compases globales (0-based) donde marcar picos de tensión.",
    )
    reasoning: str = ""

    @field_validator("time_signature", mode="before")
    @classmethod
    def _validate_time_signature(cls, v: object) -> list[int]:
        if isinstance(v, list):
            return normalize_time_signature(v)
        return normalize_time_signature(None)

    @field_validator("mode", mode="before")
    @classmethod
    def _validate_mode(cls, v: object) -> str:
        return normalize_mode(str(v) if v is not None else None)

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


class NarrativeContract(BaseModel):
    """
    Contrato narrativo inmutable por solicitud — source of truth intra-request.
    Generado tras narrative_planner; los nodos downstream no pueden desviarse.
    """
    section_ids: list[str] = Field(
        description="IDs canónicos de sección en orden dramático.",
    )
    arc_type: str = Field(
        description="Arco narrativo acordado para esta solicitud.",
    )
    global_motif: list[int] = Field(
        default_factory=list,
        description="Motivo global (grados 0-6) fijado en el contrato.",
    )
    prompt_intent_signature: str = Field(
        description="Huella de la solicitud (prompt + use_case + mood + tags).",
    )


class SectionAlignment(BaseModel):
    """Registro de reconciliación structure_planner ↔ contrato narrativo."""
    planner_section_ids: list[str] = Field(default_factory=list)
    mapping: dict[str, str] = Field(
        default_factory=dict,
        description="planner_section_id → canonical section_id",
    )
    method: str = Field(
        default="exact",
        description="exact | normalized | normalized_reorder | positional",
    )
    realigned: bool = False


class SectionNarrativeAnchor(BaseModel):
    """Ancla dramática por sección — baja variación, no editable por nodos creativos."""
    section_id: str
    narrative_role: str
    density: float = Field(ge=0.0, le=1.0)
    harmonic_tension: float = Field(ge=0.0, le=1.0)
    rhythmic_complexity: float = Field(ge=0.0, le=1.0)
    emotional_target: str = ""
    is_key_section: bool = False
    melody_coverage_min: float = Field(
        ge=0.0, le=1.0,
        description="Cobertura melódica mínima esperada en la sección.",
    )


class NarrativeAnchors(BaseModel):
    """
    Anclas narrativas intra-request — arco, tensión-release y densidad por sección.
    Source of truth para límites de nodos creativos.
    """
    arc_type: str
    global_motif: list[int] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    sections: list[SectionNarrativeAnchor] = Field(default_factory=list)
    tension_release_curve: list[float] = Field(
        default_factory=list,
        description="Tensión relativa 0-1 por sección, alineada a section_ids.",
    )
    key_section_ids: list[str] = Field(default_factory=list)


class CreativeVariationBounds(BaseModel):
    """
    Límites de variación creativa — timbres, patrones, adornos, microfraseo.
    Solo puede variar dentro de narrative_anchors.
    """
    max_optional_layers: int = Field(ge=0, le=8, default=4)
    max_lead_optionals: int = Field(ge=0, le=4, default=2)
    allowed_optional_layers: list[str] = Field(default_factory=list)
    pattern_variance: float = Field(ge=0.0, le=1.0, default=0.5)
    micro_phrase_variance: float = Field(ge=0.0, le=1.0, default=0.5)
    fill_density: float = Field(ge=0.0, le=1.0, default=0.4)
    timbre_variance: float = Field(ge=0.0, le=1.0, default=0.5)
    secondary_motif_variance: float = Field(ge=0.0, le=1.0, default=0.4)
    generation_seed: int = 0


class NodeSeeds(BaseModel):
    """Subsemillas derivadas de generation_seed por nodo del grafo."""
    generation_seed: int = 0
    seed_prompt_enhancer: int = 0
    seed_technical_spec: int = 0
    seed_prepare: int = 0
    seed_narrative_planner: int = 0
    seed_structure_planner: int = 0
    seed_strategy_planner: int = 0
    seed_harmony_planner: int = 0
    seed_development_planner: int = 0
    seed_instrument_planner: int = 0
    seed_arrangement_planner: int = 0
    seed_melody: int = 0
    seed_melody_repair: int = 0
    seed_humanize: int = 0
    seed_layer_schedule: int = 0


class ChordSpec(BaseModel):
    """Un acorde expresado como grado de escala + calidad."""
    root_degree: int = Field(ge=0, le=6, description="Grado de escala 0-6 como raíz.")
    quality: Literal["minor", "major", "dim", "dominant"] = "minor"
    bars: int = Field(ge=1, le=8, default=1, description="Compases que dura el acorde.")

class SectionHarmony(BaseModel):
    """Progresión armónica de una sección."""
    section_id: str
    progression: list[ChordSpec]

class InstrumentAssignment(BaseModel):
    """Instrumento elegido por el agente con timbre GM y nivel de mezcla."""
    instrument_id: str
    role: InstrumentRole = Field(
        default="lead",
        description="Rol musical; usado en composición, validación y humanize.",
    )
    gm_program: int = Field(
        ge=0, le=127,
        description="gm_program elegido de TIMBRES_BY_INSTRUMENT[instrument_id].",
    )
    display_name: str = Field(
        default="",
        description="Ignorado en validación; se deriva del gm_program en catálogo.",
    )
    mix_level: float = Field(default=-10.0, description="Nivel de mezcla en dB.")
    active: bool = True


class OrchestrationPlan(BaseModel):
    """Conjunto instrumental y timbres — decisión creativa del agente."""
    ensemble_concept: str = Field(
        default="",
        description="Breve concepto del ensemble (1–2 frases).",
    )
    instruments: list[InstrumentAssignment] = Field(default_factory=list)
    melody_texture: Literal["sparse", "balanced", "dense", "percussive"] = "balanced"
    drum_pattern: Literal[
        "techno", "dubstep", "house", "breakbeat",
        "halftime", "dnb", "industrial", "default",
    ] = Field(description="Patrón de batería elegido por el agente.")
    bass_pattern: Literal[
        "root_fifth", "driving", "syncopated", "pulse",
        "half_time", "walk", "octave_pulse",
    ] = Field(description="Patrón de bajo elegido por el agente.")
    arp_pattern: str = Field(default="", description="Override opcional del patrón de arpeggio.")
    harmony_pool: str = Field(default="", description="Override opcional del pool armónico.")
    stab_pattern: str = Field(
        default="",
        description="Patrón rítmico de chord_stab si la capa está activa.",
    )
    perc_pattern: str = Field(
        default="",
        description="Patrón de claps/shaker en perc_aux si la capa está activa.",
    )
    pluck_pattern: str = Field(
        default="",
        description="Patrón de synth_pluck si la capa está activa.",
    )
    counter_pattern: str = Field(
        default="",
        description="Patrón rítmico de countermelody si la capa está activa.",
    )
    echo_source: str = Field(
        default="",
        description="Fuente del eco: auto | melody | arp_synth | chord_stab.",
    )


class LayerSpec(BaseModel):
    """Capa instrumental en el arreglo — qué suena y cuándo."""
    instrument_id: str
    role: InstrumentRole = Field(
        default="lead",
        description="Rol desde technical_spec / orchestration_plan.",
    )
    active_sections: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Secciones activas, o ['*'] para todas.",
    )
    pattern_strategy: Literal[
        "loop_1bar", "phrase_4bar", "one_shot", "chord_sustain",
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
        default_factory=list,
        description="Capas que deben existir en tracks; derivadas del plan de orquestación.",
    )

class DevelopmentSegment(BaseModel):
    """Subdivisión dentro de una sección — variación de carga emocional en el tiempo."""
    start_bar: int = Field(ge=0, description="Compás relativo al inicio de la sección (0-based).")
    end_bar: int = Field(ge=1, description="Compás exclusivo donde termina el segmento.")
    transform: Literal[
        "introduce", "sequence_up", "sequence_down", "invert",
        "fragment", "expand", "climax", "resolve", "sparse",
        "ostinato", "augment", "call_response", "pedal",
    ]
    phrase_length_bars: int = Field(ge=2, le=4, default=2)
    contour: Literal[
        "ascending", "descending", "arch", "zigzag", "wave", "saw", "static",
    ] = "arch"
    motif_variant: list[int] = Field(default_factory=list)


class SectionDevelopment(BaseModel):
    """Cómo evoluciona el motivo en una sección (resumen + subdivisiones opcionales)."""
    section_id: str
    transform: Literal[
        "introduce", "sequence_up", "sequence_down", "invert",
        "fragment", "expand", "climax", "resolve", "sparse",
        "ostinato", "augment", "call_response", "pedal",
    ]
    phrase_length_bars: int = Field(ge=2, le=4, default=2)
    contour: Literal[
        "ascending", "descending", "arch", "zigzag", "wave", "saw", "static",
    ] = "arch"
    motif_variant: list[int] = Field(
        default_factory=list,
        description="Motivo transformado (grados 0-6) para esta sección.",
    )
    segments: list[DevelopmentSegment] = Field(
        default_factory=list,
        description="Micro-arcos dentro de la sección; vacío = un solo bloque.",
    )

class DevelopmentPlan(BaseModel):
    """Plan de desarrollo motivico — variación sin repetición obvia."""
    global_motif: list[int] = Field(default_factory=list)
    sections: list[SectionDevelopment]
    generation_seed: int = 0
    texture_mode: Literal["bedded", "staggered", "simultaneous", "compact"] = Field(
        default="staggered",
        description="Cama continua, escalonado, solapamiento alto o stack compacto.",
    )


class PatternIntent(BaseModel):
    """Intención de patrones — prioridades derivadas de genre_mix (pre-selección por seed)."""
    genre_mix: dict[str, float] = Field(default_factory=dict)
    drum_candidates: list[str] = Field(default_factory=list)
    bass_candidates: list[str] = Field(default_factory=list)
    harmony_candidates: list[str] = Field(default_factory=list)
    layer_bias: dict[str, list[str] | str] = Field(default_factory=dict)
    mood: str = ""
    use_case: str = "game"
    energy_level: int = 3
    composition_archetype: str | None = None


class GenerationStrategies(BaseModel):
    """Estrategias compositivas elegidas por generation_seed."""
    generation_seed: int = 0
    drum_pattern: str = "default"
    bass_pattern: str = "root_fifth"
    harmony_pool: str = "classic"
    arp_pattern: str = "up"
    stab_pattern: str = "offbeat"
    perc_pattern: str = "backbeat"
    pluck_pattern: str = "eighth"
    counter_pattern: str = "offbeat_sync"
    echo_source: str = "auto"


class PatternFieldAudit(BaseModel):
    """Auditoría por campo: candidatos, pesos y motivo de elección."""
    field: str
    candidates: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    chosen: str = ""
    selection_reason: str = ""


class PatternSelectionAudit(BaseModel):
    """Registro exportable de decisiones de patrón (strategy_planner)."""
    generation_seed: int = 0
    combo_attempt: int = 0
    combo_diversity_window: int = 0
    combo_avoided_recent: bool = False
    rhythm_combo: str = ""
    fields: list[PatternFieldAudit] = Field(default_factory=list)


class HarmonyPlan(BaseModel):
    """Plan armónico compartido por bajo, melodía y pad."""
    key: str
    mode: ScaleMode
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
    gm_program: int | None = None
    events: list[RhythmEvent] = Field(default_factory=list)

class ValidationResult(BaseModel):
    """Resultado del nodo validador."""
    score: float = Field(ge=0.0, le=1.0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    passed: bool = False
    passed_technical: bool | None = None
    passed_perceptual: bool | None = None


# ── Estado principal del grafo ────────────────────────────────

class SongState(MessagesState):
    # — Entrada creativa (LLM inicial)
    creative_brief: Optional[CreativeBrief] = None

    # — Intención y estilo (prepare, determinista)
    intent: Optional[UserIntent] = None
    style_profile: Optional[MusicalStyleProfile] = None

    # — Propuesta técnica (LLM technical_spec + normalización en prepare)
    technical_proposal: Optional[TechnicalProposal] = None

    # — Planificación
    narrative: Optional[SongNarrative] = None
    narrative_contract: Optional[NarrativeContract] = None
    section_alignment: Optional[SectionAlignment] = None
    narrative_anchors: Optional[NarrativeAnchors] = None
    creative_variation: Optional[CreativeVariationBounds] = None
    node_seeds: Optional[NodeSeeds] = None
    composition_archetype: Optional[str] = None
    archetype_reason: Optional[str] = None
    structure: Optional[SongStructure] = None
    harmony: Optional[HarmonyPlan] = None
    development: Optional[DevelopmentPlan] = None
    strategies: Optional[GenerationStrategies] = None
    genre_mix: Optional[dict[str, float]] = None
    pattern_intent: Optional[PatternIntent] = None
    pattern_selection_audit: Optional[PatternSelectionAudit] = None
    orchestration_plan: Optional[OrchestrationPlan] = None
    arrangement: Optional[ArrangementPlan] = None
    generation_seed: int = 0

    # — Composición
    tracks: list[Track] = Field(default_factory=list)

    # — Validación
    validation_result: Optional[ValidationResult] = None
    retry_count: int = 0
    repair_target: Optional[str] = None
    repair_layers: Optional[list[str]] = None
    repair_actions: Optional[list[str]] = None

    # — Observabilidad
    request_id: Optional[str] = None
    pipeline_trace: Optional[list[dict]] = None

    # — Exportación
    export_path: Optional[str] = None
    rsong_data: Optional[dict] = None
