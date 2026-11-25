"""Unholy Heat deals 2 damage, or 6 with delirium, and is not cast on a
creature it cannot kill. Goryo's Vengeance needs black mana.

Run: python tests/test_heat_damage_and_goryo_black.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.game_state import GameState
from apl import goryos_match as G
from apl import murktide_match as M


def card(name, cost="", cmc=0, type_line="Creature", p=None, t=None):
    c = Card(name, mana_cost=cost, cmc=cmc, type_line=type_line)
    c.power, c.toughness = p, t
    return c


def state(lands):
    gs = GameState(mainboard=[], on_play=True)
    gs.zones.library = [card(f"Filler {i}", type_line="Sorcery") for i in range(30)]
    gs.zones.battlefield += [card(n, type_line=f"Basic Land - {n}") for n in lands]
    gs.tap_lands()
    return gs


def heat(graveyard_types, toughness):
    apl = M.MurktideMatchAPL()
    gs, opp = state(["Mountain"]), state([])
    gs.zones.graveyard += [card(f"gy {t}", type_line=t) for t in graveyard_types]
    gs.zones.hand.append(card(M.UNHOLY, "{R}", 1, "Instant"))
    big = card("Big", "{3}", 3, "Creature - Beast", "4", str(toughness))
    opp.zones.battlefield.append(big)
    apl._use_removal(gs, opp)
    return big in opp.zones.battlefield, any(c.name == M.UNHOLY for c in gs.zones.hand)

# no delirium: 2 damage does not kill a 4/4, and the spell stays in hand
assert heat(["Instant", "Sorcery"], 4) == (True, True)
# no delirium: kills a 4/2
assert heat(["Instant", "Sorcery"], 2) == (False, False)
# delirium: 6 damage kills a 4/6 but not a 4/7
four = ["Instant", "Sorcery", "Creature", "Land"]
assert heat(four, 6) == (False, False)
assert heat(four, 7) == (True, True)


def goryo(lands):
    apl = G.GoryosMatchAPL()
    gs, opp = state(lands), state([])
    fatty = card(G.GRISELBRAND, "{4}{B}{B}{B}{B}", 8, "Legendary Creature - Demon", "7", "7")
    gs.zones.graveyard.append(fatty)
    gs.zones.hand.append(card(G.GORYOS, "{1}{B}", 2, "Instant - Arcane"))
    gs.land_played = True
    apl.main_phase_match(gs, opp)
    return any(c is fatty for c in gs.zones.battlefield)

assert goryo(["Swamp", "Plains"]) is True
assert goryo(["Plains", "Island"]) is False   # two lands, no black

print("test_heat_damage_and_goryo_black: OK")

# removal takes out the creature it targeted, not an equal-looking twin
apl = M.MurktideMatchAPL()
gs, opp = state(["Mountain"]), state([])
gs.zones.hand.append(card(M.UNHOLY, "{R}", 1, "Instant"))
plain = card("Ocelot Pride", "{W}", 1, "Creature - Cat", "1", "1")
pumped = card("Ocelot Pride", "{W}", 1, "Creature - Cat", "1", "1")
pumped._lord_power_bonus = pumped._lord_toughness_bonus = 1   # a plain attribute, not a field
assert plain is not pumped   # same printed card, two game objects
opp.zones.battlefield += [plain, pumped]
apl._use_removal(gs, opp)
assert [c is plain for c in opp.zones.battlefield] == [True], "the 1/1 twin must survive"
assert [c is pumped for c in opp.zones.graveyard] == [True]
print("identity: OK")
