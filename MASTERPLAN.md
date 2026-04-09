# MTG-Sim Master Plan — "Perfect Play" Ground-Up Build
# Updated: 2026-04-09

---

## ENGINE — Rules Foundation ✅

- [x] Summoning sickness, tapped state, turn_entered on all permanents
- [x] Turn order: main1 → combat → main2 (was broken: combat first)
- [x] Fetch land resolution (sacrifice → search → smart target → shuffle)
- [x] Smart fetch: basic > shock > tapped dual when need mana; reverse when don't
- [x] Fetch life cost (1 life per fetch from oracle)
- [x] Shock land life payment (2 life for untapped)
- [x] Enters-tapped: temples, gain lands, Elegant Parlor, fast lands, Arena of Glory
- [x] Arena of Glory conditional (untapped with Mountain in play)
- [x] Exerted permanents skip next untap
- [x] State-based actions (0 toughness death, legend rule)
- [x] Pre-combat vs post-combat spell sequencing
- [x] Main2 carries leftover mana from main1
- [x] CardDB: prefer game cards over art series/memorabilia prints

## MODERN — 15 Decks ✅

| Deck | Meta% | APL | Goldfish |
|------|-------|-----|----------|
| Boros Energy | 22.1% | boros_energy.py (verified oracle) | 100% T5.0 |
| Amulet Titan | 8.5% | amulet_titan.py | 75% T6.1 |
| Eldrazi Ramp | 7.4% | eldrazi_ramp.py (NEW) | 100% T8.2 |
| Izzet Prowess | 7.2% | izzet_prowess.py | 100% T5.8 |
| Izzet Affinity | 6.8% | izzet_affinity.py (NEW) | 85% T6.1 |
| Grinding Breach | 6.4% | ruby_storm.py (NEW) | 25% T10.6 |
| Jeskai Blink | 6.4% | generic | 100% T7.7 |
| Orzhov Blink | 6.1% | generic | 100% T8.2 |
| Goryo's Vengeance | 5.6% | goryo_vengeance.py | 100% T5.8 |
| Domain Zoo | 5.0% | modern_domain_zoo.py (NEW) | 95% T6.4 |
| Eldrazi Tron | 4.3% | eldrazi_tron.py | 85% T7.9 |
| Mono Red/Burn | 4.1% | burn.py (NEW) | 100% T5.5 |
| Temur Breach | 3.8% | ruby_storm.py | 25% T10.6 |
| Dimir Murktide | 3.5% | dimir_murktide.py (NEW) | 100% T6.5 |
| Esper Blink | 2.8% | esper_blink.py | 100% T8.9 |

**Modern Gauntlet: Boros Energy 65.3% field-weighted (1.4M games, 45s)**

## STANDARD — 14 Decks ✅

| Deck | Meta% | Goldfish |
|------|-------|----------|
| Dimir Midrange | 11.3% | 100% T7.3 |
| Mono Red Aggro | 10.6% | 95% T5.9 |
| Esper Raffine | 7.9% | 85% T9.5 |
| Dimir Aggro | 7.7% | 95% T7.8 |
| Izzet Prowess | 5.8% | 60% T8.8 |
| Gruul Aggro | 5.0% | 95% T5.9 |
| Domain Ramp | 4.6% | 90% T10.0 |
| Mono Green Landfall | 4.5% | 100% T9.0 |
| Boros Aggro | 4.3% | 100% T6.1 |
| Grixis Discard | 3.9% | 95% T9.8 |
| Izzet Lessons | 3.8% | 0% (combo) |
| Esper Pixie | 3.6% | 100% T7.3 |
| Four-Color Overlords | 3.4% | 95% T10.2 |
| Izzet Cauldron | 3.2% | 95% T8.2 |

## LEGACY — 15 Decks ✅

**Legacy Gauntlet: Humans 51.5% field-weighted (15k games)**

## INFRASTRUCTURE ✅

- [x] db_bridge.py: pull decks + meta from mtg-meta-analyzer (35K+ decks)
- [x] Consensus 75 analysis from tournament data
- [x] CardDB: art series deprioritization fix
- [x] All deck files auto-pulled from DB
- [x] test_all_modern_apls.py / test_standard_apls.py validation
- [x] MASTERPLAN.md tracking

## NEXT PRIORITIES

1. **Phase 3: Matchup Simulator** — two decks playing against each other
2. **Prowess mechanic** — spell-cast triggers pump for Swiftspear/Channeler
3. **Standard Izzet Lessons APL** — combo deck needs specific logic
4. **Pioneer format** — data exists, need APLs
5. **Variant testing** — swap cards, re-sim, compare (deck diff)
