"""Whole-game invariants on seeded matchups, in both engines:

  1. no game raises;
  2. a permanent on the battlefield is never also in another zone (checked at
     every main phase, for both players);
  3. the same seed replays the same game.

These are properties of the simulator as a whole, not of one fix.

Run: python tests/test_integration_invariants.py
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import MATCH_APL_REGISTRY
from data.deck import load_deck_from_file
from engine import match_engine, match_runner

DECKS = {
    "borosenergy": "boros_energy_modern",
    "izzetprowess": "izzet_prowess_modern",
    "domainzoo": "domain_zoo_modern",
    "jeskaiblink": "jeskai_blink_modern",
    "dimirmurktide": "dimir_murktide_modern",
    "esperblink": "esper_blink_modern",
    "yawgmoth": "yawgmoth_modern",
}
PAIRS = [("borosenergy", "izzetprowess"), ("domainzoo", "jeskaiblink"),
         ("dimirmurktide", "borosenergy"), ("esperblink", "esperblink"),
         ("yawgmoth", "izzetprowess")]
SEEDS = range(12)
ZONES = ("hand", "battlefield", "graveyard", "exile", "library")


def _apl_class(key):
    module, name = MATCH_APL_REGISTRY[key]
    return getattr(importlib.import_module(module), name)


def _duplicates(gs):
    """Permanents that are also in another zone, or on the battlefield twice.

    Not checked: the same object in two NON-battlefield zones. Card is a
    dataclass, so `hand.remove(card)` removes the first card that is EQUAL,
    which can be a different copy of the same card; the counts stay right but
    the object identities cross. That is harmless for cards with no state and
    is a known wart, so this test only guards the case that corrupts play:
    a permanent whose tapped/counters state is shared with a card elsewhere.
    """
    on_board, dupes = {}, []
    for card in gs.zones.battlefield:
        if id(card) in on_board:
            dupes.append((card.name, "battlefield", "battlefield"))
        on_board[id(card)] = True
    for zone in ZONES:
        if zone == "battlefield":
            continue
        for card in getattr(gs.zones, zone):
            if id(card) in on_board:
                dupes.append((card.name, "battlefield", zone))
    return dupes


def _watched(cls, problems):
    class Watched(cls):
        def main_phase_match(self, gs, opponent):
            for side in (gs, opponent):
                for dupe in _duplicates(side):
                    problems.append(dupe)
            return super().main_phase_match(gs, opponent)
    Watched.__name__ = cls.__name__
    return Watched


def _fingerprint(result):
    winner = getattr(result, "winner", None) or result.won
    return winner, result.kill_turn


def test_seeded_games_finish_keep_cards_in_one_zone_and_replay():
    decks = {k: load_deck_from_file(f"decks/{f}.txt")[0] for k, f in DECKS.items()}
    games = 0
    for engine in (match_engine, match_runner):
        for a, b in PAIRS:
            problems = []
            cls_a, cls_b = _watched(_apl_class(a), problems), _watched(_apl_class(b), problems)
            for seed in SEEDS:
                first = engine.run_match(cls_a(), decks[a], cls_b(), decks[b],
                                         seed=seed, on_play=seed % 2 == 0)
                again = engine.run_match(cls_a(), decks[a], cls_b(), decks[b],
                                         seed=seed, on_play=seed % 2 == 0)
                assert _fingerprint(first) == _fingerprint(again), (
                    f"{engine.__name__} {a} vs {b} seed {seed} did not replay")
                games += 1
            assert not problems, (
                f"{engine.__name__} {a} vs {b}: permanent also elsewhere: {problems[:3]}")
    assert games == 2 * len(PAIRS) * len(SEEDS)


if __name__ == "__main__":
    test_seeded_games_finish_keep_cards_in_one_zone_and_replay()
    print("test_integration_invariants: OK")
