"""
run_matchup.py — Single matchup runner (called by parallel launcher)

Runs ONE matchup and writes result to a JSON file.
Designed to be launched as an independent subprocess.

Usage (internal — called by parallel_launcher.py):
    python run_matchup.py "Dimir Reanimator" 22.4 1000 42 legacy combo
    python run_matchup.py "Eldrazi Stompy" 6.4 1000 43 legacy fair
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("data/matchup_jobs", exist_ok=True)

def main():
    opp_name    = sys.argv[1]
    field_pct   = float(sys.argv[2])
    n           = int(sys.argv[3])
    seed        = int(sys.argv[4])
    format_name = sys.argv[5]
    matchup_type= sys.argv[6]   # "combo" or "fair"

    safe = opp_name.lower().replace(" ","_").replace("'","")
    out_path = f"data/matchup_jobs/{safe}.json"

    t0 = time.time()
    result = {"opp": opp_name, "field_pct": field_pct,
              "type": matchup_type, "n": n, "error": None}
    try:
        if matchup_type == "combo":
            from engine.combo_model import run_combo_matchup
            g1 = run_combo_matchup(opp_name, n=n, game=1, seed=seed)
            g2 = run_combo_matchup(opp_name, n=n, game=2, seed=seed+1)
            match = round(g1["win_pct"] / 3 + g2["win_pct"] * 2 / 3, 1)
            result.update({"g1": g1["win_pct"], "g2": g2["win_pct"],
                           "match": match, "avg_turns": g1["avg_turns"],
                           "hard_stop": g1["hard_stop_rate"]})
        else:
            from engine.match_runner import run_match_set
            from generate_matchup_data import load_deck_and_apl
            from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn

            our_main, _, our_apl = load_deck_and_apl("Legacy Humans", format_name)
            opp_main, _, opp_apl = load_deck_and_apl(opp_name, format_name)

            if not our_main or not opp_main:
                raise ValueError(f"Deck load failed for {opp_name}")

            r = run_match_set(our_apl, our_main, opp_apl, opp_main,
                              n=n, seed=seed, mix_play_draw=True)
            opp_dist = ARCHETYPE_CLOCKS.get(
                _infer_archetype_key(opp_name), ARCHETYPE_CLOCKS["unknown"])
            sb = 6 if avg_kill_turn(opp_dist) <= 4 else 8
            g2  = min(99.0, r.win_pct() + sb)
            match = round(r.win_pct() / 3 + g2 * 2 / 3, 1)
            result.update({"g1": r.win_pct(), "g2": round(g2, 1),
                           "match": match, "avg_turns": round(r.avg_turns, 1),
                           "hard_stop": 0.0})

        result["elapsed"] = round(time.time() - t0, 1)
        print(f"OK  {opp_name}: G1={result['g1']:.1f}%  Match={result['match']:.1f}%  "
              f"({result['elapsed']}s)")

    except Exception as e:
        result["error"] = str(e)
        result["elapsed"] = round(time.time() - t0, 1)
        print(f"ERR {opp_name}: {e}")

    with open(out_path, "w") as f:
        json.dump(result, f)

if __name__ == "__main__":
    main()
