"""S3 library search (CR 701.23): fetchlands -- costs, a private search choice validated
against the exact predicate, failure to find (CR 701.23b), a fetched shock land's entry
choice, shuffle with the game RNG even on failure, no leaked library order."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import WU, _expand
from tests.v2.helpers import advance, arrange, at, events, find, new_game, put

FETCH_TEST = _expand([("Mountain", 8), ("Plains", 2), ("Sacred Foundry", 3), ("Arid Mesa", 4),
                      ("Bloodstained Mire", 3), ("Inspiring Vantage", 2), ("Monastery Swiftspear", 4),
                      ("Goblin Guide", 4), ("Lightning Bolt", 4), ("Lava Spike", 4), ("Lightning Helix", 2)])
assert len(FETCH_TEST) == 40


def _setup():
    g = new_game(FETCH_TEST, WU)
    advance(g, at("main1", active=0, turn=3))
    return g


def _crack(g, name):
    land = put(g, 0, name, "battlefield")
    act = next(a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == land)
    g.apply(act)
    return land


def _resolve_to_search(g):
    advance(g, lambda g: g.pending().kind == "search_choice")


def _names(g, oids):
    return sorted(g.s.instances[g.s.objects[o].ciid].name for o in oids)


def test_fetch_costs_are_paid_together_and_the_ability_survives():       # CR 602.2, 119.4, 113.7a
    g = _setup()
    mesa = _crack(g, "Arid Mesa")
    assert g.s.life[0] == 19 and mesa not in g.s.objects and events(g, "Sacrificed")
    e = g.s.stack[-1]
    assert e.state == "ability" and e.ability == "fetch_mountain_plains" and e.source == mesa


def test_fetch_is_not_offered_without_the_life_to_pay():                   # CR 118.3, 119.4
    g = _setup()
    mesa = put(g, 0, "Arid Mesa", "battlefield")
    arrange(g, [op("damage_player", 1, 0, 20)])
    assert not any(a.oid == mesa for a in g._activation_actions(0, True))


def test_search_options_follow_the_exact_predicate_and_stay_private():     # CR 701.23a
    g = _setup()
    _crack(g, "Arid Mesa")
    _resolve_to_search(g)
    opts = [a.oid for a in g.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None]
    assert set(_names(g, opts)) == {"Mountain", "Plains", "Sacred Foundry"}  # not Vantage, not spells
    assert A.ChooseSearchResult(0, None) in g.legal_actions()                # CR 701.23b
    assert sorted(o for o, _n in g.observe(0).my_search) == sorted(opts)
    assert g.observe(1).my_search == ()                                     # hidden from the opponent
    g2 = _setup()
    _crack(g2, "Bloodstained Mire")
    _resolve_to_search(g2)
    opts2 = [a.oid for a in g2.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None]
    assert set(_names(g2, opts2)) == {"Mountain", "Sacred Foundry"}


def test_fetch_puts_the_card_onto_the_battlefield_then_shuffles():
    g = _setup()
    _crack(g, "Arid Mesa")
    _resolve_to_search(g)
    mtn = next(a.oid for a in g.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None
               and g.s.instances[g.s.objects[a.oid].ciid].name == "Mountain")
    rng_before = g.s.rng.getstate()
    g.apply(A.ChooseSearchResult(0, mtn))
    new = g.s.zones[("bf",)][-1]
    assert g.s.instances[g.s.objects[new].ciid].name == "Mountain" and not g.s.objects[new].tapped
    sh = events(g, "Shuffled")[-1]
    assert dict(sh.data)["player"] == 0 and g.s.rng.getstate() != rng_before          # game RNG used
    t = g.s.log.transitions[-2]
    kinds = [e.kind for e in t.events]
    assert kinds.index("ZoneChanged") < kinds.index("Shuffled")              # put, THEN shuffle
    assert g.s.lands_entered_turn[0] >= 1 and not g.s.stack and g.pending().kind == "priority"


def test_failure_to_find_still_shuffles():
    g = _setup()
    _crack(g, "Arid Mesa")
    _resolve_to_search(g)
    n = len(events(g, "Shuffled"))
    g.apply(A.ChooseSearchResult(0, None))
    assert len(events(g, "Shuffled")) == n + 1 and events(g, "SearchFoundNothing")
    assert not g.s.stack and g.s.continuation is None


def test_shuffle_events_do_not_reveal_the_library_order():
    g = _setup()
    _crack(g, "Arid Mesa")
    _resolve_to_search(g)
    g.apply(A.ChooseSearchResult(0, None))
    order = tuple(g.s.zones[(0, "library")])
    for e in events(g, "Shuffled"):
        d = dict(e.data)
        assert set(d) == {"player", "commitment"}
        assert len(d["commitment"]) == 24 and all(c in "0123456789abcdef" for c in d["commitment"])
    for t in g.s.log.transitions:                                          # the order appears nowhere
        for e in t.events:
            assert order not in [v for _k, v in e.data], (t.kind, e.kind)
    assert g.observe(0).library_counts[0] == len(order)                    # observations: counts only


def test_fetched_shock_land_asks_for_its_entry_payment():                  # CR 614.12
    for pay in (True, False):
        g = _setup()
        _crack(g, "Arid Mesa")
        _resolve_to_search(g)
        sf = next(a.oid for a in g.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None
                  and g.s.instances[g.s.objects[a.oid].ciid].name == "Sacred Foundry")
        g.apply(A.ChooseSearchResult(0, sf))
        assert g.pending().kind == "entry_payment" and g.s.objects[sf].zone == "library"
        g.apply(A.ChooseEntryPayment(0, sf, pay))
        new = g.s.zones[("bf",)][-1]
        assert g.s.instances[g.s.objects[new].ciid].name == "Sacred Foundry"
        assert g.s.objects[new].tapped == (not pay) and g.s.life[0] == (17 if pay else 19)
        assert g.s.continuation is None and g.pending().kind == "priority"


def test_randomized_fetch_games_hold_invariants_and_replay():
    for seed in range(30):
        g = Game.new(FETCH_TEST, FETCH_TEST if seed % 2 else WU, 8400 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 2)])
        replay(make_record(g))


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"[ok] {name}")
            except Exception as e:                                          # noqa: BLE001
                import traceback
                failures += 1
                print(f"[FAIL] {name}: {type(e).__name__}: {str(e)[:300]}")
                traceback.print_exc(limit=4)
    print(f"SEARCH FAILURES: {failures}")
