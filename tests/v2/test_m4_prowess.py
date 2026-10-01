"""Milestone four: the Izzet Prowess card set (decks/auto/izzet_prowess_modern.txt) -- focused rules
tests, one section per grocery item (S1 lands, S2 Phyrexian mana, S3 private library decisions,
S4 delirium / statics, S5 Cori-Steel Cutter, S6 Expressive Iteration's permission, S7 Lava Dart
flashback, S8 Mishra's Bauble, S9 Slickshot Show-Off plot), plus Burn-vs-Prowess replay checks."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.cards import CardDefinition
from engine.v2.decklists import main_deck
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy
from engine.v2.record import make_record, replay
from engine.v2.rules import combat, statics
from tests.v2.decks import _expand
from tests.v2.helpers import act, advance, arrange, at, events, find, name_of, new_game, put

# Test-only synthetic decks (not real lists): every new card plus a Roiling Vortex opponent.
P_TEST = _expand([("Mountain", 6), ("Island", 2), ("Forest", 2), ("Steam Vents", 2), ("Thundering Falls", 2),
                  ("Scalding Tarn", 2), ("Wooded Foothills", 2), ("Mutagenic Growth", 2), ("Preordain", 2),
                  ("Serum Visions", 2), ("Dragon's Rage Channeler", 2), ("Violent Urge", 2),
                  ("Cori-Steel Cutter", 2), ("Expressive Iteration", 2), ("Lava Dart", 2), ("Mishra's Bauble", 2),
                  ("Slickshot Show-Off", 2), ("Monastery Swiftspear", 2)])
OPP = _expand([("Mountain", 12), ("Plains", 4), ("Roiling Vortex", 2), ("Rift Bolt", 4), ("Monastery Swiftspear", 4),
               ("Goblin Guide", 4), ("Lava Spike", 4), ("Lightning Helix", 4), ("Lightning Bolt", 2)])
assert len(P_TEST) == 40 and len(OPP) == 40


def _setup(turn=3):
    g = new_game(P_TEST, OPP)
    advance(g, at("main1", active=0, turn=turn))
    return g


def _mana(g, p, color, n=1):
    for _ in range(n):
        g.apply(next(a for a in g.legal_actions()
                     if isinstance(a, A.ActivateManaAbility) and a.player == p and a.color == color))


def _cast(g, p, oid, cost="normal", target=None, mana=(), sac=None):
    act(g, A.ProposeCast, player=p, oid=oid, cost=cost)
    if g.pending().kind == "cast_targets":
        act(g, A.ChooseTargets, player=p, targets=(target,))
    for c in mana:
        _mana(g, p, c)
    pays = [a for a in g.legal_actions() if isinstance(a, A.PayCost) and (sac is None or a.sacrifice == (sac,))]
    assert pays, f"cannot pay for {name_of(g, oid) if oid in g.s.objects else oid}"
    g.apply(pays[0])


def _pass_until(g, cond):
    advance(g, cond)


def _spell(g):
    return next(e for e in reversed(g.s.stack) if e.state == "cast")


def _resolve(g):
    advance(g, lambda g: not g.s.stack and not g.s.pending_triggers and g.pending().kind == "priority")


def _to_arrange(g):
    advance(g, lambda g: g.pending().kind == "arrange")


def _costs(g, oid):
    return {a.cost for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == oid}


def _lib_top(g, p, *names):
    """Put these cards (from library or hand) on top of p's library, names[0] ending on top."""
    oids = []
    for n in reversed(names):
        try:
            oid = find(g, p, n, "library")
        except KeyError:
            oid = find(g, p, n, "hand")
        arrange(g, [op("move", oid, "library", "top")])
        oids.append(g.s.zones[(p, "library")][0])
    return list(reversed(oids))


def _names(g, oids):
    return [name_of(g, o) for o in oids]


def _gy(g, p, *names):
    for n in names:
        put(g, p, n, "graveyard")


