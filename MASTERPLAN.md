# MTG-Sim Master Plan — "Perfect Play" Ground-Up Build
# Philosophy: Like SimC, assume the pilot plays perfectly. Every micro-decision
# must be correct because the rules engine underneath is correct.
# Status: [x] done | [~] exists but needs rework | [ ] not started

---

## PHASE 0 — Correct Rules Engine (foundation everything else sits on)

### 0A: Permanent State Tracking
Every permanent needs: tapped/untapped, turn_entered (for summoning sickness),
controller, attached_to (for equipment/auras), counters dict.

- [~] Card object — needs `tapped`, `turn_entered`, `summoning_sick` properties
- [ ] Tap/untap as explicit actions (tap to attack, tap for mana, untap in untap step)
- [ ] Summoning sickness — creatures can't attack or use tap abilities turn they enter
      UNLESS they have haste
- [ ] Lands track tapped state — no double-tapping for mana

### 0B: Mana System Upgrade
- [x] Color pip parsing and validation
- [x] Flex mana (Cavern, Ziggurat)
- [ ] Lands produce mana by TAPPING (not just "you have N lands = N mana")
- [ ] Multi-color land choice — when tapping a dual, WHICH color to produce matters
- [ ] Fetch land resolution — search library for a land, put it into play (tapped?)
- [ ] Mana ability timing — mana abilities don't use the stack

### 0C: Stack & Priority
- [ ] Spells go on the stack, resolve LIFO
- [ ] Priority passes between players (goldfish: we always have priority)
- [ ] Triggered abilities go on the stack when triggered
- [ ] State-based actions checked whenever a player would receive priority
- [ ] "Respond to trigger" decisions (relevant for opponent modeling later)

### 0D: Combat Overhaul
- [ ] Declare attackers step — choose WHICH creatures attack (not all of them)
- [ ] Summoning sick creatures excluded
- [ ] Tapped creatures excluded
- [ ] Declare blockers step (opponent side, for matchup sim)
- [ ] First strike / double strike damage ordering
- [ ] Trample — excess damage goes through
- [ ] Deathtouch — 1 damage is lethal to blocker
- [ ] Flying — can only be blocked by flying/reach
- [ ] Menace — must be blocked by 2+ creatures
- [ ] Lifelink — gain life equal to damage dealt
- [ ] Vigilance — doesn't tap to attack

### 0E: State-Based Actions
- [ ] Creature with 0 or less toughness → dies
- [ ] Creature with lethal damage marked → dies
- [ ] Player at 0 or less life → loses
- [ ] Legend rule — two legends with same name, sacrifice one
- [ ] +1/+1 and -1/-1 counters cancel
- [ ] Damage clears at end of turn (not between phases)

---

## PHASE 1 — Decision Engine ("Perfect Player" Brain)

This replaces hardcoded APL logic with a generic evaluator that finds the
optimal play given a correct rules engine.

### 1A: Legal Action Enumeration
- [ ] At any decision point, enumerate ALL legal actions
      (play land X, cast spell Y, activate ability Z, attack with subset S, pass)
- [ ] Filter by game rules (can we afford it? is it the right phase? summoning sick?)
- [ ] This is the "option tree" the perfect player considers

### 1B: Action Evaluation / Heuristic Scoring
- [ ] Score each legal action by how much it advances the win condition
- [ ] For goldfish: "which play maximizes expected damage by turn N?"
- [ ] For matchup: "which play maximizes win% given opponent's likely plays?"
- [ ] Land sequencing: score each possible land drop by future castability
      (e.g., T1 Plains over Ziggurat if we need W on T2 for specific spell)

### 1C: Main Phase 1 vs Main Phase 2 Decision
- [ ] "Should I cast this creature before or after combat?"
- [ ] Pre-combat: lords/anthems that buff existing attackers, ETB triggers that matter
- [ ] Post-combat: hold back info from opponent, haste doesn't matter if already attacked
- [ ] Flash creatures: hold for opponent's turn when possible

### 1D: Mulligan Intelligence
- [x] London mulligan mechanics
- [~] Keep/mull heuristics (exist per-APL but aren't evaluating future turns)
- [ ] Evaluate a 7-card hand by "what's my projected kill turn with this hand?"
- [ ] Bottom card selection by "which card hurts least to lose?"
- [ ] Hand scoring should use the SAME evaluation engine as in-game decisions

---

## PHASE 2 — Goldfish Simulator (your deck vs solitaire)

Built on correct rules + decision engine. Answers:
"With perfect play, what turn does this deck kill on average?"

- [x] Basic N-game Monte Carlo runner
- [x] Kill turn distribution
- [~] Turn loop (exists but needs Phase 0 fixes applied)
- [ ] Run with corrected summoning sickness, tap states, mana
- [ ] Variance + confidence intervals
- [ ] Parallel execution for speed
- [ ] Per-card statistics: "how often was Card X in my winning hands?"
- [ ] Mana curve analysis: "how often was I color-screwed?"

---

## PHASE 3 — Matchup Simulator (your deck vs their deck)

Two goldfish engines racing, with interaction model layered on.

- [~] Race model exists (clock-based)
- [ ] Opponent plays their own deck (mirror of our goldfish engine)
- [ ] Interaction hooks: "on turn N, opponent casts Thoughtseize" → our hand loses best card
- [ ] Disruption profiles per archetype (control plays wraths, aggro just races)
- [ ] Blocking model: opponent assigns blockers intelligently
- [ ] Sideboard transformation between games

---

## PHASE 4 — Estimator + Meta Analysis (tournament positioning)

- [x] Field-weighted win rates
- [x] Matchup matrix
- [~] Sideboard adjustments (heuristic, needs real sim data)
- [ ] Fed by REAL sim data from Phase 2/3 instead of heuristics
- [ ] Bo3 match modeling with actual sideboard swaps
- [ ] Meta share weighting
- [ ] "What 75 maximizes my field equity?" optimizer

---

## BUILD ORDER (what we work on, in sequence)

1. **NOW: Phase 0A** — Add tapped/summoning_sick state to Card & GameState
2. **NOW: Phase 0B** — Lands tap for mana, track tapped state
3. Phase 0D — Combat respects summoning sickness + tap state
4. Phase 0E — State-based actions (creatures die at 0 toughness)
5. Phase 1A — Enumerate legal actions at each decision point
6. Phase 1B — Score actions (replace hardcoded APL sequences)
7. Phase 1C — Main1 vs Main2 decision logic
8. Phase 2 — Re-run goldfish with correct engine, validate numbers
9. Phase 0C — Stack (needed before matchup interaction works)
10. Phase 3 — Two-player matchup sim
11. Phase 4 — Real sim data feeds estimator

---

## WHAT WE KEEP FROM CURRENT BUILD

- Card model + Scryfall integration (Layer 1) ✓
- ManaPool with color pip validation ✓ (needs tap integration)
- Zone manager ✓ (needs tap state on cards)
- Mulligan engine ✓ (keep logic needs upgrade in Phase 1D)
- Monte Carlo runner framework ✓
- Explain mode ✓ (update narration as engine changes)
- Gauntlet / estimator ✓ (Phase 4, fed by real data later)
- Claude API analysis integration ✓
