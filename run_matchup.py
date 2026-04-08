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


def bo3_win(g1: float, g2: float, g3: float = None,
            play_advantage: float = 3.0) -> float:
    """
    Bo3 match win% with correct play/draw state tracking.

    MTG rules modeled:
      G1  : 2d6 roll, highest wins, ties reroll -> exactly 50/50 play/draw
      Win game N  -> opponent LOST -> opponent CHOOSES next game -> picks play
                    -> YOU are on DRAW for game N+1
      Lose game N -> YOU LOST    -> YOU CHOOSE next game         -> you pick play
                    -> YOU are on PLAY for game N+1
      Each match: fresh 60-card main + 15-card SB, no carry-over between rounds.

    Parameters (all as percentages, 0-100):
      g1             : our avg G1 win rate (50/50 play/draw embedded)
      g2             : our avg G2 win rate WITH SB (50/50 play/draw embedded)
      g3             : our avg G3 win rate WITH SB (default = g2)
      play_advantage : play vs draw edge % (default 3%). Derives:
                         on_play  = avg + PADV/2
                         on_draw  = avg - PADV/2
    """
    PADV = play_advantage / 2

    def split(avg):
        return (min(99.0, avg + PADV) / 100,
                max( 1.0, avg - PADV) / 100)

    g1p, g1d = split(g1)
    g2p, g2d = split(g2)
    g3_val   = g3 if g3 is not None else g2
    g3p, g3d = split(g3_val)

    match = 0.0
    for g1_wr, weight in [(g1p, 0.5), (g1d, 0.5)]:
        # WIN G1: they lost -> they choose G2 -> they pick play -> WE ON DRAW G2
        win_g2          = g1_wr * g2d
        win_g2_lose_g3  = g1_wr * (1-g2d) * g3p   # we lost G2 -> we choose G3 -> ON PLAY

        # LOSE G1: we lost -> we choose G2 -> we pick play -> WE ON PLAY G2
        lose_win_g2        = (1-g1_wr) * g2p
        lose_win_g2_win_g3 = lose_win_g2 * g3d    # they lost G2 -> they choose G3 -> WE ON DRAW

        match += weight * (win_g2 + win_g2_lose_g3 + lose_win_g2_win_g3)

    return round(match * 100, 1)


def _get_sb_premium(our_deck, opp_name, format_name):
    """Load our APL and ask for matchup-specific SB premium."""
    try:
        from generate_matchup_data import load_deck_and_apl
        _, _, apl = load_deck_and_apl(our_deck, format_name)
        if apl and hasattr(apl, 'sideboard_premium'):
            return apl.sideboard_premium(opp_name, format_name)
    except Exception:
        pass
    return 6.0


def _run_combo(result, opp_name, format_name, n, seed):
    """
    Combo matchup:
      G1: real DB data if available (preferred), else ComboKillSampler
      G2/G3: G1 + our deck's sideboard_premium
    """
    from engine.combo_model import run_combo_matchup

    our_deck = result.get("our_deck", "Legacy Humans")

    # Try real DB data for G1 first — always preferred over kill-turn sampler
    g1 = None
    try:
        from meta_bridge import get_real_matchup
        g1 = get_real_matchup(our_deck, opp_name, format_name, min_matches=20)
        if g1 is not None:
            result["g1_source"] = "db"
    except Exception:
        pass

    # Fall back to combo kill-turn sampler
    if g1 is None:
        g1_data = run_combo_matchup(opp_name, n=n, game=1, seed=seed)
        g1 = g1_data["win_pct"]
        result["avg_turns"] = g1_data.get("avg_turns", 0)
        result["hard_stop"] = g1_data.get("hard_stop_rate", 0)
        result["g1_source"] = "com"

    sb  = _get_sb_premium(our_deck, opp_name, format_name)
    g2  = min(98.0, g1 + sb)
    g3  = min(98.0, g1 + sb * 0.75)
    result.update({"g1": g1, "g2": round(g2,1), "g3": round(g3,1),
                   "match": bo3_win(g1, g2, g3)})


# Archetypes whose stub decks lack real interaction — credibility cap applied to SIM G1
INTERACTIVE = {
    "thoughtseize","midrange","control","murktide","frog",
    "rakdos","jund","esper","dimir","grixis",
    "delver","tempo","taxes","death and","prison",
    "four-color","four color","bant","azorius","jeskai",
    "gruul","stompy",
}

# Our aggro decks shouldn't be floored lower than 25% vs anything
AGGRO_OUR = {"aggro","prowess","burn","swiftspear","mono red","gruul","humans"}


def _run_fair(result, our_deck, opp_name, format_name, n, seed):
    """
    Fair matchup: real DB G1 if available, else both-sides combat sim.
    G2/G3: G1 + deck-specific SB premium.
    """
    # Try real DB data first
    real_g1 = None
    try:
        from meta_bridge import get_real_matchup
        real_g1 = get_real_matchup(our_deck, opp_name, format_name, min_matches=20)
    except Exception:
        pass

    if real_g1 is None:
        from engine.match_runner import run_match_set
        from generate_matchup_data import load_deck_and_apl

        our_main, _, our_apl = load_deck_and_apl(our_deck, format_name)
        opp_main, _, opp_apl = load_deck_and_apl(opp_name, format_name)

        if not our_main or not opp_main:
            raise ValueError(f"Could not load deck for {opp_name}")

        r = run_match_set(our_apl, our_main, opp_apl, opp_main,
                          n=n, seed=seed, mix_play_draw=True)
        real_g1 = r.win_pct()

        # Credibility caps for SIM results where stubs lack real interaction
        opp_lower = opp_name.lower()
        if real_g1 > 75 and any(k in opp_lower for k in INTERACTIVE):
            real_g1 = min(real_g1, 65.0)
            result["g1_capped"] = True

        our_lower = our_deck.lower()
        if real_g1 < 25 and any(k in our_lower for k in AGGRO_OUR):
            real_g1 = max(real_g1, 25.0)
            result["g1_floored"] = True

        result["g1_source"] = "sim"
    else:
        result["g1_source"] = "db"

    sb  = _get_sb_premium(our_deck, opp_name, format_name)
    g2  = min(98.0, real_g1 + sb)
    g3  = min(98.0, real_g1 + sb * 0.75)
    result.update({"g1": real_g1, "g2": round(g2,1), "g3": round(g3,1),
                   "match": bo3_win(real_g1, g2, g3)})


def main():
    our_deck    = sys.argv[1]
    opp_name    = sys.argv[2]
    field_pct   = float(sys.argv[3])
    n           = int(sys.argv[4])
    seed        = int(sys.argv[5])
    format_name = sys.argv[6]
    mtype       = sys.argv[7]

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
        print(f"OK  [{result.get('g1_source','?').upper()}] {opp_name}: "
              f"G1={result['g1']:.1f}%  Match={result['match']:.1f}%  "
              f"({result['elapsed']}s)")

    except Exception as e:
        import traceback
        result["error"]   = str(e)
        result["elapsed"] = round(time.time() - t0, 1)
        traceback.print_exc(file=sys.stderr)
        print(f"ERR {opp_name}: {e}")

    with open(out_path, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
