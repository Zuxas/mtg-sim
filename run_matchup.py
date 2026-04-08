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
      G1  : 2d6 roll, highest wins, ties reroll → exactly 50/50 play/draw
      Win game N  → opponent LOST → opponent CHOOSES next game → picks play
                    → YOU are on DRAW for game N+1
      Lose game N → YOU LOST    → YOU CHOOSE next game          → you pick play
                    → YOU are on PLAY for game N+1
      Each match: fresh 60-card main + 15-card SB, no carry-over between rounds.

    Parameters (all as percentages, 0-100):
      g1             : our avg G1 win rate (50/50 play/draw embedded — dice roll)
      g2             : our avg G2 win rate WITH SB (50/50 play/draw embedded)
      g3             : our avg G3 win rate WITH SB (default = g2)
      play_advantage : play vs draw edge in % (default 3%). Derives:
                         on_play  = avg + PADV/2
                         on_draw  = avg - PADV/2

    Returns: match win % (0-100)
    """
    PADV = play_advantage / 2   # half applied each side of the split

    def split(avg):
        return (min(99.0, avg + PADV) / 100,   # on play
                max( 1.0, avg - PADV) / 100)   # on draw

    g1p, g1d = split(g1)
    g2p, g2d = split(g2)
    g3_val   = g3 if g3 is not None else g2
    g3p, g3d = split(g3_val)

    match = 0.0
    for g1_wr, weight in [(g1p, 0.5), (g1d, 0.5)]:
        # WIN G1 → they lost → they choose G2 → they pick play → WE ON DRAW G2
        win_g2  = g1_wr * g2d                        # 2-0
        win_g2_lose_g3  = g1_wr * (1-g2d) * g3p     # we lost G2 → we choose G3 → ON PLAY

        # LOSE G1 → we lost → we choose G2 → we pick play → WE ON PLAY G2
        lose_win_g2 = (1-g1_wr) * g2p
        lose_win_g2_win_g3 = lose_win_g2 * g3d      # they lost G2 → they choose G3 → WE ON DRAW

        match += weight * (win_g2 + win_g2_lose_g3 + lose_win_g2_win_g3)

    return round(match * 100, 1)


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
    """
    Combo matchup: G1 from ComboKillSampler (mainboard race),
    G2/G3 from our APL's sideboard_premium (SB hate changes the calculus).

    G1: can we kill them before they go off? (goldfish kill vs combo kill turn)
    G2/G3: with hate pieces, their effective kill turn shifts later — we apply
           our deck's specific SB premium rather than the combo model's G2/G3
           (which doesn't know our SB plan and produces unreliable G3 estimates).
    """
    from engine.combo_model import run_combo_matchup

    our_deck = result.get("our_deck", "Legacy Humans")

    # G1 from the combo kill-turn sampler (mainboard race, no hate)
    g1_data = run_combo_matchup(opp_name, n=n, game=1, seed=seed)
    g1      = g1_data["win_pct"]

    # G2/G3: deck-specific SB premium
    sb_premium = 6.0
    try:
        from generate_matchup_data import load_deck_and_apl
        _, _, our_apl = load_deck_and_apl(our_deck, format_name)
        if our_apl and hasattr(our_apl, 'sideboard_premium'):
            sb_premium = our_apl.sideboard_premium(opp_name, format_name)
    except Exception:
        pass

    g2 = min(98.0, g1 + sb_premium)
    g3 = min(98.0, g1 + sb_premium * 0.75)   # G3: slightly diluted (both sides adjusted)

    match = bo3_win(g1, g2, g3)
    result.update({
        "g1":        g1,
        "g2":        round(g2, 1),
        "g3":        round(g3, 1),
        "match":     match,
        "avg_turns": g1_data.get("avg_turns", 0),
        "hard_stop": g1_data.get("hard_stop_rate", 0),
        "g1_source": "com",
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

        # G1: opponent-aware mulligan via keep_vs
        if hasattr(our_apl, 'keep_vs'):
            our_apl._opp_for_mull = opp_name   # picked up by mulligan.py
        r = run_match_set(our_apl, our_main, opp_apl, opp_main,
                          n=n, seed=seed, mix_play_draw=True)
        real_g1 = r.win_pct()

        # Credibility cap for interactive decks the stub can't model properly
        INTERACTIVE = {"thoughtseize","midrange","control","murktide","frog",
                       "rakdos","jund","esper","dimir","grixis"}
        if real_g1 > 75 and any(k in opp_name.lower() for k in INTERACTIVE):
            real_g1 = min(real_g1, 65.0)
            result["g1_capped"] = True
        AGGRO_OUR = {"aggro","prowess","burn","swiftspear","mono red","gruul"}
        if real_g1 < 25 and any(k in our_deck.lower() for k in AGGRO_OUR):
            real_g1 = max(real_g1, 25.0)
            result["g1_floored"] = True

        result["g1_source"] = "sim"
    else:
        result["g1_source"] = "db"

    # ── G2/G3: deck-specific SB premium ──────────────────────────────────
    # Load our APL to ask it for the matchup-specific SB premium.
    # This replaces the crude kill-speed formula.
    sb_premium = 6.0   # default fallback
    try:
        from generate_matchup_data import load_deck_and_apl
        _, _, our_apl_for_sb = load_deck_and_apl(our_deck, format_name)
        if our_apl_for_sb and hasattr(our_apl_for_sb, 'sideboard_premium'):
            sb_premium = our_apl_for_sb.sideboard_premium(opp_name, format_name)
    except Exception:
        pass

    g2_wp = min(98.0, real_g1 + sb_premium)
    g3_wp = min(98.0, real_g1 + sb_premium * 0.75)   # G3: SB value slightly diluted

    match = bo3_win(real_g1, g2_wp, g3_wp)
    result.update({
        "g1": real_g1, "g2": round(g2_wp, 1), "g3": round(g3_wp, 1),
        "match": match, "avg_turns": 0.0, "hard_stop": 0.0,
    })


if __name__ == "__main__":
    main()
