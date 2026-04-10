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
1. Phase 3B: Interaction layer (removal, counters, discard on the stack)
2. Phase 3C: Evaluation function (Stockfish-style board scoring)
3. Variant testing (swap cards, re-sim, compare)
4. Pioneer deck file naming fix (5 matchups need mapping)
5. Standard Izzet Lessons/Prowess APL improvement

## PHASE 3A — MATCH ENGINE ✅ (2026-04-10)
- engine/match_state.py: MatchGameState wrapping two GameState instances
- engine/match_engine.py: run_match, run_match_set with full turn loop
- engine/parallel_match.py: 20-core parallel simulation (1861 games/sec)
- apl/match_apl.py: MatchAPL interface, GoldfishAdapter, GenericMatchAPL
- Combat: flying, first strike, double strike, trample, deathtouch, lifelink
- Smart blocking: trade/chump/eat/no-block decision tree
- Validated: 50K games in 27s, Boros Energy vs Izzet Prowess
- With real APLs: Izzet Prowess 84% vs Boros Energy (prowess triggers dominate)
