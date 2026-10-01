"""Best-of-three validation (milestone two, phase 5): Burn mirror matches with a supported test
sideboard, seeded random match decisions (play/draw, staged sideboard swaps), invariants ON,
every match replayed exactly through JSON, repeated seeds compared.

  python scripts/v2_bo3_validation.py --matches 500 --workers 20
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SIDE = ["Lightning Helix", "Lightning Helix", "Skullcrack", "Skullcrack"]   # supported cards (the real
                                                                           # sideboard's cards are not)


class MatchRandom:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.n = 0

    def choose_match(self, m, acts):
        from engine.v2.match import ChoosePlayDraw, DoneSideboarding, SideboardSwap
        if isinstance(acts[0], ChoosePlayDraw):
            self.n = 0
            return self.rng.choice(acts)
        swaps = [a for a in acts if isinstance(a, SideboardSwap)]
        if swaps and self.n < 3 and self.rng.random() < 0.6:
            self.n += 1
            return self.rng.choice(swaps)
        self.n = 0
        return next(a for a in acts if isinstance(a, DoneSideboarding))


def one(seed):
    from engine.v2.decklists import main_deck
    from engine.v2.match import Match, make_match_record, replay_match
    from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy
    burn = main_deck("mono_red_aggro_modern")
    try:
        m = Match(burn, SIDE, burn, SIDE, 2_000_000 + seed, check_invariants=True)
        pols = [SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)] if seed % 3 == 0 else \
            [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)] if seed % 3 == 1 else \
            [SimpleAggroPolicy(seed), RandomLegalPolicy(seed + 1)]
        res = m.run(pols, [MatchRandom(seed), MatchRandom(seed + 99)])
        rec = make_match_record(m)
        replay_match(json.loads(json.dumps(rec)))
        swaps = sum(1 for a in m.actions if type(a).__name__ == "SideboardSwap")
        return {"seed": seed, "result": list(res), "games": len(m.games), "swaps": swaps,
                "draws": sum(1 for g in m.games if g.result[0] == "draw"),
                "starting": list(m.starting), "match_hash": rec["match_hash"]}
    except Exception as e:                                           # noqa: BLE001
        return {"seed": seed, "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", type=int, default=500)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--repeat", type=int, default=50)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "v2_bo3_validation.json"))
    args = ap.parse_args()
    t0 = time.time()
    with ProcessPoolExecutor(args.workers) as ex:
        res = list(ex.map(one, range(args.matches), chunksize=5))
        again = list(ex.map(one, range(args.repeat), chunksize=5))
    errs = [r for r in res if "error" in r]
    ok = [r for r in res if "error" not in r]
    first = {r["seed"]: r for r in ok}
    report = {
        "matches": len(res), "errors": len(errs), "first_errors": errs[:3],
        "replayed_exactly": len(ok),
        "results": dict(collections.Counter(f"{r['result'][0]}:{r['result'][1]}" for r in ok)),
        "games_per_match": dict(collections.Counter(r["games"] for r in ok)),
        "matches_with_sideboard_swaps": sum(1 for r in ok if r["swaps"]),
        "total_swaps": sum(r["swaps"] for r in ok),
        "drawn_games": sum(r["draws"] for r in ok),
        "repeat_identical": sum(1 for r in again if "error" not in r and r["match_hash"] == first[r["seed"]]["match_hash"]),
        "repeat_compared": len(again),
        "wall_seconds": round(time.time() - t0, 1),
    }
    json.dump(report, open(args.out, "w"), indent=1)
    print(json.dumps(report, indent=1)[:4000])


if __name__ == "__main__":
    main()
