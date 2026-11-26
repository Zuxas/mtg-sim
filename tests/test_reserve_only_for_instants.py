"""
test_reserve_only_for_instants.py -- Grixis Elementals does not hold lands
untapped for a card it cannot cast at instant speed.

reserve_mana tells the engine how many lands to leave untapped for the
opponent's turn. The APL used to reserve four lands whenever Deceit was in
hand. Deceit is a creature with evoke and no flash, so on the core engine
(which really leaves those lands untapped) the deck played four mana short
every turn and cast a third of its spells.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.grixis_elementals_standard_match import (
    DECEIT, REQUITING_HEX, GrixisElementalsStandardMatchAPL)
from engine.card_db import CardDB


class _Card:
    def __init__(self, name):
        self.name = name


class _GS:
    def __init__(self, *names):
        self.zones = type("Z", (), {"hand": [_Card(n) for n in names]})()
        self.mana_reserve = 99


def main():
    db = CardDB()
    deceit, hex_ = db.get(DECEIT), db.get(REQUITING_HEX)
    assert "Instant" not in deceit["type_line"] and "Flash" not in deceit["oracle_text"]
    assert "Instant" in hex_["type_line"] and hex_["mana_cost"] == "{B}"
    print("PASS: Deceit is not instant speed; Requiting Hex is an instant for {B}")

    apl = GrixisElementalsStandardMatchAPL()
    for hand, want in (((DECEIT,), 0), ((DECEIT, REQUITING_HEX), 1), ((), 0)):
        gs = _GS(*hand)
        apl.reserve_mana(gs, None)
        assert gs.mana_reserve == want, (hand, gs.mana_reserve)
    print("PASS: lands are reserved only for the instant")


def other_decks():
    """The same defect in two more decks (found by auditing every reserve rule
    against the card data)."""
    from apl.izzet_spellementals_standard_match import (
        SUNDERFLOCK, IzzetSpellementalsStandardMatchAPL)
    from apl.sultai_control_standard_match import (
        KILL_PRIORITY, SultaiControlStandardMatchAPL)
    from data.card import Card, Tag
    db = CardDB()
    flock = db.get(SUNDERFLOCK)
    assert "Creature" in flock["type_line"] and "Flash" not in flock["oracle_text"]

    def opp_with(name):
        c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
                 power="2", toughness="2")
        c.tags = {Tag.CREATURE}
        return type("GS", (), {"zones": type("Z", (), {"battlefield": [c]})()})()

    gs = _GS(SUNDERFLOCK)
    IzzetSpellementalsStandardMatchAPL().reserve_mana(gs, opp_with("Bear"))
    assert gs.mana_reserve == 0, gs.mana_reserve
    print("PASS: Izzet Spellementals holds no lands for Sunderflock")

    gs = _GS(DECEIT)
    SultaiControlStandardMatchAPL().reserve_mana(gs, opp_with(KILL_PRIORITY[0]))
    assert gs.mana_reserve == 0, gs.mana_reserve
    print("PASS: Sultai Control holds no lands for Deceit")


if __name__ == "__main__":
    other_decks()
    main()
