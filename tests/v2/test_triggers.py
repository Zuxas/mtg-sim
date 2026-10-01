"""S1 triggered abilities: occurrences -> pending triggers -> SBAs -> stack (APNAP, ordering
decision, targets) -> resolution with intervening-if; Monastery Swiftspear (prowess) and
Goblin Guide."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import abilities as AB
from engine.v2 import actions as A
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import TRIGGER_TEST, WU
from tests.v2.helpers import tgame, act, advance, arrange, at, cast, events, find, new_game, put


def _setup(lands=("Mountain", "Mountain", "Mountain", "Plains")):
    g = new_game(TRIGGER_TEST, WU)
    advance(g, at("main1", active=0, turn=3))
    for land in lands:
        put(g, 0, land, "battlefield")
    return g


def _resolve_all(g):
    advance(g, lambda g: not g.s.stack and not g.s.pending_triggers)


def _power(g, oid):
    return g.s.power(oid)


def test_prowess_triggers_only_from_noncreature_spells():                   # CR 702.108a
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    gob = put(g, 0, "Raging Goblin", "hand")
    cast(g, 0, "Raging Goblin", lands=("Mountain",), oid=gob)
    assert not events(g, "Triggered")                                      # creature spell: no trigger
    _resolve_all(g)
    spike = put(g, 0, "Lava Spike", "hand")
    cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
    trig = events(g, "Triggered")
    assert len(trig) == 1 and dict(trig[0].data)["key"] == "prowess"
    top = g.s.stack[-1]
    assert top.state == "ability" and top.ability == "prowess" and top.oid is None       # CR 603.3
    assert g.s.stack[-2].state == "cast"                                   # above the spell that caused it
    _resolve_all(g)
    assert _power(g, sw) == 2 and g.s.toughness(sw) == 3 and g.s.life[1] == 17
    advance(g, at("main1", active=1))                                      # cleanup ended the effect
    assert _power(g, sw) == 1                                              # CR 514.2


def test_multiple_prowess_triggers_need_an_ordering_decision():           # CR 702.108b, 603.3b
    g = _setup()
    a = put(g, 0, "Monastery Swiftspear", "battlefield")
    b = put(g, 0, "Monastery Swiftspear", "battlefield")
    spike = put(g, 0, "Lava Spike", "hand")
    cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
    pd = g.pending()
    assert pd.kind == "order_triggers" and pd.player == 0 and len(pd.info) == 2
    opts = g.legal_actions()
    assert {x.tid for x in opts if isinstance(x, A.OrderTrigger)} == set(pd.info)
    second = pd.info[1]
    g.apply(A.OrderTrigger(0, second))                                     # chosen first -> lower on the stack
    assert g.pending().kind == "priority"
    abil = [e for e in g.s.stack if e.state == "ability"]
    assert len(abil) == 2 and g.s.stack.index(abil[0]) < g.s.stack.index(abil[1])
    stacked = [dict(e.data)["tid"] for e in events(g, "TriggerStacked")]
    assert stacked[0] == second
    _resolve_all(g)
    assert _power(g, a) == 2 and _power(g, b) == 2


def test_sbas_are_performed_before_triggers_go_on_the_stack():             # CR 117.5
    g = _setup()
    put(g, 0, "Monastery Swiftspear", "battlefield")
    knight = put(g, 1, "Youthful Knight", "battlefield")
    arrange(g, [op("damage_creature", 0, knight, 5)])                     # lethal damage marked, SBA not yet run
    spike = put(g, 0, "Lava Spike", "hand")
    cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
    kinds = [t.kind for t in g.s.log.transitions]
    i = kinds.index("cast", len(kinds) - 6)
    assert kinds[i + 1:i + 4] == ["sba", "trigger_stack", "priority"]
    assert knight not in g.s.objects


def test_prowess_from_a_creature_that_left_does_nothing():
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    spike = put(g, 0, "Lava Spike", "hand")
    cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
    arrange(g, [op("move", sw, "graveyard", "end")])
    _resolve_all(g)
    assert events(g, "ProwessNoTarget") and g.s.life[1] == 17


def _goblin_attack(top_name):
    g = _setup()
    gg = put(g, 0, "Goblin Guide", "battlefield")
    top = find(g, 1, top_name, "library")
    lib = g.s.zones[(1, "library")]
    arrange(g, [op("move", top, "library", "top")])                        # arrange the defender's top card
    top = lib[0]
    advance(g, lambda g: g.pending().kind == "declare_attack")
    g.apply(A.ChooseAttack(0, gg, True))
    return g, gg, top


def test_goblin_guide_reveals_and_moves_a_land_to_hand():
    g, gg, top = _goblin_attack("Island")
    assert dict(events(g, "Triggered")[-1].data)["key"] == "goblin_guide_reveal"
    hand_before = len(g.s.zones[(1, "hand")])
    advance(g, lambda g: not g.s.stack)
    rev = events(g, "Revealed")
    assert rev and dict(rev[-1].data)["name"] == "Island"                  # CR 701.20a
    assert len(g.s.zones[(1, "hand")]) == hand_before + 1
    assert top not in g.s.objects                                          # it moved (new object in hand)


def test_goblin_guide_reveals_a_nonland_and_leaves_it_on_top():           # CR 701.20b
    g, gg, top = _goblin_attack("Serra Angel")
    hand_before = len(g.s.zones[(1, "hand")])
    advance(g, lambda g: not g.s.stack)
    assert dict(events(g, "Revealed")[-1].data)["name"] == "Serra Angel"
    assert g.s.zones[(1, "library")][0] == top and len(g.s.zones[(1, "hand")]) == hand_before


def test_goblin_guide_with_an_empty_library_reveals_nothing():            # CR 609.3
    g = _setup()
    gg = put(g, 0, "Goblin Guide", "battlefield")
    arrange(g, [op("move", o, "exile", "end") for o in list(g.s.zones[(1, "library")])])
    advance(g, lambda g: g.pending().kind == "declare_attack")
    g.apply(A.ChooseAttack(0, gg, True))
    advance(g, lambda g: not g.s.stack)
    assert events(g, "RevealNothing")


def test_targeted_trigger_chooses_targets_when_it_is_put_on_the_stack():  # CR 603.3d
    real = AB.SPEC_BY_KEY["prowess"]
    AB.SPEC_BY_KEY["prowess"] = real._replace(targets=("creature",))
    try:
        g = _setup()
        put(g, 0, "Monastery Swiftspear", "battlefield")
        spike = put(g, 0, "Lava Spike", "hand")
        cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
        assert g.pending().kind == "trigger_targets" and not any(e.state == "ability" for e in g.s.stack)
        choice = next(a for a in g.legal_actions() if isinstance(a, A.ChooseTriggerTargets))
        g.apply(choice)
        assert g.s.stack[-1].targets == choice.targets and g.pending().kind == "priority"
    finally:
        AB.SPEC_BY_KEY["prowess"] = real


def test_trigger_with_no_legal_targets_is_removed_from_the_stack():        # CR 603.3d
    real = AB.SPEC_BY_KEY["prowess"]
    AB.SPEC_BY_KEY["prowess"] = real._replace(targets=("planeswalker",))   # no planeswalker can exist
    try:
        g = _setup()
        put(g, 0, "Monastery Swiftspear", "battlefield")
        spike = put(g, 0, "Lava Spike", "hand")
        cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
        assert events(g, "TriggerRemoved") and not any(e.state == "ability" for e in g.s.stack)
        assert g.pending().kind == "priority" and not g.s.pending_triggers
    finally:
        AB.SPEC_BY_KEY["prowess"] = real


def test_randomized_trigger_games_hold_invariants_and_replay():
    for seed in range(30):
        g = tgame(TRIGGER_TEST, TRIGGER_TEST if seed % 2 else WU, 5100 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 3)])
        replay(make_record(g))
    assert True


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
                traceback.print_exc(limit=3)
    print(f"TRIGGER FAILURES: {failures}")
