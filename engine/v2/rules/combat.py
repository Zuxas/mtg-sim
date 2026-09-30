"""Combat (CR 508-511). Pure."""
from __future__ import annotations

from itertools import product


def eligible_attackers(state) -> list:
    """CR 508.1a / 302.6 / 702.10b: untapped creatures the active player has controlled
    continuously since the turn began, or with haste."""
    out = []
    for oid in state.battlefield():
        o = state.objects[oid]
        d = state.definition(oid)
        if not d.is_creature or o.controller != state.active or o.tapped:
            continue
        if o.controlled_since < state.turn or d.has("Haste"):
            out.append(oid)
    return sorted(out)


def can_block(state, blocker, attacker) -> bool:
    """CR 509.1a untapped; CR 702.9b flying."""
    if state.definition(attacker).has("Flying") and not state.definition(blocker).has("Flying"):
        return False
    return True


def potential_blockers(state) -> list:
    defender = 1 - state.active
    out = []
    for oid in state.battlefield():
        o = state.objects[oid]
        if o.controller == defender and not o.tapped and state.definition(oid).is_creature:
            if any(can_block(state, oid, a) for a in state.attackers if a in state.objects):
                out.append(oid)
    return sorted(out)


def has_first_strike(state, oid) -> bool:
    return state.definition(oid).has("First strike")


def combat_creatures(state) -> list:
    alive = [a for a in state.attackers if a in state.objects and state.objects[a].zone == "battlefield"]
    alive += [b for b in state.blocks if b in state.objects and state.objects[b].zone == "battlefield"]
    return alive


def any_first_strike(state) -> bool:
    return any(has_first_strike(state, c) for c in combat_creatures(state))


def deals_damage_now(state, oid, first_step: bool) -> bool:
    """CR 510.4 / 702.7b: in the first-strike step only first strikers; in the second
    step only creatures without first strike (if a first-strike step happened)."""
    if first_step:
        return has_first_strike(state, oid)
    if state.first_strike_done:
        return not has_first_strike(state, oid)
    return True


def living_blockers(state, attacker) -> list:
    return sorted(b for b, a in state.blocks.items()
                  if a == attacker and b in state.objects and state.objects[b].zone == "battlefield")


def divisions(power: int, blockers: list) -> list:
    """Every division of `power` among `blockers` (CR 510.1c: as its controller chooses)."""
    k = len(blockers)
    out = []
    for parts in product(range(power + 1), repeat=k):
        if sum(parts) == power:
            out.append(tuple(zip(blockers, parts)))
    return out
