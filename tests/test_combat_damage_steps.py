"""test_combat_damage_steps.py -- issue #13.

Table-driven combat cases run against BOTH resolvers:
  engine.match_state.resolve_combat   (match_engine / Bo3 path)
  engine.match_runner._resolve_combat (run_match_set path)

Each row: attacker (power, toughness, keywords), blockers, and the expected
(face damage, attacker lifelink gain, defender lifelink gain, attacker dies,
which blockers die).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.match_state import resolve_combat, combat_damage
from engine.match_runner import TwoPlayerGameState, _resolve_combat

FS, DS, LL, TR, DT, IND = ("first_strike", "double_strike", "lifelink",
                           "trample", "deathtouch", "indestructible")


def _c(name, p, t, *kws):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature",
             oracle_text="", power=str(p), toughness=str(t), colors=[])
    c.tags = {Tag.CREATURE, *kws}
    c.summoning_sickness = False
    return c


#  name, attacker, blockers, face, atk_ll, def_ll, atk_dies, blockers_dead
CASES = [
    ("unblocked 3/3",                  (3, 3), [],               3, 0, 0, False, []),
    ("2/2 vs 2/2 trade",               (2, 2), [(2, 2)],         0, 0, 0, True,  [0]),
    ("2/2 first strike vs 2/2",        (2, 2, FS), [(2, 2)],     0, 0, 0, False, [0]),
    ("3/3 vs 3/3 first-strike blocker", (3, 3), [(3, 3, FS)],    0, 0, 0, True,  []),
    ("2/2 double strike vs 1/1",       (2, 2, DS), [(1, 1)],     0, 0, 0, False, [0]),
    ("2/2 double strike vs 3/3",       (2, 2, DS), [(3, 3)],     0, 0, 0, True,  [0]),
    ("2/2 double strike unblocked",    (2, 2, DS), [],           4, 0, 0, False, []),
    ("3/3 lifelink vs 1/1",            (3, 3, LL), [(1, 1)],     0, 3, 0, False, [0]),
    ("3/3 lifelink unblocked",         (3, 3, LL), [],           3, 3, 0, False, []),
    ("2/2 vs 1/3 lifelink blocker",    (2, 2), [(1, 3, LL)],     0, 0, 1, False, []),
    ("4/4 trample vs 2/2",             (4, 4, TR), [(2, 2)],     2, 0, 0, False, [0]),
    ("4/4 trample deathtouch vs 3/3",  (4, 4, TR, DT), [(3, 3)], 3, 0, 0, False, [0]),
    ("5/5 trample double strike vs 2/2", (5, 5, TR, DS), [(2, 2)], 8, 0, 0, False, [0]),
    ("1/1 deathtouch vs 5/5",          (1, 1, DT), [(5, 5)],     0, 0, 0, True,  [0]),
    ("3/3 vs indestructible 1/1",      (3, 3), [(1, 1, IND)],    0, 0, 0, False, []),
    ("first strike vs first strike",   (2, 2, FS), [(2, 2, FS)], 0, 0, 0, True,  [0]),
]


def _build(case):
    _, atk, blks, *_ = case
    a = _c("Attacker", *atk)
    bs = [_c(f"Blocker{i}", *b) for i, b in enumerate(blks)]
    return a, bs


def _check(label, case, got):
    name, _, _, face, all_, dll, adies, bdead = case
    want = (face, all_, dll, adies, sorted(bdead))
    assert got == want, f"[{label}] {name}: got {got}, want {want}"


def test_match_state_resolver():
    for case in CASES:
        a, bs = _build(case)
        r = resolve_combat([a], {id(a): bs} if bs else {}, 'a', None)
        got = (r.damage_to_defender, r.life_gained_attacker, r.life_gained_defender,
               a in r.attacker_deaths,
               sorted(i for i, b in enumerate(bs) if b in r.defender_deaths))
        _check("match_state", case, got)


def test_match_runner_resolver():
    for case in CASES:
        a, bs = _build(case)
        gs = TwoPlayerGameState([], [], on_play=True, seed=1)
        gs.turn = 5
        gs.bf_a, gs.bf_b = [a], list(bs)
        dmg, a_lost, b_lost, ll, dll, _hit = _resolve_combat(gs, "a")
        got = (dmg, ll, dll, a in a_lost,
               sorted(i for i, b in enumerate(bs) if b in b_lost))
        _check("match_runner", case, got)


def test_lethal_first_strike_step_stops_combat():
    """Defender at 2: a first striker deals 3 unblocked. The game is over
    before the regular step, so the double striker deals only its first hit
    and a lifelink blocker cannot gain the defender back to life."""
    fs = _c("First Striker", 3, 3, FS)
    ds = _c("Double Striker", 2, 2, DS)
    vanilla = _c("Bear", 2, 2)
    blk = _c("Lifelinker", 2, 4, LL)
    r = combat_damage([fs, ds, vanilla], {id(vanilla): [blk]}, defender_life=2)
    assert (r.face, r.defender_lifelink, r.hits_on_player) == (5, 0, 2), r
    # Same board with the defender healthy: both steps happen
    r = combat_damage([fs, ds, vanilla], {id(vanilla): [blk]}, defender_life=20)
    assert (r.face, r.defender_lifelink) == (7, 2), r


def test_lifelink_blocker_in_same_step_keeps_defender_alive():
    """Lifelink is simultaneous with damage inside one step."""
    atk = _c("Attacker", 3, 3)
    other = _c("Other", 2, 2)
    blk = _c("Lifelinker", 2, 4, LL)
    r = combat_damage([atk, other], {id(other): [blk]}, defender_life=2)
    assert 2 + r.defender_lifelink - r.face == 1, r


if __name__ == "__main__":
    test_lethal_first_strike_step_stops_combat()
    test_lifelink_blocker_in_same_step_keeps_defender_alive()
    test_match_state_resolver()
    test_match_runner_resolver()
    print(f"test_combat_damage_steps: OK ({len(CASES)} cases x 2 resolvers)")
