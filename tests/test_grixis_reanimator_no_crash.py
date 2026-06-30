"""
tests/test_grixis_reanimator_no_crash.py

Regression test for the Grixis Reanimator match-APL crash
(harness/IMPERFECTIONS.md: grixis-reanimator-match-apl-crashes-every-turn).

Root cause: the engine's verified Persist handler (SPELL_EFFECTS['Persist'] ->
_persist_spell) already reanimates the max-cmc nonlegendary creature from the
graveyard during gs.cast_spell(). The APL then re-removed the SAME card with a
value-based gs.zones.graveyard.remove(tgt), raising
"list.remove(x): x not in list" on nearly every Persist. That exception was
swallowed by _simple_play_turn's except-and-fallback, aborting Grixis's whole
turn (so its T2-T4 reanimator combo never finished executing).

The fix lets the engine own the GY->BF move and only fires the reanimated
creature's ETB (identity-guarded). This test asserts a full lowcurve-vs-Grixis
game runs WITHOUT the GrixisReanimatorMatchAPL raising -- by setting SIM_DEBUG=1
so any APL-side exception PROPAGATES (instead of being printed as a [WARN ...]
line and swallowed). Run: python tests/test_grixis_reanimator_no_crash.py
"""
import sys, os, random

# SIM_DEBUG must be set BEFORE engine import paths read it: it makes
# _simple_play_turn / _run_post_combat_phase re-raise APL exceptions instead of
# swallowing them, so the crash (if it regressed) surfaces as a hard failure.
os.environ["SIM_DEBUG"] = "1"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.match_runner import run_match

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Low Curve Boros Energy is our deck; fall back to the base Boros list if the
# lowcurve file is absent in this checkout (the crash is opponent-side / deck
# independent, so either of our decks exercises it).
OUR_DECK = os.path.join(REPO, "decks", "boros_energy_lowcurve_modern.txt")
if not os.path.exists(OUR_DECK):
    OUR_DECK = os.path.join(REPO, "decks", "boros_energy_modern.txt")
GRIXIS_DECK = os.path.join(REPO, "decks", "grixis_reanimator_modern.txt")


def main():
    deck_a, _ = load_deck_from_file(OUR_DECK)
    deck_b, _ = load_deck_from_file(GRIXIS_DECK)
    apl_a = get_match_apl("borosenergy")
    apl_b = get_match_apl("grixisreanimator")

    random.seed(12345)
    n = 50
    crashes = 0
    for i in range(n):
        try:
            run_match(apl_a, deck_a, apl_b, deck_b, seed=42 + i,
                      on_play=(i % 2 == 0))
        except Exception as e:  # noqa: BLE001 -- any APL exception is a failure
            crashes += 1
            if "list.remove" in str(e):
                print(f"FAIL game {i}: Persist double-reanimation crash regressed: {e}")
            else:
                print(f"FAIL game {i}: GrixisReanimatorMatchAPL raised: {type(e).__name__}: {e}")

    if crashes:
        print(f"FAIL: {crashes}/{n} lowcurve-vs-Grixis games crashed (expected 0).")
        sys.exit(1)
    print(f"PASS: {n}/{n} lowcurve-vs-Grixis games ran with no APL exception "
          f"(SIM_DEBUG=1).")


if __name__ == "__main__":
    main()
