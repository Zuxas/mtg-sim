"""Best-of-three matches: play/draw choice (CR 103.1), staged sideboarding (CR 100.4, 100.4a,
100.2a), match end, and exact match-level replay."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2.cards import UnsupportedCardError
from engine.v2.decklists import main_deck
from engine.v2.match import (ChoosePlayDraw, DoneSideboarding, Match, MatchError, MatchReplayMismatch,
                             SideboardSwap, make_match_record, replay_match)
from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy

_DECK = []


def _burn():
    """The Burn list, loaded lazily (not at collection time: loading card data during pytest
    collection changes the timing of unrelated tests)."""
    if not _DECK:
        _DECK.extend(main_deck("mono_red_aggro_modern"))
    return list(_DECK)


SIDE = ["Lightning Helix", "Lightning Helix", "Skullcrack", "Skullcrack"]     # supported, 4-of rule holds


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


class _MatchRandom:
    """Seeded random match decisions (play/draw, at most 3 swaps per sideboarding window)."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.swaps = 0

    def choose_match(self, obs, acts):
        if isinstance(acts[0], ChoosePlayDraw):
            self.swaps = 0
            return self.rng.choice(acts)
        swaps = [a for a in acts if isinstance(a, SideboardSwap)]
        if swaps and self.swaps < 3 and self.rng.random() < 0.6:
            self.swaps += 1
            return self.rng.choice(swaps)
        self.swaps = 0
        return next(a for a in acts if isinstance(a, DoneSideboarding))


def test_75_card_rules_and_support_are_enforced_before_the_match():   # CR 100.2a, 100.4a
    assert _raises(MatchError, lambda: Match(_burn()[:59], [], _burn(), [], 1))
    assert _raises(MatchError, lambda: Match(_burn(), ["Mountain"] * 16, _burn(), [], 1))
    assert _raises(MatchError, lambda: Match(_burn(), ["Skullcrack"] * 3, _burn(), [], 1))       # 2 + 3 > 4
    assert _raises(UnsupportedCardError, lambda: Match(_burn(), ["Chalice of the Void"], _burn(), [], 1))
    Match(_burn(), SIDE, _burn(), SIDE, 1)


def test_game_one_chooser_and_play_draw():                               # CR 103.1
    m = Match(_burn(), SIDE, _burn(), SIDE, 5)
    kind, p = m.pending
    assert kind == "play_draw" and set(m.legal_actions()) == {ChoosePlayDraw(p, True), ChoosePlayDraw(p, False)}
    m.apply(ChoosePlayDraw(p, False))                                     # chooses to draw
    assert m.current.s.starting_player == 1 - p


def test_loser_chooses_next_and_draw_keeps_previous_chooser():          # CR 103.1
    m = Match(_burn(), SIDE, _burn(), SIDE, 9, turn_limit=50)
    first = m.pending[1]
    m.apply(ChoosePlayDraw(first, True))
    m.current.run([SimpleAggroPolicy(1), SimpleAggroPolicy(2)])
    m.finish_game()
    if m.result is None:
        loser = 1 - m.games[0].result[1] if m.games[0].result[0] == "win" else first
        while m.pending[0] == "sideboard":
            m.apply(DoneSideboarding(m.pending[1]))
        assert m.pending == ("play_draw", loser)
    # a drawn game keeps the previous chooser
    m2 = Match(_burn(), SIDE, _burn(), SIDE, 11, turn_limit=1)                  # 1-turn games end in draws
    c = m2.pending[1]
    m2.apply(ChoosePlayDraw(c, True))
    m2.current.run([SimpleAggroPolicy(1), SimpleAggroPolicy(2)])
    m2.finish_game()
    assert m2.games[0].result == ("draw", "turn_limit")
    while m2.pending[0] == "sideboard":
        m2.apply(DoneSideboarding(m2.pending[1]))
    assert m2.pending == ("play_draw", c)


def test_sideboard_swaps_are_staged_and_used_by_the_next_game():       # CR 100.4
    m = Match(_burn(), SIDE, _burn(), SIDE, 13)
    m.apply(ChoosePlayDraw(m.pending[1], True))
    m.current.run([SimpleAggroPolicy(1), SimpleAggroPolicy(2)])
    m.finish_game()
    if m.result is not None:
        return
    assert m.pending == ("sideboard", 0)
    m.apply(SideboardSwap(0, "Goblin Guide", "Skullcrack"))
    assert m.main[0].count("Skullcrack") == 3 and m.main[0].count("Goblin Guide") == 3
    assert len(m.main[0]) == 60 and len(m.side[0]) == 4 and "Goblin Guide" in m.side[0]
    assert not any(isinstance(a, SideboardSwap) and a.in_name == "Chalice of the Void" for a in m.legal_actions())
    m.apply(DoneSideboarding(0))
    assert m.pending == ("sideboard", 1)
    m.apply(DoneSideboarding(1))
    m.apply(ChoosePlayDraw(m.pending[1], True))
    deck0 = [i.name for i in m.current.s.instances.values() if i.owner == 0]
    assert deck0.count("Skullcrack") == 3 and deck0.count("Goblin Guide") == 3


def test_complete_matches_end_at_two_wins_and_replay_exactly():
    for seed in range(6):
        m = Match(_burn(), SIDE, _burn(), SIDE, 100 + seed, check_invariants=True)
        pols = [SimpleAggroPolicy(seed), RandomLegalPolicy(seed + 1)] if seed % 2 else \
            [SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)]
        mp = [_MatchRandom(seed), _MatchRandom(seed + 50)]
        res = m.run(pols, mp)
        assert res[0] in ("win", "draw") and 2 <= len(m.games) <= 5
        if res[0] == "win":
            assert m.wins[res[1]] == 2
        rec = make_match_record(m)
        import json
        replay_match(json.loads(json.dumps(rec)))


def test_match_policies_get_a_frozen_observation_without_the_opponents_75():
    import dataclasses
    from engine.v2.match import MatchObservation
    seen = []

    class Spy(_MatchRandom):
        def choose_match(self, obs, acts):
            seen.append(obs)
            return super().choose_match(obs, acts)
    m = Match(_burn(), SIDE, _burn(), SIDE, 21)
    m.run([SimpleAggroPolicy(1), SimpleAggroPolicy(2)], [Spy(1), Spy(2)])
    assert seen and all(isinstance(o, MatchObservation) for o in seen)
    o = seen[-1]
    assert _raises(dataclasses.FrozenInstanceError, lambda: setattr(o, "wins", (9, 9)))
    assert isinstance(o.my_main, tuple) and isinstance(o.my_side, tuple)
    assert not any(isinstance(v, (Match, list, dict)) for v in vars(o).values())


def test_tampered_match_record_is_rejected():
    m = Match(_burn(), SIDE, _burn(), SIDE, 77)
    m.run([SimpleAggroPolicy(1), SimpleAggroPolicy(2)], [_MatchRandom(1), _MatchRandom(2)])
    rec = make_match_record(m)
    bad = dict(rec, match_hash="0" * 64)
    assert _raises(MatchReplayMismatch, lambda: replay_match(bad))
    bad2 = dict(rec, games=[dict(rec["games"][0], transition_hashes=["f" * 64])] + rec["games"][1:])
    assert _raises(MatchReplayMismatch, lambda: replay_match(bad2))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("MATCH TESTS PASS")
