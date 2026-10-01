"""State-based actions (CR 704), computed on the whole state and applied as ONE atomic
transition (CR 117.5). Pure: returns ops."""
from __future__ import annotations

from engine.v2.ops import op


def compute(state) -> tuple:
    """(ops, losers). ops empty when no SBA applies."""
    ops, losers = [], []
    for p in (0, 1):
        if state.lost[p] is not None:
            continue
        if state.life[p] <= 0:                                        # CR 704.5a
            losers.append((p, "life"))
        elif state.draw_failed[p]:                                    # CR 704.5b
            losers.append((p, "draw_from_empty_library"))
    objs, defs = state.objects, state.def_by_ciid
    for oid in list(state.zones[("bf",)]):
        o = objs[oid]
        d = defs[o.ciid]
        if not d.is_creature:
            continue
        t = (d.toughness or 0) + o.eot_toughness
        if t <= 0:                                                    # CR 704.5f
            ops.append(op("move", oid, "graveyard", "end"))
        elif o.damage >= t and not state.has_effect("indestructible", oid):   # 704.5g, 702.12b
            ops.append(op("note", "Destroyed", oid))
            ops.append(op("move", oid, "graveyard", "end"))
    for p, reason in losers:
        ops.append(op("lose", p, reason))
    for p in (0, 1):
        if state.draw_failed[p]:
            ops.append(op("clear_draw_failed", p))
    return ops, losers
