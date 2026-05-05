# mtg-sim TODO

## Active priorities (2026-05-04, resumed -- COMPLETED 3 tasks, commit b6fcfb3)

### COMPLETED THIS SESSION (2026-05-04 resume)

1. [x] **Ashling, Rekindled oracle fix** — DONE (commit b6fcfb3)
   - Handler docstring fixed: 2/1 -> 1/3 (oracle-correct P/T)
   - Handler loot ETB already correct: discard -> draw
   - GrixisElementalsMatchAPL: Rimebound flip modeled as -1U +2flex mana each turn
     (accelerates Sunderflock when Ashling is on board)

2. [x] **Izzet Lessons matchup inversion** — PARTIAL FIX (commit b6fcfb3)
   - Added main_phase2_match proxy to IzzetLessonStandardMatchAPL
   - Lessons vs Selesnya: 25% -> 62.6% (target ~75%; remaining 12pp = no stack model)
   - Lessons vs Mono-Green: now 54.8% (target ~42%; same structural gap)
   - Conditions: T5+engine+hand>=4 OR T4+Monument+engine>=2+hand>=3 OR T3+engine>=2+hand>=4 OR T4+engine+hand>=6
   - Remaining gap filed as IMPERFECTION: lessons-inversion-structural-gap

3. [x] **Mulligan logic overhaul** — DONE (commit b6fcfb3)
   - Added keep_vs_opp() to AwareMatchAPL base class
   - vs Rhythm (SimicRhythm/BantRhythm/etc.): mull without T1 ramp
   - vs combo (SultaiReanimator): keep only if fast clock OR disruption
   - vs control (IzzetLessons/Jeskai/etc.): any 2-lander fine, don't fish
   - Added keep() override that delegates when _opp_key set (match_engine wires it)

### NEXT: Standard gauntlet re-run vs PT Lorwyn Eclipsed field
   `_opp_key` which is already set at match start.

### COMPLETED this session (2026-05-04)

#### Guide-mining pass
- [x] Read 671-guide DB — fetched 15+ long-form guides from RIW Hobbies, Decktionary, TCGPlayer,
      mtg.cardsrealm, ultimateguard.com, magic.gg
- [x] Exact sideboard plans applied: Spellementals (RCQ winner), Selesnya Landfall, Mono Green
      Landfall, Dimir Excruciator, Sultai Reanimator — all from real guide data
- [x] Oracle text verified for 20+ Lorwyn Eclipsed cards: Nature's Rhythm, Spider Manifestation,
      Gene Pollinator, Formidable Speaker, Craterhoof Behemoth, Seam Rip, Mockingbird,
      Bringer of the Last Gift, Superior Spider-Man, Oblivious Bookworm, etc.

