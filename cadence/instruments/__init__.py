"""Auto-registro de todos los instrumentos compositores."""

import cadence.instruments.drums  # noqa: F401
import cadence.instruments.bass  # noqa: F401
import cadence.instruments.pad_inst  # noqa: F401
import cadence.instruments.melody_inst  # noqa: F401
import cadence.instruments.fx_riser  # noqa: F401
import cadence.instruments.perc_aux  # noqa: F401
import cadence.instruments.countermelody  # noqa: F401
import cadence.instruments.echo_synth  # noqa: F401
import cadence.instruments.arp_synth  # noqa: F401
import cadence.instruments.chord_stab  # noqa: F401
import cadence.instruments.synth_pluck  # noqa: F401

from cadence.instruments.registry import (
    compose_layer,
    get_instrument,
    list_instruments,
    register,
    InstrumentDefinition,
)
from cadence.instruments.context import ComposeContext, build_compose_context

__all__ = [
    "ComposeContext",
    "InstrumentDefinition",
    "build_compose_context",
    "compose_layer",
    "get_instrument",
    "list_instruments",
    "register",
]
