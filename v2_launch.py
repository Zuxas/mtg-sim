"""Engine v2 entry for the launcher (EXPERIMENTAL; milestone three, phase 2).

Reached ONLY through an explicit engine selection:
    python parallel_launcher.py --engine v2 --deck mono_red_aggro_modern --opponent mono_red_aggro_modern \\
        --mode game --games 10 --seed 42 [--pilot-a aggro] [--pilot-b random]
    python parallel_launcher.py --engine v2 --deck ... --opponent ... --mode bo3 --side-a none --side-b none
    python parallel_launcher.py --engine v2 --replay data/v2_runs/<run>/game_0000.json

Rules of this path:
- decks are files decks/<name>.txt named explicitly (no field routing, nothing switches engines
  automatically); every main-deck card (and, for Bo3, every sideboard card) must be supported by
  engine v2 -- otherwise the run is refused before any game starts and the exact card names are
  printed (exit code 2);
- engine choice is separate from pilot choice (--pilot-a / --pilot-b);
- no fallback to a legacy engine, no result floors, no real-data substitution: an engine error is
  reported as an engine error with its traceback and the exit code is 1;
- every game / match record is saved and can be replayed with --replay;
- output is labelled EXPERIMENTAL.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LABEL = "ENGINE V2 (EXPERIMENTAL)"
PILOTS = ("random", "aggro", "scripted")


class Refused(Exception):
    pass


def _pilot(kind, seed):
    from engine.v2.policies import BasicScriptedPolicy, RandomLegalPolicy, SimpleAggroPolicy
    return {"random": RandomLegalPolicy, "aggro": SimpleAggroPolicy, "scripted": BasicScriptedPolicy}[kind](seed)


def _sideboard(spec, deck_name):
    """'file' = the deck file's own sideboard; 'none' = empty; else a deck file stem."""
    from engine.v2.cards import ROOT as V2ROOT
    if spec == "none":
        return []
    name = deck_name if spec == "file" else spec
    path = name if name.endswith(".txt") else os.path.join(V2ROOT, "decks", f"{name}.txt")
    out, on = [], False
    try:
        with open(path, encoding="utf-8") as source:
            for line in source:
                s = line.strip()
                if s.lower().startswith("sideboard"):
                    on = True
                    continue
                if on and s and not s.startswith("//"):
                    n, card = s.split(" ", 1)
                    out += [card.strip()] * int(n)
    except (OSError, ValueError) as e:
        raise Refused(f"sideboard file {path}: {e}") from e
    return out


def _check_supported(names, what):
    """Refuse unknown / unsupported cards with their exact names (nothing has started yet)."""
    from engine.card_db import UnknownCardError
    from engine.v2.cards import UnsupportedCardError, validate_deck
    try:
        validate_deck(list(names))
    except UnsupportedCardError as e:
        raise Refused(f"{what}: cards not supported by engine v2: {', '.join(e.names)}")
    except UnknownCardError as e:
        raise Refused(f"{what}: unknown card names: {', '.join(e.names)}")


def _load(deck):
    from engine.v2.decklists import main_deck
    from engine.v2.cards import UnsupportedCardError
    from engine.card_db import UnknownCardError
    try:
        return main_deck(deck)
    except FileNotFoundError as e:
        raise Refused(f"deck file for {deck!r} not found") from e
    except (OSError, ValueError) as e:
        raise Refused(f"deck {deck}: {e}") from e
    except UnsupportedCardError as e:
        raise Refused(f"deck {deck}: cards not supported by engine v2: {', '.join(e.names)}")
    except UnknownCardError as e:
        raise Refused(f"deck {deck}: unknown card names: {', '.join(e.names)}")


def _outcome(result):
    if result[0] == "win":
        return f"win_p{result[1]}"
    return "turn_limit_draw" if result[-1] == "turn_limit" else "draw"


