---
title: Narrow Gauntlet — Izzet Lessons vs 5 Strixhaven Brews
date: 2026-04-23
task_id: bst9aitvr
status: ran_to_completion_but_results_diverge_from_reality
---

# Narrow Gauntlet Results — Izzet Lessons

## Headline

**Field-weighted match WR: 8.2%.** Tournament matchup_matrix says Izzet
Lessons is a 49.5% FWR deck. **The sim is 41 percentage points off.**

| Opp | Share | G1 | G2 | Match | Path |
|---|---|---|---|---|---|
| Superior Doomsday | 7.3% | 1.8% | 7.8% | **0.7%** | G1 sim + heuristic SB (no Bo3 plan) |
| Izzet Control | 5.0% | 36.2% | 40.4% | **32.7%** | Real Bo3, both sides SB'd |
| Roaming Elementals | 4.5% | 0.1% | 6.1% | **0.4%** | G1 sim + heuristic SB |
| Azorius Aggro | 3.6% | 8.4% | 10.1% | **2.4%** | Real Bo3, our-side SB only |
| Mono Green Aggro | 3.6% | 12.1% | 14.8% | **5.0%** | Real Bo3, our-side SB only |

Only the Izzet Control mirror-ish matchup shows a number that's even
in the right tier. Every other matchup is catastrophically worse than
reality.

## What went right

- All 5 matchups ran (zero errors)
- 125,000 total games in ~6 minutes wall time
- Commits clean, per-task discipline held
- Registry gap closed (3 pre-existing decks silently un-registered — Izzet Lessons, Superior Doomsday, Azorius Aggro)

## What the results tell us

The 99.32% cast-weighted handler coverage did not translate to sim
calibration. The gauntlet is answering "how does the sim's Izzet Lessons
play against the sim's opponents" — and the answer is "terribly."
That's a sim-quality problem, not a handler-coverage problem.

## Root causes to investigate tomorrow, in priority order

### 1. Izzet Lessons decklist is 58 cards, 4 months old (pre-Strixhaven)

`decks/izzet_lesson_standard.txt` header says "Sakano Rei, 2nd place,
2025-12-30." Counts 58 mainboard cards, not 60. Predates Strixhaven
entirely. A current tournament Lessons list scraped from mtg_meta.db
would be both legal (60) and current (post-Strixhaven cards like
Strixhaven Stadium / whatever the new Lesson support is).

**Action:** scrape a current Izzet Lessons decklist the same way the
3 brew decklists were scraped tonight.

### 2. IzzetLessonAPL behavior vs opponents

Even against GenericAPL-shim opponents (Roaming Elementals, Mono Green
Aggro) IL posts <15% G1. GenericAPL should be a weak baseline.
Something about `IzzetLessonAPL(ControlAPL)` is losing G1 play
sequencing — possibly mulligan logic rejecting hands too aggressively,
possibly not casting its win conditions.

**Action:** manual game-trace of IL vs Mono Green Aggro (should be
the cleanest matchup to debug — generic vs real control, no combo
weirdness). Inspect why Lessons is losing G1 at 88%.

### 3. SB plans missing for 2 of 5 opponents

Superior Doomsday and Roaming Elementals fell through to heuristic
G1 sim because no IL sideboard plan exists for those matchups in
`engine/sideboard.py`. Even with a calibrated IL, those matchups
would run without real sideboarding.

**Action:** add SB plans for Izzet Lessons vs each of the 5 brews
once IL's deck and APL are fixed.

## What the data does NOT change

The tournament matchup_matrix data from 6,338 recent matches still
stands: Izzet Lessons at 49.5% FWR / 4.0% stddev over 75% of the
meta. That's real-world truth and it's why Lessons is the locked
deck choice. **The gauntlet disagreeing with reality is the gauntlet
being wrong, not the deck choice being wrong.**

## Overnight inventory of work completed

- 3 GenericAPL-shim stubs for previously-uncovered Strixhaven brews
  (Izzet Control, Roaming Elementals, Mono Green Aggro) + their
  scraped decklists (placement-1 recent tournament samples)
- 3 pre-existing APL registrations that had been silently missing
  (Izzet Lessons, Superior Doomsday, Azorius Aggro)
- UTF-8 stdout fix for Windows redirect
- Narrow gauntlet launcher script
- This report

Commits (this task):
- `7fcecf6` stubs: 3 Strixhaven brews (GenericAPL shims)
- `603a6aa` narrow gauntlet: Izzet Lessons vs 5 post-Strixhaven brews
- `5279c2e` fix: utf-8 stdout for narrow gauntlet launcher
- `a91733b` registry: add missing Standard entries (Lessons, Doomsday, Azorius Aggro)