# =============================================================== S1 lands
def test_tarn_and_foothills_search_their_exact_types_and_may_fail_to_find():   # CR 701.23a/b
    for land, want in (("Scalding Tarn", {"Island", "Mountain", "Steam Vents", "Thundering Falls"}),
                       ("Wooded Foothills", {"Mountain", "Forest", "Steam Vents", "Thundering Falls"})):
        g = _setup()
        f = put(g, 0, land, "battlefield")
        act(g, A.ActivateAbility, player=0, oid=f)
        assert g.s.life[0] == 19 and f not in g.s.objects
        advance(g, lambda g: g.pending().kind == "search_choice")
        found = [a.oid for a in g.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None]
        assert set(_names(g, found)) == want
        assert A.ChooseSearchResult(0, None) in g.legal_actions()       # may fail with a valid card present
        g.apply(A.ChooseSearchResult(0, None))
        assert events(g, "SearchFoundNothing") and events(g, "Shuffled")


def test_foothills_finds_mountain_or_steam_vents_in_the_real_list():
    prowess = main_deck("decks/auto/izzet_prowess_modern.txt")
    g = Game.new(prowess, prowess, 4, check_invariants=True)
    while g.pending().kind == "mulligan_declare":
        g.apply(A.DeclareKeep(g.pending().player))
    advance(g, at("main1", active=0, turn=1))
    f = put(g, 0, "Wooded Foothills", "battlefield")
    act(g, A.ActivateAbility, player=0, oid=f)
    advance(g, lambda g: g.pending().kind == "search_choice")
    found = {name_of(g, a.oid) for a in g.legal_actions() if isinstance(a, A.ChooseSearchResult) and a.oid is not None}
    assert found == {"Mountain", "Steam Vents", "Thundering Falls"}      # no Forest in the list


def test_steam_vents_is_a_shock_land_and_taps_for_u_or_r():               # CR 614.1c, 305.6
    g = _setup()
    sv = put(g, 0, "Steam Vents", "hand")
    act(g, A.PlayLand, player=0, oid=sv)
    assert g.pending().kind == "entry_payment"
    assert {a.pay for a in g.legal_actions() if isinstance(a, A.ChooseEntryPayment)} == {True, False}
    act(g, A.ChooseEntryPayment, player=0, pay=True)
    vents = g.s.zones[("bf",)][-1]
    assert g.s.life[0] == 18 and not g.s.objects[vents].tapped
    assert {a.color for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.oid == vents} == {"U", "R"}


def test_thundering_falls_enters_tapped_and_surveils_one():              # CR 701.25a
    g = _setup()
    top = _lib_top(g, 0, "Lava Dart")[0]
    falls = put(g, 0, "Thundering Falls", "hand")
    act(g, A.PlayLand, player=0, oid=falls)
    tf = g.s.zones[("bf",)][-1]
    assert g.s.objects[tf].tapped and events(g, "EntersTapped")
    _to_arrange(g)
    opts = [a for a in g.legal_actions() if isinstance(a, A.ArrangeCards)]
    assert set(opts) == {A.ArrangeCards(0, top=(top,)), A.ArrangeCards(0, graveyard=(top,))}
    g.apply(A.ArrangeCards(0, graveyard=(top,)))
    assert _names(g, g.s.zones[(0, "graveyard")])[-1] == "Lava Dart"


# =============================================================== S2 Phyrexian mana
def test_mutagenic_growth_is_announced_with_mana_or_with_two_life():      # CR 107.4f (card ruling: chosen on announce)
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    put(g, 0, "Forest", "battlefield")
    mg = put(g, 0, "Mutagenic Growth", "hand")
    assert _costs(g, mg) == {"normal", "phyrexian:G"}
    _cast(g, 0, mg, "phyrexian:G", ("obj", sw))
    assert g.s.life[0] == 18 and _spell(g).mana_spent == 0
    _resolve(g)
    assert g.s.power(sw) == 1 + 2 + 1 and g.s.toughness(sw) == 2 + 2 + 1      # +2/+2 and prowess
    g2 = _setup()
    sw2 = put(g2, 0, "Monastery Swiftspear", "battlefield")
    put(g2, 0, "Forest", "battlefield")
    mg2 = put(g2, 0, "Mutagenic Growth", "hand")
    _cast(g2, 0, mg2, "normal", ("obj", sw2), mana=("G",))
    assert g2.s.life[0] == 20 and _spell(g2).mana_spent == 1


