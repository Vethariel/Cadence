import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from cadence.music.style_profile import effective_genre_tags
from cadence.schemas.song_state import SongState
from cadence.agent.nodes.narrative_apply import section_intent_map
from cadence.music.crescendo import narrative_intensity_curve


# ── Helpers ───────────────────────────────────────────────────

def _export_title(state: SongState) -> str:
    from cadence.analysis.benchmark_examples import export_title_for_prompt

    intent = state["intent"]
    return export_title_for_prompt(
        intent.raw_prompt,
        intent.use_case,
        intent.mood or "",
    )


def _compute_intensity_curve(state: SongState) -> list[float]:
    """Curva de intensidad por sección (narrativa o inferida desde drums)."""
    structure = state["structure"]
    narrative = state.get("narrative")

    if narrative:
        return narrative_intensity_curve(
            structure.sections,
            section_intent_map(narrative),
        )

    tracks = state.get("tracks", [])
    drums = next((t for t in tracks if t.id == "drums"), None)

    if not drums or not drums.events:
        return [0.5] * len(structure.sections)

    curve = []
    for section in structure.sections:
        section_events = [e for e in drums.events if e.section == section]
        if not section_events:
            curve.append(0.1)
            continue
        avg_velocity = sum(e.velocity for e in section_events) / len(section_events)
        density = min(1.0, len(section_events) / 64)
        intensity = round((avg_velocity / 127 * 0.6 + density * 0.4), 3)
        curve.append(intensity)

    return curve

def _compute_cue_points(state: SongState) -> list[dict]:
    """Genera cue points semánticos basados en las secciones."""
    structure = state["structure"]
    proposal = state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120
    beats_per_bar = 4
    ms_per_bar = (60000 / bpm) * beats_per_bar

    cue_points = []
    current_ms = 0

    for section in structure.sections:
        cue_points.append({
            "label": section,
            "t": int(current_ms),
        })
        bars = structure.bars_per_section.get(section, 4)
        current_ms += bars * ms_per_bar

    return cue_points

def _compute_loop_point(state: SongState) -> int:
    """El loop point es el inicio del primer chorus, drop o verse.
    Si no existe ninguno, es el inicio de la segunda sección."""
    structure = state["structure"]
    proposal = state.get("technical_proposal")
    bpm = proposal.bpm if proposal else 120
    ms_per_bar = (60000 / bpm) * 4

    loop_candidates = {"chorus", "drop", "verse", "loop"}
    current_ms = 0

    for section in structure.sections:
        if section in loop_candidates:
            return int(current_ms)
        current_ms += structure.bars_per_section.get(section, 4) * ms_per_bar

    # Fallback: inicio de la segunda sección
    if len(structure.sections) > 1:
        first_bars = structure.bars_per_section.get(structure.sections[0], 4)
        return int(first_bars * ms_per_bar)
    return 0


# ── Serializador principal ────────────────────────────────────

def _build_rsong(state: SongState) -> dict:
    intent = state["intent"]
    proposal = state.get("technical_proposal")
    structure = state["structure"]
    narrative = state.get("narrative")
    harmony = state.get("harmony")
    arrangement = state.get("arrangement")
    development = state.get("development")
    strategies = state.get("strategies")
    validation = state["validation_result"]

    profile = state.get("style_profile")

    if proposal:
        bpm = proposal.bpm
        key = proposal.key
        mode = proposal.mode
        genre_tags = effective_genre_tags(state)
        energy_level = proposal.energy_level
        time_signature = proposal.time_signature
    else:
        bpm = 120
        key = "C"
        mode = "minor"
        genre_tags = effective_genre_tags(state) or intent.style_tags
        energy_level = 3
        time_signature = [4, 4]

    return {
        "rsong_version": "1.0",
        "generated_by": "cadence",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "header": {
            "id": str(uuid.uuid4()),
            "title": _export_title(state),
            "bpm": bpm,
            "time_signature": time_signature,
            "key": f"{key} {mode}",
            "duration_ms": structure.estimated_duration_ms,
            "genre_tags": genre_tags,
            "total_bars": structure.total_bars,
        },
        "game_meta": {
            "use_case": intent.use_case,
            "loop_point_ms": _compute_loop_point(state),
            "intensity_curve": _compute_intensity_curve(state),
            "cue_points": _compute_cue_points(state),
            "energy_level": energy_level,
            "hit_objects_hint": intent.use_case in ("game", "loop"),
            "sections": structure.sections,
            **(
                {
                    "style_profile": profile.model_dump(),
                }
                if profile
                else {}
            ),
            **(
                {
                    "strategies": strategies.model_dump(),
                }
                if strategies
                else {}
            ),
            **(
                {
                    "development": {
                        "generation_seed": development.generation_seed,
                        "global_motif": development.global_motif,
                        "sections": [s.model_dump() for s in development.sections],
                    }
                }
                if development
                else {}
            ),
            **(
                {
                    "arrangement": {
                        "required_layers": arrangement.required_layers,
                        "layers": [l.model_dump() for l in arrangement.layers],
                        **(
                            {
                                "layer_schedule": {
                                    "core_layers": arrangement.layer_schedule.core_layers,
                                    "entries": [
                                        e.model_dump()
                                        for e in arrangement.layer_schedule.entries
                                    ],
                                }
                            }
                            if arrangement.layer_schedule
                            else {}
                        ),
                    }
                }
                if arrangement
                else {}
            ),
            **(
                {
                    "harmony": {
                        "key": harmony.key,
                        "mode": harmony.mode,
                        "sections": [
                            {
                                "section_id": s.section_id,
                                "progression": [c.model_dump() for c in s.progression],
                            }
                            for s in harmony.sections
                        ],
                    }
                }
                if harmony
                else {}
            ),
            **(
                {
                    "narrative": {
                        "logline": narrative.logline,
                        "arc_type": narrative.arc_type,
                        "global_motif": narrative.global_motif,
                        "sections": [s.model_dump() for s in narrative.sections],
                    }
                }
                if narrative
                else {}
            ),
        },
        "validation": {
            "score": validation.score,
            "retry_count": state.get("retry_count", 0),
        },
        "tracks": [
            {
                "id": track.id,
                "instrument": track.instrument,
                "instrument_id": track.instrument_id or track.id,
                "midi_channel": track.midi_channel,
                "role": track.role,
                **({"gm_program": track.gm_program} if track.gm_program is not None else {}),
                "event_count": len(track.events),
                "events": [
                    {
                        "t": e.t,
                        "type": e.type,
                        "pitch": e.pitch,
                        "duration_ms": e.duration_ms,
                        "velocity": e.velocity,
                        "beat_index": e.beat_index,
                        "section": e.section,
                    }
                    for e in track.events
                ],
            }
            for track in state.get("tracks", [])
        ],
    }


# ── Nodo ─────────────────────────────────────────────────────

def export_node(state: SongState) -> dict:
    """
    Serializa el estado completo al formato .rsong y lo escribe en disco.
    """
    rsong_data = _build_rsong(state)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    title = rsong_data["header"]["title"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{title}_{timestamp}.rsong"
    export_path = output_dir / filename

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(rsong_data, f, ensure_ascii=False, indent=2)

    print(f"  [export] → {export_path}")
    print(f"  [export] tracks     : {[t['id'] for t in rsong_data['tracks']]}")
    print(f"  [export] duration   : {rsong_data['header']['duration_ms']}ms")
    print(f"  [export] total events: {sum(t['event_count'] for t in rsong_data['tracks'])}")

    return {
        "export_path": str(export_path),
        "rsong_data": rsong_data,
    }
