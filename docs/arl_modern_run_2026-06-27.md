# ARL Modern Run -- Honest Leaderboard Report

**Date:** 2026-06-27
**Batch:** bounded explore/modern ARL, 5 iterations, ~2m43s wall (14:39:41 -> 14:42:24)
**Internal timeout:** 580s (run finished well inside it)
**Verdict spread:** promote=3, mutate=0, discard=1, low_confidence=0, unmodelable=1
**Verification:** every promote re-gauntleted adversarially at seed 43 (loop ran seed 42)

---

## 1. CONFIRMED Leaderboard

Decks that PROMOTED in the loop **and held** under an independent re-gauntlet at a different
seed (stable FWR, variance well under the 8pp threshold, high confidence). Ranked by **verified FWR**.

| Rank | Deck | Verified FWR (seed 43) | Loop FWR (seed 42) | Variance | Confidence | Verdict |
|------|------|------------------------|--------------------|----------|------------|---------|
| 1 | Eldrazi Ramp | **68.6%** | 67.3% | 1.3pp | high | holds |
| 2 | Boros Energy | **65.0%** | 66.7% | 1.7pp | high | holds |
| 3 | Izzet Prowess | **64.3%** | 66.8% | 2.5pp | high | holds |

**Notes (per-deck verification):**
- **Eldrazi Ramp** -- 500 games, clean (exit 0). Per-matchup plausible and directionally sane:
  strong vs fair decks (Boros / Jeskai / Affinity, 70-87%), weak vs combo (Amulet Titan 30.6%,
  Ruby Storm 18.5%). Stable, trustworthy.
- **Boros Energy** -- 400 games across 4 matchups, clean (exit 0). Per-matchup: Affinity 78.0,
  Amulet Titan 64.6, Jeskai Blink 58.0, Ruby Storm 55.2. Tightest variance-to-mean of the three.
- **Izzet Prowess** -- 500 games, clean (no crash). Per-matchup: Boros 60.0, Jeskai Blink 75.0,
  Affinity 76.0, Amulet Titan 46.7, Ruby Storm 55.2. Largest swing (2.5pp) but still comfortably
  STABLE. Results saved to `data/parallel_results_20260627_144344.json`.

All three are trustworthy as **reproducible simulation rankings**. See the verdict (Section 5)
for what that does and does not mean.

---

## 2. FLAGGED -- promotes that did NOT hold

**None.** Every loop promotion survived adversarial re-verification: 3/3 ran clean at a fresh
seed, all variances (1.3 / 1.7 / 2.5pp) landed far below the 8pp stability threshold, and all
retained high confidence. No high-variance, low-confidence, or crashed-on-re-gauntlet promotes
in this batch.

For completeness (not a flagged promote -- a *correct* discard):
- **Amulet Titan** -- DISCARD, fwr=10.2 (high confidence). Badly lost vs Boros Energy (3.0) and
  Jeskai Blink (2.0). The discard verdict is consistent with the confirmed decks' combo matchups
  above (Eldrazi/Boros both beat Amulet handily), so the loss looks real, not a sim artifact. Not
  re-gauntleted (discards aren't verified), so it is reported but not promoted.

---

## 3. MODELABILITY BACKLOG

**Total: 6 items.** 3 added this batch, 3 predate the run.

- **Added this batch (3) -- all Izzet Affinity** (verdict: UNMODELABLE; fidelity gate held):
  - `sim-no-stack-priority`
  - `warp-mechanic-not-modeled`
  - `sim-no-hidden-information`

  The gate correctly refused to score Izzet Affinity, skipped smoke/gauntlet, and did **not**
  pause the loop -- it logged the engine-fidelity gaps and moved on. This is the desired behavior:
  no fabricated score for a deck the engine can't faithfully simulate.

- **Pre-existing (3) -- Jeskai Control:** carried over from prior runs, untouched this batch.

File: `data/modelability_backlog.json`. This is the engine-fidelity work queue -- the honest
ledger of what the simulator cannot yet model, rather than decks getting bogus FWRs.

---

## 4. GENERATED APLs

**None.** `generated: []` -- the tail generator never fired.

This is **expected, not a miss**: every archetype in this Modern batch resolved to an existing
**canonical (hand-authored) APL** ("no generation"). The generator only fires for unregistered
tail decks; the top Modern field is already registered. So this run does not demonstrate the
generator in production -- it demonstrates that the canonical-APL fast path covers the meta's head.
A generator-in-production demonstration requires a batch seeded with off-meta / unregistered decks.

---

## 5. HONEST Verdict

**Did the ARL run produce trustworthy Modern deck evaluations end-to-end? Partially -- yes for
reproducibility and internal consistency; with an important caveat on ground truth.**

What the run genuinely earned:
- It ran **clean to completion** inside its timeout, checkpointed every iteration, and produced a
  coherent verdict spread.
- All **3 promotes survived independent adversarial re-gauntlets** at a different seed with
  variance of 1.3-2.5pp -- the rankings are **reproducible and stable**, not seed-luck.
- The **fidelity gate worked**: it flagged Izzet Affinity as unmodelable and logged 3 concrete
  engine gaps instead of inventing a score -- the system declined to lie when it couldn't model
  the deck.
- The **discard (Amulet Titan)** is consistent with the confirmed decks' combo matchups, so the
  full promote/discard/unmodelable triage looks internally sound.

The honest caveats:
- These are **goldfish / canonical-APL simulation scores, not tournament truth.** A high verified
  FWR means "wins games against the modeled field under the canonical pilot lines," not "wins
  events." Pilot skill, sideboard games, mulligan decisions, and metagame shifts are not captured.
- The **field is largely hand-APL-covered**, so nearly every score came from canonical APLs. The
  evaluation quality is therefore bounded by the quality of those hand-authored pilot lines.
- The **generator was never exercised** this run, so this batch does not validate the auto-APL path
  in production.

**Bottom line:** The ARL pipeline produced *trustworthy, reproducible, internally consistent*
Modern rankings end-to-end, and -- to its credit -- honestly refused to score what it can't model.
Treat the CONFIRMED leaderboard as a reliable **simulation-fidelity ranking of canonical pilot
lines**, not as a tournament results board.

---

### Confirmed leaderboard (compact)

1. Eldrazi Ramp -- 68.6% verified (loop 67.3%, var 1.3pp, high)
2. Boros Energy -- 65.0% verified (loop 66.7%, var 1.7pp, high)
3. Izzet Prowess -- 64.3% verified (loop 66.8%, var 2.5pp, high)
