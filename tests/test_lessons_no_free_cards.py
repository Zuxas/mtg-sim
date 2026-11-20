"""
test_lessons_no_free_cards.py -- Izzet Lessons only has the cards in its
deck, and counts Lessons by card type.

The match APL had a "learn" step that created a new card in hand about once
a turn (4.2 per game on the runner, 6.4 on the core). No card in the deck
has learn. This test plays seeded games on both engines and checks that
every card the deck ever holds came from its 60-card list, and that the
Lesson count behind Combustion Technique uses the Lesson card type.
"""
from __future__ import annotations
import collections, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import izzet_lesson_standard_match as mod
from data.card import Card
from engine.card_db import CardDB
from engine.match_runner import _run_single_match
from scripts.compare_engines import _load

GAMES = 20


def main():
    lessons, momo = _load("izzetlesson"), _load("azoriusmomo")
    db = CardDB()
    for name in sorted({c.name for c in lessons[1]}):
        text = (db.get(name) or {}).get("oracle_text") or ""
        assert not re.search(r"\blearn\b", text, re.I), f"{name} has learn"
    assert not hasattr(mod.IzzetLessonStandardMatchAPL, "_learn")
    print("PASS: no card in the deck has learn, and the APL has no learn step")

    limit = collections.Counter(c.name for c in lessons[1])
    cls = lessons[0]
    seen = {"max": collections.Counter()}
    orig = cls.main_phase_match

    def spy(self, gs, opp):
        out = orig(self, gs, opp)
        z = gs.zones
        have = collections.Counter(
            c.name for zone in (z.hand, z.battlefield, z.graveyard, z.library,
                                getattr(z, "exile", []))
            for c in zone if not getattr(c, "is_token", False))
        for n, k in have.items():
            seen["max"][n] = max(seen["max"][n], k)
        return out

    cls.main_phase_match = spy
    rng = random.Random(42)
    for eng in ("runner", "core"):
        for i in range(GAMES):
            _run_single_match((rng.randint(0, 999999), lessons[0], momo[0],
                               lessons[1], momo[1], i % 2 == 0, False, eng))
    extra = {n: (k, limit[n]) for n, k in seen["max"].items() if k > limit[n]
             and db.get(n) and "Token" not in (db.get(n).get("type_line") or "")}
    assert not extra, f"more copies than the deck list holds (seen, listed): {extra}"
    print(f"PASS: never more copies of a card than the deck list, {2 * GAMES} games")

    def card(name):
        d = db.get(name)
        return Card(name=name, mana_cost=d["mana_cost"], cmc=d["cmc"],
                    type_line=d["type_line"])

    gy = [card(n) for n in ("Accumulate Wisdom", "It'll Quench Ya!",
                            "Combustion Technique", "Flashfreeze", "Negate",
                            "Spell Snare")]
    gs = type("GS", (), {"zones": type("Z", (), {"graveyard": gy})()})()
    assert mod._lessons_in_gy(gs) == 3, mod._lessons_in_gy(gs)
    assert mod._combustion_max_tgh(gs) == 5
    print("PASS: Lessons in the graveyard are counted by card type")


if __name__ == "__main__":
    main()
