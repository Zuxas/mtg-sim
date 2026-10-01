"""Milestone-two validation: the real Modern Burn mirror (decks/mono_red_aggro_modern.txt main deck,
60 cards, every card explicitly supported) played entirely through engine/v2.

  python scripts/v2_burn_validation.py --games 10000 --workers 20 --logs 4

Gates (pre-registered in harness/specs/2026-09-30-v2-m2-burn-mirror-proposal.md): 0 crashes,
0 invariant violations (invariants ON in every game), 0 unsupported-card fallbacks (the deck is
validated; an altered deck must be refused), 0 illegal actions accepted (probed every game),
0 dead ends, deterministic repeats, exact replay of a sample, explicit results (turn-limit
draws reported separately), throughput reported. Win rates are diagnostic only.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DECK = "mono_red_aggro_modern"
PAIRINGS = ("random_vs_random", "aggro_vs_aggro", "aggro_vs_random")


def _policies(kind, seed):
    from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy
    if kind == "random_vs_random":
        return [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)]
    if kind == "aggro_vs_aggro":
        return [SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)]
    return [SimpleAggroPolicy(seed), RandomLegalPolicy(seed + 1)] if seed % 2 else \
        [RandomLegalPolicy(seed), SimpleAggroPolicy(seed + 1)]


def play(seed, replay_it=False):
    from engine.v2 import actions as A
    from engine.v2.decklists import main_deck
    from engine.v2.game import Game, IllegalAction
    from engine.v2.record import make_record, replay
    burn = main_deck(DECK)
    kind = PAIRINGS[seed % 3]
    try:
        g = Game.new(burn, burn, 1_000_000 + seed, starting_player=seed % 2, check_invariants=True)
        pols = _policies(kind, seed)
        dead_ends = illegal_accepted = probes = 0
        stale = None
        while g.result is None:
            acts = g.legal_actions()
            if len(acts) == 1:                                       # only Concede: a dead end
                dead_ends += 1
                break
            if stale is not None and stale not in acts and len(g.actions) % 7 == 0:
                probes += 1
                try:
                    g.apply(stale)                                   # an action from an earlier decision
                    illegal_accepted += 1
                except IllegalAction:
                    pass
            p = g.pending().player
            pol = pols[p]
            obs = g.observe(p) if getattr(pol, "uses_observation", True) else None
            a = pol.choose(obs, acts)
            stale = a
            g.apply(a)
        res = {"seed": seed, "pairing": kind, "result": list(g.result) if g.result else None,
               "turns": g.s.turn, "actions": len(g.actions), "dead_ends": dead_ends,
               "illegal_accepted": illegal_accepted, "probes": probes,
               "head": g.s.log.head, "full": g.s.full_state_hash()}
        if replay_it:
            replay(json.loads(json.dumps(make_record(g))))           # through JSON, exact
            res["replayed"] = True
        res["events"] = dict(collections.Counter(e.kind for t in g.s.log.transitions for e in t.events))
        return res
    except Exception as e:                                           # noqa: BLE001
        return {"seed": seed, "pairing": kind, "error": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-2500:]}


def _batch(seeds, workers, replay_every):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(play, seeds, [s % replay_every == 0 for s in seeds], chunksize=25))


def render(g) -> str:
    """Readable log of a complete game (for manual inspection)."""
    s = g.s
    name = lambda ciid: s.instances[ciid].name                                    # noqa: E731
    ciid_of = {}
    for t in s.log.transitions:
        for e in t.events:
            d = dict(e.data)
            if e.kind == "ZoneChanged" and "new" in d:                   # moves into public zones only
                ciid_of[d["new"]] = d["ciid"]
            if e.kind == "SpellCast":
                ciid_of[d["oid"]] = d["ciid"]
    nm = lambda oid: name(ciid_of[oid]) if oid in ciid_of else f"#{oid}"         # noqa: E731
    lines = []
    for t in s.log.transitions:
        pregame = t.kind in ("setup_cards", "setup_draw", "mulligan_execute", "mulligan_commit",
                             "mulligan_declare", "mulligan_bottom_choice", "pending")
        if pregame and not any(e.kind == "TurnBegan" for e in t.events) and s.log.transitions.index(t) < 60:
            for e in t.events:
                d = dict(e.data)
                if e.kind == "MulliganDeclared":
                    lines.append(f"  P{d['player']} declares {d['choice']}")
                elif e.kind == "MulliganTaken":
                    lines.append(f"    P{d['player']} draws a new 7 (mulligan {d['count']}; bottoms {d['count']})")
            continue
        for e in t.events:
            d = dict(e.data)
            k = e.kind
            if k == "TurnBegan":
                lines.append(f"\n=== Turn {d['turn']} (P{d['active']}) ===")
            elif k == "Set" and d["attr"] == "step" and d["value"] in ("upkeep", "main1", "declare_attackers",
                                                                    "first_strike_damage", "combat_damage", "end"):
                lines.append(f"  -- {d['value']}")
            elif k == "ZoneChanged" and "ciid" in d and (d["frm"] != "library" or d["to"] == "battlefield"):
                lines.append(f"  {name(d['ciid'])}: {d['frm']} -> {d['to']}")
            elif k == "Drew":
                lines.append(f"  P{d['player']} draws")
            elif k in ("CastProposed",):
                lines.append(f"  P{d['controller']} casts {name(d['ciid'])} from {d['frm']} ({d['cost']} cost)")
            elif k == "ModeChosen":
                lines.append(f"    mode {d['mode']}")
            elif k == "TargetsChosen":
                lines.append(f"    targets {[(t[0], t[1] if t[0] != 'obj' else nm(t[1])) for t in d['targets']]}")
            elif k == "SpellCast":
                lines.append(f"    cast ({d['mana_spent']} mana spent)")
            elif k in ("SpellResolved", "SpellFizzled", "SpellCountered", "AbilityResolved", "AbilityRemoved",
                       "SearchFoundNothing", "SuspendDeclined", "Suspended"):
                lines.append(f"    {k}")
            elif k in ("Triggered",):
                lines.append(f"  trigger: {d['key']} (P{d['controller']}, from {nm(d['source'])})")
            elif k == "AbilityActivated":
                lines.append(f"  P{d['controller']} activates {d['key']} of {nm(d['source'])}")
            elif k in ("LifeChanged",):
                lines.append(f"    P{d['player']} life {d['life']} ({d['delta']:+d})")
            elif k == "DamageDealt" and d["target"][0] == "obj":
                lines.append(f"    {nm(d['source'])} deals {d['n']} to {nm(d['target'][1])}")
            elif k in ("AttackersDeclared",):
                lines.append(f"  attackers: {[nm(a) for a in d['attackers']]}")
            elif k in ("BlockersDeclared",):
                lines.append(f"  blocks: {[(nm(b), nm(a)) for b, a in d['blocks']]}")
            elif k in ("Destroyed", "Sacrificed", "Revealed", "EntersTapped", "LifePaid", "LifeGainPrevented",
                       "TurnEffectAdded", "CounterRemoved", "MulliganTaken", "Kept", "GameEnded", "PlayerLost"):
                lines.append(f"    {k} {d}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", type=int, default=60)
    ap.add_argument("--games", type=int, default=10_000)
    ap.add_argument("--small", type=int, default=1_000)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--repeat", type=int, default=200)
    ap.add_argument("--logs", type=int, default=4)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "v2_burn_validation.json"))
    args = ap.parse_args()
    from engine.v2.cards import UnsupportedCardError
    from engine.v2.decklists import main_deck
    report = {"deck": DECK}
    burn = main_deck(DECK)
    report["deck_cards"] = len(burn)
    report["unique_cards"] = sorted(set(burn))
    altered = burn[:-1] + ["Chalice of the Void"]                     # a sideboard card, unsupported
    from engine.v2.game import Game
    try:
        Game.new(altered, burn, 0)
        report["altered_deck_refused"] = False
    except UnsupportedCardError as e:
        report["altered_deck_refused"] = str(e)

    def summarize(results, label):
        errs = [r for r in results if "error" in r]
        ok = [r for r in results if "error" not in r]
        outcomes = collections.Counter("/".join(map(str, r["result"])) for r in ok if r["result"])
        by_pair = {p: collections.Counter(("draw" if r["result"][0] == "draw" else f"P{r['result'][1]}")
                                          for r in ok if r["pairing"] == p and r["result"]) for p in PAIRINGS}
        # aggro_vs_random: seat 0 is the aggro pilot when the seed is odd
        mixed = [r for r in ok if r["pairing"] == "aggro_vs_random" and r["result"] and r["result"][0] == "win"]
        by_pair["aggro_vs_random_pilot_wins"] = collections.Counter(
            ("aggro" if (r["result"][1] == 0) == (r["seed"] % 2 == 1) else "random") for r in mixed)
        ev = collections.Counter()
        for r in ok:
            ev.update(r["events"])
        return {"games": len(results), "errors": len(errs), "first_errors": errs[:3],
                "dead_ends": sum(r["dead_ends"] for r in ok),
                "illegal_accepted": sum(r["illegal_accepted"] for r in ok),
                "illegal_probes": sum(r["probes"] for r in ok),
                "replayed_exactly": sum(1 for r in ok if r.get("replayed")),
                "outcomes": dict(outcomes),
                "turn_limit_draws": sum(1 for r in ok if r["result"] and r["result"][-1] == "turn_limit"),
                "by_pairing": {p: dict(c) for p, c in by_pair.items()},
                "mean_turns": round(sum(r["turns"] for r in ok) / max(1, len(ok)), 2),
                "mean_actions": round(sum(r["actions"] for r in ok) / max(1, len(ok)), 1),
                "event_totals": {k: ev[k] for k in ("SpellCast", "Triggered", "AbilityActivated", "Sacrificed",
                                                   "Destroyed", "SpellFizzled", "Revealed", "Suspended",
                                                   "LifeGainPrevented", "EntersTapped", "ModeChosen",
                                                   "SearchFoundNothing", "MulliganTaken", "PlayerLost")}}

    t0 = time.time()
    report["smoke"] = summarize(_batch(list(range(args.smoke)), args.workers, 1), "smoke")
    t1 = time.time()
    small = _batch(list(range(100_000, 100_000 + args.small)), args.workers, 5)
    report["run_1k"] = summarize(small, "1k")
    t2 = time.time()
    big = _batch(list(range(200_000, 200_000 + args.games)), args.workers, 10)
    report["run_10k"] = summarize(big, "10k")
    t3 = time.time()
    first = {r["seed"]: r for r in big[:args.repeat] if "error" not in r}
    again = _batch(list(first), args.workers, 10 ** 9)
    report["repeat_seeds"] = {"compared": len(again),
                              "identical": sum(1 for r in again if "error" not in r
                                               and (r["head"], r["full"]) == (first[r["seed"]]["head"],
                                                                             first[r["seed"]]["full"]))}
    report["wall_seconds"] = {"smoke": round(t1 - t0, 1), "1k": round(t2 - t1, 1), "10k": round(t3 - t2, 1)}
    report["throughput_games_per_s_wall_10k"] = round(args.games / (t3 - t2), 1)
    # single-core CPU throughput, invariants off (comparable to M7), Burn mirror, random pilots
    from engine.v2.policies import RandomLegalPolicy
    c0 = time.process_time()
    for seed in range(200):
        Game.new(burn, burn, 300_000 + seed, starting_player=seed % 2).run([RandomLegalPolicy(seed),
                                                                              RandomLegalPolicy(seed + 1)])
    report["single_core_games_per_s_cpu_invariants_off"] = round(200 / (time.process_time() - c0), 2)
    # complete logs for manual inspection
    logdir = os.path.join(ROOT, "data", "v2_burn_logs")
    os.makedirs(logdir, exist_ok=True)
    from engine.v2.policies import SimpleAggroPolicy
    for i in range(args.logs):
        kind = PAIRINGS[1] if i % 2 == 0 else PAIRINGS[2]
        g = Game.new(burn, burn, 400_000 + i, starting_player=i % 2, check_invariants=True)
        pols = [SimpleAggroPolicy(i), SimpleAggroPolicy(i + 1)] if kind == PAIRINGS[1] else \
            [SimpleAggroPolicy(i), RandomLegalPolicy(i + 1)]
        g.run(pols)
        with open(os.path.join(logdir, f"burn_mirror_{i}_{kind}.txt"), "w", encoding="utf-8") as f:
            f.write(f"Burn mirror, seed {400_000 + i}, {kind}, result {g.result}\n")
            f.write(render(g))
    json.dump(report, open(args.out, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k != "unique_cards"}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