#### PT Lorwyn Eclipsed meta shift
- [x] Discovered meta shift: Simic Rhythm 15.7% + Bant Rhythm 15.0% + 5C Rhythm 2.9% = 34.6% field
- [x] Simic Rhythm APL: full rewrite (Nature's Rhythm = {X}{G}{G} tutor sorcery, Craterhoof ETB pump)
- [x] Bant Rhythm APL: dedicated APL (Leyline Weaver/Spider Manifestation, Seam Rip {W} exile MV<=2)
- [x] Sultai Reanimator APL: Superior Spider-Man copies Bringer, Formidable Speaker discard-tutor,
      Oblivious Bookworm end-step draw/discard
- [x] Grixis Elementals APL: Requiting Hex + Deceit, Sunderflock reset, Clarion Conqueror SB
- [x] Izzet Blink APL: Thundertrap Trainer blink loop, Splash Portal draw engine

#### APL quality improvements
- [x] Jeskai Control: replaced Modern proxy (Teferi/Verdict) with Standard cards (Get Lost/Lockdown)
- [x] Jeskai Oculus: replaced Strixhaven storm proxy with current Proft's Eidetic Memory version
- [x] OPP_THREAT_MODEL: 24 → 39 archetypes, all with guide-sourced values
- [x] BLINK_BAIT: 8 → 19 entries (Craterhoof, Bringer, Superior Spider-Man, Mockingbird, etc.)
- [x] DANGEROUS_ATTACKERS: 7 → 8 entries (Gran-Gran, Icetill Explorer, Traveling Chocobo)

#### Coverage
- [x] 14/14 PT Lorwyn Eclipsed archetypes (2%+ field share) — 100% covered and load-tested
- [x] 115/134 total match APLs (85%) — all Standard covered, remaining 19 are Modern/Legacy

### Known model gaps (P1)
- **Ashling handler** — fixed: docstring corrected, Rimebound flip modeled (commit b6fcfb3)
- **Izzet Lessons inversion** — partially fixed: 25%->62.6% vs Selesnya; 12pp gap = structural (no stack model)
- **Mulligan awareness** — fixed: keep_vs_opp() in AwareMatchAPL (commit b6fcfb3)
- Mana model: `reserve_mana()` approximation only (known limitation)
- Domain Zoo P/T propagation bug (pre-existing, low priority)

### P0 -- Match-runner combat gap, remaining phases

### P0 -- Match-runner combat gap, remaining phases
Phase 1 SHIPPED at commit a31f360. Phases 2/3/4 fresh-session work,
all specced at
`harness/knowledge/tech/match-runner-combat-gap-2026-04-26.md`:
- Phase 2 (combat trigger dispatch): ~45-60 min. Wires
  `_simulate_combat_triggers` into match-runner. Voice/Phlage attack
  triggers, Ragavan treasures, Guide attack pump, Avatar Roku
  firebending. BE gauntlet predicted to shift modestly upward;
  variant likely gains more than canonical.
- Phase 3 (combat keywords): ~60-90 min. First strike, lifelink,
  deathtouch, trample, flying-vs-blocker. Refactor `_resolve_combat`
  to share with goldfish `_do_combat`.
- Phase 4 (turn-order asymmetry): ~30-45 min. Fix structural ~6pp
  player-A advantage in mirror matches. Surfaced incidentally during
  Phase 1 validation.

### P0 -- Stage 1.7 determinism (unblocks parallelism)
Specced at
`harness/knowledge/tech/perf-within-matchup-parallelism-2026-04-26.md`.
~30-60 min. Event_bus is highest-suspicion candidate. After Stage 1.7
lands, Stage 1 perf parallelism (3-5x gauntlet wall reduction)
unblocks.

### P1 -- Guide attack-trigger double-firing
Third double-firing pattern from 2026-04-26 morning. Smaller impact
than Voice + Guide ETB (only fires when Guide attacks). ~30 min.
Findings doc:
`harness/knowledge/tech/double-firing-handler-bugs-2026-04-26.md`
Remaining Triage section.

### P1 -- Three orphan engine files triage
`engine/card_priority.py` (357 lines), `engine/card_telemetry.py`
(261), `engine/oracle_parser.py` (322). Untracked, no importers.
Decide: wire up, finish, or delete. Findings doc:
`harness/knowledge/tech/load-bearing-wip-2026-04-26.md` Resolution >
Remaining triage.

### P2 -- IzzetProwess role refactor
Apply BE Phase 1+2 template. ~3-4 hours fresh session.
Spec: `harness/knowledge/tech/apl-role-refactor-2026-04-25.md`.

### P2 -- Standard *_match.py WIP triage
12 modified + 3 untracked match-mode APL files sitting since
2026-04-23. Cleanup. ~30 min.

### Tournament-relevant
- PT Strixhaven May 1-3 -> post-PT pipeline exercise
- Standard RC May 29 deck-lock around May 11-12

---

## SUPERSEDED -- 2026-04-23 sim framework MVP work
(Original tomorrow's-work item from 2026-04-23 overnight session.
The MVP fix described below was shipped weeks ago. The actual current
match-runner issue is the combat gap above, not the APL-not-invoked
claim. Preserved for context.)

## Tomorrow's work — sim framework MVP fix (surfaced 2026-04-23 overnight)

- **`engine/match_runner.py:_simple_play_turn` does not invoke APLs.**
  Accepts an `apl` parameter, never references it. Same function is
  used by Path A (Bo3 via `run_bo3_set` → `run_match`) and Path B
  (heuristic `run_match_set`). Every matchup sim ever run has played
  "one land + cheapest creatures" for both sides, ignoring APL logic
  and the 2,009-handler registry entirely.

- **MVP diff: ~40 lines to wire APL into `_simple_play_turn`.**
  Build a GameState view over TwoPlayerGameState's per-player flat
  fields (hand/bf/gy/lib lists alias directly — mutations propagate),
  populate view.mana_pool from lands-in-play (colorless approximation),
  call `apl.main_phase(view)` + `apl.main_phase2(view)`. Sync back
  land_played flag.

- **Verified: registry will fire once MVP lands.** Chain is
  `main_phase` → `_cast_all_castable` → `gs.cast_spell` → branches to
  `on_spell_resolve` (hits `SPELL_EFFECTS.get`) for spells or
  `_fire_etb_triggers` (hits `ETB_EFFECTS`) for permanents. Both
  confirmed in `engine/card_effects.py:736` and `game_state.py`.

- **Error handling: warn+continue by default, raise on `SIM_DEBUG=1`.**
  No silent-pass. Loud warnings during MVP stabilization.

- **Gated validation sequence:**
  1. 1 game with full logging — confirm APL runs, spells cast,
     game reaches > 3 turns
  2. 100 games with turn-count distribution — confirm median turn > 3,
     no turn-1 bailouts
  3. 5k-per-matchup narrow gauntlet — compare FWR to tournament 49.5%
     ballpark for Izzet Lessons
  4. 25k-per-matchup — only after step 3 looks sane

- **Known MVP limits (accept for initial validation):**
  - Colorless-mana approximation — color-requiring spells may cast
    when they shouldn't. Separate 15-30 line diff after MVP works.
  - Uses `main_phase(gs)` (goldfish) not `main_phase_match(gs, opp)`
    (opp-aware). APL plays without reacting to opponent. Upgrade
    requires opponent GameState to be accessible — another 30-50 lines.

- **Scope revised from "multi-day project → defer to post-RC" to
  "~1 day MVP, bounded risk."** Still makes RC-prep calculus:
  if MVP + Gate C produce sane FWR, sim validates sideboard work;
  if MVP fails or Gates stay red, fall back to tournament-data-only
  RC prep with no time lost vs prior plan.

## RC prep (active — May 29 Standard RC)

- **Tomorrow (2026-04-24): APL stubs for 3 Strixhaven brews.**
  Decks: Izzet Control, Roaming Elementals, Mono Green Aggro.
  None have decklists or APLs. Scrape representative decklists from
  mtg_meta.db deck_cards rows (filter by archetype + last 30 days,
  pick a high-placement sample). Create `apl/<slug>.py` as
  `GenericAPL` shims, register in `APL_REGISTRY`. Expected effort:
  ~90-135 min for all 3.

- **After stubs: narrow gauntlet.** Izzet Lessons (locked deck) vs
  the 5 Strixhaven brews at 25k games per matchup. 2 brews (Superior
  Doomsday, Azorius Aggro) already have APL+decklist ready. Gauntlet
  covers the 25% of post-Strixhaven meta that tournament-data can't
  reach yet (no samples because too new). Expected ~1-2 hours.

- **Priors file.** User's tier-feel for each of the 5 original
  candidates goes in `docs/priors-2026-04-23.md` when pasted. Compare
  against the real-world FWR data when re-evaluating after the
  May 15-17 RC meta shift.

- **Decision anchor (for May 13 deck-lock).** Izzet Lessons chosen
  based on matchup_matrix data: 49.5% FWR, 4.0% stddev, no scary
  matchups in covered 75% of meta, 7,182 matches of evidence. The
  4% stddev is the meta-shift-resilience property that justifies
  committing before May 15-17 reshuffles the field.

## Metrics to build

- **Cast-weighted coverage for current-Standard.** One-off script that,
  given the handler file and mtg_meta.db, reports "X% of Standard
  deck-slots in the last N weeks are covered by registered handlers."
  Meta-share-weighted, not card-count-weighted. The card-count number
  (now 2004 of 2172 played-and-legal Standard cards, ~92%) doesn't
  tell you when the sim is ready for the RC — the weighted number does.
  If a given wave pushes weighted coverage from 85%→95%, the loop is
  still paying; once it plateaus near 98% and starts rising in 0.1%
  increments the loop has hit diminishing returns and the next move is
  telemetry/validation work, not more handlers. Not urgent — not
  blocking Wave 2 or 3 — but worth building before a "is Standard done"
  decision comes up.

## Reporting bugs (not blocking)

- **Handler-coverage AST scanner misses direct-assignment registrations.**
  `scripts/build_priority_queue.py` and the Step 1 validator in
  `.claude/commands/validate-and-run.md` both walk the AST for
  `_SPELL_HANDLERS` / `_ETB_HANDLERS` dict literals only. They do not
  catch handlers registered via `ETB_EFFECTS[name] = fn` or
  `SPELL_EFFECTS[name] = fn` direct assignments (loop-style). Live-import
  count is 1986; AST union is 1956 — 30 handlers hidden from the scanner.
  Fix: extend the walker to also collect `ast.Assign` where target is
  `ast.Subscript` with value `ETB_EFFECTS` or `SPELL_EFFECTS` and slice
  is a string constant. Reporting bug only — the handlers work at runtime.
  Surfaced 2026-04-22 during first `/validate-and-run` dry run.
