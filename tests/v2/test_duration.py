"""S5 duration-scoped rule effects: can't gain life (CR 119.7), damage can't be prevented
(CR 615.12), indestructible (CR 702.12b), double strike (CR 702.4b, 510.4), all ending at
cleanup (CR 514.2); Skullcrack and Roiling Vortex (upkeep damage, APNAP, {R} ability)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.game import Game
from engine.v2.objects import TurnEffect
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import WU, _expand
from tests.v2.helpers import tgame, advance, arrange, at, cast, events, find, new_game, put

DURATION_TEST = _expand([("Mountain", 10), ("Plains", 4), ("Sacred Foundry", 2), ("Roiling Vortex", 4),
                         ("Skullcrack", 4), ("Lightning Helix", 4), ("Lightning Bolt", 4),
                         ("Monastery Swiftspear", 4), ("Goblin Guide", 4)])
assert len(DURATION_TEST) == 40


def _setup(opp=WU):
    g = new_game(DURATION_TEST, opp)
    advance(g, at("main1", active=0, turn=3))
    for land in ("Mountain", "Mountain", "Plains", "Plains"):
        put(g, 0, land, "battlefield")
    return g


def _resolve(g):
    advance(g, lambda g: not g.s.stack and not g.s.pending_triggers)


def test_skullcrack_stops_life_gain_and_damage_prevention_this_turn():   # CR 119.7, 615.12
    g = _setup()
    sk = put(g, 0, "Skullcrack", "hand")
    opts = {a.targets for a in [x for x in g.legal_actions()] if isinstance(a, A.ChooseTargets)}
    cast(g, 0, "Skullcrack", target=("player", 1), lands=("Mountain", "Mountain"), oid=sk)
    _resolve(g)
    assert g.s.life[1] == 17
    assert TurnEffect("no_lifegain", 0) in g.s.turn_effects and TurnEffect("no_lifegain", 1) in g.s.turn_effects
    assert TurnEffect("no_prevention", None) in g.s.turn_effects
    put(g, 0, "Mountain", "battlefield")
    helix = put(g, 0, "Lightning Helix", "hand")
    cast(g, 0, "Lightning Helix", target=("player", 1), lands=("Mountain", "Plains"), oid=helix)
    _resolve(g)
    assert g.s.life == [20, 14] and events(g, "LifeGainPrevented")           # damage dealt, no gain
    advance(g, at("upkeep", active=1))
    assert g.s.turn_effects == ()                                            # CR 514.2: ended at cleanup


def test_skullcrack_targets_only_players():
    g = _setup()
    put(g, 1, "Serra Angel", "battlefield")
    sk = put(g, 0, "Skullcrack", "hand")
    g.apply(A.ProposeCast(0, sk))
    assert {a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)} == {(("player", 0),), (("player", 1),)}


def test_roiling_vortex_deals_1_at_each_players_upkeep():
    g = _setup()
    vx = put(g, 0, "Roiling Vortex", "hand")
    cast(g, 0, "Roiling Vortex", lands=("Mountain", "Mountain"), oid=vx)
    _resolve(g)
    advance(g, at("upkeep", active=1))
    _resolve(g)
    assert g.s.life[1] == 19
    advance(g, at("upkeep", active=0))
    _resolve(g)
    assert g.s.life[0] == 19 and g.s.life[1] == 19


def test_simultaneous_upkeep_triggers_go_on_the_stack_apnap():            # CR 603.3b
    g = _setup(opp=DURATION_TEST)
    put(g, 0, "Roiling Vortex", "battlefield")
    put(g, 1, "Roiling Vortex", "battlefield")
    advance(g, at("upkeep", active=1))
    stacked = events(g, "TriggerStacked")[-2:]
    ctrls = [dict(e.data)["controller"] for e in stacked]
    assert ctrls == [1, 0]                                                    # active player's first (bottom)
    assert [e.controller for e in g.s.stack if e.state == "ability"] == [1, 0]  # NAP's resolves first
    _resolve(g)
    assert g.s.life[1] == 18


def test_roiling_vortex_r_ability_stops_only_opponents_gaining_life():
    g = _setup()
    vx = put(g, 0, "Roiling Vortex", "battlefield")
    g.apply(A.ActivateManaAbility(0, find(g, 0, "Mountain", "battlefield"), "R"))
    act = next(a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == vx)
    g.apply(act)
    _resolve(g)
    assert TurnEffect("no_lifegain", 1) in g.s.turn_effects and TurnEffect("no_lifegain", 0) not in g.s.turn_effects
    helix = put(g, 0, "Lightning Helix", "hand")
    cast(g, 0, "Lightning Helix", target=("player", 1), lands=("Mountain", "Plains"), oid=helix)
    _resolve(g)
    assert g.s.life == [23, 17]                                               # its controller still gains


def test_indestructible_survives_lethal_damage_until_cleanup():           # CR 702.12b
    g = _setup()
    bear = put(g, 0, "Monastery Swiftspear", "battlefield")
    arrange(g, [op("add_turn_effect", "indestructible", bear), op("damage_creature", 0, bear, 5)])
    advance(g, lambda g: g.pending().kind == "priority" and g.s.passes == 0 and len(g.s.log.transitions) > 0)
    g.apply(A.PassPriority(0))
    assert bear in g.s.objects                                                # lethal damage ignored
    advance(g, at("upkeep", active=1))
    assert bear in g.s.objects and g.s.objects[bear].damage == 0 and g.s.turn_effects == ()


def test_double_strike_deals_damage_in_both_steps():                       # CR 702.4b, 510.4
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    arrange(g, [op("add_turn_effect", "double_strike", sw)])
    advance(g, lambda g: g.pending().kind == "declare_attack")
    g.apply(A.ChooseAttack(0, sw, True))
    advance(g, at("end_combat"))
    steps = [dict(e.data)["value"] for e in events(g, "Set") if dict(e.data)["attr"] == "step"]
    assert "first_strike_damage" in steps
    assert g.s.life[1] == 18                                                  # 1 + 1


def test_double_strike_second_step_uses_first_step_snapshot():
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    gg = put(g, 0, "Goblin Guide", "battlefield")
    arrange(g, [op("add_turn_effect", "double_strike", sw)])
    advance(g, lambda g: g.pending().kind == "declare_attack")
    while g.pending().kind == "declare_attack":
        g.apply(A.ChooseAttack(0, g.pending().info[0], True))
    advance(g, at("end_combat"))
    # Swiftspear 1 + 1 (both steps), Goblin Guide 2 (regular step only, had neither)
    assert g.s.life[1] == 16


def test_randomized_duration_games_hold_invariants_and_replay():
    for seed in range(30):
        g = tgame(DURATION_TEST, DURATION_TEST if seed % 2 else WU, 9500 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 4)])
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
    print(f"DURATION FAILURES: {failures}")
