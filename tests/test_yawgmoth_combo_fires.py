"""
tests/test_yawgmoth_combo_fires.py

Spec: harness/specs/2026-06-30-modern-combo-interaction.md
  - Component 3 (yawgmoth cell): the deck is the Agatha's Soul Cauldron / Walking
    Ballista build (decks/yawgmoth_modern.txt). The old APL's DRAINS/UNDYING
    constants named cards the list does not run (Blood Artist / Zulaport /
    Geralf's Messenger), so the combo checker's `drain_on_board` was ALWAYS False
    and the combo fired 0/50.
  - Component 5 (yawgmoth gate): TWO STRUCTURAL ASSERTS that must PASS independent
    of the win-rate band: (1) combo-fires >= 1/50, (2) the combo damage actually
    reaches the match life total via the gs.damage_dealt + WANTS_BURN reroute (a
    scalar opponent.life write is dropped -- spec spine #3).
  - Component 6.3 + 6.5: no-crash (SIM_DEBUG=1) + combo-fires >= 1/50 in BOTH seat
    orientations (combo as seat B AND seat A).

Run: python tests/test_yawgmoth_combo_fires.py
"""
import sys, os, random

# Re-raise APL exceptions instead of swallowing them (must precede engine use).
os.environ["SIM_DEBUG"] = "1"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.game_state import GameState
from engine.match_runner import run_match_set
from apl.yawgmoth_match import YawgmothMatchAPL

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _deck(name):
    path = os.path.join(REPO, "decks", name)
    deck, _ = load_deck_from_file(path)
    return deck


class _FakeCard:
    """_check_combo_kill only reads card.name, so a name-only stand-in suffices."""
    def __init__(self, name):
        self.name = name


def test_reroute_unit():
    """FORCED BOARD: Yawgmoth + 2 undying + Cauldron + Ballista -> the combo fires
    and routes >= 20 into gs.damage_dealt (the channel WANTS_BURN propagates to
    match life). It must NOT do a scalar opponent.life write (that is dropped)."""
    apl = YawgmothMatchAPL()
    view = GameState(mainboard=[], on_play=True)
    view.zones.battlefield = [
        _FakeCard("Yawgmoth, Thran Physician"),
        _FakeCard("Young Wolf"),
        _FakeCard("Strangleroot Geist"),
        _FakeCard("Agatha's Soul Cauldron"),
        _FakeCard("Walking Ballista"),
    ]
    view.zones.graveyard = []
    opp = GameState(mainboard=[], on_play=False)
    opp.life = 20

    before_dd = view.damage_dealt
    apl._check_combo_kill(view, opp)

    assert apl._combo_fired, "combo did not fire on a fully-assembled board"
    dealt = view.damage_dealt - before_dd
    assert dealt >= 20, f"combo routed {dealt} into damage_dealt, expected >= 20 (lethal)"
    assert opp.life == 20, "combo must route via damage_dealt, NOT a scalar opp.life write"
    print(f"PASS test_reroute_unit: combo routed {dealt} via gs.damage_dealt, opp.life untouched")


def test_assembly_requires_all_pieces():
    """Negative cases: the combo must NOT fire when any piece is missing (proves
    it is a real 4-piece assembly check, not a trivially-true firing)."""
    base = ["Yawgmoth, Thran Physician", "Young Wolf", "Strangleroot Geist",
            "Agatha's Soul Cauldron", "Walking Ballista"]
    drops = {
        "no Yawgmoth": "Yawgmoth, Thran Physician",
        "one undying": "Strangleroot Geist",
        "no Cauldron": "Agatha's Soul Cauldron",
        "no Ballista": "Walking Ballista",
    }
    for label, missing in drops.items():
        apl = YawgmothMatchAPL()
        view = GameState(mainboard=[], on_play=True)
        view.zones.battlefield = [_FakeCard(n) for n in base if n != missing]
        view.zones.graveyard = []
        opp = GameState(mainboard=[], on_play=False)
        opp.life = 20
        apl._check_combo_kill(view, opp)
        assert not apl._combo_fired, f"combo wrongly fired with {label}"
        assert view.damage_dealt == 0, f"damage leaked with {label}"
    print(f"PASS test_assembly_requires_all_pieces: {len(drops)} missing-piece cases all no-fire")


def _combo_fires_over_set(a_key, b_key, a_deck, b_deck, n=50):
    a_apl, b_apl = get_match_apl(a_key), get_match_apl(b_key)
    YawgmothMatchAPL._combo_fires = 0
    res = run_match_set(a_apl, a_deck, b_apl, b_deck,
                        n=n, seed=42, mix_play_draw=True, n_workers=1)
    return YawgmothMatchAPL._combo_fires, res


def test_combo_fires_seat_b():
    """Component 6.3: boros (seat A) vs yawgmoth (seat B). 0 crashes (SIM_DEBUG=1)
    + combo-fires >= 1/50 (the structural assert)."""
    fires, res = _combo_fires_over_set(
        "borosenergylowcurve", "yawgmoth",
        _deck("boros_energy_lowcurve_modern.txt"), _deck("yawgmoth_modern.txt"))
    assert fires >= 1, f"seat-B combo fired {fires}/50 (expected >= 1)"
    print(f"PASS test_combo_fires_seat_b: combo fired {fires}/50, our_a_wins={res.a_wins}")


def test_combo_fires_seat_a():
    """Component 6.5: yawgmoth AS SEAT A vs a field deck. A zone-move/identity bug
    that only manifests when the combo pilots seat A is invisible to the seat-B
    test. 0 crashes (SIM_DEBUG=1) + combo-fires >= 1/50."""
    fires, res = _combo_fires_over_set(
        "yawgmoth", "uwcontrol",
        _deck("yawgmoth_modern.txt"), _deck("uw_control_modern.txt"))
    assert fires >= 1, f"seat-A combo fired {fires}/50 (expected >= 1)"
    print(f"PASS test_combo_fires_seat_a: combo fired {fires}/50, yawg_a_wins={res.a_wins}")


def main():
    test_reroute_unit()
    test_assembly_requires_all_pieces()
    test_combo_fires_seat_b()
    test_combo_fires_seat_a()
    print("ALL PASS: tests/test_yawgmoth_combo_fires.py")


if __name__ == "__main__":
    main()
