"""S6 alternative costs and suspend: Skewer the Critics (spectacle, CR 702.137a / 118.9) and
Rift Bolt (suspend special action, upkeep counter removal, resolution-time free cast,
CR 702.62a / 116.2f / 608.2g); Roiling Vortex's free-spell trigger."""
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

ALT_TEST = _expand([("Mountain", 12), ("Plains", 4), ("Roiling Vortex", 2), ("Rift Bolt", 4),
                    ("Skewer the Critics", 4), ("Monastery Swiftspear", 4), ("Goblin Guide", 4),
                    ("Lava Spike", 4), ("Lightning Helix", 2)])
assert len(ALT_TEST) == 40


def _setup(n_mountains=1, opp=WU):
    g = new_game(ALT_TEST, opp)
    advance(g, at("main1", active=0, turn=3))
    for _ in range(n_mountains):
        put(g, 0, "Mountain", "battlefield")
    return g


def _tap(g, n=1):
    for _ in range(n):
        oid = next(o for o in g.s.zones[("bf",)] if g.s.objects[o].controller == 0 and not g.s.objects[o].tapped
                   and g.s.definition(o).is_land)
        g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == oid
                     and a.color == "R"))


def _resolve(g):
    advance(g, lambda g: not g.s.stack and not g.s.pending_triggers)


def _costs_offered(g, oid):
    return {a.cost for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == oid}


def test_spectacle_needs_an_opponent_to_have_lost_life_this_turn():        # CR 702.137a
    g = _setup(1)
    sk = put(g, 0, "Skewer the Critics", "hand")
    assert _costs_offered(g, sk) == set()                                  # {2}{R} unaffordable, no spectacle
    arrange(g, [op("damage_player", 0, 0, 2)])                              # only I lost life
    assert _costs_offered(g, sk) == set()
    arrange(g, [op("damage_player", 0, 1, 2)])                              # an opponent lost life
    assert _costs_offered(g, sk) == {"spectacle"}


def test_spectacle_cost_is_fixed_for_the_whole_cast():                      # CR 601.2b/f
    g = _setup(3)
    sk = put(g, 0, "Skewer the Critics", "hand")
    arrange(g, [op("damage_player", 0, 1, 1)])
    assert _costs_offered(g, sk) == {"normal", "spectacle"}
    g.apply(A.ProposeCast(0, sk, "spectacle"))
    assert g.s.stack[-1].cost == "spectacle" and g.s.open_cast["cost"] == ("R",)
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    _tap(g, 1)
    pays = [a for a in g.legal_actions() if isinstance(a, A.PayCost)]
    assert pays == [A.PayCost(0, (("R", 1),))]
    g.apply(pays[0])
    assert g.s.stack[-1].mana_spent == 1
    _resolve(g)
    assert g.s.life[1] == 16 and len([o for o in g.s.zones[("bf",)] if not g.s.objects[o].tapped]) == 2


def test_skewer_normal_cost():
    g = _setup(3)
    sk = put(g, 0, "Skewer the Critics", "hand")
    g.apply(A.ProposeCast(0, sk))
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    _tap(g, 3)
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.PayCost)))
    _resolve(g)
    assert g.s.life[1] == 17


def _suspend_rift_bolt(g):
    rb = put(g, 0, "Rift Bolt", "hand")
    _tap(g, 1)
    act = next(a for a in g.legal_actions() if isinstance(a, A.Suspend) and a.oid == rb)
    g.apply(act)
    return rb


def test_suspend_is_a_special_action_exiling_with_a_time_counter():       # CR 116.2f, 702.62a
    g = _setup(1)
    rb = put(g, 0, "Rift Bolt", "hand")
    assert not any(isinstance(a, A.Suspend) for a in g.legal_actions())    # {R} not in the pool yet
    _tap(g, 1)
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.Suspend) and a.oid == rb))
    ex = g.s.zones[(0, "exile")][-1]
    assert g.s.objects[ex].counter("time") == 1 and not g.s.stack
    assert g.pending().kind == "priority" and g.pending().player == 0 and g.s.pools[0]["R"] == 0
    kinds = [t.kind for t in g.s.log.transitions][-2:]
    assert kinds == ["special_action", "priority"]


def test_suspend_only_with_sorcery_timing_for_a_sorcery():                  # CR 702.62c
    g = _setup(1)
    put(g, 0, "Rift Bolt", "hand")
    advance(g, at("main1", active=1))
    assert not any(isinstance(a, A.Suspend) for a in g.legal_actions())


