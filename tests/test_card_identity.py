"""A Card is a game object, not a value: two copies of the same printed card
are two different cards, and zone operations act on the one they are given.

Run: python tests/test_card_identity.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.game_state import GameState
from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
import engine.card_handlers_verified  # noqa: F401  (registers handlers)


def card(name, cost="", cmc=0, type_line="Creature", text=""):
    return Card(name, mana_cost=cost, cmc=cmc, type_line=type_line, oracle_text=text)


def state():
    gs = GameState(mainboard=[], on_play=True)
    gs.zones.library = [card(f"Filler {i}", type_line="Sorcery") for i in range(30)]
    return gs


def zones_of(gs, c):
    return [z for z in ("hand", "battlefield", "graveyard", "exile", "library")
            if any(x is c for x in getattr(gs.zones, z))]


# --- the basics --------------------------------------------------------------
a, b = card("Ocelot Pride", "{W}", 1), card("Ocelot Pride", "{W}", 1)
assert a != b and a == a and a not in [b] and [a, b].index(b) == 1
assert len({a, b}) == 2                      # hashable, by identity

# --- battlefield: removal, sacrifice, death take the card they are given ------
gs = state()
gs.zones.battlefield += [a, b]
gs.zones.battlefield.remove(b)
assert [x is a for x in gs.zones.battlefield] == [True]

# --- hand: discarding the second copy leaves the first -----------------------
gs = state()
h1, h2 = card("Lightning Bolt", "{R}", 1, "Instant"), card("Lightning Bolt", "{R}", 1, "Instant")
gs.zones.hand += [h1, h2]
gs.zones.remove_from_hand(h2)
assert [x is h1 for x in gs.zones.hand] == [True]

# --- a handler that moves one of two identical cards between zones -----------
# Arboreal Grazer puts a land from hand onto the battlefield tapped. With two
# identical lands in hand the land it moved used to stay in hand as well (its
# twin was removed instead), and was then played a second time already tapped.
gs = state()
l1, l2 = (card("Crumbling Vestige", type_line="Land") for _ in range(2))
gs.zones.hand += [l1, l2]
grazer = card("Arboreal Grazer", "{G}", 1, "Creature - Sloth Beast")
gs.zones.battlefield.append(grazer)
ETB_EFFECTS["Arboreal Grazer"](gs, grazer)
moved = [c for c in (l1, l2) if zones_of(gs, c) == ["battlefield"]]
stayed = [c for c in (l1, l2) if zones_of(gs, c) == ["hand"]]
assert len(moved) == 1 and len(stayed) == 1, [(zones_of(gs, c)) for c in (l1, l2)]
assert moved[0].tapped and not stayed[0].tapped

# --- a handler that recasts a graveyard card whose twin is in hand ------------
# 'Flashback' recasts the best instant/sorcery in the graveyard. It must cast
# THAT card and leave the identical copy in hand alone.
if "Flashback" in SPELL_EFFECTS:
    gs = state()
    in_gy = card("Lightning Helix", "{R}{W}", 2, "Instant")
    in_hand = card("Lightning Helix", "{R}{W}", 2, "Instant")
    gs.zones.graveyard.append(in_gy)
    gs.zones.hand.append(in_hand)
    SPELL_EFFECTS["Flashback"](gs, card("Flashback", "{R}", 1, "Sorcery"))
    assert zones_of(gs, in_hand) == ["hand"], zones_of(gs, in_hand)
    assert zones_of(gs, in_gy) in (["hand"], ["graveyard"]), zones_of(gs, in_gy)   # never lost
    assert len(zones_of(gs, in_gy)) == 1

# --- mulligan: two copies can both go to the bottom ---------------------------
from apl.boros_energy import BorosEnergyAPL
p1, p2 = (card("Seasoned Pyromancer", "{1}{R}{R}", 3, "Creature - Human Shaman") for _ in range(2))
hand = [p1, p2] + [card("Mountain", type_line="Basic Land - Mountain") for _ in range(3)] \
       + [card("Guide of Souls", "{W}", 1), card("Ocelot Pride", "{W}", 1)]
bottomed = BorosEnergyAPL().bottom(hand, 2)
assert len(bottomed) == 2 and len({id(c) for c in bottomed}) == 2
assert {id(c) for c in bottomed} == {id(p1), id(p2)}, [c.name for c in bottomed]

print("test_card_identity: OK")
