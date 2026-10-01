"""S7 modal spells and multiple / dependent targets: Boros Charm (mode before targets,
CR 601.2b / 700.2a; every mode) and Searing Blaze (player + creature that player controls,
partial target legality CR 608.2b, landfall for its controller this turn)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.game import Game
from engine.v2.objects import TurnEffect
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from engine.v2.rules import casting
from tests.v2.decks import WU, _expand
from tests.v2.helpers import tgame, advance, arrange, at, events, find, new_game, put

MODAL_TEST = _expand([("Mountain", 10), ("Plains", 4), ("Sacred Foundry", 2), ("Boros Charm", 4),
                      ("Searing Blaze", 4), ("Monastery Swiftspear", 4), ("Goblin Guide", 4),
                      ("Lightning Bolt", 4), ("Lightning Helix", 4)])
assert len(MODAL_TEST) == 40


def _setup(play_land=False):
    g = new_game(MODAL_TEST, WU)
    advance(g, at("main1", active=0, turn=3))
    for land in ("Mountain", "Mountain", "Plains"):
        put(g, 0, land, "battlefield")
    arrange(g, [op("begin_turn", g.s.turn + 2, 0)])                       # fresh turn: no landfall yet
    return g


def _pay(g, *lands):
    for name in lands:
        oid = next(o for o in g.s.zones[("bf",)] if g.s.objects[o].controller == 0 and not g.s.objects[o].tapped
                   and g.s.instances[g.s.objects[o].ciid].name == name)
        g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == oid))
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.PayCost)))


def _resolve(g):
    advance(g, lambda g: not g.s.stack and not g.s.pending_triggers)


def _charm(g, mode, target=None):
    charm = put(g, 0, "Boros Charm", "hand")
    g.apply(A.ProposeCast(0, charm))
    assert g.pending().kind == "cast_mode"                                # CR 601.2b: before targets
    g.apply(A.ChooseMode(0, mode))
    if target is not None:
        g.apply(A.ChooseTargets(0, (target,)))
    _pay(g, "Mountain", "Plains")
    _resolve(g)


def test_boros_charm_mode_0_deals_4_to_a_target_player():
    g = _setup()
    charm = put(g, 0, "Boros Charm", "hand")
    g.apply(A.ProposeCast(0, charm))
    g.apply(A.ChooseMode(0, 0))
    assert {a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)} == {(("player", 0),), (("player", 1),)}
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    _pay(g, "Mountain", "Plains")
    _resolve(g)
    assert g.s.life[1] == 16 and dict(events(g, "ModeChosen")[-1].data)["mode"] == 0


def test_boros_charm_mode_1_indestructible_for_permanents_controlled_at_resolution():   # CR 611.2c
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    foe = put(g, 1, "Serra Angel", "battlefield")
    charm = put(g, 0, "Boros Charm", "hand")
    g.apply(A.ProposeCast(0, charm))
    g.apply(A.ChooseMode(0, 1))
    assert g.pending().kind == "cast_mana"                                 # no targets for this mode
    _pay(g, "Mountain", "Plains")
    _resolve(g)
    mine = [o for o in g.s.zones[("bf",)] if g.s.objects[o].controller == 0]
    assert all(TurnEffect("indestructible", o) in g.s.turn_effects for o in mine)
    assert TurnEffect("indestructible", foe) not in g.s.turn_effects
    later = put(g, 0, "Goblin Guide", "battlefield")
    assert TurnEffect("indestructible", later) not in g.s.turn_effects
    arrange(g, [op("damage_creature", 0, sw, 9)])
    g.apply(A.PassPriority(0))
    assert sw in g.s.objects                                               # lethal damage ignored


def test_boros_charm_mode_2_gives_double_strike():
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    _charm(g, 2, ("obj", sw))
    assert TurnEffect("double_strike", sw) in g.s.turn_effects


def test_boros_charm_modes_without_legal_targets_cannot_be_chosen():      # CR 700.2a
    g = _setup()
    charm = put(g, 0, "Boros Charm", "hand")
    assert casting.castable_modes(g.s, "boros_charm") == [0, 1]           # no creature anywhere
    g.apply(A.ProposeCast(0, charm))
    assert {a.mode for a in g.legal_actions() if isinstance(a, A.ChooseMode)} == {0, 1}


def test_searing_blaze_targets_a_player_and_a_creature_that_player_controls():
    g = _setup()
    assert not casting.can_propose_cast(g.s, 0, put(g, 0, "Searing Blaze", "hand"))   # no creature at all
    mine = put(g, 0, "Goblin Guide", "battlefield")
    foe = put(g, 1, "Serra Angel", "battlefield")
    blaze = find(g, 0, "Searing Blaze", "hand")
    g.apply(A.ProposeCast(0, blaze))
    opts = {a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)}
    assert opts == {(("player", 0), ("obj", mine)), (("player", 1), ("obj", foe))}


def _blaze(g, foe, landfall):
    if landfall:
        g.apply(A.PlayLand(0, put(g, 0, "Mountain", "hand")))
    blaze = put(g, 0, "Searing Blaze", "hand")
    g.apply(A.ProposeCast(0, blaze))
    g.apply(A.ChooseTargets(0, (("player", 1), ("obj", foe))))
    _pay(g, "Mountain", "Mountain")


def test_searing_blaze_without_landfall_deals_1_and_1():
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    _blaze(g, foe, landfall=False)
    _resolve(g)
    assert g.s.life[1] == 19 and g.s.objects[foe].damage == 1


def test_searing_blaze_with_landfall_deals_3_and_3():
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    _blaze(g, foe, landfall=True)
    _resolve(g)
    assert g.s.life[1] == 17 and g.s.objects[foe].damage == 3


def test_searing_blaze_landfall_counts_only_its_controllers_lands():
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    put(g, 1, "Island", "battlefield")                                     # opponent's land entered this turn
    assert g.s.lands_entered_turn == [0, 1]
    _blaze(g, foe, landfall=False)
    _resolve(g)
    assert g.s.life[1] == 19


def test_searing_blaze_with_one_legal_target_still_resolves():            # CR 608.2b
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    _blaze(g, foe, landfall=False)
    arrange(g, [op("move", foe, "graveyard", "end")])
    _resolve(g)
    assert g.s.life[1] == 19 and not events(g, "SpellFizzled")


def test_searing_blaze_creature_controlled_by_another_player_is_illegal():
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    _blaze(g, foe, landfall=False)
    assert casting.slot_still_legal(g.s, "searing_blaze", 1, ("obj", foe), (("player", 0), ("obj", foe))) is False


def test_searing_blaze_with_no_legal_targets_does_not_resolve():           # CR 608.2b
    """Both targets illegal (the creature left; the targeted player has left the game -- the only
    way a player target becomes illegal). Resolution is invoked directly, before the SBA that
    would end the game, to exercise the 'all targets illegal' rule."""
    g = _setup()
    foe = put(g, 1, "Serra Angel", "battlefield")
    _blaze(g, foe, landfall=True)
    blaze_oid = g.s.stack[-1].oid
    arrange(g, [op("move", foe, "graveyard", "end"), op("lose", 1, "test")])
    life = list(g.s.life)
    assert g._resolve_top() is True
    assert events(g, "SpellFizzled") and g.s.life == life and not g.s.stack
    assert any(g.s.instances[g.s.objects[o].ciid].name == "Searing Blaze" for o in g.s.zones[(0, "graveyard")])
    assert blaze_oid not in g.s.objects


def test_randomized_modal_games_hold_invariants_and_replay():
    for seed in range(30):
        g = tgame(MODAL_TEST, MODAL_TEST if seed % 2 else WU, 10600 + seed, starting_player=seed % 2,
                     check_invariants=True)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 6)])
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
    print(f"MODES/TARGETS FAILURES: {failures}")
