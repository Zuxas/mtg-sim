# MTG-Sim Master Plan — "Perfect Play" Ground-Up Build
# Updated: 2026-04-09

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
### P2 — Match-aware APLs ✅ (2026-04-10)
- apl/izzet_prowess_match.py: plot mechanic, Cori-Steel Flurry, burst-turn calc, combat tricks
- apl/boros_energy_match.py: removal targeting, lifegain priority, token blocking, Static Prison live
- apl/domain_zoo_match.py: Leyline Binding, Stubborn Denial, Prismatic Ending
- apl/mono_red_match.py: kill lifegain creatures, Searing Blaze live, Fireblast sac Mountains
- apl/murktide_match.py: counterspells live, Murktide delve, hold up counter mana
- apl/jeskai_blink_match.py: Solitude pitch, Consign counter, Ephemerate blink, Teferi bounce
- GenericMatchAPL upgraded: removal targeting, burn face, cast all spell types
- Slickshot Show-Off corrected: 1/2 flying haste +2/+0 per noncreature (not standard prowess)
- Cori-Steel Cutter corrected: Artifact — Equipment with Flurry (not a creature)
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

## FULL MODERN META SOLVE (2026-04-10) — 15 decks, 52,500 games, 16.0s
6 custom APLs: Boros, Prowess, Zoo, Mono Red, Murktide, Jeskai Blink
Rank  Deck              Field WR  Worst MU
1     Boros Energy      82.8%     Esper Blink 68%
2     Esper Blink       65.9%     Boros Energy 32%
3     Orzhov Blink      65.6%     Boros Energy 31%
4     Jeskai Blink      58.1%     Boros Energy 29%
5     Goryo's Vengeance 55.5%     Esper Blink 26%
6     Izzet Prowess     53.5%     Boros Energy 30%
7     Eldrazi Tron      52.3%     Orzhov Blink 23%
8     Eldrazi Ramp      50.9%     Esper Blink 19%
9     Dimir Murktide    48.8%     Boros Energy 21%
NOTE: Jeskai dropped 72%->58% with match APL — Solitude pitch has real costs
(pitch card + give opp life). More realistic than generic 72%.
Combo decks (Breach) still 0-6%. Performance: 3,281 g/s on 16 cores.

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

## P1 BO3 MATCH ENGINE ✅ (2026-04-10)
- engine/bo3_match.py: real 3-game matches using Phase 3A match engine
- Game 1 pre-board, Games 2-3 post-board with actual card swaps
- Loser of previous game goes first (play/draw alternation)
- Per-game win rates tracked (G1, G2, G3 independently)
- Game 3 rate tracked (how often matches go the distance)
- Integrates with existing engine/sideboard.py for SB plan parsing
- Validated: 200 Bo3 matches in 1.3s (155 matches/sec)
