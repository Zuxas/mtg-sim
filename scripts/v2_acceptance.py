"""Engine v2 milestone-one acceptance runs: M2 (fuzz), M3 (replay), M4 (scripted), M7 (speed).

usage: python scripts/v2_acceptance.py [--games 10000] [--scripted 1000] [--workers 20] [--out path.json]
Spec harness/specs/2026-09-30-rules-engine-v2-design.md section 12.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from collections import Counter
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _fuzz_one(seed: int) -> dict:
    from engine.v2.game import Game
    from engine.v2.policies import RandomLegalPolicy
    from engine.v2.record import make_record, replay
    from tests.v2.decks import RG, WU
    out = {"seed": seed}
    try:
        g = Game.new(RG, WU, seed, starting_player=seed % 2, check_invariants=True, deck_rules="test")
        ps = (10_000 + seed, 20_000 + seed)
        g.run([RandomLegalPolicy(ps[0]), RandomLegalPolicy(ps[1])])
        out.update(result=list(g.result), actions=len(g.actions), transitions=len(g.s.log.transitions),
                   turns=g.s.turn)
        rec = make_record(g, policy_seeds=ps)
        try:
            replay(rec)
            out["replay"] = "ok"
            if seed < 100:                                  # M3 extra: replay ignores policy seeds entirely
                rec2 = dict(rec, policy_seeds=[random.Random(seed).randrange(10**9) for _ in ps])
                replay(rec2)
                out["replay_reseeded"] = "ok"
        except Exception as e:                              # noqa: BLE001
            out["replay"] = f"{type(e).__name__}: {e}"
    except Exception as e:                                  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
        out["trace"] = traceback.format_exc()[-1500:]
    return out


def _scripted_one(seed: int) -> dict:
    from engine.v2.game import Game
    from engine.v2.policies import BasicScriptedPolicy
    from tests.v2.decks import RG, WU
    try:
        g = Game.new(RG, WU, seed, starting_player=seed % 2, check_invariants=True, deck_rules="test")
        g.run([BasicScriptedPolicy(seed), BasicScriptedPolicy(seed + 1)])
        return {"seed": seed, "result": list(g.result), "turns": g.s.turn, "actions": len(g.actions)}
    except Exception as e:                                  # noqa: BLE001
        return {"seed": seed, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}


def _speed(n: int) -> dict:
    from engine.v2.game import Game
    from engine.v2.policies import RandomLegalPolicy
    from tests.v2.decks import RG, WU
    Game.new(RG, WU, 0, deck_rules="test")                  # warm-up: card data loaded once
    t0, c0 = time.perf_counter(), time.process_time()
    actions = 0
    for seed in range(n):
        g = Game.new(RG, WU, 50_000 + seed, starting_player=seed % 2, check_invariants=False, deck_rules="test")
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 7)])
        actions += len(g.actions)
    dt, dc = time.perf_counter() - t0, time.process_time() - c0
    return {"games": n, "wall_seconds": round(dt, 2), "games_per_s_wall": round(n / dt, 2),
            "cpu_seconds": round(dc, 2), "games_per_s_cpu": round(n / dc, 2),
            "actions_per_s_cpu": round(actions / dc), "mean_actions": round(actions / n),
            "note": "single core, random policies, invariants off, card data pre-loaded; target 200, blocker < 20"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10_000)
    ap.add_argument("--scripted", type=int, default=1_000)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--speed", type=int, default=200)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "v2_acceptance.json"))
    a = ap.parse_args()
    report = {}
    t0 = time.time()
    with Pool(a.workers) as pool:
        fuzz = pool.map(_fuzz_one, range(a.games), chunksize=25)
        scripted = pool.map(_scripted_one, range(a.scripted), chunksize=10)
    errs = [r for r in fuzz if "error" in r]
    replay_bad = [r for r in fuzz if "error" not in r and r.get("replay") != "ok"]
    reseeded = [r for r in fuzz if "replay_reseeded" in r]
    report["M2"] = {"games": len(fuzz), "exceptions_or_invariant_violations": len(errs),
                    "first_errors": errs[:3],
                    "results": Counter(f"{r['result'][0]}:{r['result'][-1]}" for r in fuzz if "result" in r),
                    "mean_actions": round(sum(r.get("actions", 0) for r in fuzz) / max(1, len(fuzz))),
                    "max_turns": max((r.get("turns", 0) for r in fuzz), default=0)}
    report["M3"] = {"replayed": sum(1 for r in fuzz if "replay" in r), "mismatches": len(replay_bad),
                    "first_mismatches": replay_bad[:3], "reseeded_policy_replays_ok": len(reseeded)}
    serr = [r for r in scripted if "error" in r]
    won = Counter(f"{r['result'][0]}:{r['result'][1] if r['result'][0] == 'win' else '-'}:{r['result'][-1]}"
                  for r in scripted if "result" in r)
    report["M4"] = {"games": len(scripted), "errors": len(serr), "first_errors": serr[:3], "outcomes": won,
                    "mean_turns": round(sum(r.get("turns", 0) for r in scripted) / max(1, len(scripted)), 2)}
    report["M7"] = _speed(a.speed)
    report["wall_seconds"] = round(time.time() - t0, 1)
    json.dump(report, open(a.out, "w"), indent=1, default=str)
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()
