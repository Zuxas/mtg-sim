"""S2 activated abilities and costs: pain-land mana abilities with life costs (no stack),
non-mana activated abilities (Sunbaked Canyon / Fiery Islet draw) with mana, tap and
sacrifice costs paid atomically, the ability surviving its sacrificed source."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2 import reducer
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from engine.v2.reducer import EngineInvariantError
from engine.v2.rules import casting
from engine.v2.rules.mana import activatable_mana_options, available_mana, can_pay
from tests.v2.decks import ACTIVATED_TEST, WU
from tests.v2.helpers import tgame, advance, arrange, at, events, find, new_game, put


def _setup():
    g = new_game(ACTIVATED_TEST, WU)
    advance(g, at("main1", active=0, turn=3))
    return g


def _mana(g, oid, color):
    g.apply(A.ActivateManaAbility(0, oid, color))


def test_pain_land_mana_ability_costs_1_life_and_does_not_use_the_stack():   # CR 605.3b, 119.4
    g = _setup()
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    opts = {a.color for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == canyon}
    assert opts == {"R", "W"}
    _mana(g, canyon, "W")
    assert g.s.life[0] == 19 and g.s.pools[0]["W"] == 1 and g.s.objects[canyon].tapped
    assert not g.s.stack and g.pending().kind == "priority" and g.pending().player == 0
    assert g.s.life_lost_turn[0]                                           # paying life is losing life
    islet = put(g, 0, "Fiery Islet", "battlefield")
    assert {a.color for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == islet} == {"U", "R"}


def test_life_payment_requires_enough_life():                               # CR 119.4, 118.3
    g = _setup()
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    arrange(g, [op("damage_player", 0, 0, 20)])                            # life 0 (SBA not yet performed)
    assert activatable_mana_options(g.s, 0, canyon) == ()
    assert reducer is not None
    try:
        reducer.commit(g.s, "probe", [op("pay_life", 0, 1)])
        raise AssertionError("paid life without enough life")
    except EngineInvariantError:
        pass


def test_exact_source_matching_for_dual_and_pain_lands():
    g = _setup()
    for name in ("Mountain", "Mountain"):
        put(g, 0, name, "battlefield")
    helix = put(g, 0, "Lightning Helix", "hand")
    assert not casting.can_propose_cast(g.s, 0, helix)                     # R + R cannot pay {R}{W}
    put(g, 0, "Sunbaked Canyon", "battlefield")
    assert casting.can_propose_cast(g.s, 0, helix)                         # Mountain R + Canyon W
    av = available_mana(g.s, 0)
    assert can_pay(("R", "W"), av) and not can_pay(("W", "W"), av) and can_pay(("2", "W"), av)


def test_pain_land_mana_while_casting_is_recorded_with_its_life_cost():
    g = _setup()
    put(g, 0, "Mountain", "battlefield")
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    helix = put(g, 0, "Lightning Helix", "hand")
    g.apply(A.ProposeCast(0, helix))
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ChooseTargets) and a.targets == (("player", 1),)))
    _mana(g, find(g, 0, "Mountain", "battlefield"), "R")
    _mana(g, canyon, "W")
    assert g.s.open_cast["activations"][-1] == (canyon, "W", 1)
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.PayCost)))
    advance(g, lambda g: not g.s.stack)
    assert g.s.life == [19 + 3, 17]


def test_canyon_draw_needs_its_whole_cost_and_survives_its_sacrifice():   # CR 602.2, 113.7a
    g = _setup()
    mountain = put(g, 0, "Mountain", "battlefield")
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    assert not any(isinstance(a, A.ActivateAbility) for a in g.legal_actions())        # {1} not available yet
    _mana(g, mountain, "R")
    acts = [a for a in g.legal_actions() if isinstance(a, A.ActivateAbility)]
    assert acts == [A.ActivateAbility(0, canyon, 0, (("R", 1),))]
    hand = len(g.s.zones[(0, "hand")])
    g.apply(acts[0])
    kinds = [t.kind for t in g.s.log.transitions]
    assert kinds[-2:] == ["activate", "priority"] or kinds[-1] == "priority"
    assert canyon not in g.s.objects and g.s.pools[0]["R"] == 0             # sacrificed, mana spent
    e = g.s.stack[-1]
    assert e.state == "ability" and e.ability == "land_draw" and e.oid is None and e.source == canyon
    assert events(g, "Sacrificed")
    advance(g, lambda g: not g.s.stack)
    assert len(g.s.zones[(0, "hand")]) == hand + 1                         # resolved without its source


def test_tapped_canyon_cannot_activate_its_draw_ability():
    g = _setup()
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    mountain = put(g, 0, "Mountain", "battlefield")
    _mana(g, canyon, "R")                                                  # tapped for mana
    _mana(g, mountain, "R")
    assert not any(isinstance(a, A.ActivateAbility) and a.oid == canyon for a in g.legal_actions())


def test_fiery_islet_draw_ability():
    g = _setup()
    islet = put(g, 0, "Fiery Islet", "battlefield")
    _mana(g, put(g, 0, "Mountain", "battlefield"), "R")
    act = next(a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == islet)
    hand = len(g.s.zones[(0, "hand")])
    g.apply(act)
    advance(g, lambda g: not g.s.stack)
    assert len(g.s.zones[(0, "hand")]) == hand + 1 and islet not in g.s.objects


def test_rollback_reverses_a_pain_land_activation_including_its_life():   # CR 733.1
    g = _setup()
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    spike = put(g, 0, "Lava Spike", "hand")
    pre_rules = g.s.rules_state_hash()
    g.apply(A.ProposeCast(0, spike))
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ChooseTargets)))
    _mana(g, canyon, "R")
    assert g.s.life[0] == 19
    g.rollback_open_cast("fault injection")
    assert g.s.life[0] == 20 and not g.s.objects[canyon].tapped and g.s.pools[0]["R"] == 0


def test_cast_time_mana_choices_keep_the_announced_cost_payable():      # CR 601.2g, 733 (spec 7.4)
    g = _setup()
    mountain = put(g, 0, "Mountain", "battlefield")
    canyon = put(g, 0, "Sunbaked Canyon", "battlefield")
    helix = put(g, 0, "Lightning Helix", "hand")
    g.apply(A.ProposeCast(0, helix))
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ChooseTargets)))
    offered = {(a.oid, a.color) for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility)}
    assert offered == {(mountain, "R"), (canyon, "W")}                       # Canyon for R would strand {W}


def test_pain_land_life_costs_share_one_life_budget():                  # CR 119.4
    g = _setup()
    a = put(g, 0, "Sunbaked Canyon", "battlefield")
    b = put(g, 0, "Sunbaked Canyon", "battlefield")
    helix = put(g, 0, "Lightning Helix", "hand")
    arrange(g, [op("damage_player", 1, 0, 19)])                              # 1 life: only ONE pain activation
    assert not casting.can_propose_cast(g.s, 0, helix)
    assert not can_pay(("R", "W"), available_mana(g.s, 0))
    arrange(g, [op("gain_life", 0, 1)])                                      # 2 life: both
    assert casting.can_propose_cast(g.s, 0, helix)


def test_randomized_activated_games_hold_invariants_and_replay():
    for seed in range(30):
        g = tgame(ACTIVATED_TEST, ACTIVATED_TEST if seed % 2 else WU, 6200 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 5)])
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
    print(f"ACTIVATED FAILURES: {failures}")