def test_phyrexian_life_needs_two_life_and_mana_needs_green():           # CR 119.4
    g = _setup()
    put(g, 0, "Monastery Swiftspear", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    mg = put(g, 0, "Mutagenic Growth", "hand")
    assert _costs(g, mg) == {"phyrexian:G"}                                # no green source
    arrange(g, [op("damage_player", 1, 0, 19)])                              # 1 life left
    assert _costs(g, mg) == set()


def test_mutagenic_growth_for_life_triggers_roiling_vortex():             # "if no mana was spent to cast it"
    g = _setup()
    put(g, 1, "Roiling Vortex", "battlefield")
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    mg = put(g, 0, "Mutagenic Growth", "hand")
    _cast(g, 0, mg, "phyrexian:G", ("obj", sw))
    _resolve(g)
    assert g.s.life[0] == 20 - 2 - 5


# =============================================================== S3 private library decisions
def test_preordain_scry_two_is_private_then_draws():                      # CR 701.22a
    g = _setup()
    put(g, 0, "Island", "battlefield")
    a, b, c = _lib_top(g, 0, "Mountain", "Lava Dart", "Forest")
    pre = put(g, 0, "Preordain", "hand")
    _cast(g, 0, pre, mana=("U",))
    _to_arrange(g)
    opts = [x for x in g.legal_actions() if isinstance(x, A.ArrangeCards)]
    assert len(opts) == 6                                                   # 2 top orders + 2 bottom orders + 2 splits
    assert g.observe(0).my_look == ((a, "Mountain"), (b, "Lava Dart")) and g.observe(1).my_look == ()
    assert g.pending().info == ("scry", 2)
    g.apply(A.ArrangeCards(0, bottom=(b, a)))
    lib = g.s.zones[(0, "library")]
    assert _names(g, lib[-2:]) == ["Lava Dart", "Mountain"] and "Forest" in _names(g, g.s.zones[(0, "hand")])
    known = g.observe(0).my_known
    assert {(n, pos) for _o, pos, _x, n in known} == {("Lava Dart", len(lib) - 2), ("Mountain", len(lib) - 1)}
    assert g.observe(1).my_known == ()
    assert _names(g, g.s.zones[(0, "graveyard")]) == ["Preordain"]
    arr = events(g, "LibraryArranged")[-1]
    assert dict(arr.data)["bottom"] == 2 and "commitment" in dict(arr.data)


def test_serum_visions_draws_first_then_scries_two():
    g = _setup()
    put(g, 0, "Island", "battlefield")
    a, b, c = _lib_top(g, 0, "Mountain", "Lava Dart", "Forest")
    sv = put(g, 0, "Serum Visions", "hand")
    _cast(g, 0, sv, mana=("U",))
    _to_arrange(g)
    assert a in g.s.zones[(0, "hand")] or "Mountain" in _names(g, g.s.zones[(0, "hand")])
    assert [n for _o, n in g.observe(0).my_look] == ["Lava Dart", "Forest"]


def _ei_setup(lib_names=("Mountain", "Lava Dart", "Preordain")):
    g = _setup()
    put(g, 0, "Island", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    cards = _lib_top(g, 0, *lib_names)
    ei = put(g, 0, "Expressive Iteration", "hand")
    _cast(g, 0, ei, mana=("U", "R"))
    _to_arrange(g)
    return g, cards


def test_expressive_iteration_hand_bottom_exile_and_play_the_land_this_turn():
    g, (mtn, dart, pre) = _ei_setup()
    opts = [x for x in g.legal_actions() if isinstance(x, A.ArrangeCards)]
    assert len(opts) == 6 and all(len(x.hand) == len(x.bottom) == len(x.exile) == 1 for x in opts)
    g.apply(A.ArrangeCards(0, hand=(pre,), bottom=(dart,), exile=(mtn,)))
    ex = g.s.zones[(0, "exile")][-1]
    assert name_of(g, ex) == "Mountain" and _names(g, g.s.zones[(0, "library")][-1:]) == ["Lava Dart"]
    assert ("may_play", (0, ex)) in [tuple(e) for e in g.s.turn_effects]
    _resolve(g)
    act(g, A.PlayLand, player=0, oid=ex)                                     # a land play from exile
    assert name_of(g, g.s.zones[("bf",)][-1]) == "Mountain" and g.s.land_played[0] == 1


def test_expressive_iteration_exiled_spell_castable_this_turn_only():
    g, (mtn, dart, pre) = _ei_setup()
    g.apply(A.ArrangeCards(0, hand=(mtn,), bottom=(pre,), exile=(dart,)))
    ex = g.s.zones[(0, "exile")][-1]
    _resolve(g)
    put(g, 0, "Mountain", "battlefield")
    assert _costs(g, ex) == {"normal"}                                       # normal cost and timing
    advance(g, at("main1", active=0, turn=5))
    assert ex in g.s.zones[(0, "exile")] and _costs(g, ex) == set()         # permission ended; stays exiled


def test_expressive_iteration_exiled_land_needs_an_available_land_play():  # card ruling, CR 305.2
    g, (mtn, dart, pre) = _ei_setup()
    g.apply(A.ArrangeCards(0, hand=(pre,), bottom=(dart,), exile=(mtn,)))
    ex = g.s.zones[(0, "exile")][-1]
    _resolve(g)
    act(g, A.PlayLand, player=0, oid=find(g, 0, "Mountain", "hand") if "Mountain" in _names(g, g.s.zones[(0, "hand")])
        else put(g, 0, "Mountain", "hand"))
    assert not any(isinstance(a, A.PlayLand) and a.oid == ex for a in g.legal_actions())


def test_expressive_iteration_with_two_cards_puts_one_in_hand_and_one_on_the_bottom():   # card ruling
    g = _setup()
    for c in ("Island", "Mountain", "Mountain"):
        put(g, 0, c, "battlefield")
    ei = put(g, 0, "Expressive Iteration", "hand")
    lib = g.s.zones[(0, "library")]
    arrange(g, [op("move", x, "exile", "end") for x in list(lib)[2:]])
    _cast(g, 0, ei, mana=("U", "R"))
    _to_arrange(g)
    a, b = g.s.continuation.data[1:]
    assert set(x for x in g.legal_actions() if isinstance(x, A.ArrangeCards)) == {
        A.ArrangeCards(0, hand=(a,), bottom=(b,)), A.ArrangeCards(0, hand=(b,), bottom=(a,))}


# =============================================================== S4 delirium and statics
def test_delirium_counts_distinct_card_types_of_cards_only():             # DRC ruling: these card types
    def d(types):
        return CardDefinition("x", "", (), 0, (), (), types, (), None, None, (), "x", "1")
    defs = {1: d(("Artifact", "Creature")), 2: d(("Land",)), 3: d(("Instant",)), 4: d(("Creature",)),
            5: d(("Enchantment",))}
    s = SimpleNamespace(zones={(0, "graveyard"): [11, 12, 14]}, objects={i + 10: SimpleNamespace(ciid=i) for i in defs},
                        def_by_ciid=defs, instances={i: SimpleNamespace(token=False) for i in defs})
    assert statics.card_types_in_graveyard(s, 0) == 3                       # artifact + creature + land
    s.zones[(0, "graveyard")].append(13)
    assert statics.delirium(s, 0)                                           # + instant = 4
    s.instances[5] = SimpleNamespace(token=True)
    s.zones[(0, "graveyard")][:] = [11, 12, 15]
    assert statics.card_types_in_graveyard(s, 0) == 3                       # a token is not a card


def _delirium(g, p=0):
    _gy(g, p, "Mountain", "Lava Dart", "Preordain", "Mishra's Bauble")       # land, instant, sorcery, artifact


def test_drc_with_delirium_is_a_3_3_flier_that_must_attack_and_can_block():   # CR 508.1d
    g = _setup()
    drc = put(g, 0, "Dragon's Rage Channeler", "battlefield")
    assert (g.s.power(drc), g.s.toughness(drc), g.s.has_kw(drc, "Flying")) == (1, 1, False)
    _delirium(g)
    assert (g.s.power(drc), g.s.toughness(drc), g.s.has_kw(drc, "Flying")) == (3, 3, True)
    advance(g, lambda g: g.pending().kind == "declare_attack" and g.s.turn == 5)
    assert [a.attacks for a in g.legal_actions() if isinstance(a, A.ChooseAttack)] == [True]
    g2 = _setup()
    drc2 = put(g2, 0, "Dragon's Rage Channeler", "battlefield")
    _delirium(g2)
    gob = put(g2, 1, "Goblin Guide", "battlefield")
    advance(g2, lambda g: g.pending().kind == "declare_attack" and g.s.active == 1)
    act(g2, A.ChooseAttack, player=1, oid=gob, attacks=True)
    advance(g2, lambda g: g.pending().kind == "declare_block")
    assert A.ChooseBlock(0, drc2, gob) in g2.legal_actions()                # it does not lose the ability to block


def test_drc_with_damage_dies_when_delirium_is_lost():                    # CR 704.5g, 611.3a
    g = _setup()
    drc = put(g, 0, "Dragon's Rage Channeler", "battlefield")
    _delirium(g)
    arrange(g, [op("damage_creature", 0, drc, 2)])
    g.apply(A.PassPriority(0))
    assert drc in g.s.objects                                               # 3/3 with 2 damage survives
    bauble = find(g, 0, "Mishra's Bauble", "graveyard")
    arrange(g, [op("move", bauble, "exile", "end")])                         # three types left
    g.apply(A.PassPriority(1))
    assert drc not in g.s.objects and "Dragon's Rage Channeler" in _names(g, g.s.zones[(0, "graveyard")])


def test_violent_urge_first_strike_and_double_strike_only_with_delirium():
    g = _setup()
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    _gy(g, 0, "Mountain", "Preordain", "Mishra's Bauble")                    # 3 types; Urge on the stack doesn't count
    vu = put(g, 0, "Violent Urge", "hand")
    _cast(g, 0, vu, target=("obj", sw), mana=("R",))
    _resolve(g)
    assert g.s.has_kw(sw, "First strike") and not g.s.has_kw(sw, "Double strike")
    assert g.s.power(sw) == 1 + 1 + 1                                        # +1/+0 and prowess
    g2 = _setup()
    sw2 = put(g2, 0, "Monastery Swiftspear", "battlefield")
    put(g2, 0, "Mountain", "battlefield")
    _delirium(g2)
    vu2 = put(g2, 0, "Violent Urge", "hand")
    _cast(g2, 0, vu2, target=("obj", sw2), mana=("R",))
    _resolve(g2)
    assert g2.s.has_kw(sw2, "First strike") and g2.s.has_kw(sw2, "Double strike")


# =============================================================== S5 Cori-Steel Cutter
def _equip_actions(g, cutter):
    return [a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == cutter]


def test_equip_is_sorcery_speed_targets_your_creature_and_grants_the_bonus():   # CR 702.6a, 301.5
    g = _setup()
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")
    mine = put(g, 0, "Monastery Swiftspear", "battlefield")                   # summoning sick this turn
    foe = put(g, 1, "Goblin Guide", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    assert not _equip_actions(g, cutter)                                      # {1}{R} not in the pool yet
    _mana(g, 0, "R", 2)
    eq = _equip_actions(g, cutter)
    assert {a.targets for a in eq} == {(("obj", mine),)}                     # only a creature you control
    g.apply(eq[0])
    _resolve(g)
    assert g.s.attachments == {cutter: mine}
    assert (g.s.power(mine), g.s.toughness(mine)) == (2, 3)
    assert g.s.has_kw(mine, "Trample") and g.s.has_kw(mine, "Haste")
    assert mine in combat.eligible_attackers(g.s)                            # haste: can attack now
    advance(g, at("main1", active=1, turn=4))
    arrange(g, [op("add_mana", 1, "R", 2)])
    assert not _equip_actions(g, cutter)                                      # not on the opponent's turn


def test_reequip_moves_the_equipment_and_equipping_the_same_creature_does_nothing():   # CR 701.3b
    g = _setup()
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")
    a = put(g, 0, "Monastery Swiftspear", "battlefield")
    b = put(g, 0, "Dragon's Rage Channeler", "battlefield")
    arrange(g, [op("attach", cutter, a), op("add_mana", 0, "R", 4)])
    g.apply(next(x for x in _equip_actions(g, cutter) if x.targets == (("obj", a),)))
    _resolve(g)
    assert g.s.attachments == {cutter: a} and events(g, "AttachNoChange")
    g.apply(next(x for x in _equip_actions(g, cutter) if x.targets == (("obj", b),)))
    _resolve(g)
    assert g.s.attachments == {cutter: b} and g.s.power(a) == 1 + 0 and g.s.power(b) == 2


def test_flurry_counts_spells_cast_before_the_cutter_and_attaching_is_optional():   # card ruling
    g = _setup()
    for _ in range(3):
        put(g, 0, "Mountain", "battlefield")
    d1 = put(g, 0, "Lava Dart", "hand")
    _cast(g, 0, d1, target=("player", 1), mana=("R",))
    _resolve(g)
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")                  # entered after the first spell
    d2 = put(g, 0, "Lava Dart", "hand")
    _cast(g, 0, d2, target=("player", 1), mana=("R",))
    assert g.s.spells_cast_turn[0] == 2
    advance(g, lambda g: g.pending().kind == "attach_choice")
    token = g.s.zones[("bf",)][-1]
    assert name_of(g, token) == "Monk Token" and g.s.instances[g.s.objects[token].ciid].token
    assert {a.attach for a in g.legal_actions() if isinstance(a, A.ChooseAttach)} == {True, False}
    act(g, A.ChooseAttach, player=0, attach=False)
    _resolve(g)
    assert cutter not in g.s.attachments
    b = put(g, 0, "Mishra's Bauble", "hand")
    _cast(g, 0, b)
    _resolve(g)
    assert len(events(g, "TokenCreated")) == 1                               # the third spell: no flurry


def test_monk_token_has_prowess_ceases_to_exist_and_the_equipment_stays():   # CR 704.5d, 704.5n, 111.7
    g = _setup()
    for _ in range(2):
        put(g, 0, "Mountain", "battlefield")
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")
    b1, b2 = put(g, 0, "Mishra's Bauble", "hand"), put(g, 0, "Mishra's Bauble", "hand")
    _cast(g, 0, b1)
    _resolve(g)
    _cast(g, 0, b2)
    advance(g, lambda g: g.pending().kind == "attach_choice")
    act(g, A.ChooseAttach, player=0, attach=True)
    _resolve(g)
    token = next(o for o in g.s.zones[("bf",)] if name_of(g, o) == "Monk Token")
    assert g.s.attachments == {cutter: token} and (g.s.power(token), g.s.toughness(token)) == (2, 2)
    dart = put(g, 0, "Lava Dart", "hand")
    _cast(g, 0, dart, target=("player", 1), mana=("R",))
    _resolve(g)
    assert g.s.power(token) == 3                                              # prowess
    arrange(g, [op("damage_creature", 0, token, 3)])
    g.apply(A.PassPriority(0))
    assert token not in g.s.objects and not g.s.attachments
    assert not any(g.s.instances[g.s.objects[o].ciid].token for z in g.s.zones.values() for o in z)
    assert cutter in g.s.zones[("bf",)] and events(g, "TokenCeasedToExist") and events(g, "Unattached")


def _attack_with(g, attacker, blocker):
    advance(g, lambda g: g.pending().kind == "declare_attack" and g.s.active == 0)
    while g.pending().kind == "declare_attack":
        oid = g.pending().info[0]
        g.apply(A.ChooseAttack(0, oid, oid == attacker))
    while g.pending().kind != "declare_block":
        g.apply(A.PassPriority(g.pending().player))
    while g.pending().kind == "declare_block":
        bl = g.pending().info[0]
        g.apply(A.ChooseBlock(1, bl, attacker if bl == blocker else None))


def test_trample_assigns_lethal_to_the_blocker_before_the_player():      # CR 702.19b
    g = _setup()
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    gg = put(g, 1, "Goblin Guide", "battlefield")
    arrange(g, [op("attach", cutter, sw)])
    advance(g, at("main1", active=0, turn=5))
    arrange(g, [op("eot_mod", sw, 3, 0), op("damage_creature", 0, gg, 1)])   # 5 power; blocker has 1 damage
    _attack_with(g, sw, gg)
    advance(g, lambda g: g.pending().kind == "assign_damage")
    divs = {a.division for a in g.legal_actions() if isinstance(a, A.AssignCombatDamage)}
    assert divs == {((gg, 5), ("player", 0))} | {((gg, k), ("player", 5 - k)) for k in (1, 2, 3, 4)}
    life = g.s.life[1]
    act(g, A.AssignCombatDamage, player=0, division=((gg, 1), ("player", 4)))
    assert g.s.life[1] == life - 4 and gg not in g.s.objects


def test_trample_with_its_blocker_removed_deals_all_damage_to_the_player():   # CR 702.19d
    g = _setup()
    cutter = put(g, 0, "Cori-Steel Cutter", "battlefield")
    sw = put(g, 0, "Monastery Swiftspear", "battlefield")
    gg = put(g, 1, "Goblin Guide", "battlefield")
    arrange(g, [op("attach", cutter, sw)])
    advance(g, at("main1", active=0, turn=5))
    _attack_with(g, sw, gg)
    arrange(g, [op("move", gg, "graveyard", "end")])
    life = g.s.life[1]
    advance(g, lambda g: g.s.step == "end_combat" or g.s.step == "main2")
    assert g.s.life[1] == life - 2


# =============================================================== S7 Lava Dart flashback
def test_lava_dart_flashback_sacrifices_a_mountain_and_is_exiled():      # CR 702.34a
    g = _setup()
    dart = put(g, 0, "Lava Dart", "graveyard")
    assert _costs(g, dart) == set()                                          # no Mountain to sacrifice
    vents = put(g, 0, "Steam Vents", "battlefield")                          # an Island Mountain
    arrange(g, [op("tap", vents)])
    assert _costs(g, dart) == {"flashback"}
    _cast(g, 0, dart, "flashback", ("player", 1), sac=vents)
    assert vents not in g.s.objects and _spell(g).mana_spent == 0
    _resolve(g)
    assert g.s.life[1] == 19 and "Lava Dart" in _names(g, g.s.zones[(0, "exile")])
    assert "Lava Dart" not in _names(g, g.s.zones[(0, "graveyard")]) and events(g, "ReplacedByExile")


def test_flashback_spell_is_exiled_even_when_it_fizzles():
    g = _setup()
    dart = put(g, 0, "Lava Dart", "graveyard")
    mtn = put(g, 0, "Mountain", "battlefield")
    gg = put(g, 1, "Goblin Guide", "battlefield")
    _cast(g, 0, dart, "flashback", ("obj", gg), sac=mtn)
    arrange(g, [op("move", gg, "graveyard", "end")])
    _resolve(g)
    assert events(g, "SpellFizzled") and "Lava Dart" in _names(g, g.s.zones[(0, "exile")])


# =============================================================== S8 Mishra's Bauble
def test_bauble_look_is_private_and_the_draw_waits_for_the_next_upkeep():   # CR 603.7a-e
    g = _setup()
    top = g.s.zones[(1, "library")][0]
    bauble = put(g, 0, "Mishra's Bauble", "battlefield")
    acts = [a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == bauble]
    assert {a.targets for a in acts} == {(("player", 0),), (("player", 1),)}
    g.apply(next(a for a in acts if a.targets == (("player", 1),)))
    assert bauble not in g.s.objects
    _resolve(g)
    looked = dict(events(g, "LookedAt")[-1].data)
    assert looked["library"] == 1 and "oid" not in looked and "name" not in looked and "ciid" not in looked
    assert g.observe(0).my_known == ((1, 0, top, name_of(g, top)),) and g.observe(1).my_known == ()
    advance(g, lambda g: g.s.turn == 4 and g.s.step == "upkeep" and g.pending().kind == "priority")
    assert g.s.stack[-1].ability == "bauble_draw" and g.s.stack[-1].controller == 0
    hand = len(g.s.zones[(0, "hand")])
    _resolve(g)
    assert len(g.s.zones[(0, "hand")]) == hand + 1 and not g.s.delayed     # drew once, during turn 4's upkeep
    advance(g, at("main1", active=0, turn=5))
    assert len(events(g, "DelayedTriggerCreated")) == 1


def test_bauble_cast_for_zero_triggers_roiling_vortex():
    g = _setup()
    put(g, 1, "Roiling Vortex", "battlefield")
    b = put(g, 0, "Mishra's Bauble", "hand")
    _cast(g, 0, b)
    _resolve(g)
    assert g.s.life[0] == 15


# =============================================================== S9 Slickshot Show-Off
def test_slickshot_gets_plus_two_per_noncreature_spell():
    g = _setup()
    sl = put(g, 0, "Slickshot Show-Off", "battlefield")
    put(g, 0, "Mountain", "battlefield")
    assert g.s.has_kw(sl, "Flying") and g.s.has_kw(sl, "Haste")
    b = put(g, 0, "Mishra's Bauble", "hand")
    _cast(g, 0, b)
    _resolve(g)
    assert g.s.power(sl) == 3


def test_plot_is_a_main_phase_special_action_and_the_free_cast_waits_a_turn():   # CR 702.170a-d, 116.2k
    g = _setup()
    sl = put(g, 0, "Slickshot Show-Off", "hand")
    assert not [a for a in g.legal_actions() if isinstance(a, A.Plot)]       # {1}{R} not in the pool
    arrange(g, [op("add_mana", 0, "R", 2)])
    plots = [a for a in g.legal_actions() if isinstance(a, A.Plot)]
    assert plots and all(a.oid == sl for a in plots)
    g.apply(plots[0])
    ex = g.s.zones[(0, "exile")][-1]
    assert g.s.plotted == ((ex, 3),) and g.pending().player == 0 and not g.s.stack     # no stack
    assert _costs(g, ex) == set()                                            # not the turn it became plotted
    advance(g, at("main1", active=1, turn=4))
    assert _costs(g, ex) == set()                                            # not on the opponent's turn
    advance(g, at("main1", active=0, turn=5))
    put(g, 1, "Roiling Vortex", "battlefield")
    assert _costs(g, ex) == {"plot"}
    _cast(g, 0, ex, "plot")
    assert _spell(g).mana_spent == 0
    _resolve(g)
    sl2 = next(o for o in g.s.zones[("bf",)] if name_of(g, o) == "Slickshot Show-Off")
    assert sl2 in combat.eligible_attackers(g.s) and g.s.life[0] == 15     # haste; Vortex: no mana spent


def test_a_plotted_card_need_not_be_cast():
    g = _setup()
    sl = put(g, 0, "Slickshot Show-Off", "hand")
    arrange(g, [op("add_mana", 0, "R", 2)])
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.Plot)))
    ex = g.s.zones[(0, "exile")][-1]
    advance(g, at("main1", active=0, turn=7))
    assert ex in g.s.zones[(0, "exile")] and _costs(g, ex) == {"plot"}     # still castable on any later turn


# =============================================================== Burn vs Prowess: replay + determinism
def _play(seed, starting, burn_seat, aggro=True):
    burn, prow = main_deck("mono_red_aggro_modern"), main_deck("decks/auto/izzet_prowess_modern.txt")
    decks = (burn, prow) if burn_seat == 0 else (prow, burn)
    g = Game.new(decks[0], decks[1], seed, starting_player=starting, check_invariants=True)
    pols = [SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)] if aggro else \
        [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)]
    g.run(pols)
    return g


def test_burn_vs_prowess_records_replay_exactly_and_repeat_identically():
    for seed in range(8):
        g = _play(seed, seed % 2, (seed // 2) % 2, aggro=seed % 3 != 0)
        rec = make_record(g, policy_seeds=[seed, seed + 1])
        g2 = replay(rec)
        assert g2.s.log.head == g.s.log.head
        g3 = _play(seed, seed % 2, (seed // 2) % 2, aggro=seed % 3 != 0)
        assert make_record(g3, policy_seeds=[seed, seed + 1]) == rec


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("M4 PROWESS TESTS PASS")
