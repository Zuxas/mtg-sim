"""test_swap_cards.py -- issue #33.

MTGSim.test_swap renamed a copy of the outgoing card, so 'Path to Exile'
was simulated as a 1-mana red burn spell with Lightning Bolt's text.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from data import deck as deck_loader
from api.sim_api import swap_cards

FAKE_DB = {
    "Path to Exile": {"name": "Path to Exile", "mana_cost": "{W}", "cmc": 1.0,
                      "type_line": "Instant", "colors": ["W"],
                      "oracle_text": "Exile target creature. Its controller may search ..."},
    "Mountain": {"name": "Mountain", "mana_cost": "", "cmc": 0.0,
                 "type_line": "Basic Land - Mountain", "oracle_text": "", "colors": []},
}


def _bolt():
    return Card(name="Lightning Bolt", mana_cost="{R}", cmc=1, type_line="Instant",
                oracle_text="Lightning Bolt deals 3 damage to any target.", colors=["R"])


def _bear():
    return Card(name="Grizzly Bears", mana_cost="{1}{G}", cmc=2, type_line="Creature - Bear",
                oracle_text="", power="2", toughness="2", colors=["G"])


def _deck():
    return [_bolt() for _ in range(4)] + [_bear() for _ in range(4)]


def _with_fake_db(fn):
    real = deck_loader._get_cards_local
    deck_loader._get_cards_local = lambda names: {n: FAKE_DB[n] for n in names if n in FAKE_DB}
    saved = os.environ.pop("MTG_SIM_ALLOW_UNRESOLVED", None)
    try:
        return fn()
    finally:
        deck_loader._get_cards_local = real
        if saved is not None:
            os.environ["MTG_SIM_ALLOW_UNRESOLVED"] = saved


def test_incoming_card_is_the_real_card():
    deck = _deck()
    var = _with_fake_db(lambda: swap_cards(deck, "lightning bolt", "Path to Exile"))
    path = [c for c in var if c.name == "Path to Exile"]
    assert len(path) == 1 and len([c for c in var if c.name == "Lightning Bolt"]) == 3
    p = path[0]
    assert (p.mana_cost, p.type_line, p.colors) == ("{W}", "Instant", ["W"])
    assert p.oracle_text.startswith("Exile target creature")
    assert len(var) == len(deck) and len([c for c in deck if c.name == "Lightning Bolt"]) == 4, \
        "the original deck is not modified"


def test_creature_swapped_for_a_land_is_a_land():
    var = _with_fake_db(lambda: swap_cards(_deck(), "Grizzly Bears", "Mountain"))
    land = next(c for c in var if c.name == "Mountain")
    assert land.is_land() and not land.power and not land.toughness


def test_count_swaps_that_many_copies():
    var = _with_fake_db(lambda: swap_cards(_deck(), "Lightning Bolt", "Path to Exile", count=3))
    assert sum(c.name == "Path to Exile" for c in var) == 3
    assert sum(c.name == "Lightning Bolt" for c in var) == 1
    assert len({id(c) for c in var if c.name == "Path to Exile"}) == 3, "separate Card objects"


def _raises(fn, needle):
    try:
        _with_fake_db(fn)
    except ValueError as e:
        assert needle in str(e), str(e)
        return
    raise AssertionError("expected ValueError")


def test_unknown_card_out_raises():
    _raises(lambda: swap_cards(_deck(), "Counterspell", "Path to Exile"), "Counterspell")


def test_too_many_copies_raises():
    _raises(lambda: swap_cards(_deck(), "Lightning Bolt", "Path to Exile", count=5), "has 4")


def test_bad_count_raises():
    for bad in (0, -1, 1.5):
        _raises(lambda: swap_cards(_deck(), "Lightning Bolt", "Path to Exile", count=bad), "count")


def test_unknown_card_in_raises():
    _raises(lambda: swap_cards(_deck(), "Lightning Bolt", "Pathh to Exile"), "Pathh to Exile")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_swap_cards: OK")
