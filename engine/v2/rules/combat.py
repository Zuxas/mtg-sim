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
        if o.controlled_since < state.turn or state.has_kw(oid, "Haste"):
            out.append(oid)
    return sorted(out)


def can_block(state, blocker, attacker) -> bool:
    """CR 509.1a untapped; CR 702.9b flying."""
    if state.has_kw(attacker, "Flying") and not state.has_kw(blocker, "Flying"):
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
    return state.has_kw(oid, "First strike")                          # printed or gained (CR 702.7b)


def has_double_strike(state, oid) -> bool:
    return state.has_kw(oid, "Double strike")


def strikes_first(state, oid) -> bool:
    return has_first_strike(state, oid) or has_double_strike(state, oid)


def combat_creatures(state) -> list:
    alive = [a for a in state.attackers if a in state.objects and state.objects[a].zone == "battlefield"]
    alive += [b for b in state.blocks if b in state.objects and state.objects[b].zone == "battlefield"]
    return alive


def any_first_strike(state) -> bool:
    return any(strikes_first(state, c) for c in combat_creatures(state))


def deals_damage_now(state, oid, first_step: bool) -> bool:
    """CR 510.4 / 702.4b / 702.7b: the first combat damage step has only creatures with first
    strike or double strike; the second has those that had neither as the first step began,
    plus those that currently have double strike."""
    if first_step:
        return strikes_first(state, oid)
    if state.first_strike_done:
        return oid not in state.first_step_strikers or has_double_strike(state, oid)
    return True


def living_blockers(state, attacker) -> list:
    return sorted(b for b, a in state.blocks.items()
                  if a == attacker and b in state.objects and state.objects[b].zone == "battlefield")


def divisions(power: int, blockers: list, lethal=None) -> list:
    """Every division of `power` among `blockers` (CR 510.1c: as its controller chooses). With
    trample (`lethal` = lethal damage per blocker, given), the division may also assign damage to the
    defending player -- the ("player", n) entry -- but only once every blocker is assigned lethal
    damage (CR 702.19b)."""
    k = len(blockers)
    out = []
    if lethal is None:
        for parts in product(range(power + 1), repeat=k):
            if sum(parts) == power:
                out.append(tuple(zip(blockers, parts)))
        return out
    for parts in product(range(power + 1), repeat=k + 1):
        if sum(parts) != power:
            continue
        to_player = parts[-1]
        if to_player and any(parts[i] < lethal[i] for i in range(k)):
            continue
        out.append(tuple(zip(blockers, parts[:k])) + (("player", to_player),))
    return out


def has_trample(state, oid) -> bool:
    return state.has_kw(oid, "Trample")


def lethal_damage(state, oid) -> int:
    """Damage that is lethal now, counting damage already marked (CR 702.19b, 120.6)."""
    return max(0, state.toughness(oid) - state.objects[oid].damage)
