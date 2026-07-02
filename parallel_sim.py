"""
parallel_sim.py — Parallel simulation runner using all available CPU cores

Splits matchup simulations across all cores simultaneously.
24 cores → 24 matchups at once instead of sequential.
~20x speedup on a 24-core machine.

Usage:
    python parallel_sim.py                    # full Legacy field, 1000 games each
    python parallel_sim.py --n 5000           # higher sample count
    python parallel_sim.py --format modern    # Modern field
    python parallel_sim.py --cores 12         # limit core count
"""

import sys, os, json, time, argparse
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Worker function — runs in a separate process
# Each worker handles one matchup independently
# ---------------------------------------------------------------------------

def _worker(task: dict) -> dict:
    """
    Worker process: simulate one matchup and return results.
    Called by multiprocessing.Pool — must be importable at module level.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    our_deck   = task["our_deck"]
    opp_name   = task["opp_name"]
    field_pct  = task["field_pct"]
    n          = task["n"]
    seed       = task["seed"]
    format_name = task["format_name"]
    use_combo  = task["use_combo"]

    try:
        if use_combo:
            # Combo matchup: use hand-aware interaction model
            from engine.combo_model import run_combo_matchup
            g1 = run_combo_matchup(opp_name, n=n, game=1, seed=seed)
            g2 = run_combo_matchup(opp_name, n=n, game=2, seed=seed+1)
            match = round(g1["win_pct"] / 3 + g2["win_pct"] * 2 / 3, 1)
            return {
                "opp":       opp_name,
                "field_pct": field_pct,
                "g1":        g1["win_pct"],
                "g2":        g2["win_pct"],
                "match":     match,
                "avg_turns": g1["avg_turns"],
                "hard_stop": g1["hard_stop_rate"],
                "type":      "combo",
                "n":         n,
                "error":     None,
            }
        else:
            # Fair matchup: both-sides combat sim
            from engine.match_runner import run_match_set
            from generate_matchup_data import load_deck_and_apl

            our_main, _, our_apl  = load_deck_and_apl(our_deck, format_name)
            opp_main, _, opp_apl  = load_deck_and_apl(opp_name, format_name)

            if not our_main or not opp_main:
                return {"opp": opp_name, "field_pct": field_pct,
                        "error": "deck load failed", "type": "fair"}

            # G1
            r_g1 = run_match_set(our_apl, our_main, opp_apl, opp_main,
                                  n=n, seed=seed, mix_play_draw=True)
            # G2/G3 — sb premium approximation (no full sb sim yet)
            opp_key = opp_name.lower().replace(" ", "")
            from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn
            opp_dist = ARCHETYPE_CLOCKS.get(
                _infer_archetype_key(opp_name), ARCHETYPE_CLOCKS["unknown"])
            opp_avg = avg_kill_turn(opp_dist)
            sb = 6 if opp_avg <= 4 else (8 if opp_avg <= 5.5 else 11)
            g2_wp = min(99.0, r_g1.win_pct() + sb)
            match  = round(r_g1.win_pct() / 3 + g2_wp * 2 / 3, 1)

            return {
                "opp":       opp_name,
                "field_pct": field_pct,
                "g1":        r_g1.win_pct(),
                "g2":        round(g2_wp, 1),
                "match":     match,
                "avg_turns": round(r_g1.avg_turns, 1),
                "hard_stop": 0.0,
                "type":      "fair",
                "n":         n,
                "error":     None,
            }

    except Exception as e:
        return {"opp": opp_name, "field_pct": field_pct,
                "error": str(e), "type": "unknown"}


# ---------------------------------------------------------------------------
# Main parallel runner
# ---------------------------------------------------------------------------

COMBO_ARCHETYPES = {
    "dimir reanimator", "lotus combo", "cephalid breakfast",
    "sneak and show", "mono red painter", "doomsday", "bant nadu",
}

LEGACY_FIELD = {
    "Dimir Reanimator": 22.4, "Lotus Combo": 10.5, "Dimir Tempo": 10.5,
    "Cephalid Breakfast": 7.5, "Eldrazi Stompy": 6.4, "Sneak And Show": 5.4,
    "Mono Red Painter": 5.0, "Doomsday": 4.9, "Izzet Delver": 4.7,
    "Death And Taxes": 4.6, "Bant Nadu": 4.3, "Four-Color": 3.7,
    "Jeskai Control": 3.6, "Mono Red Aggro": 3.4, "Mono Red Prison": 3.2,
}


def run_parallel(
    our_deck:    str   = "Legacy Humans",
    format_name: str   = "legacy",
    field:       dict  = None,
    n:           int   = 1000,
    cores:       int   = None,
    seed:        int   = 42,
) -> list[dict]:

    if field is None:
        field = LEGACY_FIELD

    n_cores = cores or max(1, mp.cpu_count() - 2)  # leave 2 cores free

    # Build task list
    tasks = []
    for i, (opp, pct) in enumerate(field.items()):
        if opp.lower() == our_deck.lower():
            continue
        use_combo = opp.lower() in COMBO_ARCHETYPES
        tasks.append({
            "our_deck":    our_deck,
            "opp_name":    opp,
            "field_pct":   pct,
            "n":           n,
            "seed":        seed + i * 1000,
            "format_name": format_name,
            "use_combo":   use_combo,
        })

    print(f"\nParallel sim: {len(tasks)} matchups × {n} games")
    print(f"Cores: {n_cores} / {mp.cpu_count()} available")
    print(f"Expected time: ~{max(1, len(tasks) // n_cores * 2)}-{max(2, len(tasks) // n_cores * 5)} minutes")
    print(f"{'─'*65}")

    t0 = time.time()
    results = []
    completed = 0

    with ProcessPoolExecutor(max_workers=n_cores) as executor:
        futures = {executor.submit(_worker, t): t for t in tasks}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            completed += 1
            if r.get("error"):
                print(f"  [{completed}/{len(tasks)}] {r['opp']}: ERROR")
            else:
                print(f"  [{completed}/{len(tasks)}] {r['opp']}: "
                      f"G1={r['g1']:.1f}%  Match={r['match']:.1f}%")

    elapsed = time.time() - t0

    # Print results
    print(f"\n{'Opponent':<28} {'Field%':>6}  {'G1':>6}  {'G2':>6}  {'Match':>7}  Type")
    print("─" * 65)

    total_w = weighted_match = 0
    for r in sorted(results, key=lambda x: -x.get("field_pct", 0)):
        if r.get("error"):
            print(f"  {r['opp']:<26} ERROR: {r['error']}")
            continue
        fp = r["field_pct"]
        print(f"  {r['opp']:<26} {fp:>5.1f}%  "
              f"{r['g1']:>5.1f}%  {r['g2']:>5.1f}%  "
              f"{r['match']:>6.1f}%  {r['type']}")
        weighted_match += r["match"] * fp
        total_w += fp

    print(f"{'─'*65}")
    # Wilson 95% band on the FWR (effective N = total games behind the
    # weighted rate). Appended AFTER the pct so arl_loop.FWR_RE still parses.
    from engine.stats_util import wilson_bounds_pct
    fw = weighted_match / total_w if total_w else 0
    n_eff = n * sum(1 for r in results if not r.get("error"))
    fw_lo, fw_hi = wilson_bounds_pct(fw, n_eff)
    if total_w > 0:
        print(f"  Field-weighted match win%: {fw:.1f}% [{fw_lo:.1f}–{fw_hi:.1f}]")
    print(f"  Time: {elapsed:.0f}s on {n_cores} cores  "
          f"({n * len(tasks):,} total games)")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = f"data/parallel_results_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump({
            "our_deck":   our_deck,
            "format":     format_name,
            "n_per_matchup": n,
            "cores":      n_cores,
            "elapsed_s":  round(elapsed, 1),
            "field_weighted_match": round(weighted_match / total_w, 1) if total_w else 0,
            "field_weighted_match_lo": round(fw_lo, 1),
            "field_weighted_match_hi": round(fw_hi, 1),
            "results":    results,
        }, f, indent=2)
    print(f"  Saved: {out_path}")

    # Update live matrix (concurrency-safe RMW; see engine/atomic_json.py)
    from engine.atomic_json import atomic_rmw_json
    matrix_path = "data/sim_matchup_matrix.json"
    new_row = {r["opp"]: r["g1"] for r in results if not r.get("error")}
    atomic_rmw_json(
        matrix_path,
        lambda matrix: matrix.update({our_deck: new_row}),
        default_factory=dict,
    )

    return results


if __name__ == "__main__":
    # Required for multiprocessing on Windows
    mp.freeze_support()

    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",   default="Legacy Humans")
    ap.add_argument("--format", default="legacy")
    ap.add_argument("--n",      type=int, default=1000)
    ap.add_argument("--cores",  type=int, default=None)
    ap.add_argument("--seed",   type=int, default=42)
    args = ap.parse_args()

    run_parallel(
        our_deck=args.deck,
        format_name=args.format,
        n=args.n,
        cores=args.cores,
        seed=args.seed,
    )
