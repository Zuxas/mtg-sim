"""Smoke-test: do counterspells actually fire reactively?

Runs N matches Dimir Jermey (Snare/Phantom/Negate) vs Izzet Spellementals
(cheap noncreature spells = many counter-window opportunities). Captures
both players' log lines and counts three discriminating signals:

  (1) "[reactive] cast X -> counter Y"   resolver fired
  (2) "[COUNTERED]"                       spell was nullified
  (3) "(reactive only)"                   handler fired on holder's own turn
                                          (proactive cast = APL bug)

Pattern decode (per advisor):
  (1)+(2) present, (3) absent  -> resolver works; yesterday's memo stale
  (3) present, (1) absent      -> APLs are casting counters proactively
  none present                 -> integration not reaching try_counter_spell
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.match_runner import run_match

N = 20
DECK_A = "decks/dimir_midrange_jermey_standard.txt"
DECK_B = "decks/izzet_spellementals_standard.txt"
KEY_A = "dimirmidrangejermey"
KEY_B = "izzetspellementals"


def _all_log_lines(result, mgs=None):
    """Pull log lines from any object that exposes _log_lines."""
    lines = []
    for attr in ("gs_a", "gs_b", "_gs_a", "_gs_b"):
        for src in (result, mgs):
            if src is None:
                continue
            obj = getattr(src, attr, None)
            if obj is not None:
                lines.extend(getattr(obj, "_log_lines", []) or [])
    return lines


def main():
    apl_a = get_match_apl(KEY_A)
    apl_b = get_match_apl(KEY_B)
    deck_a, _ = load_deck_from_file(DECK_A)
    deck_b, _ = load_deck_from_file(deck_path := DECK_B)

    counts = {
        "reactive_cast": 0,    # signal (1)
        "countered":     0,    # signal (2)
        "reactive_only": 0,    # signal (3) -- handler fired in main phase
        "match_end_turn": 0,
    }
    sample_lines = {"reactive_cast": [], "countered": [], "reactive_only": []}
    matches_with_signal = {"reactive_cast": 0, "countered": 0, "reactive_only": 0}

    pat_reactive = re.compile(r"\[reactive\] cast .+ -> counter")
    pat_countered = re.compile(r"\[COUNTERED\]")
    pat_reactive_only = re.compile(r"\(reactive only\)|\(reactive\)|\(no target on own turn\)")

    for s in range(N):
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=(s % 2 == 0))
        except Exception as e:
            print(f"  seed={s} FAILED: {type(e).__name__}: {e}")
            continue

        # MatchResult exposes mgs via attribute? Let's just try both.
        mgs = getattr(r, "mgs", None) or getattr(r, "_mgs", None)
        lines = _all_log_lines(r, mgs)
        counts["match_end_turn"] += getattr(r, "kill_turn", 0) or 0

        seen_in_match = {"reactive_cast": False, "countered": False, "reactive_only": False}
        for ln in lines:
            if pat_reactive.search(ln):
                counts["reactive_cast"] += 1
                seen_in_match["reactive_cast"] = True
                if len(sample_lines["reactive_cast"]) < 3:
                    sample_lines["reactive_cast"].append(ln.strip())
            if pat_countered.search(ln):
                counts["countered"] += 1
                seen_in_match["countered"] = True
                if len(sample_lines["countered"]) < 3:
                    sample_lines["countered"].append(ln.strip())
            if pat_reactive_only.search(ln):
                counts["reactive_only"] += 1
                seen_in_match["reactive_only"] = True
                if len(sample_lines["reactive_only"]) < 3:
                    sample_lines["reactive_only"].append(ln.strip())
        for k, v in seen_in_match.items():
            if v:
                matches_with_signal[k] += 1

    print(f"\nN={N} matches: {DECK_A.split('/')[-1]} vs {DECK_B.split('/')[-1]}")
    print(f"Avg kill turn: {counts['match_end_turn']/max(N,1):.1f}")
    print()
    print("Signal counts (total events / matches with >=1):")
    print(f"  (1) [reactive] cast ... -> counter:  {counts['reactive_cast']:>4}  /  {matches_with_signal['reactive_cast']}/{N} matches")
    print(f"  (2) [COUNTERED]:                     {counts['countered']:>4}  /  {matches_with_signal['countered']}/{N} matches")
    print(f"  (3) handler '(reactive only)':       {counts['reactive_only']:>4}  /  {matches_with_signal['reactive_only']}/{N} matches")
    print()
    for k, samples in sample_lines.items():
        if samples:
            print(f"Sample lines [{k}]:")
            for s in samples:
                print(f"   | {s}")
            print()


if __name__ == "__main__":
    main()