def _to_my_next_upkeep_cast_choice(g):
    advance(g, lambda g: g.pending().kind == "suspend_cast_choice")


def test_upkeep_removes_the_last_counter_and_the_card_is_cast_free():      # CR 702.62a, 608.2g
    g = _setup(1)
    _suspend_rift_bolt(g)
    _to_my_next_upkeep_cast_choice(g)
    assert g.s.active == 0 and g.s.step == "upkeep"
    assert [dict(e.data)["key"] for e in events(g, "Triggered")][-2:] == ["suspend_upkeep", "suspend_cast"]
    assert {a.cast for a in g.legal_actions() if isinstance(a, A.ChooseSuspendCast)} == {True, False}
    g.apply(A.ChooseSuspendCast(0, True))
    assert g.pending().kind == "cast_targets"
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    pays = [a for a in g.legal_actions() if isinstance(a, A.PayCost)]
    assert pays == [A.PayCost(0, ())]                                      # without paying its mana cost
    life = g.s.life[1]
    g.apply(pays[0])
    top = g.s.stack[-1]
    assert top.state == "cast" and top.cost == "free" and top.mana_spent == 0
    assert not any(e.state == "ability" and e.ability == "suspend_cast" for e in g.s.stack)
    assert g.s.continuation is None and g.pending().player == 0             # active player gets priority
    _resolve(g)
    assert g.s.life[1] == life - 3


def test_declining_the_suspend_cast_leaves_it_exiled():
    g = _setup(1)
    _suspend_rift_bolt(g)
    _to_my_next_upkeep_cast_choice(g)
    g.apply(A.ChooseSuspendCast(0, False))
    ex = g.s.zones[(0, "exile")]
    assert any(g.s.instances[g.s.objects[o].ciid].name == "Rift Bolt" for o in ex)
    assert g.s.continuation is None and not g.s.stack


def test_roiling_vortex_punishes_a_spell_cast_without_mana():             # CR 603.4
    g = _setup(1, opp=ALT_TEST)
    put(g, 1, "Roiling Vortex", "battlefield")
    _suspend_rift_bolt(g)
    _to_my_next_upkeep_cast_choice(g)
    g.apply(A.ChooseSuspendCast(0, True))
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    g.apply(A.PayCost(0, ()))
    keys = [dict(e.data)["key"] for e in events(g, "Triggered")]
    assert "vortex_free_cast" in keys
    me = g.s.life[0]
    _resolve(g)
    assert g.s.life[0] <= me - 5                                           # 5 to the player who cast it


def test_roiling_vortex_ignores_spells_cast_with_mana():
    g = _setup(1, opp=ALT_TEST)
    put(g, 1, "Roiling Vortex", "battlefield")
    spike = put(g, 0, "Lava Spike", "hand")
    g.apply(A.ProposeCast(0, spike))
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    _tap(g, 1)
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.PayCost)))
    assert "vortex_free_cast" not in [dict(e.data)["key"] for e in events(g, "Triggered")]


def test_suspend_cast_triggers_prowess():
    g = _setup(1)
    put(g, 0, "Monastery Swiftspear", "battlefield")
    _suspend_rift_bolt(g)
    _to_my_next_upkeep_cast_choice(g)
    g.apply(A.ChooseSuspendCast(0, True))
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    g.apply(A.PayCost(0, ()))
    assert "prowess" in [dict(e.data)["key"] for e in events(g, "Triggered")]


def test_suspended_card_that_cannot_be_cast_remains_exiled():           # CR 702.62a "if able"
    from engine.v2.rules import casting
    g = _setup(1)
    _suspend_rift_bolt(g)
    real = casting.target_choices
    casting.target_choices = lambda *a, **k: []                            # no legal target anywhere
    try:
        _to_my_next_upkeep_cast_choice(g)
        assert [a for a in g.legal_actions() if isinstance(a, A.ChooseSuspendCast)] == [A.ChooseSuspendCast(0, False)]
    finally:
        casting.target_choices = real
    g.apply(A.ChooseSuspendCast(0, False))
    assert any(g.s.instances[g.s.objects[o].ciid].name == "Rift Bolt" for o in g.s.zones[(0, "exile")])


def test_randomized_alt_cost_games_hold_invariants_and_replay():
    for seed in range(30):
        g = Game.new(ALT_TEST, ALT_TEST if seed % 2 else WU, 11700 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 8)])
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
    print(f"ALT-COST FAILURES: {failures}")
