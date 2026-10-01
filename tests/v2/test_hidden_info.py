"""Milestone four, S0: hidden information stays out of the event log. Observations were already
hidden-information safe; the log is now too: card creation does not link objects to card names,
moves between hidden zones (library / hand) carry a keyed commitment instead of the card identity,
and private library decisions log only commitments. Transition hashes still commit to the hidden
content (different hidden cards -> different hashes)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import reducer
from engine.v2.decklists import main_deck
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy

HIDDEN = ("library", "hand")


def _game(seed=3):
    b = main_deck("mono_red_aggro_modern")
    g = Game.new(b, b, seed, starting_player=0)
    g.run([SimpleAggroPolicy(1), RandomLegalPolicy(2)])
    return g


def test_card_creation_does_not_link_objects_to_names():
    g = _game()
    created = [dict(e.data) for t in g.s.log.transitions for e in t.events if e.kind == "CardCreated"]
    assert created and all("oid" not in d for d in created)
    assert all({"ciid", "name", "owner", "commitment"} <= set(d) for d in created)


def test_moves_between_hidden_zones_carry_no_card_identity():
    g = _game()
    hidden = 0
    for t in g.s.log.transitions:
        for e in t.events:
            if e.kind != "ZoneChanged":
                continue
            d = dict(e.data)
            if d["frm"] in HIDDEN and d["to"] in HIDDEN:
                hidden += 1
                assert "ciid" not in d and "name" not in d and len(d["commitment"]) == 16
            else:
                assert "ciid" in d                                    # public moves stay auditable
    assert hidden >= 14                                               # at least both opening hands


def test_hidden_moves_still_commit_to_their_content():
    b = main_deck("mono_red_aggro_modern")
    heads = set()
    for pick in (0, 5):
        g = Game.new(b, b, 11, starting_player=0)
        lib = g.s.zones[(0, "library")]
        reducer.commit(g.s, "probe", [op("move", lib[pick], "hand", "end")])
        heads.add(g.s.log.head)
    lib = Game.new(b, b, 11, starting_player=0).s.zones[(0, "library")]
    assert len(heads) == 2 or lib[0] == lib[5]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("HIDDEN INFO TESTS PASS")
