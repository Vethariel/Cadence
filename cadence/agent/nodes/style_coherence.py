"""Verificación de coherencia timbral tras instrument_planner."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from cadence.config import settings
from cadence.music.instrument_catalog import (
    get_timbres,
    resolve_timbre,
    timbre_programs,
    validate_orchestration,
)
from cadence.music.style_profile import format_profile_for_llm
from cadence.schemas.song_state import (
    OrchestrationPlan,
    SongState,
    StyleCoherenceVerdict,
    TimbreFix,
)


def _format_plan_timbres(plan: OrchestrationPlan) -> str:
    lines = [f"Concepto: {plan.ensemble_concept or '—'}"]
    for a in plan.instruments:
        if not a.active:
            continue
        if a.instrument_id in ("drums", "perc_aux"):
            lines.append(f"  • {a.instrument_id} (percusión)")
            continue
        lines.append(f"  • {a.instrument_id}: gm {a.gm_program} — {a.display_name}")
    lines.append(f"drum_pattern={plan.drum_pattern} bass_pattern={plan.bass_pattern}")
    return "\n".join(lines)


def apply_timbre_fixes(
    plan: OrchestrationPlan,
    fixes: list[TimbreFix],
    *,
    generation_seed: int,
) -> OrchestrationPlan:
    """Aplica correcciones GM validadas contra el catálogo."""
    if not fixes:
        return plan

    by_id = {a.instrument_id: a for a in plan.instruments}
    for fix in fixes:
        if fix.instrument_id not in by_id:
            continue
        allowed = timbre_programs(fix.instrument_id)
        if fix.gm_program not in allowed:
            continue
        prog, name = resolve_timbre(
            fix.instrument_id,
            fix.gm_program,
            generation_seed=generation_seed,
        )
        item = by_id[fix.instrument_id]
        by_id[fix.instrument_id] = item.model_copy(
            update={"gm_program": prog, "display_name": name},
        )

    return plan.model_copy(
        update={"instruments": [by_id[a.instrument_id] for a in plan.instruments]},
    )


def style_coherence_node(state: SongState) -> dict:
    """
    Revisa que timbres y patrones encajen con el prompt y el perfil de estilo.
    Aplica correcciones GM sugeridas por el LLM.
    """
    intent = state["intent"]
    profile = state.get("style_profile")
    plan = state.get("orchestration_plan")
    proposal = state.get("technical_proposal")
    seed = state.get("generation_seed", 0)

    if not plan:
        return {
            "style_coherence": StyleCoherenceVerdict(
                passed=False,
                issues=["Sin orchestration_plan"],
            ),
        }

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
        temperature=0.2,
    ).with_structured_output(StyleCoherenceVerdict)

    timbre_lines = []
    for iid in sorted({a.instrument_id for a in plan.instruments if a.active}):
        opts = get_timbres(iid)
        if len(opts) <= 12:
            timbre_lines.append(
                f"[{iid}] " + ", ".join(f"{p}:{n}" for p, n in opts),
            )
        else:
            timbre_lines.append(
                f"[{iid}] " + ", ".join(f"{p}:{n}" for p, n in opts[:10]) + ", …",
            )

    system = SystemMessage(content=(
        "Verificas coherencia timbral de una orquestación de videojuego.\n"
        "Compara el plan con el prompt y el perfil de estilo.\n\n"
        "Si hay incoherencias (ej. calliope en boss dubstep, pad orquestal en techno), "
        "devuelve passed=false, issues breves, y timbre_fixes con gm_program del catálogo.\n"
        "melody y chord_stab NO pueden compartir el mismo gm_program.\n"
        "Solo propón fixes para instrumentos melódicos/pad/fx — no drums.\n"
        "Si todo encaja, passed=true y listas vacías.\n"
        "Responde SOLO con el objeto estructurado."
    ))

    human = HumanMessage(content=(
        f"Prompt: {intent.raw_prompt}\n"
        f"Uso: {intent.use_case} | Energía: {proposal.energy_level if proposal else 3}/5\n\n"
        f"{format_profile_for_llm(profile)}\n\n"
        f"Plan actual:\n{_format_plan_timbres(plan)}\n\n"
        "Catálogo resumido:\n" + "\n".join(timbre_lines[:14]),
    ))

    verdict: StyleCoherenceVerdict = llm.invoke([system, human])
    fixed_plan = apply_timbre_fixes(plan, verdict.timbre_fixes, generation_seed=seed)

    energy = proposal.energy_level if proposal else 3
    validated = validate_orchestration(
        fixed_plan,
        use_case=intent.use_case,
        energy_level=energy,
        genre_tags=[],
        generation_seed=seed,
        style_profile=profile,
    )

    return {
        "orchestration_plan": validated,
        "style_coherence": verdict,
    }


def route_after_style_coherence(state: SongState) -> str:
    """Reintenta instrument_planner una vez si la coherencia falla sin fixes."""
    verdict = state.get("style_coherence")
    retries = state.get("style_coherence_retries", 0)
    if (
        verdict
        and not verdict.passed
        and not verdict.timbre_fixes
        and retries < 1
    ):
        return "instrument_planner"
    return "arrangement_planner"
