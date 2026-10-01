"""Milestone-four validation: Modern Burn (decks/mono_red_aggro_modern.txt) vs Izzet Prowess
(decks/auto/izzet_prowess_modern.txt), main decks only, played entirely through engine/v2.

  python scripts/v2_matchup_validation.py --games 10000 --workers 20

Four separately reported cells of games/4 each:
  burn_seat0_burn_starts, burn_seat0_prowess_starts, burn_seat1_burn_starts, burn_seat1_prowess_starts.
Gates (harness/specs/2026-10-01-v2-m4-matchup-survey.md): 0 crashes, 0 invariant violations (invariants
ON in every game), 0 dead ends, 0 illegal actions accepted (a stale action is probed every 7th
decision), exact replay of >= 1,000 records sampled across the four cells (through JSON), repeated
game + policy seeds give identical records, manual inspection of complete logs from every cell that
together cover every new mechanic, matchup throughput + the M7 benchmark (floor 20 games/s).
Win rates are diagnostic only (untuned pilots; no target).
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

BURN = "mono_red_aggro_modern"
PROWESS = "decks/auto/izzet_prowess_modern.txt"
PAIRINGS = ("random_vs_random", "aggro_vs_aggro", "aggro_vs_random")
# cell -> (Burn's seat, the starting player's deck)
CELLS = {"burn_seat0_burn_starts": (0, "burn"), "burn_seat0_prowess_starts": (0, "prowess"),
         "burn_seat1_burn_starts": (1, "burn"), "burn_seat1_prowess_starts": (1, "prowess")}
CELL_BASE = {c: 1_000_000 * (i + 1) for i, c in enumerate(CELLS)}


def _cell_setup(cell):
    burn_seat, starts = CELLS[cell]
    starting = burn_seat if starts == "burn" else 1 - burn_seat
    return burn_seat, starting


def _policies(kind, seed):
    from engine.v2.policies import RandomLegalPolicy, SimpleAggroPolicy
    if kind == "random_vs_random":
        return [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)]
    if kind == "aggro_vs_aggro":
        return [SimpleAggroPolicy(seed), SimpleAggroPolicy(seed + 1)]
    return [SimpleAggroPolicy(seed), RandomLegalPolicy(seed + 1)] if seed % 2 else \
        [RandomLegalPolicy(seed), SimpleAggroPolicy(seed + 1)]


def _decks(burn_seat):
    from engine.v2.decklists import main_deck
    burn, prow = main_deck(BURN), main_deck(PROWESS)
    return (burn, prow) if burn_seat == 0 else (prow, burn)


# ------------------------------------------------------------------ mechanic coverage (from the log)
def coverage(g) -> dict:
    """Which new (milestone-four) mechanics this game exercised, read from its event log."""
    s = g.s
    nm = lambda ciid: s.instances[ciid].name                                     # noqa: E731
    seen = collections.Counter()
    tokens = {dict(e.data)["oid"] for t in s.log.transitions for e in t.events if e.kind == "TokenCreated"}
    for t in s.log.transitions:
        kinds = [e.kind for e in t.events]
        fx = [dict(e.data).get("effect") for e in t.events if e.kind == "TurnEffectAdded"]
        if "first_strike" in fx:
            seen["violent_urge"] += 1
            if "double_strike" in fx:
                seen["violent_urge_double_strike_delirium"] += 1
        for e in t.events:
            d = dict(e.data)
            k = e.kind
            if k == "AbilityActivated":
                seen[{"fetch_island_mountain": "scalding_tarn", "fetch_mountain_forest": "wooded_foothills",
                      "equip": "equip", "bauble_look": "bauble_activate"}.get(d["key"], "other_activation")] += 1
            elif k == "Triggered":
                if d["key"] in ("drc_surveil", "falls_surveil", "flurry", "slickshot_pump", "bauble_draw"):
                    seen[d["key"]] += 1
                if d["key"] == "prowess" and d["source"] in tokens:
                    seen["monk_token_prowess"] += 1
            elif k == "CastProposed":
                n = nm(d["ciid"])
                if d["cost"].startswith("phyrexian"):
                    seen["phyrexian_life"] += 1
                elif n == "Mutagenic Growth":
                    seen["phyrexian_mana"] += 1
                if d["cost"] == "flashback":
                    seen["flashback"] += 1
                if d["cost"] == "plot":
                    seen["plotted_cast"] += 1
                if d["frm"] == "exile" and d["cost"] == "normal":
                    seen["cast_from_exile_permission"] += 1
                if n in ("Preordain", "Serum Visions"):
                    seen["scry_" + n.split()[0].lower()] += 1
                if n == "Expressive Iteration":
                    seen["expressive_iteration"] += 1
            elif k == "ZoneChanged":
                if d["frm"] == "exile" and d["to"] == "battlefield" and s.def_by_ciid[d["ciid"]].is_land:
                    seen["land_played_from_exile"] += 1
                if d["to"] == "battlefield" and nm(d["ciid"]) in ("Steam Vents", "Thundering Falls"):
                    seen[nm(d["ciid"]).lower().replace(" ", "_")] += 1
                if d["frm"] == "library" and d["to"] == "graveyard":
                    seen["surveil_to_graveyard"] += 1
            elif k == "LibraryArranged" and d["bottom"]:
                seen["card_put_on_bottom"] += 1
            elif k in ("TokenCreated", "TokenCeasedToExist", "Plotted", "ReplacedByExile", "LookedAt",
                       "DelayedTriggerCreated", "Unattached"):
                seen[k] += 1
            elif k == "Attached":
                seen["Attached" + ("_flurry_token" if d["creature"] in tokens else "")] += 1
            elif k == "AttachDeclined":
                seen["flurry_attach_declined"] += 1
            elif k == "AttachNoChange":
                seen["equip_same_creature_no_change"] += 1
            elif k == "DamageDivisionChosen" and any(b == "player" and n > 0 for b, n in d["division"]):
                seen["trample_excess_to_player"] += 1
            elif k == "PendingEntry" and d["value"] is not None:
                seen["shock_choice"] += 1
        if "EntersTapped" in kinds and any(e.kind == "ZoneChanged" and "ciid" in dict(e.data)
                                           and nm(dict(e.data)["ciid"]) == "Thundering Falls" for e in t.events):
            seen["falls_enters_tapped"] += 1
    return dict(seen)


def play(seed, cell, replay_it=False, cover=False):
    from engine.v2.game import Game, IllegalAction
    from engine.v2.record import make_record, replay
    from engine.v2.rules import statics
    burn_seat, starting = _cell_setup(cell)
    kind = PAIRINGS[seed % 3]
    try:
        a, b = _decks(burn_seat)
        g = Game.new(a, b, CELL_BASE[cell] + seed, starting_player=starting, check_invariants=True)
        pols = _policies(kind, seed)
        dead_ends = illegal_accepted = probes = 0
        drc_delirium = must_attack = 0
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
            pd = g.pending()
            if cover and pd.kind == "declare_attack" and statics.must_attack(g.s, pd.info[0]):
                must_attack += 1
            p = pd.player
            pol = pols[p]
            obs = g.observe(p) if getattr(pol, "uses_observation", True) else None
            act = pol.choose(obs, acts)
            stale = act
            g.apply(act)
            if cover and any(g.s.def_by_ciid[g.s.objects[o].ciid].effect_key == "dragons_rage_channeler"
                             and statics.delirium(g.s, g.s.objects[o].controller) for o in g.s.zones[("bf",)]):
                drc_delirium += 1
        res = {"seed": seed, "cell": cell, "pairing": kind, "burn_seat": burn_seat, "starting": starting,
               "result": list(g.result) if g.result else None, "turns": g.s.turn, "actions": len(g.actions),
               "dead_ends": dead_ends, "illegal_accepted": illegal_accepted, "probes": probes,
               "head": g.s.log.head, "full": g.s.full_state_hash()}
        if replay_it:
            replay(json.loads(json.dumps(make_record(g, policy_seeds=[seed, seed + 1]))))   # through JSON, exact
            res["replayed"] = True
        if cover:
            cv = coverage(g)
            if drc_delirium:
                cv["drc_delirium_on_battlefield"] = 1
            if must_attack:
                cv["drc_must_attack_decision"] = must_attack
            res["coverage"] = cv
        res["events"] = dict(collections.Counter(e.kind for t in g.s.log.transitions for e in t.events))
        return res
    except Exception as e:                                           # noqa: BLE001
        return {"seed": seed, "cell": cell, "pairing": kind, "error": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-2500:]}


def _batch(seeds, cell, workers, replay_every, cover=False):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(play, seeds, [cell] * len(seeds), [s % replay_every == 0 for s in seeds],
                           [cover] * len(seeds), chunksize=25))


# ------------------------------------------------------------------ readable logs
def render(g) -> str:
    s = g.s
    name = lambda ciid: s.instances[ciid].name                                    # noqa: E731
    ciid_of = {}
    for t in s.log.transitions:
        for e in t.events:
            d = dict(e.data)
            if e.kind == "ZoneChanged" and "new" in d:
                ciid_of[d["new"]] = d["ciid"]
            elif e.kind in ("SpellCast", "TokenCreated"):
                ciid_of[d["oid"]] = d["ciid"]
    nm = lambda oid: name(ciid_of[oid]) if oid in ciid_of else f"#{oid}"         # noqa: E731
    who = lambda p: f"P{p}({'Burn' if 'Lightning Helix' in s.config['decks'][p] else 'Prowess'})"   # noqa: E731
    lines = []
    for t in s.log.transitions:
        if t.index < 3 and t.kind.startswith("setup"):
            continue
        for e in t.events:
            d = dict(e.data)
            k = e.kind
            if k == "TurnBegan":
                lines.append(f"\n=== Turn {d['turn']} ({who(d['active'])}) ===")
            elif k == "MulliganDeclared":
                lines.append(f"  {who(d['player'])} declares {d['choice']}")
            elif k == "Set" and d["attr"] == "step" and d["value"] in ("upkeep", "main1", "declare_attackers",
                                                                    "first_strike_damage", "combat_damage", "end"):
                lines.append(f"  -- {d['value']}")
            elif k == "ZoneChanged" and "ciid" in d:
                lines.append(f"  {name(d['ciid'])}: {d['frm']} -> {d['to']}")
            elif k == "ZoneChanged":
                lines.append(f"  (hidden) {who(d['owner'])} {d['frm']} -> {d['to']}")
            elif k == "Drew":
                lines.append(f"  {who(d['player'])} draws")
            elif k == "CastProposed":
                lines.append(f"  {who(d['controller'])} casts {name(d['ciid'])} from {d['frm']} ({d['cost']} cost)")
            elif k == "TargetsChosen":
                lines.append(f"    targets {[(x[0], x[1] if x[0] != 'obj' else nm(x[1])) for x in d['targets']]}")
            elif k == "SpellCast":
                lines.append(f"    cast ({d['mana_spent']} mana spent)")
            elif k in ("Triggered",):
                lines.append(f"  trigger: {d['key']} ({who(d['controller'])}, from {nm(d['source'])})")
            elif k == "AbilityActivated":
                tg = [(x[0], x[1] if x[0] != 'obj' else nm(x[1])) for x in d["targets"]]
                lines.append(f"  {who(d['controller'])} activates {d['key']} of {nm(d['source'])}" + (f" -> {tg}" if tg else ""))
            elif k == "LifeChanged":
                lines.append(f"    {who(d['player'])} life {d['life']} ({d['delta']:+d})")
            elif k == "DamageDealt":
                tgt = nm(d["target"][1]) if d["target"][0] == "obj" else who(d["target"][1])
                lines.append(f"    {nm(d['source'])} deals {d['n']} to {tgt}")
            elif k == "AttackersDeclared":
                lines.append(f"  attackers: {[nm(a) for a in d['attackers']]}")
            elif k == "BlockersDeclared":
                lines.append(f"  blocks: {[(nm(b), nm(a)) for b, a in d['blocks']]}")
            elif k == "DamageDivisionChosen":
                lines.append(f"  damage division for {nm(d['attacker'])}: "
                             f"{[(b if b == 'player' else nm(b), n) for b, n in d['division']]}")
            elif k == "LibraryArranged":
                lines.append(f"    {who(d['player'])} arranges library: {d['top']} on top, {d['bottom']} on bottom (cards hidden)")
            elif k == "LookedAt":
                lines.append(f"    {who(d['player'])} looks at the top card of {who(d['library'])}'s library (private)")
            elif k == "TokenCreated":
                lines.append(f"    {d['name']} created for {who(d['controller'])}")
            elif k == "Attached":
                lines.append(f"    {nm(d['equipment'])} attached to {nm(d['creature'])}")
            elif k == "Unattached":
                lines.append(f"    {nm(d['equipment'])} unattached")
            elif k == "PTModified":
                lines.append(f"    {nm(d['oid'])} gets {d['p']:+d}/{d['t']:+d}")
            elif k == "Plotted":
                lines.append(f"    plotted (turn {d['turn']})")
            elif k == "ReplacedByExile":
                lines.append(f"    flashback: exiled instead of -> {d['instead_of']}")
            elif k == "TurnEffectAdded":
                a = d["a"]
                lines.append(f"    effect {d['effect']} on {nm(a) if isinstance(a, int) else a}")
            elif k == "DelayedTriggerCreated":
                lines.append(f"    delayed trigger {d['key']} for turn {d['turn']}")
            elif k in ("SpellResolved", "SpellFizzled", "SpellCountered", "AbilityResolved", "AbilityRemoved",
                       "SearchFoundNothing", "AttachNoChange", "AttachDeclined", "TokenCeasedToExist", "Destroyed",
                       "Sacrificed", "Revealed", "EntersTapped", "LifePaid", "LifeGainPrevented", "SearchFound",
                       "MulliganTaken", "Kept", "GameEnded", "PlayerLost", "Suspended"):
                lines.append(f"    {k} {d}")
    return "\n".join(lines)


def summarize(results):
    errs = [r for r in results if "error" in r]
    ok = [r for r in results if "error" not in r]
    wins = collections.Counter()
    for r in ok:
        res = r["result"]
        if res is None:
            continue
        if res[0] == "draw":
            wins["draw:" + res[-1]] += 1
        else:
            wins["Burn" if res[1] == r["burn_seat"] else "Prowess"] += 1
    by_pair = {p: collections.Counter() for p in PAIRINGS}
    for r in ok:
        res = r["result"]
        if res:
            by_pair[r["pairing"]]["draw" if res[0] == "draw" else ("Burn" if res[1] == r["burn_seat"] else "Prowess")] += 1
    ev = collections.Counter()
    for r in ok:
        ev.update(r["events"])
    keys = ("SpellCast", "Triggered", "AbilityActivated", "TokenCreated", "TokenCeasedToExist", "Attached",
            "Unattached", "LookedAt", "LibraryArranged", "DelayedTriggerCreated", "Plotted", "ReplacedByExile",
            "DamageDivisionChosen", "SearchFoundNothing", "MulliganTaken", "PlayerLost", "LifeGainPrevented")
    return {"games": len(results), "errors": len(errs), "first_errors": errs[:3],
            "dead_ends": sum(r["dead_ends"] for r in ok),
            "illegal_accepted": sum(r["illegal_accepted"] for r in ok),
            "illegal_probes": sum(r["probes"] for r in ok),
            "replayed_exactly": sum(1 for r in ok if r.get("replayed")),
            "results": dict(wins),
            "turn_limit_draws": sum(1 for r in ok if r["result"] and r["result"][-1] == "turn_limit"),
            "by_pairing": {p: dict(c) for p, c in by_pair.items()},
            "mean_turns": round(sum(r["turns"] for r in ok) / max(1, len(ok)), 2),
            "mean_actions": round(sum(r["actions"] for r in ok) / max(1, len(ok)), 1),
            "event_totals": {k: ev[k] for k in keys}}


def write_logs(args) -> dict:
    """Complete logs for manual inspection: per cell, games chosen greedily (from every pairing) to
    cover every mechanic seen in that cell's candidates, plus a game won by each deck."""
    from engine.v2.game import Game
    logdir = os.path.join(ROOT, "data", "v2_m4_logs")
    os.makedirs(logdir, exist_ok=True)
    out = {}
    for cell in CELLS:
        cands = [r for r in _batch(list(range(args.cover_candidates)), cell, args.workers, 10 ** 9, True)
                 if "error" not in r]                                    # every pairing
        union = set().union(*(r["coverage"] for r in cands))
        chosen, covered = [], set()
        while covered != union and len(chosen) < 10:
            best = max(cands, key=lambda r: len(set(r["coverage"]) - covered))
            chosen.append(best)
            covered |= set(best["coverage"])
        winner = lambda r: "Burn" if r["result"][0] == "win" and r["result"][1] == r["burn_seat"] else \
            ("Prowess" if r["result"][0] == "win" else "draw")       # noqa: E731
        for deck in ("Burn", "Prowess"):
            if not any(winner(r) == deck for r in chosen):
                pick = next((r for r in cands if winner(r) == deck), None)
                if pick is not None:
                    chosen.append(pick)
        files = []
        for r in chosen:
            burn_seat, starting = _cell_setup(cell)
            x, y = _decks(burn_seat)
            g = Game.new(x, y, CELL_BASE[cell] + r["seed"], starting_player=starting, check_invariants=True)
            g.run(_policies(r["pairing"], r["seed"]))
            assert g.s.log.head == r["head"]                             # the logged game is the scanned game
            path = os.path.join(logdir, f"{cell}_seed{r['seed']}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Burn (seat {burn_seat}) vs Izzet Prowess, cell {cell}, seed {CELL_BASE[cell] + r['seed']}, "
                        f"{r['pairing']}, result {g.result} (winner: {winner(r)})\ncoverage: {sorted(r['coverage'])}\n")
                f.write(render(g))
            files.append({"file": os.path.relpath(path, ROOT).replace("\\", "/"), "winner": winner(r),
                          "pairing": r["pairing"], "turns": r["turns"]})
        out[cell] = {"files": files, "mechanics_covered": sorted(covered),
                     "mechanics_seen_in_candidates": sorted(union), "candidates": len(cands),
                     "mechanic_game_counts": dict(collections.Counter(k for r in cands for k in r["coverage"]))}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=10_000, help="total; games/4 per cell")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--replay-every", type=int, default=8, help="replay every Nth seed (>= 1,000 total at 10k)")
    ap.add_argument("--repeat", type=int, default=100, help="repeated seeds per cell")
    ap.add_argument("--cover-candidates", type=int, default=600, help="games per cell scanned for log coverage")
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "v2_m4_validation.json"))
    ap.add_argument("--logs-only", action="store_true", help="regenerate only the logs section of --out")
    args = ap.parse_args()
    if args.logs_only:
        import shutil
        report = json.load(open(args.out, encoding="utf-8"))
        shutil.rmtree(os.path.join(ROOT, "data", "v2_m4_logs"), ignore_errors=True)
        report["logs"] = write_logs(args)
        json.dump(report, open(args.out, "w"), indent=1, default=str)
        print(json.dumps(report["logs"], indent=1, default=str)[:6000])
        return
    from engine.v2.cards import UnsupportedCardError
    from engine.v2.decklists import main_deck
    from engine.v2.game import Game
    report = {"decks": {"burn": BURN, "prowess": PROWESS}}
    prow = main_deck(PROWESS)
    report["prowess_cards"] = len(prow)
    report["prowess_unique"] = sorted(set(prow))
    try:
        Game.new(prow[:-1] + ["Murktide Regent"], main_deck(BURN), 0)          # a sideboard card: refused
        report["altered_deck_refused"] = False
    except UnsupportedCardError as e:
        report["altered_deck_refused"] = str(e)
    per = args.games // 4
    report["cells"] = {}
    timings = {}
    firsts = {}
    for cell in CELLS:
        t0 = time.time()
        res = _batch(list(range(per)), cell, args.workers, args.replay_every)
        timings[cell] = time.time() - t0
        report["cells"][cell] = summarize(res)
        report["cells"][cell]["wall_seconds"] = round(timings[cell], 1)
        report["cells"][cell]["games_per_s_wall"] = round(per / timings[cell], 1)
        firsts[cell] = {r["seed"]: r for r in res[:args.repeat] if "error" not in r}
        print(cell, json.dumps({k: v for k, v in report["cells"][cell].items() if k != "first_errors"}), flush=True)
    rep = {}
    for cell in CELLS:
        again = _batch(list(firsts[cell]), cell, args.workers, 10 ** 9)
        rep[cell] = {"compared": len(again),
                     "identical": sum(1 for r in again if "error" not in r and
                                      (r["head"], r["full"]) == (firsts[cell][r["seed"]]["head"], firsts[cell][r["seed"]]["full"]))}
    report["repeat_seeds"] = rep
    tot = {k: sum(report["cells"][c][k] for c in CELLS) for k in ("games", "errors", "dead_ends", "illegal_accepted",
                                                                    "illegal_probes", "replayed_exactly", "turn_limit_draws")}
    report["totals"] = tot
    report["throughput_games_per_s_wall"] = round(args.games / sum(timings.values()), 1)
    # single-core CPU throughput, invariants off, Burn vs Prowess, random pilots (comparable to M7)
    from engine.v2.policies import RandomLegalPolicy
    a, b = _decks(0)
    Game.new(a, b, 0)
    c0 = time.process_time()
    for seed in range(200):
        Game.new(a, b, 9_000_000 + seed, starting_player=seed % 2).run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)])
    report["matchup_single_core_games_per_s_cpu_invariants_off"] = round(200 / (time.process_time() - c0), 2)
    from scripts.v2_acceptance import _speed
    report["M7"] = _speed(200)
    report["logs"] = write_logs(args)
    json.dump(report, open(args.out, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("prowess_unique", "cells")}, indent=1, default=str)[:8000])


if __name__ == "__main__":
    main()
