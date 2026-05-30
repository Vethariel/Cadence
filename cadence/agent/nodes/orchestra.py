"""Nodo de orquestación — compone todas las capas vía registry."""

from cadence.schemas.song_state import SongState, Track


def compose_orchestra_node(state: SongState) -> dict:
    """
    Itera ArrangementPlan.layers y compone cada instrumento registrado.
    Respeta repair_layers para re-generación parcial en el repair loop.
    """
    import cadence.instruments  # noqa: F401 — registra instrumentos
    from cadence.instruments import build_compose_context, compose_layer, get_instrument
    from cadence.music.narrative_contract import assert_sections_match_contract

    structure = state.get("structure")
    contract = state.get("narrative_contract")
    if structure and contract:
        assert_sections_match_contract(structure, contract, context="compose_orchestra")

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
    compose_state = dict(state)
    compose_state["tracks"] = tracks

    def _sort_key(layer):
        iid = layer.instrument_id
        if iid == "echo_synth":
            return (2, iid)
        if get_instrument(iid).requires_llm:
            return (1, iid)
        return (0, iid)

    ordered = sorted(layers, key=_sort_key)

    def _compose_one(layer) -> None:
        ctx = build_compose_context(compose_state, layer)
        if not ctx.active_sections() and layer.min_density > 0:
            return
        track = compose_layer(ctx)
        if track and track.events:
            tracks.append(track)
            compose_state["tracks"] = tracks

    for layer in ordered:
        _compose_one(layer)

    present = {t.id for t in tracks}
    for layer in layers:
        iid = layer.instrument_id
        if iid in present:
            continue
        _compose_one(layer)

    return {"tracks": tracks, "repair_layers": None}
