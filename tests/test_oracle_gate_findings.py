"""Three gaps the oracle gate found on 2026-11-19, each checked on the APL:

  - Goryo's Vengeance exiles the reanimated creature at our end step
    (unless Ephemerate blinked it);
  - Cultivator Colossus puts lands in tapped (untapped with Amulet of Vigor);
  - Strix Serenade's Bird token has flying.

Run: python tests/test_oracle_gate_findings.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.game_state import GameState
from engine.keywords import KWTag, get_keywords


def card(name, cost="", cmc=0, type_line="Creature", text=""):
    return Card(name, mana_cost=cost, cmc=cmc, type_line=type_line, oracle_text=text)


def state():
    gs = GameState(mainboard=[], on_play=True)
    gs.zones.library = [card(f"Filler {i}", type_line="Sorcery") for i in range(30)]
    return gs


# --- Goryo's Vengeance -------------------------------------------------------
from apl import goryos_match as G

def goryo(with_ephemerate, white_source=True):
    apl = G.GoryosMatchAPL()
    gs, opp = state(), state()
    fatty = card(G.GRISELBRAND, "{4}{B}{B}{B}{B}", 8, "Legendary Creature - Demon")
    gs.zones.graveyard.append(fatty)
    gs.zones.battlefield += [card("Swamp", type_line="Basic Land - Swamp") for _ in range(2)]
    gs.zones.hand.append(card(G.GORYOS, "{1}{B}", 2, "Instant - Arcane"))
    if with_ephemerate:
        gs.zones.hand.append(card(G.EPHEMERATE, "{W}", 1, "Instant"))
        if white_source:
            gs.zones.battlefield.append(card("Plains", type_line="Basic Land - Plains"))
    apl.main_phase_match(gs, opp)
    assert any(c is fatty for c in gs.zones.battlefield), "combo did not fire"
    apl.own_end_step(gs, opp)
    return fatty, gs

fatty, gs = goryo(False)
assert not any(c is fatty for c in gs.zones.battlefield) and any(c is fatty for c in gs.zones.exile)
fatty, gs = goryo(True)
assert any(c is fatty for c in gs.zones.battlefield), "Ephemerate should keep it"
fatty, gs = goryo(True, white_source=False)   # Ephemerate is not free
assert any(c is fatty for c in gs.zones.exile) and any(c.name == G.EPHEMERATE for c in gs.zones.hand)

# --- Cultivator Colossus -----------------------------------------------------
from apl import amulet_titan_match as A

def colossus(with_amulet):
    apl = A.AmuletTitanMatchAPL()
    gs = state()
    forest = card("Forest", type_line="Basic Land - Forest")
    gs.zones.hand.append(forest)
    if with_amulet:
        gs.zones.battlefield.append(card(A.AMULET, "{1}", 1, "Artifact"))
    apl._trigger_creature_etb(gs, state(), card(A.COLOSSUS, "{4}{G}{G}{G}", 7, "Creature - Plant Beast"))
    assert forest in gs.zones.battlefield
    return forest

assert colossus(False).tapped is True
assert colossus(True).tapped is False

# --- Strix Serenade ----------------------------------------------------------
import inspect
from apl import jeskai_blink_match as J
src = inspect.getsource(J)
i = src.index('Card("Bird Token"')
assert 'oracle_text="Flying"' in src[i:i + 200]
bird = Card("Bird Token", mana_cost=None, cmc=0, type_line="Token Creature - Bird", oracle_text="Flying")
assert KWTag.FLYING in get_keywords(bird)

print("test_oracle_gate_findings: OK")
