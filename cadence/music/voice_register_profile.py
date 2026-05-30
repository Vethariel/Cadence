"""
Perfil de registro de voz — densidad y articulación de melody + bass.

Fuente única derivada de arquetipo, textura, texture_mode y presión de stack.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from cadence.music.texture_policy import infer_texture_mode
from cadence.schemas.song_state import OrchestrationPlan, SectionIntent, SongState

LeadDensityTier = Literal["sparse", "moderate", "dense", "hyper"]
LeadArticulation = Literal["legato", "mixed", "staccato"]
BassGridTier = Literal["half", "quarter", "eighth", "sixteenth"]

LEAD_SUPPORT_IDS = frozenset({
    "arp_synth", "countermelody", "synth_pluck", "chord_stab", "echo_synth",
})

BASS_BY_TIER: dict[BassGridTier, tuple[str, ...]] = {
    "half": ("half_time", "pulse", "root_fifth", "sub_drop"),
    "quarter": ("root_fifth", "half_time", "syncopated", "pulse"),
    "eighth": ("syncopated", "walk", "root_fifth", "half_time", "staccato"),
    "sixteenth": ("driving", "octave_pulse", "staccato", "walk", "syncopated"),
}

BASS_REMAP_FOR_SPARSE_GRID: dict[str, str] = {
    "driving": "half_time",
    "octave_pulse": "root_fifth",
    "staccato": "half_time",
    "walk": "syncopated",
}

_TIER_ORDER: tuple[LeadDensityTier, ...] = ("sparse", "moderate", "dense", "hyper")
_ART_ORDER: tuple[LeadArticulation, ...] = ("legato", "mixed", "staccato")
_BASS_ORDER: tuple[BassGridTier, ...] = ("half", "quarter", "eighth", "sixteenth")


def _tier_index(tier: LeadDensityTier) -> int:
    return _TIER_ORDER.index(tier)


def _cap_tier(tier: LeadDensityTier, ceiling: LeadDensityTier) -> LeadDensityTier:
    if _tier_index(tier) > _tier_index(ceiling):
        return ceiling
    return tier


def _cap_art(art: LeadArticulation, ceiling: LeadArticulation) -> LeadArticulation:
    if _ART_ORDER.index(art) < _ART_ORDER.index(ceiling):
        return ceiling
    return art


def _cap_bass(tier: BassGridTier, ceiling: BassGridTier) -> BassGridTier:
    if _BASS_ORDER.index(tier) > _BASS_ORDER.index(ceiling):
        return ceiling
    return tier


@dataclass(frozen=True)
class VoiceRegisterProfile:
    lead_density_tier: LeadDensityTier
    lead_articulation: LeadArticulation
    bass_grid_tier: BassGridTier
    allow_densify: bool
    allow_fill_gaps: bool
    quantize_lead_to_harmony: bool
    min_melody_duration_steps: int
    bass_duration_factor: float
    max_melody_notes_per_bar: float | None
    max_staccato_ratio: float | None
    stack_pressure: bool
    texture_mode: str
    melody_texture: str
    composition_archetype: str

    def to_dict(self) -> dict:
        return asdict(self)

    def bass_pool_priority(self) -> list[str]:
        from cadence.music.strategy_pools import BASS_POOL

        preferred = list(BASS_BY_TIER[self.bass_grid_tier])
        seen: set[str] = set()
        out: list[str] = []
        for p in preferred:
            if p not in seen:
                seen.add(p)
                out.append(p)
        for p in BASS_POOL:
            if p not in seen:
                out.append(p)
        return out

    def notes_per_bar_target(
        self,
        energy_level: int,
        *,
        narrative_role: str | None = None,
    ) -> int:
        role = narrative_role or ""
        tier = self.lead_density_tier
        if tier == "hyper":
            return 10 if role in ("climax", "tension") and energy_level >= 5 else 9
        if tier == "dense":
            if role in ("climax", "tension"):
                return 8 if energy_level >= 5 else 7
            return 7 if energy_level >= 4 else 6
        if tier == "moderate":
            if self.composition_archetype == "moderate_cinematic":
                if role in ("climax", "tension"):
                    return 7 if energy_level >= 4 else 6
                return 6 if energy_level >= 3 else 5
            if role in ("climax", "tension"):
                return 5 if energy_level >= 5 else 4
            return 4 if energy_level >= 4 else 3
        if role in ("climax", "tension"):
            return 4
        return 3

    def melody_rest_ratio_for_intent(
        self,
        intent: SectionIntent | None,
        *,
        use_case: str = "game",
        energy_level: int = 3,
    ) -> float:
        if self.lead_density_tier == "hyper":
            if intent and intent.narrative_role in ("climax", "tension"):
                return 0.02
            if intent and intent.density >= 0.7:
                return 0.04
            return 0.05
        if self.lead_density_tier == "dense":
            if intent and intent.narrative_role in ("climax", "tension"):
                return 0.05
            if intent and intent.density >= 0.7:
                return 0.08
            return 0.10
        if self.lead_articulation == "legato":
            uc = (use_case or "game").lower()
            if intent is None:
                return 0.20 if uc in ("loop", "cutscene") else 0.15
            if intent.density < 0.35:
                return 0.35
        if self.composition_archetype == "orchestral_boss":
            if intent.narrative_role in ("climax", "tension"):
                return 0.22 if energy_level >= 5 else 0.28
            if intent.density >= 0.7:
                return 0.25
            return 0.32
        if intent.narrative_role in ("climax", "tension"):
            return 0.18 if energy_level >= 5 else 0.22
        if intent.density >= 0.7:
            return 0.20
        return 0.25
        uc = (use_case or "game").lower()
        if intent is None:
            return 0.15 if uc in ("loop", "cutscene") else 0.12
        if intent.density < 0.35:
            return 0.30
        if intent.density < 0.55:
            return 0.22
        if intent.narrative_role in ("climax", "tension"):
            return 0.10
        return 0.15

    def is_dense_melody_target(self, energy_level: int = 3, use_case: str = "game") -> bool:
        if self.lead_density_tier in ("hyper", "dense"):
            return True
        if self.lead_density_tier == "moderate":
            return (
                self.melody_texture in ("dense", "percussive")
                and energy_level >= 4
                and (use_case or "game").lower() == "game"
            )
        return False

    def melody_min_notes_per_bar_validator(
        self,
        energy_level: int,
    ) -> float | None:
        if self.lead_density_tier == "hyper":
            return 5.5 if energy_level >= 5 else 5.0
        if self.lead_density_tier == "dense":
            return 4.5 if energy_level >= 5 else 4.0
        return None

    def melody_max_long_gap_ratio(self, energy_level: int) -> float | None:
        if self.lead_density_tier == "hyper":
            return 0.18 if energy_level >= 5 else 0.22
        if self.lead_density_tier == "dense":
            return 0.28
        return None

    def llm_archetype_hint(self, notes_target: int) -> str:
        art = self.lead_articulation
        min_steps = self.min_melody_duration_steps
        if art == "staccato":
            return (
                f"\nPerfil de registro STACCATO ({self.lead_density_tier}): "
                f"melodía densa (≥{notes_target} notas/compás en climax), "
                "notas cortas (1-2 steps), pocos silencios.\n"
            )
        if art == "legato":
            return (
                f"\nPerfil de registro LEGATO ({self.lead_density_tier}): "
                f"melodía expresiva (~{notes_target} notas/compás en climax), "
                f"notas de {min_steps}-8 steps, deja respirar entre frases; "
                "evita machine-gun de semicorcheas.\n"
            )
        return (
            f"\nPerfil de registro MIXTO ({self.lead_density_tier}): "
            f"~{notes_target} notas/compás en secciones activas, "
            f"duración típica {min_steps}-4 steps.\n"
        )

    def normalize_bass_pattern_id(self, pattern_id: str) -> str:
        from cadence.music.pattern_registry import pattern_family

        if self.bass_grid_tier in ("eighth", "sixteenth"):
            return pattern_id
        fam = pattern_family(pattern_id)
        sparse = BASS_REMAP_FOR_SPARSE_GRID.get(fam)
        if not sparse:
            return pattern_id
        parts = pattern_id.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in ("a", "b", "c"):
            return f"{sparse}_{parts[1]}"
        return sparse


def _base_from_archetype(
    archetype: str,
    energy_level: int,
    use_case: str,
    melody_texture: str,
) -> tuple[LeadDensityTier, LeadArticulation, BassGridTier]:
    from cadence.music.composition_archetypes import normalize_archetype, policy_family

    arch = normalize_archetype(archetype)
    fam = policy_family(arch)
    uc = (use_case or "game").lower()
    tex = melody_texture or "balanced"

    if arch == "lofi_downtempo":
        return "sparse", "legato", "half"
    if arch == "stealth_tension":
        return "sparse", "legato", "half"
    if arch == "menu_theme":
        tier: LeadDensityTier = "sparse" if energy_level <= 2 else "moderate"
        return tier, "legato", "quarter"
    if arch == "moderate_cinematic":
        return "moderate", "legato", "eighth"
    if arch == "energetic_game":
        if energy_level >= 4:
            return "dense", "mixed", "eighth"
        return "moderate", "mixed", "eighth"
    if fam == "dense":
        return "hyper", "staccato", "sixteenth"
    if fam in ("compact", "energetic"):
        return "dense", "mixed", "eighth"
    if fam == "sparse":
        tier = "sparse" if energy_level <= 2 else "moderate"
        return tier, "legato", "half"
    if fam == "cinematic":
        tier = "sparse" if energy_level <= 2 else "moderate"
        return tier, "legato", "half"
    if arch == "hybrid_epic":
        return "moderate", "mixed", "eighth"
    if fam == "orchestral":
        return "moderate", "legato", "quarter"

    if tex == "sparse":
        return "sparse", "legato", "half"
    if tex in ("dense", "percussive"):
        if energy_level >= 5:
            return "dense", "mixed", "eighth"
        return "moderate", "mixed", "eighth"
    if uc in ("loop", "cutscene"):
        return "sparse" if energy_level <= 2 else "moderate", "legato", "half"
    if energy_level >= 5:
        return "dense", "mixed", "eighth"
    if energy_level >= 4:
        return "moderate", "mixed", "eighth"
    return "moderate", "mixed", "quarter"


def _apply_texture_mode(
    tier: LeadDensityTier,
    art: LeadArticulation,
    bass: BassGridTier,
    texture_mode: str,
    *,
    composition_archetype: str,
    allow_densify: bool,
    allow_fill: bool,
    quantize: bool,
) -> tuple[LeadDensityTier, LeadArticulation, BassGridTier, bool, bool, bool]:
    from cadence.music.composition_archetypes import policy_family

    mode = texture_mode or "staggered"
    if policy_family(composition_archetype) == "dense":
        return tier, art, bass, allow_densify, allow_fill, quantize
    if mode == "bedded":
        tier = _cap_tier(tier, "moderate")
        art = _cap_art(art, "legato")
        bass = _cap_bass(bass, "quarter")
        return tier, art, bass, False, False, False
    if mode == "compact":
        tier = _cap_tier(tier, "dense")
        bass = _cap_bass(bass, "eighth")
        return tier, art, bass, allow_densify, allow_fill, quantize
    if mode == "simultaneous":
        tier = _cap_tier(tier, "moderate")
        art = _cap_art(art, "legato")
        bass = _cap_bass(bass, "quarter")
        return tier, art, bass, False, False, False
    return tier, art, bass, allow_densify, allow_fill, quantize


def _apply_stack_pressure(
    tier: LeadDensityTier,
    art: LeadArticulation,
    bass: BassGridTier,
    *,
    stack_pressure: bool,
    allow_densify: bool,
    allow_fill: bool,
    quantize: bool,
) -> tuple[LeadDensityTier, LeadArticulation, BassGridTier, bool, bool, bool]:
    if not stack_pressure:
        return tier, art, bass, allow_densify, allow_fill, quantize
    tier = _cap_tier(tier, "moderate")
    art = _cap_art(art, "legato")
    bass = _cap_bass(bass, "quarter")
    return tier, art, bass, False, False, False


def _articulation_params(art: LeadArticulation) -> tuple[int, float, float | None, float | None]:
    if art == "staccato":
        return 1, 1.8, None, None
    if art == "legato":
        return 4, 4.5, 7.5, 0.40
    return 2, 2.8, 9.5, 0.58


def resolve_voice_register_profile(
    *,
    composition_archetype: str,
    energy_level: int = 3,
    use_case: str = "game",
    melody_texture: str = "balanced",
    texture_mode: str | None = None,
    harmonic_support_count: int = 0,
    lead_support_count: int = 0,
    active_optional_count: int = 0,
    narrative_sections: dict[str, SectionIntent] | None = None,
    genre_mix: dict[str, float] | None = None,
) -> VoiceRegisterProfile:
    from cadence.music.composition_archetypes import normalize_archetype, policy_family

    arch = normalize_archetype(composition_archetype or "default_game")
    tier, art, bass = _base_from_archetype(arch, energy_level, use_case, melody_texture)

    if genre_mix:
        orch = sum(
            genre_mix.get(k, 0.0)
            for k in ("orchestral", "cinematic", "epic", "symphonic")
        )
        dance = sum(genre_mix.get(k, 0.0) for k in ("techno", "dubstep", "house", "dance"))
        if orch >= 0.2 and dance < 0.15:
            tier = _cap_tier(tier, "moderate")
            art = _cap_art(art, "legato")
            bass = _cap_bass(bass, "quarter")
        elif dance >= 0.25 and arch == "default_game":
            tier = "dense" if energy_level >= 4 else tier
            bass = _cap_bass(bass, "eighth") if _BASS_ORDER.index(bass) < _BASS_ORDER.index("eighth") else bass

    if melody_texture == "sparse":
        tier = _cap_tier(tier, "sparse")
        art = _cap_art(art, "legato")
        bass = _cap_bass(bass, "half")
    elif melody_texture in ("dense", "percussive") and policy_family(arch) not in (
        "orchestral", "cinematic", "sparse",
    ):
        if tier == "moderate":
            tier = "dense"

    mode = texture_mode or infer_texture_mode(
        use_case=use_case,
        energy_level=energy_level,
        narrative_sections=narrative_sections,
        active_optional_count=active_optional_count,
        composition_archetype=arch,
    )

    stack_pressure = (
        harmonic_support_count >= 2
        or lead_support_count >= 2
        or (mode == "simultaneous" and active_optional_count >= 2)
    )

    allow_densify = tier in ("dense", "hyper") and not stack_pressure
    allow_fill = tier in ("dense", "hyper", "moderate") and melody_texture != "sparse"
    quantize = (
        harmonic_support_count >= 2
        and energy_level >= 4
        and (use_case or "game").lower() == "game"
        and not stack_pressure
    )

    tier, art, bass, allow_densify, allow_fill, quantize = _apply_texture_mode(
        tier,
        art,
        bass,
        mode,
        composition_archetype=arch,
        allow_densify=allow_densify,
        allow_fill=allow_fill,
        quantize=quantize,
    )
    tier, art, bass, allow_densify, allow_fill, quantize = _apply_stack_pressure(
        tier,
        art,
        bass,
        stack_pressure=stack_pressure,
        allow_densify=allow_densify,
        allow_fill=allow_fill,
        quantize=quantize,
    )

    min_steps, bass_factor, max_notes, max_staccato = _articulation_params(art)

    return VoiceRegisterProfile(
        lead_density_tier=tier,
        lead_articulation=art,
        bass_grid_tier=bass,
        allow_densify=allow_densify,
        allow_fill_gaps=allow_fill and not stack_pressure,
        quantize_lead_to_harmony=quantize,
        min_melody_duration_steps=min_steps,
        bass_duration_factor=bass_factor,
        max_melody_notes_per_bar=max_notes,
        max_staccato_ratio=max_staccato,
        stack_pressure=stack_pressure,
        texture_mode=mode,
        melody_texture=melody_texture,
        composition_archetype=arch,
    )


def _lead_support_count(active_ids: set[str]) -> int:
    return sum(1 for iid in LEAD_SUPPORT_IDS if iid in active_ids)


def profile_from_state(state: SongState) -> VoiceRegisterProfile:
    from cadence.music.harmonic_coherence import (
        active_instrument_ids_from_plan,
        count_harmonic_support_layers,
    )

    cached = state.get("voice_register_profile")
    if isinstance(cached, dict) and cached.get("lead_density_tier"):
        return VoiceRegisterProfile(**cached)

    from cadence.music.narrative_contract import section_intent_map_from_state
    from cadence.music.style_archetype import (
        get_composition_archetype,
        melody_texture_for_archetype,
    )

    intent = state["intent"]
    proposal = state.get("technical_proposal")
    plan: OrchestrationPlan | None = state.get("orchestration_plan")
    development = state.get("development")
    arrangement = state.get("arrangement")

    archetype = get_composition_archetype(state)
    energy = proposal.energy_level if proposal else 3
    use_case = intent.use_case if intent else "game"
    requested_tex = getattr(plan, "melody_texture", "balanced") if plan else "balanced"
    melody_texture = melody_texture_for_archetype(
        archetype, energy, use_case, requested_tex,
    )

    _core = frozenset({"drums", "bass", "melody", "pad"})
    active = active_instrument_ids_from_plan(plan)
    if arrangement and arrangement.layers:
        active |= {
            l.instrument_id
            for l in arrangement.layers
            if l.active_sections and l.active_sections != ["silence"]
        }

    optional_count = sum(
        1 for l in (arrangement.layers if arrangement else [])
        if l.instrument_id not in _core
        and l.active_sections
        and l.active_sections != ["silence"]
    )

    intent_map = section_intent_map_from_state(state, context="voice_register")
    texture_mode = (
        development.texture_mode if development else None
    )

    return resolve_voice_register_profile(
        composition_archetype=archetype,
        energy_level=energy,
        use_case=use_case,
        melody_texture=melody_texture,
        texture_mode=texture_mode,
        harmonic_support_count=count_harmonic_support_layers(active),
        lead_support_count=_lead_support_count(active),
        active_optional_count=optional_count,
        narrative_sections=intent_map or None,
        genre_mix=state.get("genre_mix"),
    )


def get_voice_register_profile(state: SongState) -> VoiceRegisterProfile:
    return profile_from_state(state)
