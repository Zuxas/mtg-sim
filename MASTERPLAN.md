# MTG-Sim Master Plan -- "Perfect Play" Ground-Up Build
# Last updated: 2026-04-27 (post-Phase-3 + 100k canonical headline)

## DEFINITIVE CANONICAL HEADLINE (2026-04-27)

**Boros Energy 100k Modern field-weighted: 65.8%** (1.4M games, 42min wall,
post-everything-2026-04-27 engine). Supersedes the 71.5% number from
commit `0bc20bf`, which was on the stub canonical + pre-Phase-1+4 engine
+ double-firing handlers + pre-canonical-alignment.

Sample-size validation: 1k preview at 65.6% (commit `972de04`) matched
within +/-0.2pp. Methodology robust.

Cumulative session work converging to this number:
- Foundation alignment (`7e213ea` + `0c0f42c`)
- Voice + Guide ETB double-firing fix (`8fc9b82`)
- Match-runner Phase 1 main_phase2 wiring (`a31f360`)
- Match-runner Phase 4 turn-order asymmetry (`9721329`)
- Canonical-deck alignment to .txt (`362b04c`)
- Match-runner Phase 3 combat keywords partial (`972de04`)

Phase 3.5 (full keyword-effects coverage) in progress -- 11-stage arc
will produce a NEW 100k headline after completion.

## CURRENT STATE (2026-04-26)

### Engine
- Foundation stable (post-2026-04-26 fix, commits 7e213ea + 0c0f42c).
  Committed engine self-consistent; previously had load-bearing
  uncommitted WIP that crashed goldfish on stash.
- Transform infrastructure complete (T1.3+T1.4 arc, 2026-04-26
  morning): DFC fields, gs.transform mechanic, planeswalker dispatch,
  saga transform, Ajani Avenger + Roku/Avatar Roku consumers.
- Match-runner Phase 1 shipped (2026-04-26 morning, commit a31f360):
  main_phase2 wired into both-sides sim. Mono Red, Phlage hardcast,
  Bombardment lethal sac, Ocelot end-step now fire in match mode.
  Phase 2 (combat triggers) + Phase 3 (combat keywords) + Phase 4
  (turn-order asymmetry) remain fresh-session work.
- Determinism arc: Stage 1.5 + 1.6 partial fixes shipped. Stage 1.7
  (event_bus suspected) specced for fresh session. Within-matchup
  parallelism (3-5x gauntlet wall reduction) blocked on Stage 1.7.
- Two double-firing handler bugs resolved (commit 8fc9b82): Voice
  Mobilize damage and Guide ETB life/energy. Guide attack-trigger
  has similar pattern flagged for fresh-session.

### Boros Energy APL (canonical)
- Variant-adaptive role refactor complete (Phase 1+2). Same APL
  handles canonical 75 + Voice/Pyromancer attrition variants
  automatically via _compute_roles().
