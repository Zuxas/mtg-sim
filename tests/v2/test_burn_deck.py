"""The real Modern Burn list (decks/mono_red_aggro_modern.txt main deck) through engine v2:
every card supported, any unsupported card refused, complete scripted games with invariants
on and exact replay."""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2.cards import SUPPORTED, UnsupportedCardError
from engine.v2.decklists import main_deck
from engine.v2.game import Game
from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy
from engine.v2.record import make_record, replay

BURN = "mono_red_aggro_modern"


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


def test_the_exact_burn_main_deck_is_fully_supported():
    deck = main_deck(BURN)
    assert len(deck) == 60
    c = collections.Counter(deck)
    assert c["Mountain"] == 3 and c["Arid Mesa"] == 4 and c["Lightning Helix"] == 2 and c["Skullcrack"] == 2
    assert set(deck) <= set(SUPPORTED) and len(set(deck)) == 18


def test_one_unsupported_card_refuses_the_game():
    deck = main_deck(BURN)
    for swap in ("Chalice of the Void", "Exquisite Firecraft", "Wear // Tear"):
        assert _raises(Exception, lambda: Game.new(deck[:-1] + [swap], deck, 0))
    assert _raises(UnsupportedCardError, lambda: Game.new(deck[:-1] + ["Chalice of the Void"], deck, 0))


def test_scripted_complete_burn_mirror_games():
    deck = main_deck(BURN)
    for seed in range(6):
        g = Game.new(deck, deck, 777 + seed, starting_player=seed % 2, check_invariants=True)
        g.run([SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)])
        assert g.result is not None and g.result[0] in ("win", "draw")
        kinds = collections.Counter(e.kind for t in g.s.log.transitions for e in t.events)
        assert kinds["SpellCast"] > 0 and kinds["LifeChanged"] > 0
        replay(make_record(g))


def test_random_and_mixed_burn_mirror_games_replay_exactly():
    deck = main_deck(BURN)
    for seed in range(10):
        pols = [RandomLegalPolicy(seed), SimpleAggroPolicy(seed + 1)] if seed % 2 else \
            [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)]
        g = Game.new(deck, deck, 900 + seed, starting_player=seed % 2, check_invariants=True)
        g.run(pols)
        replay(make_record(g))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("BURN DECK TESTS PASS")
