"""
mulligan_sweep.py -- Track A: goldfish mulligan-threshold parameter sweep.

Varies the keep thresholds (min_lands, min_keep_cards, max_mulligans) for an
archetype and measures the resulting GOLDFISH metrics (kill turn, goldfish
win rate, mulligan rate) across a grid of combinations -- mirroring the
Affinity COUNTER_COST env-var sweep pattern, but for the mulligan knob.

SCOPE: Track A ONLY (per harness/specs/2026-06-28-mulligan-sweep-impl-plan.md).
  - This is a CHEAP CALIBRATION / PRE-FILTER, not a win-rate measurement.
    Goldfish has no opponent, so its "win rate" means "reached lethal within
    max_turns", NOT match win rate. Columns are labeled honestly. The true WR
    sweep (Track B) is BLOCKED on an engine prerequisite (Gotcha G1) and is
    intentionally NOT implemented here.
  - This script is purely ADDITIVE. It overrides the APL keep on a throwaway
    instance and monkeypatches apl.base_apl.take_opening_hand for the duration
    of each cell, then restores it. It writes NO on-disk APL or deck file.

How the swept variables reach the goldfish code path:
  * min_lands / min_keep_cards: injected by replacing the APL instance's
    `keep` attribute with a parametric closure. base_apl.run_game reads
    `self.keep` when no opponent archetype is set (the goldfish case), so the
    instance override takes effect.
  * max_mulligans: base_apl.run_game calls take_opening_hand WITHOUT passing
    max_mulligans (it is pinned to the function default 4), so we monkeypatch
    the module global apl.base_apl.take_opening_hand with a functools.partial
    that binds max_mulligans for the cell, then restore it.

Card roles are derived from the Card API (c.is_land(), c.has(Tag.CREATURE)),
NOT from fragile per-APL name constants (Gotcha G5). The "keepable non-land"
role defaults to creatures but can be overridden with --key-tag for
ramp/combo decks where the payoff is not a creature.

CONVENTIONS (mtg-sim/CONVENTIONS.md): ASCII-only terminal output; run with
PYTHONIOENCODING=utf-8; sys.path set from repo root; exit 0 on success, 1 on
error.

Usage:
    PYTHONIOENCODING=utf-8 python scripts/mulligan_sweep.py --deck borosenergy --n 200
    python scripts/mulligan_sweep.py --deck borosenergy --n 2000 --seed 42 --csv out.csv
    python scripts/mulligan_sweep.py --deck-file decks/amulet_titan_modern.txt \\
        --apl amulettitan --key-tag ramp --min-lands 2,3,4

Gate 1 (calibration): run Boros Energy first. A (2,1,2)-style aggro threshold
should land near the top of the ranking; if it is demonstrably bad, the harness
has a bug. "All rows within noise" is an expected, reportable outcome at small
N, not a pass.
"""

import os
import sys
import argparse
import functools

# --- sys.path from repo root (Gotcha G9; mirrors scripts/ convention) ---
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SIM_ROOT not in sys.path:
    sys.path.insert(0, SIM_ROOT)

from data.card import Tag
from data.deck import load_deck_from_file
from engine.runner import run_simulation
from apl import get_apl, get_apl_entry
import apl.base_apl as base_apl


# Friendly --key-tag aliases -> Tag constant strings.
_KEY_TAG_ALIASES = {
    "creature":     Tag.CREATURE,
    "ramp":         Tag.RAMP,
    "threat":       Tag.THREAT,
    "combo":        Tag.COMBO_PIECE,
    "combo_piece":  Tag.COMBO_PIECE,
    "artifact":     Tag.ARTIFACT,
    "removal":      Tag.REMOVAL,
    "one_drop":     Tag.ONE_DROP,
    "two_drop":     Tag.TWO_DROP,
    "three_drop":   Tag.THREE_DROP,
}