def run(args) -> int:
    """Run the v2 path described by parsed launcher args; returns the process exit code."""
    if args.replay:
        return replay_file(args.replay)
    if not getattr(args, "deck_explicit", False) or not args.opponent:
        print(f"{LABEL}: --engine v2 needs explicit --deck and --opponent deck files (decks/<name>.txt)")
        return 2
    count = args.games if args.mode == "game" else args.matches
    if count < 1 or args.turn_limit < 1:
        print(f"{LABEL}: game/match count and --turn-limit must be positive")
        return 2
    print(f"\n{LABEL}  |  mode={args.mode}  seed={args.seed}  pilots={args.pilot_a}/{args.pilot_b}")
    try:
        deck_a, deck_b = _load(args.deck), _load(args.opponent)
        side_a = side_b = []
        if args.mode == "bo3":
            side_a, side_b = _sideboard(args.side_a, args.deck), _sideboard(args.side_b, args.opponent)
            _check_supported(side_a, f"sideboard of {args.deck}")
            _check_supported(side_b, f"sideboard of {args.opponent}")
    except Refused as e:
        print(f"REFUSED before play: {e}")
        return 2
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_s{args.seed}"
    out_dir = args.record_dir or os.path.join(ROOT, "data", "v2_runs", run_id)
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    tally = {"win_p0": 0, "win_p1": 0, "draw": 0, "turn_limit_draw": 0, "engine_error": 0}
    errors, records = [], []
    n = count
    for i in range(n):
        seed = args.seed + i
        try:
            if args.mode == "game":
                rec, res = _one_game(deck_a, deck_b, seed, args)
                path = os.path.join(out_dir, f"game_{i:04d}.json")
            else:
                rec, res = _one_match(deck_a, side_a, deck_b, side_b, seed, args)
                path = os.path.join(out_dir, f"match_{i:04d}.json")
        except Exception as e:                                    # reported, never swallowed, never a fallback
            tally["engine_error"] += 1
            errors.append({"index": i, "seed": seed, "error": f"{type(e).__name__}: {e}",
                           "trace": traceback.format_exc()[-3000:]})
            print(f"  ENGINE ERROR [{i}] seed={seed}: {type(e).__name__}: {e}")
            continue
        with open(path, "w", encoding="utf-8") as target:
            json.dump(rec, target)
        records.append(os.path.basename(path))
        tally[_outcome(res)] += 1
    summary = {
        "engine": "v2", "status": "EXPERIMENTAL", "engine_version": _version(), "mode": args.mode,
        "deck": args.deck, "opponent": args.opponent, "pilots": [args.pilot_a, args.pilot_b],
        "seed": args.seed, "count": n, "turn_limit": args.turn_limit, "results": tally,
        "engine_errors": errors, "records": records, "record_dir": out_dir,
        "elapsed_s": round(time.time() - t0, 2),
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as target:
        json.dump(summary, target, indent=1)
    unit = "games" if args.mode == "game" else "matches"
    print(f"  {n} {unit}:  P0 ({args.deck}) wins {tally['win_p0']}  |  P1 ({args.opponent}) wins "
          f"{tally['win_p1']}  |  draws {tally['draw']}  |  turn-limit draws {tally['turn_limit_draw']}  |  "
          f"ENGINE ERRORS {tally['engine_error']}")
    print(f"  Records + summary: {out_dir}")
    print(f"  {LABEL}: results are experimental validation data, not metagame predictions.")
    return 1 if errors else 0


def _version():
    from engine.v2 import ENGINE_VERSION
    return ENGINE_VERSION


def _one_game(deck_a, deck_b, seed, args):
    from engine.v2.game import Game
    from engine.v2.record import make_record
    g = Game.new(deck_a, deck_b, seed, starting_player=seed % 2, turn_limit=args.turn_limit,
                 check_invariants=args.invariants)
    g.run([_pilot(args.pilot_a, seed), _pilot(args.pilot_b, seed + 1)])
    rec = make_record(g, policy_seeds=[seed, seed + 1])
    rec["launcher"] = {"pilots": [args.pilot_a, args.pilot_b], "label": LABEL}
    return rec, g.result


def _one_match(deck_a, side_a, deck_b, side_b, seed, args):
    from engine.v2.match import Match, make_match_record
    m = Match(deck_a, side_a, deck_b, side_b, seed, turn_limit=args.turn_limit, check_invariants=args.invariants)
    res = m.run([_pilot(args.pilot_a, seed), _pilot(args.pilot_b, seed + 1)])
    rec = make_match_record(m)
    rec["launcher"] = {"pilots": [args.pilot_a, args.pilot_b], "label": LABEL,
                       "match_decisions": "first legal (play first, no sideboard swaps)"}
    return rec, res


def replay_file(path) -> int:
    """Replay a saved game or match record; prints and returns 0 when it reproduces exactly."""
    from engine.v2.match import replay_match
    from engine.v2.record import replay
    try:
        with open(path, encoding="utf-8") as source:
            rec = json.load(source)
        if "games" in rec:
            m = replay_match(rec)
            print(f"{LABEL} replay OK: match result {m.result} ({len(m.games)} games)")
        else:
            g = replay(rec)
            print(f"{LABEL} replay OK: game result {g.result}")
    except Exception as e:                                        # a mismatch is an error, reported as such
        print(f"{LABEL} REPLAY FAILED: {type(e).__name__}: {e}")
        return 1
    return 0
