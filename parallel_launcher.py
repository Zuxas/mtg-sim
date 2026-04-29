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


def launch_all(our_deck, format_name, field, n, cores, seed):
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
    print(f"  Field-weighted match win%: {fw:.1f}%")
    print(f"  Total: {elapsed:.0f}s  |  {n * total:,} games  |  {n_cores} cores")

    # Save
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"data/parallel_results_{ts}.json"
    with open(out, "w") as f:
        json.dump({
            "our_deck": our_deck, "format": format_name,
            "field_weighted_match": round(fw, 1),
            "elapsed_s": round(elapsed, 1),
            "n_per_matchup": n, "results": done,
        }, f, indent=2)
    print(f"  Saved: {out}")

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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",   default="Legacy Humans")
    ap.add_argument("--format", default="legacy")
    ap.add_argument("--n",      type=int, default=1000)
    ap.add_argument("--cores",  type=int, default=20)
    ap.add_argument("--top-n",  type=int, default=20)
    ap.add_argument("--seed",   type=int, default=42)
    args = ap.parse_args()

    from format_config import get_field
    field = get_field(args.format, args.top_n)
    launch_all(args.deck, args.format, field, args.n, args.cores, args.seed)
