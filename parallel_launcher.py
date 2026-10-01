"""
parallel_launcher.py — Launch all matchups as independent subprocesses

Format-agnostic. Works for Legacy, Modern, Pioneer, Standard.

Subprocess output layout: data/matchup_jobs/<our_deck_slug>/<opp_slug>.json
Keyed on (our_deck, opp); see matchup_jobs.matchup_job_path. Prior layout
keyed on opp only and clobbered between concurrent variant + canonical
runs (cache-collision-bug-2026-04-27.md).

Usage:
    python parallel_launcher.py --deck "Legacy Humans"   --format legacy
    python parallel_launcher.py --deck "Boros Energy"    --format modern
    python parallel_launcher.py --deck "Boros Heroic"    --format pioneer
    python parallel_launcher.py --deck "Mono Red Aggro"  --format standard
    python parallel_launcher.py --deck "Boros Energy"    --format modern --n 5000
"""
import sys, os, json, time, subprocess, argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from matchup_jobs import matchup_job_path
os.makedirs("data/matchup_jobs", exist_ok=True)
os.makedirs("logs", exist_ok=True)


def launch_all(our_deck, format_name, field, n, cores, seed, inner_workers=1):
    from format_config import is_combo

    tasks = []
    for i, (opp, pct) in enumerate(field.items()):
        if opp.lower() == our_deck.lower():
            continue
        tasks.append({
            "opp": opp, "pct": pct,
            "seed": seed + i * 1000,
            "combo": is_combo(opp, format_name),
            "idx": i,
        })

    total   = len(tasks)
    n_cores = min(cores, total)

    print(f"\nParallel launcher: {our_deck} vs {format_name.upper()} field")
    print(f"Matchups: {total}  |  Games each: {n:,}  |  Cores: {n_cores}")
    print(f"{'-'*65}")

    t0      = time.time()
    running = {}
    pending = list(tasks)
    done    = []

    while pending or running:
        while pending and len(running) < n_cores:
            task = pending.pop(0)
            opp  = task["opp"]
            safe = opp.lower().replace(" ", "_").replace("'", "")
            log_path = f"logs/{safe}.log"
            cmd = [
                sys.executable, "run_matchup.py",
                our_deck,
                opp,
                str(task["pct"]),
                str(n),
                str(task["seed"]),
                format_name,
                "combo" if task["combo"] else "fair",
                str(inner_workers),
            ]
            log_f = open(log_path, "w", encoding="utf-8")
            proc  = subprocess.Popen(
                cmd, stdout=log_f, stderr=log_f,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            running[opp] = (proc, log_f, task)
            print(f"  >> [{len(done)+len(running)}/{total}] {opp} ({'combo' if task['combo'] else 'fair'})")

        finished = []
        for opp, (proc, log_f, task) in running.items():
            if proc.poll() is not None:
                log_f.close()
                finished.append(opp)
                out_path = matchup_job_path(our_deck, opp)
                if out_path.exists():
                    with open(out_path) as f:
                        r = json.load(f)
                    done.append(r)
                    status  = "ERR" if r.get("error") else "OK "
                    elapsed = r.get("elapsed", 0)
                    g1      = r.get("g1", 0)
                    match   = r.get("match", 0)
                    print(f"  {status} [{len(done)}/{total}] {opp}: "
                          f"G1={g1:.1f}%  Match={match:.1f}%  ({elapsed}s)")
                else:
                    print(f"  ERR [{len(done)+1}/{total}] {opp}: no output file")
                    done.append({"opp": opp, "field_pct": task["pct"],
                                 "error": "no output", "g1": 0, "match": 0})

        for opp in finished:
            del running[opp]

        if running:
            time.sleep(1)

    elapsed = time.time() - t0

    # Summary table
    print(f"\n{'-'*70}")
    print(f"{'Opponent':<28} {'Field%':>6}  {'G1':>6}  {'G2':>6}  {'Match':>7}  Type")
    print(f"{'-'*70}")

    total_w = weighted = 0
    for r in sorted(done, key=lambda x: -x.get("field_pct", 0)):
        if r.get("error"):
            print(f"  {'ERROR':<26} {r['field_pct']:>5.1f}%  — {r['error'][:35]}")
            continue
        fp    = r["field_pct"]
        g1    = r.get("g1", 0)
        g2    = r.get("g2", 0)
        match = r.get("match", 0)
        mtype = r.get("type", "?")
        print(f"  {r['opp']:<26} {fp:>5.1f}%  {g1:>5.1f}%  {g2:>5.1f}%  "
              f"{match:>6.1f}%  {mtype}")
        weighted += match * fp
        total_w  += fp

    print(f"{'-'*70}")
    fw = weighted / total_w if total_w else 0
    # Wilson 95% band on the FWR (effective N = total games behind the
    # weighted rate). Appended AFTER the pct so arl_loop.FWR_RE still parses.
    from engine.stats_util import wilson_bounds_pct
    n_eff = n * sum(1 for r in done if not r.get("error"))
    fw_lo, fw_hi = wilson_bounds_pct(fw, n_eff)
    print(f"  Field-weighted match win%: {fw:.1f}% [{fw_lo:.1f}–{fw_hi:.1f}]")
    # Spec harness/specs/2026-09-30-strict-mode.md: legacy engine output is experimental;
    # coverage = share of the field that produced a result (errors are excluded above).
    from engine.strict import is_strict
    strict = is_strict()
    field_total = sum(t["pct"] for t in tasks)
    coverage = 100.0 * total_w / field_total if field_total else 0.0
    print(f"  Engine: legacy match_engine (EXPERIMENTAL)  |  strict={strict}  |  "
          f"coverage {coverage:.1f}% of field share ({sum(1 for r in done if r.get('error'))} errors)")
    print(f"  Total: {elapsed:.0f}s  |  {n * total:,} games  |  {n_cores} cores")

    # Save
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"data/parallel_results_{ts}.json"
    with open(out, "w") as f:
        json.dump({
            "our_deck": our_deck, "format": format_name,
            "field_weighted_match": round(fw, 1),
            "field_weighted_match_lo": round(fw_lo, 1),
            "field_weighted_match_hi": round(fw_hi, 1),
            "elapsed_s": round(elapsed, 1),
            "n_per_matchup": n, "results": done,
            "engine_status": "legacy-experimental", "strict": strict,
            "coverage_pct": round(coverage, 1),
        }, f, indent=2)
    print(f"  Saved: {out}")

    if strict:
        return done       # strict runs are partial by design; keep the default matrix rows
    # Update matchup matrix (concurrency-safe RMW; see engine/atomic_json.py)
    from engine.atomic_json import atomic_rmw_json
    matrix_path = "data/sim_matchup_matrix.json"
    key = f"{our_deck} ({format_name})"
    new_row = {r["opp"]: r.get("g1", 0) for r in done if not r.get("error")}
    atomic_rmw_json(
        matrix_path,
        lambda matrix: matrix.update({key: new_row}),
        default_factory=dict,
    )

    return done


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",          default="Legacy Humans")
    ap.add_argument("--format",        default="legacy")
    ap.add_argument("--n",             type=int, default=1000)
    ap.add_argument("--cores",         type=int, default=20)
    ap.add_argument("--top-n",         type=int, default=20)
    ap.add_argument("--seed",          type=int, default=42)
    ap.add_argument("--inner-workers", type=int, default=1,
                    help="Per-matchup parallel game workers (default 1 = sequential)")
    ap.add_argument("--strict", action="store_true",
                    help="Strict simulation mode (MTG_SIM_STRICT=1): no fallback, floor, real-data "
                         "substitution or unsupported cards -- such cells error instead")
    # Engine selection (default unchanged: the legacy engines). v2 is EXPERIMENTAL and opt-in only.
    ap.add_argument("--engine", choices=("legacy", "v2"), default="legacy",
                    help="legacy (default) or v2 (EXPERIMENTAL rules engine; explicit decks, no field)")
    v2 = ap.add_argument_group("engine v2 (only with --engine v2)")
    v2.add_argument("--opponent", help="v2: opponent deck file stem (decks/<name>.txt)")
    v2.add_argument("--mode", choices=("game", "bo3"), default="game", help="v2: single games or best-of-three")
    v2.add_argument("--games", type=int, default=1, help="v2 game mode: number of games (seeds seed..seed+N-1)")
    v2.add_argument("--matches", type=int, default=1, help="v2 bo3 mode: number of matches")
    v2.add_argument("--pilot-a", choices=("random", "aggro", "scripted"), default="random",
                    help="v2: player (pilot) for --deck -- independent of the engine choice")
    v2.add_argument("--pilot-b", choices=("random", "aggro", "scripted"), default="random",
                    help="v2: player (pilot) for --opponent")
    v2.add_argument("--side-a", default="file", help="v2 bo3: sideboard of --deck: file | none | <deck stem>")
    v2.add_argument("--side-b", default="file", help="v2 bo3: sideboard of --opponent: file | none | <deck stem>")
    v2.add_argument("--turn-limit", type=int, default=50, help="v2: turn limit (a turn-limit draw is reported apart)")
    v2.add_argument("--record-dir", default=None, help="v2: where to save records (default data/v2_runs/<run>)")
    v2.add_argument("--replay", default=None, help="v2: replay a saved game/match record and verify it")
    v2.add_argument("--no-invariants", dest="invariants", action="store_false",
                    help="v2: skip per-transition invariant checks (on by default)")
    return ap


def main(argv=None):
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw_argv)
    if args.engine == "v2":
        # Explicit selection only; never a fallback in either direction.
        args.deck_explicit = any(x == "--deck" or x.startswith("--deck=") for x in raw_argv)
        import v2_launch
        return v2_launch.run(args)
    if args.strict:
        os.environ["MTG_SIM_STRICT"] = "1"

    from format_config import get_field
    field = get_field(args.format, args.top_n)
    launch_all(args.deck, args.format, field, args.n, args.cores, args.seed,
               inner_workers=args.inner_workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
