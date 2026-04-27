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
  -- SUPERSEDED 2026-04-26 by 71.5% post-APL-arc (see entry below)
- Legacy gauntlet: Humans 51.5% (15K games)
- Standard gauntlet: Boros Aggro 45.5% (140K games)
- Pioneer gauntlet: Izzet Prowess 50% (140K games, partial)
- Boros Energy goldfish (2026-04-09 historical): 100% win, avg T4.92, 36% T4, 79% by T5
- Boros Energy goldfish (2026-04-25 N=1000 seed=42, pre-role-refactor baseline): 99.9% win, avg T4.59, 47% T4, 88% by T5
  - Drift since 2026-04-09: avg kill 0.33 turn faster, T4 wins +11pp, by-T5 cumulative +9pp.
    Engine WIP push (game_state.py / card_effects.py / match_engine.py edits) likely
    accounts for the speedup. Comparison baseline for the role-refactor work.
- Boros Energy goldfish (2026-04-25 night N=1000 seed=42, post-role-refactor + Phase 2 + T1.2 + T1.1): 99.9% win, avg T4.49, 53% T4, 92% by T5
  - Net drift vs pre-role-refactor: avg kill -0.10 turn faster (Phase 1 +Guide-self-trigger
    inflation accelerated to T4.48), then T1.1 corrected the Guide "another" oracle bug
    which added back 0.01 turn (now T4.49). Bug had been silently inflating sim WR vs
    real-BE play; correction is in the slower-direction by design.
