"""Nodo de orquestación — compone todas las capas vía registry."""

from cadence.schemas.song_state import SongState, Track


def compose_orchestra_node(state: SongState) -> dict:
    """
    Itera ArrangementPlan.layers y compone cada instrumento registrado.
    Respeta repair_layers para re-generación parcial en el repair loop.
    """
    import cadence.instruments  # noqa: F401 — registra instrumentos
    from cadence.instruments import build_compose_context, compose_layer, get_instrument

    arrangement = state.get("arrangement")
    if not arrangement:
        return {}

    repair_layers = state.get("repair_layers")
    layers = arrangement.layers

    if repair_layers:
        repair_set = set(repair_layers)
        layers = [l for l in layers if l.instrument_id in repair_set]

    compose_ids = {l.instrument_id for l in layers}
    tracks: list[Track] = [
        t for t in state.get("tracks", [])
        if t.id not in compose_ids
    ]

    ordered = sorted(
        layers,
        key=lambda l: (1 if get_instrument(l.instrument_id).requires_llm else 0, l.instrument_id),
    )

    for layer in ordered:
        ctx = build_compose_context(state, layer)
        if not ctx.active_sections() and layer.min_density > 0:
            continue
        track = compose_layer(ctx)
        if track and track.events:
            tracks.append(track)

    return {"tracks": tracks, "repair_layers": None}
