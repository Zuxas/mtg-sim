"""
parallel_launcher.py — Launch all matchups as independent subprocesses

No Pool, no spawn bootstrapping issues.
Each matchup is a fully isolated python process.
All processes start simultaneously, results collected when they finish.

Usage:
    python parallel_launcher.py               # full Legacy field, 1000 games
    python parallel_launcher.py --n 2000      # higher sample
    python parallel_launcher.py --cores 12    # limit concurrency
"""
import sys, os, json, time, subprocess, argparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("data/matchup_jobs", exist_ok=True)
os.makedirs("logs", exist_ok=True)

COMBO = {
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


def launch_all(field, n, cores, seed, format_name, our_deck):
    tasks = []
    for i, (opp, pct) in enumerate(field.items()):
        mtype = "combo" if opp.lower() in COMBO else "fair"
        tasks.append({
            "opp": opp, "pct": pct, "seed": seed + i * 1000,
            "type": mtype, "idx": i,
        })

    total   = len(tasks)
    n_cores = min(cores, total)

    print(f"\nParallel launcher: {total} matchups × {n:,} games")
    print(f"Concurrency: {n_cores} processes")
    print(f"Each process is independent — no Pool issues")
    print(f"{'─'*60}")

    t0       = time.time()
    running  = {}   # {opp: proc}
    pending  = list(tasks)
    done     = []

    while pending or running:
        # Start new processes up to concurrency limit
        while pending and len(running) < n_cores:
            task = pending.pop(0)
            opp  = task["opp"]
            safe = opp.lower().replace(" ","_").replace("'","")
            log_path = f"logs/{safe}.log"
            cmd = [
                sys.executable, "run_matchup.py",
                opp, str(task["pct"]), str(n),
                str(task["seed"]), format_name, task["type"],
            ]
            log_f = open(log_path, "w")
            proc  = subprocess.Popen(cmd, stdout=log_f, stderr=log_f,
                                      cwd=os.path.dirname(os.path.abspath(__file__)),
                                      env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            running[opp] = (proc, log_f, task)
            print(f"  >> Started: {opp} ({task['type']})")

        # Poll running processes
        finished_this_round = []
        for opp, (proc, log_f, task) in running.items():
            if proc.poll() is not None:
                log_f.close()
                finished_this_round.append(opp)
                safe = opp.lower().replace(" ","_").replace("'","")
                result_path = f"data/matchup_jobs/{safe}.json"
                if os.path.exists(result_path):
                    with open(result_path) as f:
                        r = json.load(f)
                    done.append(r)
                    status = "ERR" if r.get("error") else "OK "
                    g1 = r.get("g1", 0); match = r.get("match", 0)
                    elapsed = r.get("elapsed", 0)
                    print(f"  {status} [{len(done)}/{total}] {opp}: "
                          f"G1={g1:.1f}%  Match={match:.1f}%  ({elapsed}s)")
                else:
                    print(f"  ERR [{len(done)+1}/{total}] {opp}: no output file")
                    done.append({"opp": opp, "field_pct": task["pct"],
                                 "error": "no output", "g1": 0, "match": 0})

        for opp in finished_this_round:
            del running[opp]

        if running:
            time.sleep(1)

    elapsed = time.time() - t0

    # Summary
    print(f"\n{'─'*60}")
    print(f"{'Opponent':<28} {'Field%':>6}  {'G1':>6}  {'G2':>6}  {'Match':>7}  Type")
    print(f"{'─'*60}")

    total_w = weighted = 0
    for r in sorted(done, key=lambda x: -x.get("field_pct", 0)):
        if r.get("error"):
            print(f"  {'ERROR':<26} {r['field_pct']:>5.1f}%  — {r['error'][:30]}")
            continue
        fp = r["field_pct"]
        print(f"  {r['opp']:<26} {fp:>5.1f}%  "
              f"{r.get('g1',0):>5.1f}%  {r.get('g2',0):>5.1f}%  "
              f"{r.get('match',0):>6.1f}%  {r.get('type','?')}")
        weighted += r.get("match", 0) * fp
        total_w  += fp

    print(f"{'─'*60}")
    if total_w:
        fw = weighted / total_w
        print(f"  Field-weighted match win%: {fw:.1f}%")
    print(f"  Total time: {elapsed:.0f}s  ({n * total:,} games across {n_cores} cores)")

    # Save results
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"data/parallel_results_{ts}.json"
    with open(out, "w") as f:
        json.dump({"field_weighted_match": round(weighted/total_w, 1) if total_w else 0,
                   "elapsed_s": round(elapsed, 1), "n_per_matchup": n,
                   "results": done}, f, indent=2)
    print(f"  Saved: {out}")

    # Update sim matrix
    matrix_path = "data/sim_matchup_matrix.json"
    matrix = {}
    if os.path.exists(matrix_path):
        with open(matrix_path) as f:
            matrix = json.load(f)
    matrix[our_deck] = {r["opp"]: r.get("g1", 0) for r in done if not r.get("error")}
    with open(matrix_path, "w") as f:
        json.dump(matrix, f, indent=2)

    return done


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",   default="Legacy Humans")
    ap.add_argument("--format", default="legacy")
    ap.add_argument("--n",      type=int, default=1000)
    ap.add_argument("--cores",  type=int, default=20)
    ap.add_argument("--seed",   type=int, default=42)
    args = ap.parse_args()

    launch_all(
        field=LEGACY_FIELD, n=args.n,
        cores=args.cores, seed=args.seed,
        format_name=args.format, our_deck=args.deck,
    )