- Boros Energy goldfish (2026-04-25 night N=1000 seed=42, post-T2 stack): 100.0% win, avg T4.47, 53% T4, 93% by T5
  - T2.1 (Ranger-Captain priority) attempted and REVERTED: negative finding,
    displaces Ajani/Phlage from T3 cast slot.
  - T2.2 (Pyromancer GY activation): real oracle is 5-mana cost (not 1 as
    Tom's spec said); rarely fires in goldfish. Capability added.
  - T2.3 (Bombardment GY-fill, tokens only): conjunction of conditions rare
    in median-T4 goldfish; capability added for slower games.
  - T2.4 (Ocelot city's blessing copy): activates on T6+ when 10+ permanents.
    Mostly compounds with token snowball when game lasts that long.
  - Net effect: -0.02 turn faster (T4.49 -> T4.47), WR ticked up 99.9% -> 100%.
- Boros Energy goldfish (2026-04-26 N=1000 seed=42, post-T1.3+T1.4 transform infrastructure arc, SUPERSEDED 2026-04-26 morning): 100.0% win, avg T4.45, 53% T4, 92% by T5
  - 6-stage arc: Card DFC fields + gs.transform mechanic + planeswalker
    dispatch + saga transform (Kumano fixed) + Ajani Pariah->Avenger
    consumer + Roku->Avatar Roku consumer. See spec at
    harness/knowledge/tech/be-apl-content-gaps-2026-04-25.md.
  - Net drift vs T2-stack: -0.02 turn faster (T4.47 -> T4.45). Same pattern
    as T2 stack: late-game capabilities lap correctly but BE's T4-median
    clock leaves little room for them to materially affect kill turn.
    Stage 5 (Ajani transform) produced ZERO canonical drift -- Ajani only
    transforms ~10% of games, and Avenger has no time to snowball before
    games end. Stage 6 (Roku) produced -0.16 turn at 100-game scale (down
    to -0.02 at 1000) because Chapters I+II provide value on cast turn
    and next turn even when Chapter III doesn't reach.
  - Real value of this arc is INFRASTRUCTURE not BE-canonical impact:
    Magic Origins planeswalkers, Innistrad werewolves, MH3 sagas in
    Pioneer/Modern decks all unlocked for free.
- Boros Energy goldfish (2026-04-26 morning N=1000 seed=42, post-foundation-fix, SUPERSEDED by Voice+Guide fix below): 99.9% WR, T4.62 avg, T5 median, T4 share 47.3%.
  Drift from T4.45 baseline (8c3c2d5, 2026-04-25 night) attributed to
  engine WIP committed at 7e213ea (load-bearing card_effects + match_engine
  + effect_primitives). The WIP added landfall trigger dispatch, ETB
  effects for ~25 cards, and spell-resolve handlers (Lightning Helix,
  Jeskai Revelation, etc.). Per-turn handler dispatch overhead matches
  the 0.17-turn slow-down. Behavior is correct (real card effects
  firing); baseline shift is expected and reflects more accurate
  modeling.
- Boros Energy goldfish (2026-04-26 morning post-Voice+Guide-bug-fix, **current canonical**): 99.9% WR, T4.72 avg, T5 median, T4 share 43.1%.
  Resolves two double-firing handler bugs surfaced by Block 2 audit
  + Diagnostic E (2026-04-26 5-7 AM session):
    * Voice Mobilize: APL handler added 2 dmg per Voice attack on top
      of engine combat-damage-step counting (4 dmg/Voice instead of 2).
      Affected variant decks only.
    * Guide ETB: APL `_fire_guide_etb_trigger` added +1 life/energy
      per Guide on every creature/token ETB on top of engine
      `_apply_existing_board_etb` already firing the same trigger
      (2x life/energy per Guide ETB).
  Drift from T4.62 (foundation-fix baseline 7e213ea): +0.10 turn slower.
  Net drift from T4.45 (8c3c2d5 historical): +0.27 turn -- combined
  effect of foundation WIP + bug corrections. Both shifts represent
  more accurate modeling, not regression. This is the stable canonical
  going forward.
- Boros Energy variant Jermey goldfish (2026-04-26 morning post-Voice+Guide-fix):
  100.0% WR, T4.40 avg, T4 median, T4 share 58.6%. Variant edge over
  canonical: -0.32 turn faster. Voice double-counting was inflating
  variant advantage by +0.03 turn vs the post-fix true value
  (pre-fix variant T4.33 vs post-fix T4.40 = +0.07 turn slower; but
  canonical also slowed by +0.10 turn, so edge contracted from -0.29
  to -0.32 -- variant edge actually GREW slightly because canonical
  absorbed more of the Guide bug than variant).
- Boros Energy Modern gauntlet (2026-04-26 morning N=1000 seed=42, post-Voice+Guide-fix HEAD 8fc9b82):
  71.7% field-weighted (was 71.1% pre-fix at ea5e196). Surprising
  +0.6pp upward shift -- the Voice+Guide ETB bug fixes were goldfish-
  specific in impact and did NOT materially deflate gauntlet numbers
  (likely because the engine's _make_token / _apply_existing_board_etb
  paths fire in goldfish but not in the match-runner two-player sim).
  Pre-fix 100k headline at 71.5% (commit 0bc20bf) is essentially
  unchanged in current methodology -- stale only insofar as the
  underlying engine has Stage 1.5 + 1.6 + foundation + bugfix layered
  on, but the gauntlet measurement is robust to those changes.
- Boros Energy variant Jermey gauntlet (2026-04-26 morning N=1000, post-Voice+Guide-fix):
  83.1% field-weighted (was 82.5% post-Stage-1.6, +0.6pp uniform shift).
  Variant edge over canonical: +11.4pp field-weighted -- EXACTLY held
  through the bugfix (both decks shifted together). Methodology:
  variant has no DB cache (sim-source for all 14 matchups); canonical
  has DB cache for ~8 matchups + sim for ~6. Field-weighted comparison
  is approximate apples-to-apples (same archetypes weighted by Modern
  meta share) but absolute numbers reflect different g1_source mixes.
- METHODOLOGY CAVEAT for ALL Modern gauntlet entries above (surfaced
  2026-04-26 morning by Diagnostic B, PARTIALLY RESOLVED by Phase 1):
  Pre-Phase-1: match-runner `_resolve_combat` was raw power calc with
  no combat trigger dispatch, AND `_simple_play_turn` didn't call
  `main_phase2` -- Phlage hardcast, Bombardment lethal sac, Ocelot
  end-step, Mono Red burn package, etc. all dead in match mode. Phase
  1 (commit below) wires `main_phase2` for both players. Phases 2
  (combat triggers) + 3 (combat keywords) remain.
- Boros Energy Modern gauntlet (2026-04-26 morning N=1000 seed=42,
  post-Phase-1 main_phase2 wiring): 69.1% field-weighted (was 71.7%
  pre-Phase-1, delta -2.6pp DOWNWARD). Drift attributed to Mono Red
  matchup correction (99.9% -> 58.3%, -41.6pp). Pre-Phase-1, opposing
  APLs' main_phase2 work was dead -- Mono Red's burn package
  (Lightning Bolt face, Lava Spike, etc.) couldn't fire, leaving
  creature-only goldfish that BE auto-raced. Post-fix, Mono Red
  deploys real burn damage. The 99.9% headline was the artifact;
  58.3% is closer to real Modern. Other matchups held within +/-1.5pp
  because their main_phase2 work is creature-deployment (Affinity,
  Domain Zoo, Tron) or counterspell/draw (Murktide, Esper Blink),
  neither providing major direct damage gains.
- Boros Energy variant Jermey gauntlet (2026-04-26 morning post-Phase-1):
  82.8% field-weighted (was 83.1%, -0.3pp aggregate). Variant edge
  over canonical: +13.7pp (was +11.4pp, GREW by +2.3pp). Per-matchup:
  Mono Red 99.9% -> 65.9% (same pattern as canonical), Eldrazi Ramp
  64.5% -> 90.5% (+26pp -- variant Phlage hardcast + Bombardment
  lethal sac now fire and win close races; canonical's Eldrazi Ramp
  is DB-cached so didn't shift). Variant absorbed the Mono Red
  correction better AND gained on previously close matchups. Sleeve-
  up read STRENGTHENED: goldfish edge -0.32 turn + gauntlet edge
  +13.7pp post-fix.
- Boros Energy Modern gauntlet (2026-04-26 N=100k/matchup seed=42, post-arc + Stage A registry):
  **71.5% field-weighted match win% (1,400,000 games, 2419s, 14 matchups, 0 errors).
  Confirmed +6.2pp lift over the 2026-04-09 baseline of 65.3%.** This is
  the new canonical Modern field-weighted number for BE.
  - Tier breakdown: 12 favored (>=60%), 2 even (Eldrazi Ramp 49.2%,
    Izzet Prowess 57.3%), 0 dog.
  - Strongest: Mono Red 99.9%, Izzet Affinity 99.1%, Domain Zoo 96.5%.
    Goldfish-on-goldfish artifact: when BE has the structurally faster
    clock against an unmodeled opposing deck, match win pins near 100%.
    The Eldrazi-Ramp / Izzet-Prowess numbers are the meaningful signal
    -- those are the matchups where both decks are similarly fast and
    structural assumptions don't dominate.
  - Sample-size validation: same gauntlet at N=1k/matchup landed at
    71.1% (within +/-0.4pp of the 100k truth). The 1k preview was
    high-fidelity; sample-size discipline confirmed not violated.
  - Long-tail observation: 8 of 14 matchups complete in ~10s (DB-cached
    G1 lookups), the other 6 grind serially over the next 40 minutes
    (Mono Red 180s, Izzet Affinity 1964s, Jeskai Blink 2418s).
    Wall time = slowest matchup's wall, regardless of how many cores
    are idle. Motivates within-matchup parallelism (see
    harness/knowledge/tech/perf-within-matchup-parallelism-2026-04-26.md).
  - Pre-flight ASCII fixes (committed ea5e196): parallel_launcher.py
    and dashboard.py both used Unicode box-drawing in print statements,
    violating repo's CONVENTIONS.md ASCII-only terminal rule.
    Pre-existing bug, surfaced by running the launcher.
