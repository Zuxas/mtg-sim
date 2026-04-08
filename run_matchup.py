"""
run_matchup.py — Single matchup runner (called by parallel_launcher)

Usage:
    python run_matchup.py OUR_DECK OPP_DECK FIELD_PCT N SEED FORMAT TYPE
    python run_matchup.py "Boros Energy" "Amulet Titan" 8.7 1000 42 modern combo
    python run_matchup.py "Legacy Humans" "Eldrazi Stompy" 6.4 1000 43 legacy fair
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("data/matchup_jobs", exist_ok=True)


def bo3_win(g1: float, g2: float, g3: float = None) -> float:
    """Correct Bo3 match win probability.
    P = P(win G1,G2) + P(win G1,lose G2,win G3) + P(lose G1,win G2,win G3)
    All inputs as percentages (0-100).
    """
    g1 /= 100; g2 /= 100
    g3 = ((g1 + g2) / 2) if g3 is None else g3 / 100
    return round((g1*g2 + g1*(1-g2)*g3 + (1-g1)*g2*g3) * 100, 1)


def main():
    our_deck    = sys.argv[1]
    opp_name    = sys.argv[2]
    field_pct   = float(sys.argv[3])
    n           = int(sys.argv[4])
    seed        = int(sys.argv[5])
    format_name = sys.argv[6]
    mtype       = sys.argv[7]   # "combo" or "fair"

    safe     = opp_name.lower().replace(" ","_").replace("'","")
    out_path = f"data/matchup_jobs/{safe}.json"

    t0     = time.time()
    result = {"opp": opp_name, "our_deck": our_deck, "field_pct": field_pct,
              "type": mtype, "n": n, "error": None}
    try:
        if mtype == "combo":
            _run_combo(result, opp_name, format_name, n, seed)
        else:
            _run_fair(result, our_deck, opp_name, format_name, n, seed)

        result["elapsed"] = round(time.time() - t0, 1)
        print(f"OK  {opp_name}: G1={result['g1']:.1f}%  Match={result['match']:.1f}%  "
              f"({result['elapsed']}s)")

    except Exception as e:
        import traceback
        result["error"]   = str(e)
        result["elapsed"] = round(time.time() - t0, 1)
        print(f"ERR {opp_name}: {e}")
        traceback.print_exc()

    with open(out_path, "w") as f:
        json.dump(result, f)


def _run_combo(result, opp_name, format_name, n, seed):
    """Combo matchup: hand-aware kill-turn sampler."""
    from format_config import get_combo_dist
    from engine.combo_model import run_combo_matchup

    # Update combo_model's kill dist dynamically
    import engine.combo_model as cm
    dist = get_combo_dist(opp_name, format_name)
    # Patch the sampler for this archetype
    _orig = cm.ComboKillSampler if hasattr(cm, 'ComboKillSampler') else None
    # (combo_model uses its own internal dists — we inject via opp name match)

    g1 = run_combo_matchup(opp_name, n=n, game=1, seed=seed)
    g2 = run_combo_matchup(opp_name, n=n, game=2, seed=seed+1)
    g3 = run_combo_matchup(opp_name, n=n, game=3, seed=seed+2)
    match = bo3_win(g1["win_pct"], g2["win_pct"], g3["win_pct"])
    result.update({
        "g1": g1["win_pct"], "g2": g2["win_pct"], "g3": g3["win_pct"],
        "match": match, "avg_turns": g1["avg_turns"],
        "hard_stop": g1["hard_stop_rate"],
    })


def _run_fair(result, our_deck, opp_name, format_name, n, seed):
    """
    Fair matchup: use real tournament G1 data if available,
    fall back to both-sides combat sim.
    """
    from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn

    # Try real DB data first
    try:
        from meta_bridge import get_real_matchup
        real_g1 = get_real_matchup(our_deck, opp_name, format_name, min_matches=30)
    except Exception:
        real_g1 = None

    if real_g1 is None:
        # Fall back to both-sides combat sim
        from engine.match_runner import run_match_set
        from generate_matchup_data import load_deck_and_apl

        our_main, _, our_apl = load_deck_and_apl(our_deck, format_name)
        opp_main, _, opp_apl = load_deck_and_apl(opp_name, format_name)

        if not our_main or not opp_main:
            raise ValueError(f"Could not load deck for {opp_name}")

        r = run_match_set(our_apl, our_main, opp_apl, opp_main,
                          n=n, seed=seed, mix_play_draw=True)
        real_g1 = r.win_pct()
        result["g1_source"] = "sim"
    else:
        result["g1_source"] = "db"

    # G2/G3 — SB premium on top of real G1
    opp_dist = ARCHETYPE_CLOCKS.get(
        _infer_archetype_key(opp_name), ARCHETYPE_CLOCKS["unknown"])
    opp_avg = avg_kill_turn(opp_dist)
    sb  = 5 if opp_avg >= 6 else (8 if opp_avg >= 5 else 10)
    g2_wp = min(98.0, real_g1 + sb)
    g3_wp = min(98.0, real_g1 + sb * 0.7)

    match = bo3_win(real_g1, g2_wp, g3_wp)
    result.update({
        "g1": real_g1, "g2": round(g2_wp, 1), "g3": round(g3_wp, 1),
        "match": match, "avg_turns": 0.0, "hard_stop": 0.0,
    })


if __name__ == "__main__":
    main()
