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


OFFSET = 10 ** 6


def _game(seed=3, deck="mono_red_aggro_modern"):
    """A full game; returns (game, every ObjectId that ever existed in a library or hand)."""
    b = main_deck(deck)
    g = Game.new(b, b, seed, starting_player=0)
    pols = [SimpleAggroPolicy(1), RandomLegalPolicy(2)]
    hidden = set()

    def note():
        for p in (0, 1):
            for z in HIDDEN:
                hidden.update(g.s.zones[(p, z)])
    note()
    while g.result is None:
        p = g.pending().player
        g.apply(pols[p].choose(g.observe(p), g.legal_actions()))
        note()
    return g, hidden


def _ints(v):
    if isinstance(v, bool):
        return
    if isinstance(v, int):
        yield v
    elif isinstance(v, (tuple, list)):
        for x in v:
            yield from _ints(x)
    elif isinstance(v, str) and v[:1] == "O" and v[1:].isdigit():   # "O<oid>" stack ids (not "P<n>" / "A<n>")
        yield int(v[1:])


def test_card_creation_does_not_link_objects_to_names():
    g, _h = _game()
    created = [dict(e.data) for t in g.s.log.transitions for e in t.events if e.kind == "CardCreated"]
    assert created and all("oid" not in d for d in created)
    assert all({"ciid", "name", "owner", "commitment"} <= set(d) for d in created)


def test_moves_between_hidden_zones_carry_no_card_identity():
    g, _h = _game()
    hidden = 0
    for t in g.s.log.transitions:
        for e in t.events:
            if e.kind != "ZoneChanged":
                continue
            d = dict(e.data)
            if d["frm"] in HIDDEN and d["to"] in HIDDEN:
                hidden += 1
                assert set(d) == {"owner", "frm", "to", "commitment"} and len(d["commitment"]) == 16
            else:
                assert "ciid" in d                                    # public moves stay auditable
                assert ("old" in d) == (d["frm"] not in HIDDEN) and ("new" in d) == (d["to"] not in HIDDEN)
    assert hidden >= 14                                               # at least both opening hands


def test_no_object_id_of_a_hidden_card_ever_appears_in_the_log():
    """Not even as a number: a library / hand ObjectId in the log would link a later public event
    to the draw (or library position) it came from. Instrumented so ObjectIds are >= 10**6 (and so
    cannot collide with seats, counts, trigger ids or card instance ids); then EVERY integer in
    every event field is checked."""
    orig = reducer._alloc_oid
    reducer._alloc_oid = lambda s: orig(s) + OFFSET
    try:
        games = [_game(seed) for seed in (3, 8, 21)]
    finally:
        reducer._alloc_oid = orig
    for g, hidden in games:
        assert len(hidden) > 60 and min(hidden) > OFFSET
        leaks = [(t.index, e.kind, k) for t in g.s.log.transitions for e in t.events for k, v in e.data
                 if not set(_ints(v)).isdisjoint(hidden)]
        assert not leaks, leaks[:5]
        drew = [dict(e.data) for t in g.s.log.transitions for e in t.events if e.kind == "Drew"]
        assert drew and all(set(d) == {"player"} for d in drew)


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
