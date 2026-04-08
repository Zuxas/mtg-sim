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

def bo3_win(g1: float, g2: float, g3: float = None) -> float:
    """
    Correct Bo3 match win probability.
    P(win match) = P(win G1,G2) + P(win G1, lose G2, win G3)
                                 + P(lose G1, win G2, win G3)
    G3 defaults to average of G1 and G2 (both players have boarded).
    All inputs as percentages (0-100).
    """
    g1 /= 100; g2 /= 100
    g3 = ((g1 + g2) / 2) if g3 is None else g3 / 100
    match = g1*g2 + g1*(1-g2)*g3 + (1-g1)*g2*g3
    return round(match * 100, 1)


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
            g3 = run_combo_matchup(opp_name, n=n, game=3, seed=seed+2)
            match = bo3_win(g1["win_pct"], g2["win_pct"], g3["win_pct"])
            result.update({"g1": g1["win_pct"], "g2": g2["win_pct"],
                           "g3": g3["win_pct"], "match": match,
                           "avg_turns": g1["avg_turns"],
                           "hard_stop": g1["hard_stop_rate"]})
        else:
            from engine.match_runner import run_match_set
            from generate_matchup_data import load_deck_and_apl
            from engine.combo_model import build_library_g2

            our_main, _, our_apl = load_deck_and_apl("Legacy Humans", format_name)
            opp_main, _, opp_apl = load_deck_and_apl(opp_name, format_name)

            if not our_main or not opp_main:
                raise ValueError(f"Deck load failed for {opp_name}")

            # G1 — both maindecks, 50/50 play/draw
            r_g1 = run_match_set(our_apl, our_main, opp_apl, opp_main,
                                  n=n, seed=seed, mix_play_draw=True)

            # G2 — we sideboard (approximated: +6-11% based on opp speed)
            # Opponent on play G2 (loser of G1 picks — on avg they're slightly
            # more likely to have won G1 vs fair decks we're favored against)
            from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn
            opp_dist = ARCHETYPE_CLOCKS.get(
                _infer_archetype_key(opp_name), ARCHETYPE_CLOCKS["unknown"])
            opp_avg = avg_kill_turn(opp_dist)
            # SB premium: faster opp = more targeted hate = bigger swing
            sb = 5 if opp_avg >= 6 else (8 if opp_avg >= 5 else 10)
            g2_wp = min(98.0, r_g1.win_pct() + sb)

            # G3 — 50/50, both boarded, slightly less swing than G2
            g3_wp = min(98.0, r_g1.win_pct() + sb * 0.7)

            match = bo3_win(r_g1.win_pct(), g2_wp, g3_wp)
            result.update({"g1": r_g1.win_pct(), "g2": round(g2_wp, 1),
                           "g3": round(g3_wp, 1), "match": match,
                           "avg_turns": round(r_g1.avg_turns, 1),
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
