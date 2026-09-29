"""
calibration/scoreboard.py -- score the two-player sim against REAL match results.
Spec harness/specs/2026-09-30-sim-real-scoreboard.md.

For every pair of modeled decks (calibration/name_map_<fmt>.json) with enough
real matches since --since:
  * sim G1 win rate from the ENGINE itself: engine.match_runner.run_match, seat A
    = alphabetically-first deck, on_play alternating, seed = --seed + i (house
    convention). No ComboKillSampler -- this scores the engine, not a model.
  * converted to a Bo3 match win rate without sideboarding, p^2 (3 - 2p), because
    real rows are MATCH results (which include sideboarded games -- a known gap).
  * vs the real win rate (draws excluded from the rate) with a Wilson 95% CI.
Also: FIELD check (modeled share in format_config vs real share) and LIST check
(the sim decklist vs the real decklists under its labels).

Output: data/scoreboard/<fmt>-<date>-<commit>.json + .md, one row appended to
data/scoreboard/history.csv. Read-only on the live DB.

Usage:
    PYTHONHASHSEED=0 python -m calibration.scoreboard --format modern --since 2026-05-15
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import os
import subprocess
import sys
import time
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.stats_util import wilson_bounds  # noqa: E402
from calibration import real_results as rr  # noqa: E402

TRUSTED_N = 400       # decisive real matches (July calibration protocol)
DIRECTIONAL_N = 100


# ---------------------------------------------------------------- pure metrics

def bo3(p: float) -> float:
    """Match win probability from a per-game win probability, no sideboarding:
    win 2-0 (p^2) or 2-1 (2 p^2 (1-p)) = p^2 (3 - 2p)."""
    return p * p * (3 - 2 * p)


def trust_band(decisive: int) -> str:
    return ("trusted" if decisive >= TRUSTED_N else
            "directional" if decisive >= DIRECTIONAL_N else "noise")


def cell_stats(sim_wins: int, sim_n: int, real: dict) -> dict:
    """One cell from the first deck's point of view. Rates are 0-1."""
    g1 = sim_wins / sim_n
    sim_match = bo3(g1)
    decisive = real["wins"] + real["losses"]
    real_wr = real["wins"] / decisive if decisive else 0.5
    lo, hi = wilson_bounds(real["wins"], decisive)
    return {
        "sim_g1": round(g1, 4), "sim_match": round(sim_match, 4), "sim_n": sim_n,
        "real_wr": round(real_wr, 4), "real_lo": round(lo, 4), "real_hi": round(hi, 4),
        "real_decisive": decisive, "real_draws": real["draws"],
        "delta": round(sim_match - real_wr, 4),
        "miss": not (lo <= sim_match <= hi),
        "same_side": (sim_match - 0.5) * (real_wr - 0.5) > 0,
        "real_clear": not (lo <= 0.5 <= hi),        # real result clearly favours one side
        "trust": trust_band(decisive),
    }


def correlation_and_spread(xs: list[float], ys: list[float]) -> dict:
    """How well sim rates track real ones (Pearson r, regression slope of real on
    sim) and how one-sided each side is (mean distance from 50%). spread_ratio > 1
    = the sim is more extreme than reality (overconfident)."""
    n = len(xs)
    out = {"spread_sim_pp": round(100 * sum(abs(x - 0.5) for x in xs) / n, 2) if n else None,
           "spread_real_pp": round(100 * sum(abs(y - 0.5) for y in ys) / n, 2) if n else None,
           "pearson_r": None, "slope_real_on_sim": None, "spread_ratio": None}
    if out["spread_real_pp"]:
        out["spread_ratio"] = round(out["spread_sim_pp"] / out["spread_real_pp"], 2)
    if n >= 3:
        mx, my = sum(xs) / n, sum(ys) / n
        sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        sxx = sum((a - mx) ** 2 for a in xs)
        syy = sum((b - my) ** 2 for b in ys)
        if sxx and syy:
            out["pearson_r"] = round(sxy / math.sqrt(sxx * syy), 3)
            out["slope_real_on_sim"] = round(sxy / sxx, 3)
    return out


