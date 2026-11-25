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


if __name__ == "__main__":
    main()
