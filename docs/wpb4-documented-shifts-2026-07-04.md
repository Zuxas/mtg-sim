# WP-B4 documented baseline shifts (for the DEFERRED combined 100k re-anchor)

All measured at the small gate sizes; directions are the canonical shift, magnitudes
will settle at 100k. Run the re-anchor with PINNED PYTHONHASHSEED or n_workers=1
(the match_engine path has PRE-EXISTING cross-process set-ordering noise; see below).

## Match path (match_runner / TwoPlayerGameState) -- Phase-2 stream interleave shift
- Boros-vs-Affinity MATCH n=300 seed=42: a_wins 181 -> 189, b_wins 119 -> 111, avg_turns 6.330000 -> 6.426667
  (Phase 1 was byte-identical to baseline; the shift is entirely Phase 2.)

## Match path (match_engine / MatchGameState, via run_bo3) -- Phase-2 shift + determinism FIX
- run_bo3(seed=777) Boros-vs-Affinity: baseline DRIFTED same-seed (winner b then a); post-migration IDENTICAL winner=b, a=1 b=2, turns=25.
- run_bo3_set n=20 seed=42 nw=1: baseline a=6 -> post-migration a=5 (Phase-2 shift).

## Goldfish (per-game reseed, by-design documented shift)
- Amulet Titan goldfish n=100 seed=42: won 100 -> 98, avg_kill_turn 6.450000 -> 6.142857
- Humans goldfish n=100 seed=42: avg 4.780000 -> 4.710000, total mulls 48 -> 44 (won 100 unchanged)

## NOT re-anchored
- race.py / opponent.py Monte-Carlo (analysis-only, left byte-identical on global module; unseeded ~0.2pp noise as before)
- atomic_json.py retry jitter (out of scope, stays global)

## PRE-EXISTING (NOT caused by WP-B4, NOT fixed by it)
- run_bo3_set n_workers 1 vs 4 NON-invariance: baseline a=6 (nw1) vs a=5 (nw4); post-migration a=5 (nw1) vs a=4 (nw4).
  This is id()/set-iteration cross-process ordering nondeterminism (the "id()-ordering predecessor"
  documented in mtg-sim/CLAUDE.md and tests/test_determinism.py cross-process section). RNG migration
  neither introduces nor removes it. => Confirms the plan's FALSIFIABLE GATE-3 contingency: residual
  cross-process/same-seed drift on this path is ORDERING-sourced, not RNG-sourced; killing global
  random does NOT deliver the byte-gate here. The WP-A P2 unblock is NOT earned by WP-B4 alone.