def headline(cells: list[dict]) -> dict:
    """Weighted by decisive real matches. `direction_agree` only over cells whose
    real CI excludes 50% (otherwise 'which side is favoured' is not known)."""
    if not cells:
        return {"cells": 0}
    w = sum(c["real_decisive"] for c in cells)
    mae = sum(c["real_decisive"] * abs(c["delta"]) for c in cells) / w
    clear = [c for c in cells if c["real_clear"]]
    xs, ys = [c["sim_match"] for c in cells], [c["real_wr"] for c in cells]
    return {
        **correlation_and_spread(xs, ys),
        "cells": len(cells),
        "real_matches": w,
        "weighted_mae_pp": round(100 * mae, 2),
        "median_abs_delta_pp": round(100 * sorted(abs(c["delta"]) for c in cells)[len(cells) // 2], 2),
        "misses": sum(1 for c in cells if c["miss"]),
        "direction_agree": (round(sum(1 for c in clear if c["same_side"]) / len(clear), 3)
                            if clear else None),
        "direction_cells": len(clear),
    }


def list_check(sim_cards: set[str], real_profile: dict) -> dict:
    """Cosine between the sim list (card present = 1) and the real inclusion
    profile, plus the staples the sim misses and the cards real lists rarely run."""
    if not real_profile:
        return {"cosine": None}
    num = sum(v for c, v in real_profile.items() if c in sim_cards)
    den = math.sqrt(len(sim_cards)) * math.sqrt(sum(v * v for v in real_profile.values()))
    return {
        "cosine": round(num / den, 3) if den else None,
        "missing_staples": sorted((c for c, v in real_profile.items() if v >= 0.6 and c not in sim_cards),
                                  key=lambda c: -real_profile[c]),
        "rare_in_real": sorted(c for c in sim_cards if real_profile.get(c, 0) < 0.1),
    }


# ---------------------------------------------------------------- sim side

def _quiet():
    return contextlib.redirect_stdout(io.StringIO())


def sim_cell(spec_a: dict, spec_b: dict, n: int, seed: int, decks: dict) -> int:
    """First deck's wins over n engine games (fresh pilots every game)."""
    from engine.match_runner import run_match
    from apl import get_match_apl
    deck_a, deck_b = decks[spec_a["deck_file"]], decks[spec_b["deck_file"]]
    wins = 0
    with _quiet():
        for i in range(n):
            r = run_match(get_match_apl(spec_a["apl"]), deck_a,
                          get_match_apl(spec_b["apl"]), deck_b,
                          on_play=(i % 2 == 0), seed=seed + i)
            wins += bool(r.won)
    return wins


def _load_decks(name_map: dict) -> dict:
    from data.deck import load_deck_from_file
    out = {}
    with _quiet():
        for spec in name_map.values():
            out[spec["deck_file"]] = load_deck_from_file(os.path.join(ROOT, spec["deck_file"]))[0]
    return out


def _commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                       text=True).strip()
    except Exception:
        return "unknown"


def _mismodel(a: str, b: str) -> str | None:
    try:
        from mismodeled_matchups import lookup
    except Exception:
        return None
    for d in (a, b):
        rec = lookup(d)
        if rec:
            return f"{d}: {rec.get('direction', 'flagged')}"
    return None


# ---------------------------------------------------------------- run

def run(fmt: str, since: str, n: int, seed: int, min_real: int, out_dir: str,
        db_path: str | None = None, until: str | None = None) -> dict:
    name_map = rr.load_name_map(fmt)
    con = rr.connect_ro(db_path)
    real = rr.real_matchups(con, fmt, since, name_map, until)
    cov = real.pop("_coverage")
    decks = _load_decks(name_map)
    t0 = time.time()

    cells = []
    for (a, b), r in sorted(real.items()):
        if r["wins"] + r["losses"] < min_real:
            continue
        wins = sim_cell(name_map[a], name_map[b], n, seed, decks)
        c = cell_stats(wins, n, r)
        c.update(a=a, b=b, mismodel=_mismodel(a, b))
        cells.append(c)

    from format_config import FORMATS
    modeled = FORMATS[fmt]["field"]
    real_share = rr.real_field_shares(con, fmt, since, name_map, until)
    # the modeled field may use another key for a mapped deck ("Affinity" for Izzet Affinity)
    field_key = {d: spec.get("field_key", d) for d, spec in name_map.items()}
    by_field = {fk: d for d, fk in field_key.items()}
    field = sorted(({"deck": by_field.get(k, k), "modeled_pct": modeled.get(k),
                     "real_pct": round(100 * real_share.get(by_field.get(k, k), 0), 2)}
                    for k in set(modeled) | set(field_key.values())), key=lambda x: -(x["real_pct"] or 0))

    lists = {}
    for d, spec in name_map.items():
        n_real, prof = rr.real_list_profile(con, fmt, since, spec["labels"])
        lists[d] = {"real_decks": n_real, **list_check({c.name for c in decks[spec["deck_file"]]}, prof)}

    report = {
        "format": fmt, "since": since, "until": until, "commit": _commit(),
        "generated": date.today().isoformat(), "n_per_cell": n, "seed": seed, "min_real": min_real,
        "coverage": {"real_rows": cov["rows"], "mapped_rows": cov["mapped_rows"],
                     "mapped_share": round(cov["mapped_rows"] / cov["rows"], 3) if cov["rows"] else 0,
                     "top_unmapped": dict(list(cov["unmapped_labels"].items())[:15]),
                     "real_field_unmapped_pct": round(100 * real_share.get("_unmapped", 0), 2)},
        "headline": {"all": headline(cells),
                     "not_flagged": headline([c for c in cells if not c["mismodel"]]),
                     "trusted": headline([c for c in cells if c["trust"] == "trusted"])},
        "cells": sorted(cells, key=lambda c: -abs(c["delta"]) * math.sqrt(c["real_decisive"])),
        "field": field, "lists": lists, "elapsed_s": round(time.time() - t0, 1),
    }
    _write(report, out_dir)
    return report


def _markdown(r: dict) -> str:
    h = r["headline"]["all"]
    L = [f"# Sim vs real -- {r['format']} since {r['since']} (commit {r['commit']})", "",
         f"Covers **{100 * r['coverage']['mapped_share']:.0f}%** of {r['coverage']['real_rows']:,} real match rows. "
         f"{h.get('cells', 0)} cells, {h.get('real_matches', 0):,} decisive real matches, sim n={r['n_per_cell']}/cell.", "",
         "| Slice | Cells | Weighted mean abs delta | Median abs delta | Outside real CI | Same favourite | r (sim vs real) | Spread sim / real |",
         "|---|---|---|---|---|---|---|---|"]
    for k, v in r["headline"].items():
        if v.get("cells"):
            da = f"{100 * v['direction_agree']:.0f}% of {v['direction_cells']}" if v["direction_agree"] is not None else "-"
            L.append(f"| {k} | {v['cells']} | {v['weighted_mae_pp']}pp | {v['median_abs_delta_pp']}pp | "
                     f"{v['misses']} | {da} | {v['pearson_r']} | {v['spread_sim_pp']}pp / {v['spread_real_pp']}pp |")
    L += ["", "## Worst cells (|delta| weighted by real sample)", "",
          "| Matchup | Sim G1 | Sim match | Real | Real 95% CI | n | Delta | Trust | Flag |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in r["cells"][:15]:
        L.append(f"| {c['a']} vs {c['b']} | {100 * c['sim_g1']:.1f}% | {100 * c['sim_match']:.1f}% | "
                 f"{100 * c['real_wr']:.1f}% | {100 * c['real_lo']:.0f}-{100 * c['real_hi']:.0f} | "
                 f"{c['real_decisive']} | {100 * c['delta']:+.1f} | {c['trust']} | {c['mismodel'] or ''} |")
    L += ["", "## Field: modeled share vs real share", "", "| Deck | Modeled % | Real % |", "|---|---|---|"]
    for f in r["field"]:
        L.append(f"| {f['deck']} | {f['modeled_pct'] if f['modeled_pct'] is not None else '-'} | {f['real_pct']} |")
    L.append(f"| (real decks not modeled) | - | {r['coverage']['real_field_unmapped_pct']} |")
    L += ["", "Top unmapped real labels: " + ", ".join(f"{k} ({v})" for k, v in r["coverage"]["top_unmapped"].items()),
          "", "## Lists: sim decklist vs real lists", "",
          "| Deck | Real lists | Cosine | Missing staples (>=60% of real lists) | Sim cards rare in real (<10%) |",
          "|---|---|---|---|---|"]
    for d, l in sorted(r["lists"].items(), key=lambda x: (x[1].get("cosine") is None, x[1].get("cosine") or 0)):
        L.append(f"| {d} | {l['real_decks']} | {l.get('cosine')} | {', '.join(l.get('missing_staples', [])[:6])} | "
                 f"{', '.join(l.get('rare_in_real', [])[:6])} |")
    return "\n".join(L) + "\n"


def _write(r: dict, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, f"{r['format']}-{r['generated']}-{r['commit']}")
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in r.items() if k != "elapsed_s"}, f, indent=1, sort_keys=True)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(_markdown(r))
    hist = os.path.join(out_dir, "history.csv")
    new = not os.path.exists(hist)
    h = r["headline"]["all"]
    with open(hist, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["commit", "generated", "format", "since", "cells", "real_matches",
                        "weighted_mae_pp", "misses", "direction_agree", "mapped_share",
                        "pearson_r", "spread_ratio"])
        w.writerow([r["commit"], r["generated"], r["format"], r["since"], h.get("cells"),
                    h.get("real_matches"), h.get("weighted_mae_pp"), h.get("misses"),
                    h.get("direction_agree"), r["coverage"]["mapped_share"],
                    h.get("pearson_r"), h.get("spread_ratio")])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Score the sim against real match results.")
    ap.add_argument("--format", default="modern")
    ap.add_argument("--since", default="2026-05-15")
    ap.add_argument("--until", default=None)
    ap.add_argument("--n", type=int, default=400, help="sim games per cell")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-real", type=int, default=DIRECTIONAL_N,
                    help="minimum decisive real matches for a cell")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "scoreboard"))
    args = ap.parse_args(argv)
    r = run(args.format, args.since, args.n, args.seed, args.min_real, args.out, until=args.until)
    h = r["headline"]["all"]
    print(f"coverage {100 * r['coverage']['mapped_share']:.0f}% of {r['coverage']['real_rows']} real rows; "
          f"{h.get('cells', 0)} cells; weighted MAE {h.get('weighted_mae_pp')}pp; misses {h.get('misses')}; "
          f"direction agree {h.get('direction_agree')} ({h.get('direction_cells')} clear cells); "
          f"r {h.get('pearson_r')}; spread sim/real {h.get('spread_ratio')}x; "
          f"{r['elapsed_s']}s")
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
