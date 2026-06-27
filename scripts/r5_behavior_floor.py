"""R5 behavior-floor + falsifier harness (forced-engine, cache-bypassed).

Calls engine.match_runner.run_match_set DIRECTLY (no run_matchup.py db-cache),
n_workers=1 (module-global PW counters are not process-shared), seed=42, so the
g1_source is genuinely "sim". Runs Eldrazi Tron (match APL, WANTS_PW_LOYALTY)
against a small set of opponents, gate ON vs gate OFF, and reports the three
instrumentation counters + the on/off MWR delta.

Usage: PYTHONIOENCODING=utf-8 python scripts/r5_behavior_floor.py [n]
ASCII-only.
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_matchup_data import load_deck_and_apl
from apl import get_match_apl
from engine import planeswalkers as pw
from engine.match_runner import run_match_set

OPPONENTS = ["borosenergy", "uwblink"]
TRON = "eldrazitron"
FMT = "modern"


def _load_main(key):
    main, side, _gold = load_deck_and_apl(key, FMT)
    return main


def _run(tron_main, opp_main, opp_key, n, gate_on):
    tron_apl = get_match_apl(TRON)
    opp_apl = get_match_apl(opp_key)
    if opp_apl is None:
        # fall back to goldfish-adapter via the loaded goldfish apl
        _m, _s, opp_apl = load_deck_and_apl(opp_key, FMT)
    # Force the gate state on the Tron APL instance (and its class) for this run.
    setattr(tron_apl, "WANTS_PW_LOYALTY", gate_on)
    type(tron_apl).WANTS_PW_LOYALTY = gate_on
    pw.reset_fire_count()
    res = run_match_set(tron_apl, tron_main, opp_apl, opp_main,
                        n=n, seed=42, mix_play_draw=True, n_workers=1)
    return {
        "opp": opp_key,
        "gate_on": gate_on,
        "n": n,
        "tron_wr": round(res.win_pct(), 2) if hasattr(res, "win_pct") else None,
        "a_wins": res.a_wins,
        "b_wins": res.b_wins,
        "PW_ACTIVATIONS": pw.PW_ACTIVATIONS,
        "PW_ULTIMATES": pw.PW_ULTIMATES,
        "PW_COMBAT_DEATHS": pw.PW_COMBAT_DEATHS,
    }


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    tron_main = _load_main(TRON)
    opp_mains = {k: _load_main(k) for k in OPPONENTS}

    out = {"n": n, "rows": []}
    for opp in OPPONENTS:
        on = _run(tron_main, opp_mains[opp], opp, n, True)
        off = _run(tron_main, opp_mains[opp], opp, n, False)
        delta = None
        if on["tron_wr"] is not None and off["tron_wr"] is not None:
            delta = round(on["tron_wr"] - off["tron_wr"], 2)
        out["rows"].append({"opp": opp, "on": on, "off": off, "mwr_delta_pp": delta})
        print(f"[{opp}] ON  wr={on['tron_wr']} act={on['PW_ACTIVATIONS']} "
              f"ult={on['PW_ULTIMATES']} deaths={on['PW_COMBAT_DEATHS']}")
        print(f"[{opp}] OFF wr={off['tron_wr']} act={off['PW_ACTIVATIONS']} "
              f"ult={off['PW_ULTIMATES']} deaths={off['PW_COMBAT_DEATHS']}  "
              f"delta={delta}pp")

    # Aggregate counters across opponents (gate ON).
    tot_act = sum(r["on"]["PW_ACTIVATIONS"] for r in out["rows"])
    tot_ult = sum(r["on"]["PW_ULTIMATES"] for r in out["rows"])
    tot_death = sum(r["on"]["PW_COMBAT_DEATHS"] for r in out["rows"])
    games = n * len(OPPONENTS)
    out["aggregate_on"] = {
        "games": games,
        "PW_ACTIVATIONS": tot_act,
        "PW_ULTIMATES": tot_ult,
        "PW_COMBAT_DEATHS": tot_death,
        "activations_per_game": round(tot_act / games, 3) if games else 0,
    }
    print("\nAGG ON  games=%d act=%d (%.2f/game) ult=%d deaths=%d" % (
        games, tot_act, out["aggregate_on"]["activations_per_game"],
        tot_ult, tot_death))
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    main()