- SPECIAL_MECHANICS dispatch: Phlage, Ajani (front+Avenger), Ocelot
  (incl city's blessing T2.4), Guide pump, Arena haste, Bombardment
  (lethal + T2.3 GY-fill), Pyromancer (loot + GY activation), Voice
  Mobilize, Avatar Roku firebending.
- Goldfish baseline (post-Voice+Guide-fix, current canonical):
  99.9% WR, T4.72 avg, T5 median, T4 share 43.1%.
- Modern field-weighted (1k seed=42, post-Phase-1): 69.1%. Mono Red
  corrected from 99.9% (artifact) to 58.3%.

### Variant Jermey 75 (validated for tournament play)
- 4 Ragavan / 4 Ocelot / 4 Guide / 4 Phlage / 4 Ajani / 3 Voice /
  1 Screaming Nemesis / 2 Pyromancer / 4 Galvanic / 2 Thraben Charm /
  1 Bolt / 3 Bombardment / 1 Blood Moon MB / 23 lands.
- Goldfish: 100% WR, T4.40 avg, T4 median, T4 share 58.6%.
- Modern field-weighted (1k post-Phase-1): 82.8%.
- Variant edge over canonical: -0.32 turn goldfish, +13.7pp gauntlet.
- Sleeve-up read: variant for fast field, canonical for grindy.

### Tooling
- sleeve_check.py (commit 5801804): variant-vs-canonical comparison
  runner with --gauntlet flag. Copy-to-clipboard readout.
- parallel_launcher.py + dashboard.py: ASCII-only fixes shipped.
- 8 tracked engine files committed today; 3 orphan engine files
  (card_priority/telemetry/oracle_parser) flagged for triage.

### Open architectural findings (fresh-session work, all specced)
- Match-runner Phase 2 (combat triggers): ~45-60 min
- Match-runner Phase 3 (combat keywords): ~60-90 min
- Match-runner Phase 4 (turn-order asymmetry): ~30-45 min
- Stage 1.7 (event_bus determinism): ~30-60 min
- Guide attack-trigger double-firing: ~30 min
- Three orphan engine files triage: decision-needed
- All findings documented in `harness/knowledge/tech/`.

---

## HISTORICAL -- 2026-04-09 baseline (preserved below for reference)

## ENGINE ✅
- Summoning sickness, tapped state, turn_entered
- Turn order: main1 → combat → main2
- Fetch land resolution (smart: basic > shock > tapped dual)
- Shock land life, enters-tapped, Arena of Glory, exert
- State-based actions (0 toughness, legend rule)
- Pre-combat vs post-combat spell sequencing
- Prowess mechanic (+1/+0 per noncreature spell)
- CardDB art series deprioritization fix

## 4 FORMATS OPERATIONAL

### Modern — 15 decks, 100k gauntlet ✅
| Deck | Meta% | Goldfish |
|------|-------|----------|
| Boros Energy (YOUR 75) | 22.1% | 100% T5.0 |
| Burn | 4.1% | 100% T5.5 |
| Izzet Prowess | 7.2% | 100% T5.7 |
| Murktide | 3.5% | 100% T6.5 |
| Affinity | 6.8% | 85% T6.1 |
| + 10 more decks | | |

**Boros Energy: 65.3% field-weighted (1.4M games, 45s)**

### Legacy — 15 decks ✅
**Humans: 51.5% field-weighted (15k games)**

### Standard — 14 decks ✅
**Boros Aggro: 45.5% field-weighted (140k games)**

### Pioneer — 15 decks ✅
**Izzet Prowess: 50% field-weighted (140k games)**

## BOROS ENERGY APL — Oracle-Verified
- Ocelot Pride: end-step tokens on lifegain
- Ajani: 2/1 Cat token ETB, transform when Cats die
- Phlage: hardcast → 3 bolt + sacrifice, escape → 6/6 + bolt on attack
- Guide of Souls: "whenever you attack" + 3E → +2/+2 flying
- Arena of Glory: exert for haste
- Goblin Bombardment: lethal-only sacrifice
- Galvanic Discharge: +3 energy (target own creature)
- Smart fetch: basic > shock when need mana, Parlor when don't

## INFRASTRUCTURE
- db_bridge.py: 35K+ tournament decks across 4 formats
- 59 deck files auto-pulled from DB
- 15+ APLs (7 new this session)
- Consensus 75 analysis from 1,328 Boros Ocelot lists
- test_all_modern_apls.py / test_standard_apls.py / test_pioneer_apls.py

## NEXT PRIORITIES
### P0 — Graphify setup ✅ (2026-04-10)
### P1 — Bo3 match support ✅ (2026-04-10)
### P2 — Match-aware APLs ✅ (2026-04-10) — 13 of 15 decks
- apl/izzet_prowess_match.py: plot mechanic, Cori-Steel Flurry, burst-turn calc, combat tricks
- apl/boros_energy_match.py: removal targeting, lifegain priority, token blocking, Static Prison live
- apl/domain_zoo_match.py: Leyline Binding, Stubborn Denial, Prismatic Ending
- apl/mono_red_match.py: kill lifegain creatures, Searing Blaze live, Fireblast sac Mountains
- apl/murktide_match.py: counterspells live, Murktide delve, hold up counter mana
- apl/jeskai_blink_match.py: Solitude pitch, Consign counter, Ephemerate blink, Teferi bounce
- apl/affinity_match.py: Cranial Plating equip, metalcraft Blast, free creatures, Overseer pump
- apl/esper_blink_match.py: Solitude pitch, Fatal Push, Thoughtseize disruption, Ephemerate
- apl/eldrazi_tron_match.py: Tron assembly, TKS hand exile, Karn tutor, Chalice lock, All Is Dust
- apl/eldrazi_ramp_match.py: Eldrazi Temple, ramp spells, Emrakul cost reduction, Kozilek's Return
- apl/goryos_match.py: Goryo's Vengeance reanimate, Faithless discard, Force of Negation counter
- apl/amulet_titan_match.py: Amulet of Vigor, bounce lands, Primeval Titan, Spelunking haste
- GenericMatchAPL upgraded: removal targeting, burn face, cast all spell types
- Only Grinding Breach + Temur Breach use GenericMatchAPL (dead decks per user)
### P3 — Eval weight calibration ✅ (2026-04-10)
- Grid search across 10 weight combinations, 600 samples from 3 matchups
- Default weights validated at 99.5% accuracy: material 1.0, tempo 0.5, clock 2.0, threats 1.5, resources 0.3
- Clock (race math) confirmed as dominant predictor — matches competitive MTG intuition
- Future: instrument mid-game eval to improve in-progress game predictions
### BACKLOG (non-Modern = low priority)
- Pioneer deck file naming fix
- Standard Izzet Lessons APL
- Website integration (inject sim data into playbooks)
- Web dashboard / Discord bot

## DEFINITIVE Bo3 META SOLVE (2026-04-10)
13 APLs + 66 SB plans, 21,000 Bo3 matches, 14.4s on 16 cores
Rank  Deck              Bo3 WR   Worst MU
1     Boros Energy      89.4%    Prowess 50% (coin flip)
2     Izzet Prowess     77.1%    Boros 50%
3     Eldrazi Ramp      57.9%    Prowess 24%
4     Jeskai Blink      54.6%    Prowess 15%
5     Orzhov Blink      49.0%    Boros 7%
ANSWER: Play Boros or Prowess — nothing else close in Bo3.

## FULL MODERN G1 META SOLVE (2026-04-10) — 15 decks, 52,500 games, 15.2s
13 custom APLs covering all non-Breach decks
Rank  Deck              Field WR  Worst MU
1     Boros Energy      80.9%     Prowess 51%
2     Izzet Prowess     70.6%     Boros 49%
3     Eldrazi Ramp      58.6%     Prowess 36%
Performance: 3,454 g/s on 16 cores.

## PHASE 3A — MATCH ENGINE ✅ (2026-04-10)
- engine/match_state.py: MatchGameState wrapping two GameState instances
- engine/match_engine.py: run_match, run_match_set with full turn loop
- engine/parallel_match.py: 20-core parallel simulation (1861 games/sec)
- apl/match_apl.py: MatchAPL interface, GoldfishAdapter, GenericMatchAPL
- Combat: flying, first strike, double strike, trample, deathtouch, lifelink
- Smart blocking: trade/chump/eat/no-block decision tree
- Validated: 50K games in 27s, Boros Energy vs Izzet Prowess

## PHASE 3B — INTERACTION LAYER ✅ (2026-04-10)
- engine/stack.py: simplified spell stack (cast → respond → resolve LIFO)
- 60+ spells classified: removal, counter, discard, burn, bounce, wrath, pump
- Oracle text heuristic fallback for unknown spells
- Reactive interaction wired into turn loop (after main phase 1)
- Resolution: kill creatures, deal damage, discard cards, bounce, wrath boards

## PHASE 3C — EVALUATION FUNCTION ✅ (2026-04-10)
- engine/evaluator.py: 5-component board scoring
- Components: material (keyword-weighted), tempo, clock (race math), threats (unanswered evasion), resources (hand+GY+energy)
- Keyword multipliers: flying 1.4x, deathtouch 1.5x, double strike 1.6x, etc.
- evaluate_breakdown() for per-component debugging
- Validated: tracks game momentum correctly (T4 +4 → T8 -7 → T10 +21)

## PHASE 3D — VARIANT TESTING ✅ (2026-04-10)
- engine/variant.py: compare_variants() + field analysis
- Swap cards, re-sim, compare win rates
- Field-weighted analysis across multiple opponents
- Validated: "Phlage -> Bolt" = +0.3% vs Prowess but -1.0% field-weighted

## PHASE 3E — META SOLVER ✅ (2026-04-10)
- engine/meta_solver.py: parallel matchup matrix + field-weighted ranking
- Runs every deck vs every deck, computes full NxN matrix
- Field-weighted win rate = expected performance at a tournament
- Validated: 4-deck Modern field, 3000 games in 3.7s (16 workers)
- Output: ranked deck list + matchup matrix + recommendation

## RC TOURNAMENT SIMULATION (2026-04-10)
1000 events, 200 players, 8 rounds Swiss, Bo3 matchup data:
  Boros Energy:  5.4-2.6 avg | 11.3% Top8 | 42.9% Day2
  Izzet Prowess: 5.3-2.7 avg | 10.6% Top8 | 39.5% Day2
  Orzhov Blink:  4.7-3.3 avg |  1.8% Top8 | 15.0% Day2
  Everything else: <1% Top8 rate
ANSWER: Play Boros or Prowess. Nothing else is close.


15 decks, 21,000 Bo3 matches, 66 SB plans, 14.9s on 16 cores (1406/s)
Rank  Deck              Bo3 WR   G1 WR    Worst MU (Bo3)
1     Boros Energy      86.0%    80.0%    Prowess 50%
2     Izzet Prowess     74.5%    52.5%    Boros 50% ← SB plan is incredible
3     Orzhov Blink      66.8%    62.8%    Boros 31%
4     Esper Blink       64.0%    62.9%    Boros 24%
5     Jeskai Blink      52.9%    55.0%    Prowess 17%
KEY INSIGHT: Prowess jumps from 52.5% G1 to 74.5% Bo3 because
the +4 Unholy Heat SB plan flips most matchups post-board.
Boros vs Prowess = 50/50 in Bo3 (coin flip — matches competitive reality).
- engine/bo3_match.py: real 3-game matches using Phase 3A match engine
- Game 1 pre-board, Games 2-3 post-board with actual card swaps
- Loser of previous game goes first (play/draw alternation)
- Per-game win rates tracked (G1, G2, G3 independently)
- Game 3 rate tracked (how often matches go the distance)
- Integrates with existing engine/sideboard.py for SB plan parsing
- Validated: 200 Bo3 matches in 1.3s (155 matches/sec)
