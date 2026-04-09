# MTG-Sim Architecture Map
# Read this FIRST before working on the codebase.
# Last updated: 2026-04-09

## GOD NODES (most connected, touch these carefully)

1. **engine/game_state.py** (836 lines) — THE core. Turn loop, combat, mana,
   zones, ETB triggers, state-based actions, fetch/shock land resolution, 
   prowess tracking. Every APL depends on this.

2. **apl/base_apl.py** (290 lines) — Turn loop driver. Calls gs.run_turn(),
   self.main_phase(), gs.run_combat(), self.main_phase2(), gs._end().
   All APLs inherit from BaseAPL.

3. **data/card.py** (165 lines) — Card dataclass. Fields: name, mana_cost,
   cmc, type_line, oracle_text, power, toughness, tags, counters, tapped,
   turn_entered, summoning_sickness.

4. **engine/card_db.py** (266 lines) — Scryfall card database. 37K cards.
   CRITICAL: prefers game cards over art series prints (fixed 2026-04-09).
   Source: ../mtg-meta-analyzer/data/rules_reference/scryfall_oracle_cards.json

5. **data/deck.py** (182 lines) — Deck loader. Parses text → Card objects.
   Uses CardDB for enrichment. DFC_CORRECTIONS dict for known bad data.

## CALL FLOW (how a simulation runs)

```
parallel_launcher.py → run_matchup.py → parallel_sim.py
                                            ↓
                                    APL.run_game(mainboard)
                                            ↓
                                    take_opening_hand() [mulligan.py]
                                            ↓
                                    TURN LOOP (base_apl.py):
                                      gs.run_turn()     → untap, upkeep, draw
                                      gs.tap_lands()    → mana from untapped lands
                                      apl.main_phase()  → PRE-COMBAT decisions
                                      gs.run_combat()   → declare attackers, damage
                                      apl.main_phase2() → POST-COMBAT decisions  
                                      gs._end()         → cleanup
```

## TURN ORDER (fixed 2026-04-09, was broken before)
main1 → combat → main2 (correct)
NOT: combat → main1 → main2 (old broken order)

## KEY ENGINE FEATURES
- Summoning sickness: creatures can't attack turn they enter (unless haste)
- Tapped state: lands track tapped, no double-tapping
- Fetch lands: sacrifice → search library → smart target → shuffle (1 life)
- Shock lands: pay 2 life for untapped (goldfish always pays)
- Enters-tapped: Elegant Parlor always, Arena of Glory without Mountain, fast lands >2
- Exert: Arena of Glory exert skips next untap
- State-based actions: 0 toughness death, legend rule
- Prowess: +1/+0 per noncreature spell cast this turn
- Bombardment: only sacrifice for lethal (was eating board before)


## APL MAP (deck-specific logic)

### Modern (15 decks)
| APL File | Deck | Key Mechanics |
|----------|------|---------------|
| boros_energy.py | Boros Energy (YOUR deck) | Ocelot end-step tokens, Ajani 2/1 ETB, Phlage hardcast+escape, Arena haste, Bombardment lethal, Guide energy, Ragavan treasure |
| burn.py | Mono Red/Burn | Face spells (Bolt 3, Spike 3, Charm 4), Roiling Vortex 1/turn |
| izzet_affinity.py | Izzet Affinity | 0-drop dump, Cranial Plating +artifacts power, Galvanic Blast metalcraft |
| modern_domain_zoo.py | Domain Zoo | Leyline free T0, Scion domain cost reduction, Bolt face, Phlage |
| dimir_murktide.py | Dimir Murktide | Ragavan haste+treasure, cantrips fill GY, Murktide delve 8/8+, Bolt |
| ruby_storm.py | Storm (Teg) | Ral flips after 3 spells → 1 dmg/spell, Medallion cost reduction, PiF replay GY |
| eldrazi_ramp.py | Eldrazi Ramp | Temple +1 mana for Eldrazi, Emrakul cost reduction by GY types |
| izzet_prowess.py | Izzet Prowess | Prowess engine, cantrips |
| amulet_titan.py | Amulet Titan | Existing |
| goryo_vengeance.py | Goryo's Vengeance | Existing |
| eldrazi_tron.py | Eldrazi Tron | Existing |
| esper_blink.py | Esper Blink | Existing |
| generic_apl.py | Jeskai/Orzhov Blink | Curve out, attack |

### Standard (14 decks)
- standard_aggro.py: universal for Mono Red, Gruul, Boros, Dimir Aggro, Izzet Prowess
- generic_apl.py: midrange/control/combo decks

### Legacy (15 decks)  
- humans.py: Humans (detailed pre/post combat, Champion/Lieutenant/Guide synergy)
- + existing APLs for Delver, Elves, Reanimator, etc.


## DATA SOURCES

| Source | Path | Contents |
|--------|------|----------|
| Scryfall Oracle | ../mtg-meta-analyzer/data/rules_reference/scryfall_oracle_cards.json | 37K cards, oracle text, P/T |
| Tournament DB | ../mtg-meta-analyzer/data/mtg_meta.db | 35K+ decks, 5K events, 1.7M card entries |
| Saved Decks | mtg_meta.db → saved_decks table | 14 curated 75s (Team Resolve gauntlet + MXP prep) |
| Format Config | format_config.py | Meta shares, combo flags, kill distributions for 4 formats |
| Deck Files | decks/*.txt | 59 deck files (auto-pulled from DB via db_bridge.py) |

## db_bridge.py — Key Functions
- load_saved_deck(name, format) → deck text from curated 75s
- load_tournament_deck(archetype, format, top) → deck text from tournament data
- get_meta_field(format) → {archetype: share%} dict
- list_saved_decks() / list_meta_archetypes() → discovery

## KNOWN ISSUES / TECH DEBT
1. Phlage Scryfall data is bugged (CMC 0, empty oracle) — hardcoded in APL
2. Some DFC cards need DFC_CORRECTIONS in deck.py
3. Storm APL at 25-30% win rate — needs better combo sequencing
4. Pioneer parallel_launcher: 5 matchups fail on deck name mapping
5. Standard Izzet Lessons: 0% win (combo, needs specific APL)
6. Gauntlet G1 win rates use estimator, not actual goldfish-vs-goldfish (needs Phase 3)

## VALIDATED RESULTS (2026-04-09)
- Modern 100k gauntlet: Boros Energy 65.3% field-weighted (1.4M games, 45s)
- Legacy gauntlet: Humans 51.5% (15K games)
- Standard gauntlet: Boros Aggro 45.5% (140K games)
- Pioneer gauntlet: Izzet Prowess 50% (140K games, partial)
- Boros Energy goldfish: 100% win, avg T4.92, 36% T4, 79% by T5
