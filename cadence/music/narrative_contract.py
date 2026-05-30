"""
Contrato narrativo por solicitud — source of truth intra-request para secciones y motivo.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import TYPE_CHECKING

from cadence.schemas.song_state import (
    NarrativeContract,
    SectionAlignment,
    SectionIntent,
    SongNarrative,
    SongStructure,
    UserIntent,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cadence.narrative")


class SectionAlignmentError(ValueError):
    """No se pudo mapear structure.sections al contrato narrativo."""


def compute_prompt_intent_signature(intent: UserIntent) -> str:
    """Huella estable de la solicitud (heterogeneidad inter-request)."""
    parts = [
        intent.raw_prompt.strip(),
        intent.use_case,
        intent.mood.strip(),
        ",".join(sorted(t.strip().lower() for t in intent.style_tags if t.strip())),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


def build_narrative_contract(
    narrative: SongNarrative,
    intent: UserIntent,
) -> NarrativeContract:
    """Congela el guion narrativo como contrato inmutable para el resto del grafo."""
    section_ids = [s.id for s in narrative.sections]
    if not section_ids:
        raise ValueError("narrative_contract requiere al menos una sección en el guion")

    return NarrativeContract(
        section_ids=section_ids,
        arc_type=narrative.arc_type,
        global_motif=list(narrative.global_motif),
        prompt_intent_signature=compute_prompt_intent_signature(intent),
    )


def _normalize_section_id(section_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", section_id.lower().strip()).strip("_")


def map_planner_sections_to_contract(
    planner_sections: list[str],
    contract_ids: list[str],
) -> tuple[dict[str, str], str]:
    """
    Mapea IDs del structure_planner → IDs canónicos del contrato.

    Returns:
        (planner_to_canonical, method) donde method describe la estrategia usada.

    Raises:
        SectionAlignmentError si el mapeo no es confiable.
    """
    if not planner_sections:
        raise SectionAlignmentError("structure.sections vacío")
    if not contract_ids:
        raise SectionAlignmentError("narrative_contract.section_ids vacío")

    if planner_sections == contract_ids:
        return {p: p for p in planner_sections}, "exact"

    planner_set = set(planner_sections)
    contract_set = set(contract_ids)
    if planner_set == contract_set:
        by_norm = {_normalize_section_id(c): c for c in contract_ids}
        mapping: dict[str, str] = {}
        for p in planner_sections:
            canon = by_norm.get(_normalize_section_id(p))
            if not canon:
                raise SectionAlignmentError(
                    f"ID de planner sin par canónico tras normalizar: {p!r}",
                )
            mapping[p] = canon
        if len(mapping) == len(planner_sections):
            return mapping, "normalized_reorder"
        raise SectionAlignmentError("mapeo normalizado incompleto")

    if len(planner_sections) != len(contract_ids):
        raise SectionAlignmentError(
            f"conteo distinto: planner={len(planner_sections)} "
            f"contrato={len(contract_ids)} — "
            f"planner={planner_sections!r} contrato={contract_ids!r}",
        )

    by_norm = {_normalize_section_id(c): c for c in contract_ids}
    mapping = {}
    used_canonical: set[str] = set()
    for p in planner_sections:
        canon = by_norm.get(_normalize_section_id(p))
        if canon and canon not in used_canonical:
            mapping[p] = canon
            used_canonical.add(canon)
        else:
            mapping[p] = ""

    if all(mapping.values()) and len(mapping) == len(contract_ids):
        return mapping, "normalized"

    if len(planner_sections) == len(contract_ids):
        positional = dict(zip(planner_sections, contract_ids))
        if len(set(positional.values())) == len(contract_ids):
            return positional, "positional"
        raise SectionAlignmentError("mapeo posicional con colisión de IDs canónicos")

    raise SectionAlignmentError(
        f"sin mapeo confiable: planner={planner_sections!r} contrato={contract_ids!r}",
    )


def _remap_bars(
    bars: dict[str, int],
    planner_to_canonical: dict[str, str],
    canonical_order: list[str],
) -> dict[str, int]:
    out: dict[str, int] = {}
    for planner_id, canon_id in planner_to_canonical.items():
        if planner_id in bars:
            out[canon_id] = bars[planner_id]
    for cid in canonical_order:
        if cid not in out:
            for key, val in bars.items():
                if _normalize_section_id(key) == _normalize_section_id(cid):
                    out[cid] = val
                    break
    return out


def _remap_narrative_sections(
    narrative: SongNarrative,
    planner_to_canonical: dict[str, str],
    canonical_order: list[str],
) -> list[SectionIntent]:
    by_planner = {s.id: s for s in narrative.sections}
    aligned: list[SectionIntent] = []
    for canon_id in canonical_order:
        planner_id = next(
            (p for p, c in planner_to_canonical.items() if c == canon_id),
            None,
        )
        if planner_id and planner_id in by_planner:
            aligned.append(by_planner[planner_id].model_copy(update={"id": canon_id}))
        elif canon_id in by_planner:
            aligned.append(by_planner[canon_id])
        else:
            matched = None
            for sec in narrative.sections:
                if _normalize_section_id(sec.id) == _normalize_section_id(canon_id):
                    matched = sec.model_copy(update={"id": canon_id})
                    break
            if matched is None:
                raise SectionAlignmentError(
                    f"SectionIntent no encontrada para sección canónica {canon_id!r}",
                )
            aligned.append(matched)
    if len(aligned) != len(canonical_order):
        raise SectionAlignmentError(
            f"no se pudieron alinear SectionIntent: "
            f"esperado {len(canonical_order)}, obtuvo {len(aligned)}",
        )
    return aligned


def align_structure_to_contract(
    structure: SongStructure,
    narrative: SongNarrative,
    contract: NarrativeContract,
) -> tuple[SongStructure, SongNarrative, SectionAlignment]:
    """
    Normaliza structure y narrative a los IDs canónicos del contrato.
    """
    canonical = list(contract.section_ids)
    planner_sections = list(structure.sections)
    planner_to_canonical, method = map_planner_sections_to_contract(
        planner_sections, canonical,
    )

    realigned = planner_sections != canonical or any(
        p != c for p, c in planner_to_canonical.items()
    )

    bars = _remap_bars(structure.bars_per_section, planner_to_canonical, canonical)
    if set(bars.keys()) != set(canonical):
        missing = set(canonical) - set(bars.keys())
        raise SectionAlignmentError(
            f"bars_per_section incompleto tras alinear; faltan: {sorted(missing)}",
        )

    total_bars = sum(bars[c] for c in canonical)
    aligned_structure = SongStructure(
        sections=canonical,
        bars_per_section=bars,
        total_bars=total_bars,
        estimated_duration_ms=structure.estimated_duration_ms,
    )

    aligned_narrative = narrative.model_copy(update={
        "sections": _remap_narrative_sections(narrative, planner_to_canonical, canonical),
        "arc_type": contract.arc_type,
        "global_motif": list(contract.global_motif),
    })

    alignment = SectionAlignment(
        planner_section_ids=planner_sections,
        mapping=planner_to_canonical,
        method=method,
        realigned=realigned,
    )
    return aligned_structure, aligned_narrative, alignment


def assert_sections_match_contract(
    structure: SongStructure,
    contract: NarrativeContract,
    *,
    context: str = "",
) -> None:
    """Assert obligatorio: igualdad de sets y orden del contrato."""
    prefix = f"{context}: " if context else ""
    if set(structure.sections) != set(contract.section_ids):
        raise AssertionError(
            f"{prefix}secciones distintas — "
            f"structure={structure.sections!r} contrato={contract.section_ids!r}",
        )
    if structure.sections != contract.section_ids:
        raise AssertionError(
            f"{prefix}orden de secciones distinto — "
            f"structure={structure.sections!r} contrato={contract.section_ids!r}",
        )


def contract_section_intent_map(
    narrative: SongNarrative | None,
    contract: NarrativeContract | None,
    *,
    context: str = "",
    request_id: str | None = None,
    state: dict | None = None,
) -> dict[str, SectionIntent]:
    """Mapa de intención por ID canónico; falla si falta una sección del contrato."""
    if not contract:
        if narrative and context:
            from cadence.observability.pipeline_log import log_narrative_contract_fallback

            trace_state = state if state is not None else (
                {"request_id": request_id} if request_id else None
            )
            if trace_state is not None:
                if request_id and not trace_state.get("request_id"):
                    trace_state["request_id"] = request_id
                log_narrative_contract_fallback(trace_state, node=context)
            else:
                logger.warning(
                    json.dumps(
                        {
                            "event": "narrative_contract_fallback",
                            "request_id": request_id,
                            "node": context,
                            "context": context,
                            "contract_section_ids_count": 0,
                            "message": (
                                "narrative_contract ausente; usando section_intent_map "
                                "(compatibilidad legacy)"
                            ),
                        },
                        ensure_ascii=False,
                    ),
                )
        from cadence.agent.nodes.narrative_apply import section_intent_map

        return section_intent_map(narrative)
    intents = {s.id: s for s in (narrative.sections if narrative else [])}
    out: dict[str, SectionIntent] = {}
    for sid in contract.section_ids:
        if sid not in intents:
            raise SectionAlignmentError(
                f"SectionIntent faltante para id canónico del contrato: {sid!r}",
            )
        out[sid] = intents[sid]
    return out


def section_intent_map_from_state(
    state: dict,
    *,
    context: str,
) -> dict[str, SectionIntent]:
    """Lee narrative + narrative_contract desde SongState."""
    return contract_section_intent_map(
        state.get("narrative"),
        state.get("narrative_contract"),
        context=context,
        request_id=state.get("request_id"),
        state=state,
    )
