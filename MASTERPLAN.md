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
- apl/affinity_match.py: Cranial Plating equip, metalcraft Blast, free creatures, Overseer pump
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

## FULL MODERN META SOLVE (2026-04-10) — 15 decks, 52,500 games, 17.0s
7 custom APLs: Boros, Prowess, Zoo, Mono Red, Murktide, Jeskai Blink, Affinity
Rank  Deck              Field WR  Worst MU
1     Boros Energy      80.0%     Esper Blink 68%
2     Esper Blink       62.9%     Boros Energy 32%
3     Orzhov Blink      62.8%     Boros Energy 31%
4     Jeskai Blink      55.0%     Boros Energy 29%
5     Goryo's Vengeance 52.6%     Esper Blink 29%
6     Izzet Prowess     52.5%     Boros Energy 30%
7     Eldrazi Tron      48.2%     Esper Blink 26%
8     Eldrazi Ramp      46.7%     Esper Blink 21%
9     Izzet Affinity    44.7%     Boros Energy 22%
10    Dimir Murktide    44.4%     Boros Energy 17%
NOTE: Combo decks (Breach) still 0-6% — need graveyard combo model.
7 of 15 decks have custom APLs + upgraded GenericMatchAPL for rest.
Performance: 3,088 g/s on 16 cores. Total: 52,500 games in 17s.

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