def make_keep(min_lands, min_keep_cards, key_tag):
    """Build a parametric goldfish keep() closure (Gotcha G5: type-derived).

    Keeps any hand of 4 or fewer cards (already mulliganed deep -- you take
    what you get), otherwise requires at least `min_lands` lands AND at least
    `min_keep_cards` non-land cards carrying `key_tag`.
    """
    def keep(hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        keepers = sum(1 for c in hand
                      if not c.is_land() and c.has(key_tag))
        return lands >= min_lands and keepers >= min_keep_cards
    return keep


def parse_int_list(s):
    """Parse a comma-separated list of ints, e.g. '1,2,3'."""
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if tok:
            out.append(int(tok))
    return out


def resolve_key_tag(name):
    if name in _KEY_TAG_ALIASES:
        return _KEY_TAG_ALIASES[name]
    # Allow passing a raw tag string directly.
    return name


def resolve_deck_file(deck_key, deck_file_arg):
    """Resolve a deck file path from an explicit arg or the APL registry entry."""
    if deck_file_arg:
        path = deck_file_arg
        if not os.path.isabs(path):
            path = os.path.join(SIM_ROOT, path)
        return path
    entry = get_apl_entry(deck_key)
    if not entry:
        return None
    stub = entry[2]
    if isinstance(stub, str) and stub.lower().endswith(".txt"):
        path = stub
        if not os.path.isabs(path):
            path = os.path.join(SIM_ROOT, path)
        return path
    # Stub key or None -- not a file path; caller must pass --deck-file.
    return None


def run_cell(deck_key, apl_override, mainboard, min_l, min_k, max_m,
             key_tag, n, on_play, mixed, seed):
    """Run one grid cell. Returns a dict of metrics or None on failure."""
    apl = get_apl(apl_override or deck_key)
    if apl is None:
        return None

    # Inject min_lands / min_keep_cards via the instance keep attribute.
    apl.keep = make_keep(min_l, min_k, key_tag)

    # Inject max_mulligans by binding it onto the module-global
    # take_opening_hand that base_apl.run_game resolves at call time.
    orig_toh = base_apl.take_opening_hand
    base_apl.take_opening_hand = functools.partial(orig_toh, max_mulligans=max_m)
    try:
        res = run_simulation(
            apl=apl,
            mainboard=mainboard,
            n=n,
            on_play=on_play,
            mixed_play_draw=mixed,
            seed=seed,
        )
    finally:
        base_apl.take_opening_hand = orig_toh

    akt = res.avg_kill_turn()
    mkt = res.median_kill_turn()
    return {
        "min_lands":   min_l,
        "min_keep":    min_k,
        "max_mulls":   max_m,
        "gf_win_rate": round(res.win_rate() * 100, 1),
        "avg_kill":    round(akt, 3) if akt is not None else None,
        "median_kill": int(mkt) if mkt is not None else None,
        "win_by_t3":   res.win_by_turn(3),
        "win_by_t4":   res.win_by_turn(4),
        "win_by_t5":   res.win_by_turn(5),
        "avg_mulls":   round(res.avg_mulligans(), 3),
        "mull_rate":   res.mull_rate(),
    }


# Objective -> (sort key getter, reverse?).  Cells with a missing primary
# metric (e.g. no kills at all) sort to the bottom.
_OBJECTIVES = {
    "avg_kill":    (lambda r: (r["avg_kill"] is None, r["avg_kill"]
                               if r["avg_kill"] is not None else 1e9), False),
    "gf_win_rate": (lambda r: r["gf_win_rate"], True),
    "win_by_t4":   (lambda r: r["win_by_t4"], True),
}


def sort_rows(rows, objective):
    keyfn, reverse = _OBJECTIVES[objective]
    return sorted(rows, key=keyfn, reverse=reverse)


_COLS = [
    ("rank",        "rank",        4),
    ("min_lands",   "minL",        4),
    ("min_keep",    "minK",        4),
    ("max_mulls",   "maxM",        4),
    ("gf_win_rate", "gfWR%",       7),
    ("avg_kill",    "avgKill",     8),
    ("median_kill", "medKill",     7),
    ("win_by_t3",   "byT3%",       6),
    ("win_by_t4",   "byT4%",       6),
    ("win_by_t5",   "byT5%",       6),
    ("avg_mulls",   "avgMul",      6),
    ("mull_rate",   "mul%",        6),
]


def _fmt(val, width):
    if val is None:
        s = "N/A"
    else:
        s = str(val)
    return s.rjust(width)


def print_table(rows, objective, archetype, n):
    print("")
    print("  == mulligan sweep (GOLDFISH; gfWR% = reached-lethal-in-time, NOT match WR) ==")
    print("  archetype: %s   n=%d/cell   cells=%d   sorted by: %s"
          % (archetype, n, len(rows), objective))
    header = "".join(label.rjust(w) for _, label, w in _COLS)
    print("  " + header)
    print("  " + "-" * len(header))
    for i, r in enumerate(rows, 1):
        cells = []
        for field_key, _, w in _COLS:
            if field_key == "rank":
                cells.append(_fmt(i, w))
            else:
                cells.append(_fmt(r[field_key], w))
        print("  " + "".join(cells))
    print("")


def write_csv(rows, path):
    cols = [c[0] for c in _COLS if c[0] != "rank"]
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join("" if r[c] is None else str(r[c]) for c in cols))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    p = argparse.ArgumentParser(
        description="Track A goldfish mulligan-threshold sweep (calibration/pre-filter).")
    p.add_argument("--deck", default="borosenergy",
                   help="Registry deck key (e.g. borosenergy, amulettitan). "
                        "Used to resolve both the APL and (if a .txt) the deck file.")
    p.add_argument("--deck-file", default=None,
                   help="Explicit deck file path (overrides registry-derived path; "
                        "required when the registry stub is not a .txt).")
    p.add_argument("--apl", default=None,
                   help="Override APL registry key (default: same as --deck).")
    p.add_argument("--n", type=int, default=2000, help="Games per grid cell.")
    p.add_argument("--seed", type=int, default=42,
                   help="Fixed RNG seed reused across cells for paired comparison.")
    p.add_argument("--min-lands", default="1,2,3",
                   help="Comma list of min_lands values (default 1,2,3).")
    p.add_argument("--min-keep", default="0,1,2",
                   help="Comma list of min_keep_cards values (default 0,1,2).")
    p.add_argument("--max-mulls", default="1,2,3",
                   help="Comma list of max_mulligans values (default 1,2,3).")
    p.add_argument("--key-tag", default="creature",
                   help="Tag for the 'keepable non-land' role "
                        "(creature, ramp, threat, combo, artifact, ...).")
    p.add_argument("--objective", default="avg_kill",
                   choices=sorted(_OBJECTIVES.keys()),
                   help="Ranking objective (default avg_kill, ascending).")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--draw", action="store_true", help="Run all games on the draw.")
    grp.add_argument("--mixed", action="store_true",
                     help="Randomly alternate play/draw 50/50.")
    p.add_argument("--csv", default=None, help="Write the ranked grid to a CSV file.")
    args = p.parse_args()

    deck_key = args.deck
    deck_path = resolve_deck_file(deck_key, args.deck_file)
    if not deck_path:
        print("ERROR: could not resolve a deck file for '%s'. "
              "Pass --deck-file explicitly." % deck_key)
        return 1
    if not os.path.exists(deck_path):
        print("ERROR: deck file not found: %s" % deck_path)
        return 1

    key_tag = resolve_key_tag(args.key_tag)
    min_lands = parse_int_list(args.min_lands)
    min_keep = parse_int_list(args.min_keep)
    max_mulls = parse_int_list(args.max_mulls)
    on_play = not args.draw
    mixed = args.mixed

    print("Loading deck: %s" % deck_path)
    mainboard, _ = load_deck_from_file(deck_path)
    if not mainboard:
        print("ERROR: deck loaded empty.")
        return 1

    # Probe APL once for a name / load failure.
    probe = get_apl(args.apl or deck_key)
    if probe is None:
        print("ERROR: no APL registered for '%s'." % (args.apl or deck_key))
        return 1
    archetype = getattr(probe, "name", deck_key)

    total = len(min_lands) * len(min_keep) * len(max_mulls)
    print("Sweeping %d cells (%s) x n=%d, key-tag=%s, mode=%s, seed=%d ..."
          % (total, "x".join(str(len(x)) for x in (min_lands, min_keep, max_mulls)),
             args.n, key_tag, ("mixed" if mixed else ("draw" if args.draw else "play")),
             args.seed))

    rows = []
    cell = 0
    for ml in min_lands:
        for mk in min_keep:
            for mm in max_mulls:
                cell += 1
                print("  [cell %d/%d] min_lands=%d min_keep=%d max_mulls=%d"
                      % (cell, total, ml, mk, mm))
                r = run_cell(deck_key, args.apl, mainboard, ml, mk, mm,
                             key_tag, args.n, on_play, mixed, args.seed)
                if r is None:
                    print("    [skip] APL failed to load for this cell.")
                    continue
                rows.append(r)

    if not rows:
        print("ERROR: no cells produced results.")
        return 1

    ranked = sort_rows(rows, args.objective)
    print_table(ranked, args.objective, archetype, args.n)

    if args.csv:
        csv_path = args.csv
        if not os.path.isabs(csv_path):
            csv_path = os.path.join(os.getcwd(), csv_path)
        write_csv(ranked, csv_path)
        print("  CSV written: %s" % csv_path)

    print("  NOTE: goldfish is a pre-filter only (Gotcha G2). gfWR% is "
          "reach-lethal-in-time, not match WR. Track B (true WR) is blocked on "
          "the engine mulligan-refactor prerequisite (Gotcha G1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
