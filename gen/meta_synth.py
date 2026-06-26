"""
gen/meta_synth.py -- Synthesize a candidate metagame from top decks.

Given scored decks, pick the top-N that are mutually distinct (by core package /
color identity), re-score each as a closed field against the OTHERS, and emit a
meta report: relative shares (proportional to fitness) plus a pairwise race
matrix from each deck's goldfish kill distribution (engine race via
sim_bridge.race_win_pct).

Output: data/auto_pipeline/meta_<run>.json
"""

import os
import json

from sim_bridge import race_win_pct
from gen import PIPELINE_DATA


def _distinct_top(entries, n):
    """Keep the highest-fitness deck per (core package, color identity) bucket."""
    seen, out = set(), []
    for e in sorted(entries, key=lambda x: -x["fitness"]):
        core = (e.get("packages") or ["?"])[0]
        bucket = (core, "".join(e.get("color_identity", [])))
        if bucket in seen:
            continue
        seen.add(bucket)
        out.append(e)
        if len(out) >= n:
            break
    return out


def synthesize_meta(entries, *, top_n=6, run_id="run", n_race=20000,
                    out_dir=None, save=True):
    """
    entries: list of {deck_id, fitness, color_identity, packages, kill_distribution}.
    Returns the meta report dict and (optionally) writes it to disk.
    """
    field = _distinct_top([e for e in entries if e.get("kill_distribution")], top_n)
    if not field:
        return {"run_id": run_id, "field": [], "matrix": {}, "shares": {}}

    total_fit = sum(max(0.0, e["fitness"]) for e in field) or 1.0
    shares = {e["deck_id"]: round(max(0.0, e["fitness"]) / total_fit * 100, 1) for e in field}

    matrix = {}
    for a in field:
        row = {}
        for b in field:
            if a["deck_id"] == b["deck_id"]:
                row[b["deck_id"]] = 50.0
            else:
                row[b["deck_id"]] = race_win_pct(a["kill_distribution"],
                                                 b["kill_distribution"], n=n_race)
        matrix[a["deck_id"]] = row

    # field win rate = share-weighted race vs the rest of the synthesized field
    field_wr = {}
    for a in field:
        wr = sum(matrix[a["deck_id"]][b["deck_id"]] * (shares[b["deck_id"]] / 100.0)
                 for b in field if b["deck_id"] != a["deck_id"])
        denom = sum(shares[b["deck_id"]] / 100.0 for b in field if b["deck_id"] != a["deck_id"]) or 1.0
        field_wr[a["deck_id"]] = round(wr / denom, 1)

    report = {
        "run_id": run_id,
        "field": [{"deck_id": e["deck_id"], "fitness": e["fitness"],
                   "color_identity": e.get("color_identity", []),
                   "packages": e.get("packages", []),
                   "share_pct": shares[e["deck_id"]],
                   "intra_field_wr": field_wr[e["deck_id"]]} for e in field],
        "shares": shares,
        "matrix": matrix,
    }

    if save:
        out_dir = out_dir or PIPELINE_DATA
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"meta_{run_id}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        os.replace(tmp, path)
        report["_path"] = path
    return report
