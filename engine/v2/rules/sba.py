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
    for oid in list(state.battlefield()):
        d = state.definition(oid)
        if not d.is_creature:
            continue
        t = state.toughness(oid)
        if t <= 0:                                                    # CR 704.5f
            ops.append(op("move", oid, "graveyard", "end"))
        elif state.objects[oid].damage >= t:                          # CR 704.5g
            ops.append(op("note", "Destroyed", oid))
            ops.append(op("move", oid, "graveyard", "end"))
    for p, reason in losers:
        ops.append(op("lose", p, reason))
    for p in (0, 1):
        if state.draw_failed[p]:
            ops.append(op("clear_draw_failed", p))
    return ops, losers
