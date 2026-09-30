"""M1: rules unit tests for engine v2 (each cites the pinned CR, see tests/v2/cr_citations.py).
Player 0 = RG, player 1 = WU unless stated."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.ops import op
from tests.v2.decks import DECKOUT, RG, WU
from tests.v2.helpers import (act, advance, arrange, at, cast, events, find, name_of, new_game, put, tap_for)


def ciid(g, oid):
    return g.s.objects[oid].ciid


def gy_names(g, p):
    return [name_of(g, o) for o in g.s.zones[(p, "graveyard")]]


def bf_names(g, p):
    return [name_of(g, o) for o in g.s.zones[("bf",)] if g.s.objects[o].controller == p]


# ------------------------------------------------------------------ CR 103.5 mulligans
def test_mulligan_declaration_rounds_and_simultaneous_execute():
    g = new_game(keep=False, starting=1)
    s = g.s
    assert (g.pending().kind, g.pending().player) == ("mulligan_declare", 1)      # starting player first
    act(g, A.DeclareMulligan, player=1)
    assert (g.pending().kind, g.pending().player) == ("mulligan_declare", 0)
    n0 = len(s.log.transitions)
    act(g, A.DeclareMulligan, player=0)
    ex = [t for t in s.log.transitions[n0:] if t.kind == "mulligan_execute"]
    assert len(ex) == 1 and sum(e.kind == "Drew" for e in ex[0].events) == 14      # simultaneous: one transition
    assert (g.pending().kind, g.pending().player) == ("mulligan_bottom", 1)
    assert len(s.zones[(1, "hand")]) == 7 and len(s.zones[(0, "hand")]) == 7       # provisional hands


def test_bottom_is_chosen_after_seeing_seven_hidden_and_committed_together():
    g = new_game(keep=False, starting=0)
    s = g.s
    act(g, A.DeclareMulligan, player=0)
    act(g, A.DeclareMulligan, player=1)
    choices = [a for a in g.legal_actions() if isinstance(a, A.BottomCards)]
    assert len(choices) == 7 and all(len(a.cards) == 1 for a in choices)          # N = 1, from the new 7
    obs1_before = g.observe(1)
    pick = choices[4]
    picked_ciid = ciid(g, pick.cards[0])
    g.apply(pick)
    obs1_after = g.observe(1)
    assert obs1_after.opp_hand_count == obs1_before.opp_hand_count == 7           # hidden until commit
    assert obs1_after.library_counts == obs1_before.library_counts
    assert len(s.zones[(0, "hand")]) == 7                                          # not yet moved
    act(g, A.BottomCards, player=1, cards=(s.zones[(1, "hand")][0],))
    assert len(s.zones[(0, "hand")]) == 6 and len(s.zones[(1, "hand")]) == 6      # committed together
    assert s.objects[s.zones[(0, "library")][-1]].ciid == picked_ciid


def test_ordered_bottom_and_repeated_rounds():
    g = new_game(keep=False, starting=0)
    s = g.s
    act(g, A.DeclareMulligan, player=0)
    act(g, A.DeclareKeep, player=1)
    act(g, A.BottomCards, player=0, cards=(s.zones[(0, "hand")][0],))
    assert (g.pending().kind, g.pending().player) == ("mulligan_declare", 0)       # next round, only player 0
    act(g, A.DeclareMulligan, player=0)
    choices = [a for a in g.legal_actions() if isinstance(a, A.BottomCards)]
    assert len(choices) == 7 * 6 and all(len(a.cards) == 2 for a in choices)       # ordered, N = 2
    h = s.zones[(0, "hand")]
    x, y = h[5], h[2]
    cx, cy = ciid(g, x), ciid(g, y)
    act(g, A.BottomCards, player=0, cards=(x, y))
    lib = s.zones[(0, "library")]
    assert (s.objects[lib[-2]].ciid, s.objects[lib[-1]].ciid) == (cx, cy)
    assert len(s.zones[(0, "hand")]) == 5


def test_mulligan_zero_card_floor():
    g = new_game(keep=False, starting=0)
    s = g.s
    for _ in range(7):
        act(g, A.DeclareMulligan, player=0)
        if g.pending().kind == "mulligan_declare" and g.pending().player == 1:
            act(g, A.DeclareKeep, player=1)
        g.apply(next(a for a in g.legal_actions() if isinstance(a, A.BottomCards)))
    assert s.mull_count[0] == 7 and len(s.zones[(0, "hand")]) == 0
    assert [type(a).__name__ for a in g.legal_actions()] == ["DeclareKeep", "Concede"]


# ------------------------------------------------------------------ turn structure, mana
def test_starting_player_skips_first_draw():
    g = new_game(starting=0)
    advance(g, at("main1", turn=1))
    assert len(g.s.zones[(0, "hand")]) == 7
    advance(g, at("main1", turn=2))
    assert len(g.s.zones[(1, "hand")]) == 8


def test_mana_floats_then_empties_between_steps():
    g = new_game()
    advance(g, at("main1", turn=1))
    m = put(g, 0, "Mountain", "battlefield")
    act(g, A.ActivateManaAbility, player=0, oid=m)                                # CR 605.3a, outside casting
    assert g.s.pools[0]["R"] == 1 and g.pending().kind == "priority"
    advance(g, at("begin_combat", turn=1))
    assert g.s.pools[0]["R"] == 0 and events(g, "ManaEmptied")                    # CR 500.5, 106.4


def test_two_identical_lands_are_two_actions():
    g = new_game()
    advance(g, at("main1", turn=1))
    m1, m2 = put(g, 0, "Mountain", "battlefield"), put(g, 0, "Mountain", "battlefield")
    mana = [a for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility)]
    assert {a.oid for a in mana} == {m1, m2}
    act(g, A.ActivateManaAbility, player=0, oid=m2)
    assert g.s.objects[m2].tapped and not g.s.objects[m1].tapped


def test_one_land_per_turn_and_sorcery_timing():
    g = new_game()
    advance(g, at("upkeep", turn=1))
    put(g, 0, "Forest", "hand")
    put(g, 0, "Forest", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Grizzly Bears", "hand")
    kinds = {type(a).__name__ for a in g.legal_actions()}
    assert "PlayLand" not in kinds and not any(isinstance(a, A.ProposeCast) and name_of(g, a.oid) == "Grizzly Bears"
                                               for a in g.legal_actions())            # CR 307.1: main phase only
    advance(g, at("main1", turn=1))
    act(g, A.PlayLand, player=0, oid=find(g, 0, "Forest", "hand"))
    put(g, 0, "Mountain", "hand")
    assert not any(isinstance(a, A.PlayLand) for a in g.legal_actions())             # CR 305.2
    put(g, 0, "Lightning Bolt", "hand")
    cast(g, 0, "Lightning Bolt", ("player", 1), lands=("Mountain",))
    assert not any(isinstance(a, A.ProposeCast) and name_of(g, a.oid) == "Grizzly Bears"
                   for a in g.legal_actions())                                         # stack not empty


def test_only_instants_on_the_opponents_turn():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 1, "Island", "battlefield"); put(g, 1, "Island", "battlefield"); put(g, 1, "Island", "battlefield")
    put(g, 1, "Wind Drake", "hand")
    advance(g, at("main1", turn=1, player=1))                                        # P1 holds priority in P0's main
    assert not any(isinstance(a, A.ProposeCast) and name_of(g, a.oid) == "Wind Drake" for a in g.legal_actions())


# ------------------------------------------------------------------ casting, resolution, identity
def test_creature_resolves_to_battlefield_new_object_same_card():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 0, "Forest", "battlefield"); put(g, 0, "Mountain", "battlefield")
    bears = put(g, 0, "Grizzly Bears", "hand")
    card = ciid(g, bears)
    cast(g, 0, "Grizzly Bears", lands=("Forest", "Mountain"), oid=bears)
    entry = g.s.stack[-1]
    assert bears in g.s.retired and entry.oid != bears and entry.sid == f"O{entry.oid}"
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)             # CR 608.3a
    new = [o for o in g.s.zones[("bf",)] if g.s.objects[o].ciid == card][0]
    o = g.s.objects[new]
    assert new not in (bears, entry.oid) and o.controller == 0 and o.controlled_since == 1   # CR 110.2
    advance(g, lambda gg: gg.s.step == "declare_attackers" or gg.s.step == "end_combat")
    assert not (g.s.pending and g.s.pending.kind == "declare_attack")               # CR 302.6: summoning sick


def test_haste_creature_can_attack_the_turn_it_is_cast():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Raging Goblin", "hand")
    cast(g, 0, "Raging Goblin", lands=("Mountain",))
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)
    advance(g, lambda gg: gg.s.pending.kind == "declare_attack")                    # CR 702.10b
    gob = g.s.pending.info[0]
    act(g, A.ChooseAttack, player=0, oid=gob, attacks=True)
    assert g.s.objects[gob].tapped                                                   # CR 508.1f


def test_attackers_tap_but_vigilance_does_not():
    g = new_game()
    advance(g, at("main1", turn=1))
    serra = put(g, 1, "Serra Angel", "battlefield")
    knight = put(g, 1, "Youthful Knight", "battlefield")
    advance(g, lambda gg: gg.s.turn == 2 and gg.s.pending.kind == "declare_attack")
    while g.s.pending.kind == "declare_attack":
        act(g, A.ChooseAttack, player=1, oid=g.s.pending.info[0], attacks=True)
    assert set(g.s.attackers) == {serra, knight}
    assert g.s.objects[knight].tapped and not g.s.objects[serra].tapped             # CR 702.20b


def test_flying_cannot_be_blocked_by_non_flyer():
    g = new_game()
    advance(g, at("main1", turn=1))
    drake = put(g, 1, "Wind Drake", "battlefield")
    put(g, 0, "Grizzly Bears", "battlefield")
    advance(g, lambda gg: gg.s.turn == 2 and gg.s.pending.kind == "declare_attack")
    act(g, A.ChooseAttack, player=1, oid=drake, attacks=True)
    seen_block = False
    while not (g.s.step == "combat_damage" and g.s.pending.kind == "priority"):
        seen_block |= g.s.pending.kind == "declare_block"
        if g.s.pending.kind == "priority":
            g.apply(A.PassPriority(g.s.pending.player))
        else:
            g.apply(g.legal_actions()[0])
    assert not seen_block and g.s.blocks == {} and g.s.life[0] == 18               # CR 702.9b


def _to_blocks(g, attacker_player, attacker_oids):
    advance(g, lambda gg: gg.s.pending.kind == "declare_attack" and gg.s.active == attacker_player)
    while g.s.pending.kind == "declare_attack":
        oid = g.s.pending.info[0]
        act(g, A.ChooseAttack, player=attacker_player, oid=oid, attacks=oid in attacker_oids)
    advance(g, lambda gg: gg.s.pending.kind == "declare_block")


def test_first_strike_blocked_by_bears():
    g = new_game()
    advance(g, at("main1", turn=1))
    knight = put(g, 1, "Youthful Knight", "battlefield")
    bears = put(g, 0, "Grizzly Bears", "battlefield")
    bears_card = ciid(g, bears)
    _to_blocks(g, 1, {knight})
    act(g, A.ChooseBlock, player=0, blocker=bears, attacker=knight)
    advance(g, at("end_combat"))
    assert "Grizzly Bears" in gy_names(g, 0) and knight in g.s.objects                # CR 510.4
    assert g.s.objects[knight].damage == 0
    assert any(g.s.objects.get(o) is None for o in [bears]) and bears_card in [g.s.objects[o].ciid for o in g.s.zones[(0, "graveyard")]]


def test_first_strike_vs_first_strike_both_die():
    g = new_game(WU, WU)
    advance(g, at("main1", turn=1))
    k1 = put(g, 1, "Youthful Knight", "battlefield")
    k0 = put(g, 0, "Youthful Knight", "battlefield")
    _to_blocks(g, 1, {k1})
    act(g, A.ChooseBlock, player=0, blocker=k0, attacker=k1)
    advance(g, at("first_strike_damage"))
    fs = [t for t in g.s.log.transitions if t.kind == "combat_damage"]
    assert len(fs) == 1 and sum(e.kind == "DamageDealt" for e in fs[0].events) == 2
    advance(g, at("end_combat"))
    assert "Youthful Knight" in gy_names(g, 0) and "Youthful Knight" in gy_names(g, 1)


def test_damage_division_every_legal_split_applied_atomically():
    for split in ((3, 0), (2, 1), (1, 2), (0, 3)):
        g = new_game()
        advance(g, at("main1", turn=1))
        giant = put(g, 0, "Hill Giant", "battlefield")
        knight = put(g, 1, "Youthful Knight", "battlefield")
        drake = put(g, 1, "Wind Drake", "battlefield")
        _to_blocks(g, 0, {giant})
        while g.s.pending.kind == "declare_block":
            act(g, A.ChooseBlock, player=1, blocker=g.s.pending.info[0], attacker=giant)
        advance(g, lambda gg: gg.s.pending.kind == "assign_damage")
        divs = {tuple(n for _b, n in a.division) for a in g.legal_actions() if isinstance(a, A.AssignCombatDamage)}
        assert divs == {(3, 0), (2, 1), (1, 2), (0, 3)}                              # CR 510.1c, no order
        n0 = len(g.s.log.transitions)
        act(g, A.AssignCombatDamage, player=0, attacker=giant, division=tuple(zip(sorted([knight, drake]), split)))
        dmg = [t for t in g.s.log.transitions[n0:] if t.kind == "combat_damage"]
        assert len(dmg) == 1
        from_giant = sorted(dict(e.data)["n"] for e in dmg[0].events
                            if e.kind == "DamageDealt" and dict(e.data)["source"] == giant)
        assert from_giant == sorted(n for n in split if n)


def test_bolt_fizzles_when_its_target_died():
    g = new_game(RG, RG)
    advance(g, at("main1", turn=1))
    bears = put(g, 1, "Grizzly Bears", "battlefield")
    put(g, 0, "Mountain", "battlefield"); put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Lightning Bolt", "hand"); put(g, 0, "Lightning Bolt", "hand")
    cast(g, 0, "Lightning Bolt", ("obj", bears), lands=("Mountain",))
    cast(g, 0, "Lightning Bolt", ("obj", bears), lands=("Mountain",))
    for _ in range(2):
        act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)
    assert len(events(g, "SpellFizzled")) == 1 and g.s.life[1] == 20                  # CR 608.2b
    assert gy_names(g, 0).count("Lightning Bolt") == 2 and "Grizzly Bears" in gy_names(g, 1)   # CR 608.2n


def test_bolt_to_player():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Lightning Bolt", "hand")
    cast(g, 0, "Lightning Bolt", ("player", 1), lands=("Mountain",))
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)
    assert g.s.life[1] == 17


def test_giant_growth_saves_from_bolt_and_wears_off():
    g = new_game(RG, RG)
    advance(g, at("main1", turn=1))
    bears = put(g, 1, "Grizzly Bears", "battlefield")
    put(g, 1, "Forest", "battlefield"); put(g, 1, "Giant Growth", "hand")
    put(g, 0, "Mountain", "battlefield"); put(g, 0, "Lightning Bolt", "hand")
    cast(g, 0, "Lightning Bolt", ("obj", bears), lands=("Mountain",))
    act(g, A.PassPriority, player=0)
    cast(g, 1, "Giant Growth", ("obj", bears), lands=("Forest",))
    act(g, A.PassPriority, player=1); act(g, A.PassPriority, player=0)                # GG resolves
    assert g.s.power(bears) == 5
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)                # Bolt resolves
    assert bears in g.s.objects and g.s.objects[bears].damage == 3
    advance(g, at("upkeep", turn=2))
    assert g.s.objects[bears].damage == 0 and g.s.power(bears) == 2                  # CR 514.2


def test_giant_growth_does_not_follow_a_card_to_a_new_zone():
    g = new_game(RG, RG)
    advance(g, at("main1", turn=1))
    bears = put(g, 1, "Grizzly Bears", "battlefield")
    put(g, 1, "Forest", "battlefield"); put(g, 1, "Giant Growth", "hand")
    put(g, 0, "Mountain", "battlefield"); put(g, 0, "Lightning Bolt", "hand")
    act(g, A.PassPriority, player=0)
    cast(g, 1, "Giant Growth", ("obj", bears), lands=("Forest",))
    act(g, A.PassPriority, player=1)
    cast(g, 0, "Lightning Bolt", ("obj", bears), lands=("Mountain",))
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)                # Bolt kills Bears
    assert bears not in g.s.objects and bears in g.s.retired                          # CR 400.7
    act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)                # GG: target gone
    assert len(events(g, "SpellFizzled")) == 1
    card = [o for o in g.s.zones[(1, "graveyard")] if name_of(g, o) == "Grizzly Bears"][0]
    assert g.s.objects[card].eot_power == 0


def test_counterspell_and_counter_the_counter():
    g = new_game(WU, WU)
    advance(g, at("main1", turn=1))
    for p in (0, 1):
        for _ in range(3):
            put(g, p, "Island", "battlefield")
        put(g, p, "Counterspell", "hand")
    put(g, 0, "Divination", "hand")
    cast(g, 0, "Divination", lands=("Island", "Island", "Island"))
    div = g.s.stack[-1].sid
    act(g, A.PassPriority, player=0)
    cast(g, 1, "Counterspell", ("stack", div), lands=("Island", "Island"))
    cs1 = g.s.stack[-1].sid
    act(g, A.PassPriority, player=1)
    for _ in range(2):
        put(g, 0, "Island", "battlefield")
    cast(g, 0, "Counterspell", ("stack", cs1), lands=("Island", "Island"))
    hand_before = len(g.s.zones[(0, "hand")])
    for _ in range(2):
        act(g, A.PassPriority, player=0); act(g, A.PassPriority, player=1)
    assert len(events(g, "SpellCountered")) == 1                                        # CR 701.6a
    assert len(g.s.zones[(0, "hand")]) == hand_before + 2                             # Divination resolved
    assert gy_names(g, 1).count("Counterspell") == 1 and gy_names(g, 0).count("Counterspell") == 1


def test_propose_cast_offered_only_when_completable():
    g = new_game(RG, WU)
    advance(g, at("main1", turn=1))
    put(g, 0, "Forest", "battlefield")
    gg_ = put(g, 0, "Giant Growth", "hand")
    hg = put(g, 0, "Hill Giant", "hand")
    props = {a.oid for a in g.legal_actions() if isinstance(a, A.ProposeCast)}
    assert gg_ not in props and hg not in props                                       # no creature / unpayable
    put(g, 0, "Mountain", "battlefield")
    bolt = put(g, 0, "Lightning Bolt", "hand")
    assert bolt in {a.oid for a in g.legal_actions() if isinstance(a, A.ProposeCast)}   # players are targets
    g2 = new_game(WU, WU)
    advance(g2, at("main1", turn=1))
    put(g2, 0, "Island", "battlefield"); put(g2, 0, "Island", "battlefield")
    cs = put(g2, 0, "Counterspell", "hand")
    assert cs not in {a.oid for a in g2.legal_actions() if isinstance(a, A.ProposeCast)}   # empty stack


def test_rollback_restores_rules_state_and_original_object_id():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 0, "Forest", "battlefield"); put(g, 0, "Mountain", "battlefield")
    bears = put(g, 0, "Grizzly Bears", "hand")
    idx = g.s.zones[(0, "hand")].index(bears)
    pre_rules, pre_full, pre_head = g.s.rules_state_hash(), g.s.full_state_hash(), g.s.log.head
    pre_next_oid = g.s.next_oid
    act(g, A.ProposeCast, player=0, oid=bears)
    assert g.s.objects[bears].zone == "suspended" and g.s.stack[-1].sid.startswith("P")
    tap_for(g, 0, "Forest")
    n0 = len(g.s.log.transitions)
    g.rollback_open_cast("fault injection")                                          # CR 733.1
    assert g.s.rules_state_hash() == pre_rules
    assert g.s.zones[(0, "hand")].index(bears) == idx and g.s.objects[bears].zone == "hand"
    assert g.s.next_oid == pre_next_oid and bears not in g.s.retired                  # no id rewound or reused
    assert g.s.full_state_hash() != pre_full and g.s.log.head != pre_head
    assert [t.kind for t in g.s.log.transitions[n0:]] == ["rollback"]
    assert (g.pending().kind, g.pending().player) == ("priority", 0)                  # CR 733.2


def test_deck_out_loses_at_next_sba():
    g = new_game(RG, DECKOUT, starting=0)
    advance(g, lambda gg: gg.result is not None, max_steps=20000)
    assert g.result == ("win", 0, "draw_from_empty_library")                          # CR 704.5b
    assert events(g, "DrawFailed")


def test_simultaneous_loss_is_a_draw():
    g = new_game()
    advance(g, at("main1", turn=1))
    arrange(g, [op("damage_player", None, 0, 20), op("damage_player", None, 1, 20)])
    act(g, A.PassPriority, player=0)                                                  # SBA before priority
    assert g.result == ("draw", "simultaneous_loss")                                  # CR 104.4a


def test_turn_limit_is_a_draw():
    g = new_game(turn_limit=2)
    advance(g, lambda gg: gg.result is not None)
    assert g.result == ("draw", "turn_limit") and g.s.turn == 2


def test_discard_to_seven_at_cleanup():
    g = new_game()
    advance(g, at("main1", turn=1))
    for _ in range(3):
        put(g, 0, "Mountain", "hand")
    advance(g, lambda gg: gg.s.pending.kind == "discard")
    assert g.s.pending.info == (3,)                                                   # CR 514.1
    g.apply(g.legal_actions()[0])
    assert len(g.s.zones[(0, "hand")]) == 7


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"[ok] {name}")
            except Exception as e:
                fails += 1
                import traceback
                print(f"[FAIL] {name}: {type(e).__name__}: {e}")
                traceback.print_exc(limit=4)
    print("M1 FAILURES:", fails)
