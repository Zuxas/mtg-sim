"""test_mana_costs.py -- issue #16.

ManaPool mis-costed four kinds of mana symbol:
  {C}      was dropped (Thought-Knot Seer castable off RRRR)
  {X/P}    needed colored mana (Mutagenic Growth uncastable with no mana)
  {A/B}    only accepted A;  {2/X} cost 1 generic
  lands with no basic type made any color (Urza's Tower, Eldrazi Temple)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.mana import ManaPool, parse_cost

TKS = "{3}{C}"             # Thought-Knot Seer
GROWTH = "{G/P}"           # Mutagenic Growth
DISMEMBER = "{1}{B/P}{B/P}"
HELIX = "{R}{W}"           # control: plain two-color cost
CHARM = "{R/W}{R/W}"       # hybrid, e.g. Boros Reckoner pips
FLAYER = "{2/W}{2/W}{2/W}"  # Spectral Procession-style


def test_colorless_pip_needs_colorless_mana():
    assert not ManaPool(R=4).can_pay(TKS, 4)
    assert not ManaPool(R=3, flex=1).can_pay(TKS, 4), "flex is any COLOR, not colorless"
    pool = ManaPool(R=3, C=1)
    assert pool.pay(TKS, 4) and pool.total() == 0
    pool = ManaPool(C=4)
    assert pool.pay(TKS, 4) and pool.total() == 0


def test_generic_can_still_be_paid_with_colorless():
    pool = ManaPool(C=2, R=1)
    assert pool.pay("{2}{R}", 3) and pool.total() == 0


def test_phyrexian_pays_life_when_there_is_no_mana():
    pool = ManaPool()
    assert pool.can_pay(GROWTH, 1)
    assert pool.pay(GROWTH, 1) and pool.life_paid == 2


def test_phyrexian_uses_spare_mana_before_life():
    pool = ManaPool(G=1)
    assert pool.pay(GROWTH, 1) and pool.life_paid == 0 and pool.G == 0
    pool = ManaPool(R=1)                    # wrong color: life
    assert pool.pay(GROWTH, 1) and pool.life_paid == 2 and pool.R == 1


def test_dismember_costs():
    pool = ManaPool(R=1)                    # {1} + 4 life
    assert pool.pay(DISMEMBER, 3) and pool.life_paid == 4 and pool.total() == 0
    pool = ManaPool(B=2, R=1)               # full mana, no life
    assert pool.pay(DISMEMBER, 3) and pool.life_paid == 0 and pool.total() == 0
    pool = ManaPool(B=1, R=1)               # one B pip in mana, one in life
    assert pool.pay(DISMEMBER, 3) and pool.life_paid == 2 and pool.total() == 0
    assert not ManaPool().can_pay(DISMEMBER, 3), "the generic {1} still needs mana"


def test_apl_can_refuse_to_pay_life():
    pool = ManaPool(phyrexian_life_ok=False)
    assert not pool.can_pay(GROWTH, 1)
    pool.G = 1
    assert pool.pay(GROWTH, 1) and pool.life_paid == 0


def test_life_paid_resets_between_spells():
    pool = ManaPool(R=1)
    pool.pay(GROWTH, 1)
    assert pool.life_paid == 2
    pool.pay("{R}", 1)
    assert pool.life_paid == 0


def test_two_color_hybrid_takes_either_color():
    assert ManaPool(W=2).can_pay(CHARM, 2)
    assert ManaPool(R=2).can_pay(CHARM, 2)
    assert ManaPool(R=1, W=1).can_pay(CHARM, 2)
    assert ManaPool(flex=2).can_pay(CHARM, 2)
    assert not ManaPool(G=2).can_pay(CHARM, 2)
    pool = ManaPool(R=1, W=3)               # spends what it has most of
    assert pool.pay("{R/W}", 1) and (pool.R, pool.W) == (1, 2)


def test_two_generic_hybrid():
    assert ManaPool(W=3).can_pay(FLAYER, 6)
    assert ManaPool(R=6).can_pay(FLAYER, 6)
    assert not ManaPool(R=5).can_pay(FLAYER, 6)
    pool = ManaPool(W=1, R=4)               # W + 2 + 2
    assert pool.pay(FLAYER, 6) and pool.total() == 0


def test_plain_costs_unchanged():
    assert ManaPool(R=1, W=1).can_pay(HELIX, 2)
    assert not ManaPool(R=2).can_pay(HELIX, 2)
    assert ManaPool(R=1, flex=1).can_pay(HELIX, 2)
    assert parse_cost("{2}{W}{U}") == {"generic": 2, "W": 1, "U": 1}
    assert parse_cost("{X}{R}") == {"generic": 0, "R": 1}


def test_lands_without_a_basic_type_follow_their_text():
    def made(type_line, name, text):
        pool = ManaPool()
        pool.add_land(type_line, name, text)
        return {k: v for k, v in vars(pool).items() if k in "WUBRGC" or k == "flex" if v}
    assert made("Land - Urza's Tower", "Urza's Tower", "{T}: Add {C}. If you control ...") == {"C": 1}
    assert made("Land", "Eldrazi Temple", "{T}: Add {C}.\n{T}: Add {C}{C}. Spend this mana only ...") == {"C": 1}
    assert made("Land", "Cavern of Souls", "{T}: Add {C}.\n{T}: Add one mana of any color. ...") == {"flex": 1}
    assert made("Land", "Battlefield Forge", "{T}: Add {C}.\n{T}: Add {R} or {W}. ...") == {"flex": 1}
    assert made("Land", "Pendelhaven", "{T}: Add {G}.") == {"G": 1}
    assert made("Land", "Mystery Land", "") == {"flex": 1}, "no text: old behavior"
    assert made("Basic Land - Mountain", "Mountain", "({T}: Add {R}.)") == {"R": 1}
    assert made("Land - Island Mountain", "Steam Vents", "({T}: Add {U} or {R}.)") == {"flex": 1}


def test_hybrid_search_finds_the_legal_assignment():
    # greedy would spend W on {W/U} and then have nothing for {W/R}
    pool = ManaPool(W=1, U=1)
    assert pool.pay("{W/U}{W/R}", 2) and pool.total() == 0
    assert not ManaPool(U=2).can_pay("{W/U}{W/R}", 2)
    pool = ManaPool(W=1, R=2)                   # {2/W}{R/W}: R for hybrid, W for 2/W, or 2 generic
    assert pool.can_pay("{2/W}{R/W}", 3)


def test_cannot_pay_more_life_than_you_have():
    from data.card import Card
    from engine.game_state import GameState
    growth = lambda: Card(name="Mutagenic Growth", mana_cost=GROWTH, cmc=1,
                          type_line="Instant", oracle_text="", colors=["G"])
    gs = GameState(mainboard=[], on_play=True)
    gs.life = 1
    spell = growth()
    gs.zones.hand = [spell]
    assert gs.cast_spell(spell) is False and gs.life == 1 and spell in gs.zones.hand
    gs.life = 2                                  # paying to exactly 0 is legal
    assert gs.can_pay_mana(GROWTH, 1)
    gs.life = 1
    gs.mana_pool.add("G", 1)                     # with mana there is no life cost
    assert gs.cast_spell(spell) is not False and gs.life == 1


def test_every_payment_path_charges_life():
    """cast_spell, counterspells, the priority stack and the reactive window
    all pay through GameState.pay_mana."""
    import inspect
    from engine import game_state, counter_resolver, priority_stack, match_engine
    for mod in (counter_resolver, priority_stack, match_engine):
        src = inspect.getsource(mod)
        assert "mana_pool.pay(" not in src and "pay_mana(" in src, mod.__name__
    gs = game_state.GameState(mainboard=[], on_play=True)
    assert gs.pay_mana(DISMEMBER, 3) is False    # the generic {1} has no mana
    gs.mana_pool.add("R", 1)
    assert gs.pay_mana(DISMEMBER, 3) and gs.life == 16


def test_cast_spell_charges_phyrexian_life():
    from data.card import Card
    from engine.game_state import GameState
    gs = GameState(mainboard=[], on_play=True)
    growth = Card(name="Mutagenic Growth", mana_cost=GROWTH, cmc=1, type_line="Instant",
                  oracle_text="", colors=["G"])
    gs.zones.hand = [growth]
    assert gs.cast_spell(growth) is not False
    assert gs.life == 18, gs.life


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_mana_costs: OK")
