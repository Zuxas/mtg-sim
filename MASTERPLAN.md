# MTG-Sim Master Plan — "Perfect Play" Ground-Up Build
# Philosophy: Like SimC, assume the pilot plays perfectly. Every micro-decision
# must be correct because the rules engine underneath is correct.
# Status: [x] done | [~] exists but needs rework | [ ] not started
# Updated: 2026-04-08

---

## PHASE 0 — Correct Rules Engine ✅ (goldfish-complete)

### 0A: Permanent State Tracking ✅
- [x] Card object: `tapped`, `turn_entered`, `summoning_sickness` fields
- [x] Tap/untap as explicit actions (untap in untap step, tap for mana)
- [x] Summoning sickness enforced — creatures can't attack turn they enter
- [x] Haste creatures bypass summoning sickness
- [x] Lands track tapped state — no double-tapping

### 0B: Mana System ✅
- [x] Color pip parsing and validation
- [x] Flex mana (Cavern, Ziggurat)
- [x] Lands tap for mana with tapped state tracking
- [x] Fetch land resolution (sacrifice, search library, put into play, shuffle)
- [x] Shock land decision (pay 2 life in goldfish for speed)
- [x] Enters-tapped detection (temples, gain lands, fast lands, bridges)
- [x] Main2 carries leftover mana from main1 (was broken: 0 mana in main2)

### 0C: Stack & Priority — DEFERRED
- [ ] Stack needed for opponent interaction (Phase 3)
- [ ] Not needed for goldfish sim

### 0D: Combat ✅ (goldfish-complete)
- [x] Summoning sick creatures excluded from attackers
- [x] Tapped creatures excluded from attackers  
- [x] Haste override for summoning sickness
- [x] All eligible creatures attack (optimal for goldfish)
- [ ] Declare blockers (needed for matchup sim — Phase 3)

### 0E: State-Based Actions ✅
- [x] Creature with effective toughness <= 0 → graveyard
- [x] Legend rule — duplicate legends sacrifice the older one
- [x] SBAs checked after cast_spell, put_via_vial, before combat

---

## PHASE 1 — Decision Engine ✅ (core decisions implemented)

### 1A: Legal Action Enumeration — DEFERRED
- [ ] Generic "enumerate all legal actions" framework
- [ ] Not needed yet — deck-specific APLs handle decisions directly

### 1B: Action Evaluation — DEFERRED
- [ ] Generic scoring engine for legal actions
- [ ] Will build when we have multiple decks needing shared logic

### 1C: Pre-Combat vs Post-Combat ✅
- [x] Spells that increase combat damage → cast pre-combat
- [x] Lieutenant ETB pumps attacking Humans → pre-combat
- [x] Humans grow attacking Champion → pre-combat
- [x] Everything else → post-combat (summoning sick anyway)
- [x] Result: same hand kills T5 instead of T6

### 1D: Mulligan Intelligence
- [x] London mulligan mechanics
- [x] Opponent-aware keep logic (keep_vs)
- [x] ML model integration for borderline hands
- [ ] Project kill turn from hand composition
- [ ] Bottom selection by "which card hurts least to lose?"

### Land Sequencing ✅
- [x] Smart land selection for Humans (Cavern > flex > Plains > utility)
- [x] Considers non-creature spell needs in hand

---

## PHASE 2 — Goldfish Simulator ✅ (validated)

- [x] Monte Carlo runner (N-game goldfish)
- [x] Kill turn distribution
- [x] Correct turn loop with all Phase 0 fixes
- [x] 1000-game validation: avg kill T4.79, 39% T4 kills
- [x] Pre-combat sequencing produces faster kills
- [ ] Variance + confidence intervals
- [ ] Parallel execution (multiprocessing)
- [ ] Per-card statistics

---

## PHASE 3 — Matchup Simulator (NEXT MAJOR MILESTONE)

- [~] Race model exists (clock-based)
- [ ] Opponent plays their own deck (mirror goldfish engine)
- [ ] Interaction hooks (Thoughtseize, Wrath effects)
- [ ] Blocking model
- [ ] Sideboard transformation between games

---

## PHASE 4 — Estimator + Meta Analysis ✅ (functional)

- [x] Field-weighted win rates
- [x] Matchup matrix (15 matchups)
- [x] Sideboard adjustments (heuristic)
- [x] Parallel gauntlet runner (15 cores)
- [x] Validated: 51.5% field-weighted (realistic for combo-heavy meta)
- [ ] Fed by real sim data from Phase 3 instead of heuristics
- [ ] Bo3 match modeling with actual sideboard swaps

---

## VALIDATED RESULTS (2026-04-08, corrected engine)

Goldfish: avg kill T4.79 | 39% T4 | 85% by T5 | 100% win

Field-weighted match win: 51.5%
  Bad:  Reanimator 25.5%, Breakfast 18%, Eldrazi 21%, Sneak 30%
  Even: Painter 54.5%, Nadu 66%, Red Aggro 70%
  Good: Four-Color 82%, Delver 76.5%, Tempo 75%, DnT 74%
