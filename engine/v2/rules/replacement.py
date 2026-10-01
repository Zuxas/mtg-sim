"""Enters-the-battlefield replacement effects of the supported lands (CR 614.1c-d, 614.12).
Pure. Applied by the game inside the SAME transition as the zone change.

- Inspiring Vantage: "This land enters tapped unless you control two or fewer other lands."
  (CR 614.1d) -- counted from the battlefield BEFORE it enters, so every land counted is an
  "other" land.
- Sacred Foundry: "As this land enters, you may pay 2 life. If you don't, it enters tapped."
  (CR 614.1c) -- the controller chooses before the move commits; paying is possible only with
  at least 2 life (CR 119.4).
"""
from __future__ import annotations

ENTRY = {"inspiring_vantage": "fastland", "sacred_foundry": "shockland"}
SHOCK_LIFE = 2


def entry_kind(state, oid):
    return ENTRY.get(state.definition(oid).effect_key)


def needs_entry_choice(state, oid) -> bool:
    return entry_kind(state, oid) == "shockland"


def can_pay_shock(state, player) -> bool:
    return state.life[player] >= SHOCK_LIFE


def other_lands(state, controller) -> int:
    return sum(1 for x in state.zones[("bf",)]
               if state.objects[x].controller == controller and state.definition(x).is_land)


def enters_tapped(state, oid, controller, pay) -> bool:
    kind = entry_kind(state, oid)
    if kind == "fastland":
        return other_lands(state, controller) > 2
    if kind == "shockland":
        return not pay
    return False
