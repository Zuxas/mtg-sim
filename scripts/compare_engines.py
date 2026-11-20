"""
scripts/compare_engines.py -- play the same seeded games on both match engines
and report where they disagree (#62, migration step 2).

For every pair in the Standard field, each game is played once on
engine.match_runner and once on engine.match_engine with the same seed,
decks and play/draw flag. Output is a CSV plus an ASCII table sorted by the
size of the win-rate gap. Agreement between engines is NOT proof that either
is rules-correct; a gap only says where to look.

Usage:
    python scripts/compare_engines.py [--games N] [--seed S] [--decks k1,k2,...]
                                      [--out data/engine_comparison.csv]
"""
import argparse, csv, itertools, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.match_runner import _run_single_match
from scripts.full_field_gauntlet import STANDARD_DECKS, _get_deck_file

ENGINES = ("runner", "core")
FIELDS = ["deck_a", "deck_b", "games"] + [
    f"{e}_{k}" for e in ENGINES
    for k in ("wr", "play_wr", "draw_wr", "ties", "avg_turn", "max_turn", "crashes")
] + ["wr_gap", "gap_ci95", "same_winner_pct", "adapted", "post_combat_hook",
     "first_crash"]

# Hooks the runner calls after combat that the core never calls. A deck that
# overrides one (BaseAPL's is a no-op) plays a different game on each engine
# before any rule differs.
POST_COMBAT_HOOKS = ("main_phase2_match", "main_phase2")


def _load(key):
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    path = _get_deck_file(key)
    if not path:
        return None
    main, _ = load_deck_from_file(path)
    return type(get_match_apl(key)), main


def _pct(num, den):
    return round(100.0 * num / den, 1) if den else ""


def compare_pair(a, b, n, seed):
    """Play n seeded games of a vs b on each engine. Returns one CSV row."""
    (cls_a, deck_a), (cls_b, deck_b) = a[1], b[1]
    rng = random.Random(seed)
    seeds = [rng.randint(0, 999999) for _ in range(n)]
    row = {"deck_a": a[0], "deck_b": b[0], "games": n, "first_crash": ""}
    winners = {}
    for eng in ENGINES:
        won, turns, ties, crashes = [], [], 0, 0
        for i, s in enumerate(seeds):
            try:
                m = _run_single_match((s, cls_a, cls_b, deck_a, deck_b,
                                       i % 2 == 0, False, eng))
            except Exception as exc:  # a crash is a finding, not a stop
                crashes += 1
                won.append(None)
                row["first_crash"] = row["first_crash"] or \
                    f"{eng} seed {s}: {type(exc).__name__}: {exc}"[:200]
                continue
            won.append(bool(m.won))
            turns.append(m.turn_count or m.kill_turn)
            ties += bool(m.tie)
        played = [w for w in won if w is not None]
        play = [w for i, w in enumerate(won) if w is not None and i % 2 == 0]
        draw = [w for i, w in enumerate(won) if w is not None and i % 2 == 1]
        row.update({
            f"{eng}_wr": _pct(sum(played), len(played)),
            f"{eng}_play_wr": _pct(sum(play), len(play)),
            f"{eng}_draw_wr": _pct(sum(draw), len(draw)),
            f"{eng}_ties": ties,
            f"{eng}_avg_turn": round(sum(turns) / len(turns), 2) if turns else "",
            f"{eng}_max_turn": max(turns) if turns else "",
            f"{eng}_crashes": crashes,
        })
        winners[eng] = won
    both = [(r, c) for r, c in zip(winners["runner"], winners["core"])
            if r is not None and c is not None]
    row["same_winner_pct"] = _pct(sum(r == c for r, c in both), len(both))
    row["wr_gap"] = (round(row["core_wr"] - row["runner_wr"], 1)
                     if "" not in (row["core_wr"], row["runner_wr"]) else "")
    # Paired interval: the same seeds are played on both engines, so only the
    # games whose winner flipped carry information about the gap.
    if both:
        d = [c - r for r, c in both]
        mean = sum(d) / len(d)
        var = sum((x - mean) ** 2 for x in d) / max(len(d) - 1, 1)
        row["gap_ci95"] = round(196.0 * (var / len(d)) ** 0.5, 1)
    from apl.match_apl import MatchAPL
    row["adapted"] = "/".join(k for k, (cls, _) in (a, b)
                              if not issubclass(cls, MatchAPL))
    row["post_combat_hook"] = "/".join(
        k for k, (cls, _) in (a, b)
        if any(getattr(getattr(cls, h, None), "__qualname__", "BaseAPL.")
               .split(".")[0] != "BaseAPL" for h in POST_COMBAT_HOOKS))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--decks", default="", help="comma-separated registry keys")
    ap.add_argument("--out", default="data/engine_comparison.csv")
    args = ap.parse_args()

    keys = [k for k in args.decks.split(",") if k] or list(STANDARD_DECKS.values())
    loaded = []
    for k in keys:
        pair = _load(k)
        if pair is None:
            print(f"[skip] {k}: no deck file")
        else:
            loaded.append((k, pair))

    rows = []
    for a, b in itertools.combinations(loaded, 2):
        rows.append(compare_pair(a, b, args.games, args.seed))
        r = rows[-1]
        print(f"{r['deck_a']:<24} vs {r['deck_b']:<24} runner {r['runner_wr']:>5}"
              f"  core {r['core_wr']:>5}  gap {r['wr_gap']:>6}"
              f"  same-winner {r['same_winner_pct']:>5}%"
              f"  crashes {r['runner_crashes']}/{r['core_crashes']}"
              f"{'  post-combat hook: ' + r['post_combat_hook'] if r['post_combat_hook'] else ''}",
              flush=True)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    gaps = sorted((r for r in rows if r["wr_gap"] != ""),
                  key=lambda r: -abs(r["wr_gap"]))
    print(f"\nLargest gaps (core minus runner), {args.games} games per pair:")
    for r in gaps[:15]:
        print(f"  {r['wr_gap']:>+6.1f} +/-{r['gap_ci95']:<5} {r['deck_a']} vs {r['deck_b']}")
    crashed = [r for r in rows if r["runner_crashes"] or r["core_crashes"]]
    print(f"\n{len(rows)} pairs, {len(crashed)} with crashes. Wrote {args.out}")
    for r in crashed[:10]:
        print(f"  {r['deck_a']} vs {r['deck_b']}: {r['first_crash']}")


if __name__ == "__main__":
    main()
