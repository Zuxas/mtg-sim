"""S4 enters-the-battlefield replacements: Inspiring Vantage (fast land, CR 614.1d) and
Sacred Foundry (shock land, CR 614.1c / 614.12 choice before the move, CR 119.4)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import WU, _expand
from tests.v2.helpers import tgame, advance, arrange, at, events, find, new_game, put

LAND_TEST = _expand([("Mountain", 8), ("Inspiring Vantage", 4), ("Sacred Foundry", 4), ("Sunbaked Canyon", 2),
                     ("Monastery Swiftspear", 4), ("Goblin Guide", 4), ("Lightning Bolt", 4), ("Lava Spike", 4),
                     ("Lightning Helix", 6)])
assert len(LAND_TEST) == 40


def _setup(others=0):
    g = new_game(LAND_TEST, WU)
    advance(g, at("main1", active=0, turn=3))
    for _ in range(others):
        put(g, 0, "Mountain", "battlefield")
    return g


def _play(g, name):
    oid = put(g, 0, name, "hand")
    g.apply(A.PlayLand(0, oid))
    return oid


def _new_land(g):
    return g.s.zones[("bf",)][-1]


def test_inspiring_vantage_untapped_with_two_or_fewer_other_lands():        # CR 614.1d
    for others in (0, 1, 2):
        g = _setup(others)
        put(g, 1, "Island", "battlefield")                                  # opponent's lands don't count
        put(g, 1, "Island", "battlefield")
        put(g, 1, "Island", "battlefield")
        _play(g, "Inspiring Vantage")
        assert not g.s.objects[_new_land(g)].tapped, others


def test_inspiring_vantage_tapped_with_three_other_lands():
    g = _setup(3)
    _play(g, "Inspiring Vantage")
    v = _new_land(g)
    assert g.s.objects[v].tapped and events(g, "EntersTapped")
    assert g.pending().kind == "priority" and g.s.land_played[0] == 1


def test_sacred_foundry_choice_happens_before_the_move_commits():          # CR 614.12
    g = _setup()
    oid = _play(g, "Sacred Foundry")
    assert g.pending().kind == "entry_payment" and g.s.objects[oid].zone == "hand"
    assert g.s.land_played[0] == 0
    opts = {a.pay for a in g.legal_actions() if isinstance(a, A.ChooseEntryPayment)}
    assert opts == {True, False}
    g.apply(A.ChooseEntryPayment(0, oid, True))
    f = _new_land(g)
    assert not g.s.objects[f].tapped and g.s.life[0] == 18 and g.s.land_played[0] == 1
    kinds = [t.kind for t in g.s.log.transitions]
    assert kinds[-2:] == ["play_land", "priority"]                         # payment + move in ONE transition
    assert {a.color for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == f} == {"R", "W"}


def test_sacred_foundry_declined_enters_tapped():
    g = _setup()
    oid = _play(g, "Sacred Foundry")
    g.apply(A.ChooseEntryPayment(0, oid, False))
    assert g.s.objects[_new_land(g)].tapped and g.s.life[0] == 20


def test_sacred_foundry_unable_to_pay_must_enter_tapped():                 # CR 119.4
    g = _setup()
    arrange(g, [op("damage_player", 1, 0, 19)])                             # 1 life
    oid = _play(g, "Sacred Foundry")
    opts = [a for a in g.legal_actions() if isinstance(a, A.ChooseEntryPayment)]
    assert opts == [A.ChooseEntryPayment(0, oid, False)]
    g.apply(opts[0])
    assert g.s.objects[_new_land(g)].tapped and g.s.life[0] == 1


def test_randomized_land_games_hold_invariants_and_replay():
    for seed in range(30):
        g = tgame(LAND_TEST, LAND_TEST if seed % 2 else WU, 7300 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)])
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
    print(f"REPLACEMENT FAILURES: {failures}")
