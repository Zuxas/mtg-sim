# Standard Card Handler Scope
# Generated: 2026-05-03
# Source: Scryfall MCP, all sets legal in Standard as of this date

## Total Standard Pool

**4,430 unique oracle cards** legal in paper Standard (-is:digital).
Of these, roughly:
- ~400 are pure keyword/vanilla cards (no handler needed)
- ~300 are lands handled by the engine (basic land types, fast lands, etc.)
- ~600-800 are already registered in our ETB_EFFECTS / SPELL_EFFECTS / SAGA_EFFECTS
- **~2,900-3,200 still need handlers**

---

## Set-by-Set Breakdown

| Set | Code | Cards | Released | In local oracle DB | Priority |
|-----|------|-------|----------|--------------------|----------|
| Wilds of Eldraine | woe | 381 | 2023-09 | YES | P2 |
| The Lost Caverns of Ixalan | lci | 416 | 2023-11 | YES | P2 |
| Murders at Karlov Manor | mkm | 440 | 2024-02 | YES | P2 |
| Outlaws of Thunder Junction | otj | 374 | 2024-04 | YES | P2 |
| The Big Score | big | 95 | 2024-04 | YES | P2 |
| Bloomburrow | blb | 398 | 2024-08 | YES | P2 |
| Duskmourn: House of Horror | dsk | 419 | 2024-09 | YES | P2 |
| Foundations | fdn | 771 | 2024-11 | YES (mostly reprints) | P2 |
| Aetherdrift | dft | 553 | 2025-02 | PARTIAL | P2 |
| Tarkir: Dragonstorm | tdm | 427 | 2025-04 | PARTIAL | P2 |
| Final Fantasy | fin | 595 | 2025-06 | NO — needs bulk fetch | P1 |
| Edge of Eternities | eoe | 399 | 2025-08 | NO — needs bulk fetch | P2 |
| Marvel's Spider-Man | spm | 286 | 2025-09 | NO — needs bulk fetch | P2 |
| Avatar: The Last Airbender | tla | 394 | 2025-11 | NO — needs bulk fetch | P1 |
| Lorwyn Eclipsed | ecl | 408 | 2026-01 | NO — needs bulk fetch | P2 |
| Teenage Mutant Ninja Turtles | tmt | 320 | 2026-03 | NO — needs bulk fetch | P2 |
| Secrets of Strixhaven | sos | 368 | 2026-04 | NO — needs bulk fetch | P0 |
| Through the Omenpaths | ??? | ~390 | digital | DIGITAL ONLY | skip |
| **TOTAL (paper)** | | **~6,644** | | | |

Note: card_count includes all printings/variants. Unique oracle cards = ~4,430.

---

## Current Coverage Estimate

Based on the SOS audit (24.8% for a new set) and known working decks:

| Category | Estimate |
|----------|---------|
| Already registered (all registries) | ~800 unique cards |
| Auto-parseable with updated oracle data | ~1,000-1,200 cards |
| Need hand-writing | **~2,400-2,600 cards** |
| Keyword/vanilla (no handler needed) | ~400 cards |
| Lands (engine handles) | ~300 cards |

At 30 hand-written handlers/hour: **80-90 hours of focused work.**
At 5 sessions/week, 2 hours/session: **~8-9 weeks.**

---

## The Blocking Problem: Stale Oracle Data

Our local `scryfall_oracle_cards.json` was last fetched before SOS (Apr 2026).
Sets missing from local DB:
- fin, eoe, spm, tla, ecl, tmt, sos (partial)

**Fix first:** run `scripts/fetch_scryfall_bulk.sh`
- Adds ~1,400 new oracle cards to the local DB
- Unlocks the auto-parser for all those sets
- Estimated net gain: ~300-400 additional auto-generated handlers
- Time: ~10 minutes to fetch, ~30 minutes to run the pipeline

---

## Recommended Attack Order

### Phase 1 — Foundation (unblock everything else)
1. **Fetch Scryfall bulk** — `scripts/fetch_scryfall_bulk.sh`
   Adds all new set oracle data locally.
2. **Re-run build_sos_all_handlers.py across all sets**
   Generate `engine/<set>_auto_handlers.py` for each set.
   Expected auto-coverage jump: 25% → 40-50% per new set.
3. **Expand oracle_parser for SOS/new mechanics**
   Add patterns for: Infusion, Prepared, Increment, Opus, Spree, Paradigm,
   Earthbend, Mobilize, Room (unlock). Each pattern added clears ~10-30 cards.

### Phase 2 — Competitive priority (cards in real decklists)
Focus only on cards that appear in competitive Standard decks.
From our current decks + PT SOS data, the critical card pool is ~200-300 cards.
We already have ~90% coverage of PT SOS meta cards.

Priority order by format impact:
1. Final Fantasy (fin) — Tifa, Sazh, Mossborn already done. ~40 more key cards.
2. Avatar: The Last Airbender (tla) — Ba Sing Se, Badgermole, Iroh already done.
3. Tarkir: Dragonstorm (tdm) — used in SOS meta decks?
4. Duskmourn, Bloomburrow, OTJ — older, more established coverage
5. TMNT, Spider-Man, Lorwyn Eclipsed, Edge of Eternities — newest, mostly unknown

### Phase 3 — Complete coverage
Hand-write all remaining cards not auto-parseable.
Work set-by-set, prioritize by rarity (mythic/rare hit decks most).
~2,400 cards total, probably 8-9 focused weeks.

---

## Mechanics Needing Parser Support (unlock ~300-500 auto-handlers)

| Mechanic | Sets | Cards affected | Pattern to add |
|----------|------|----------------|----------------|
| Infusion (end-step sacrifice) | sos | ~15 | end-step trigger |
| Prepared (copy on cast) | sos | ~20 | state flag |
| Increment (scales with mana spent) | sos | ~8 | counter scaling |
| Opus (cast trigger) | sos | ~10 | spell trigger |
| Earthbend (animate land) | tla, sos | ~25 | land animation |
| Mobilize N (attack tokens) | tla | ~20 | attack trigger |
| Room / unlock door | dsk | ~30 | DFC mechanic |
| Survival (life trigger) | fin | ~15 | conditional |
| Limit (max uses) | fin | ~20 | activation cap |
| Vehicle / crew | dft | ~30 | tap creatures |

Adding each pattern to oracle_parser.py = all matching cards auto-handled.

---

## Quick Wins (can be done now without bulk update)

1. `fetch_scryfall_bulk.sh` → immediately unlocks ~1,400 new oracle cards
2. Run auto-handler pipeline across all 17 set codes
3. Hand-write the 5 SOS Dragon cards (Elder Dragons appear in decklists)
4. Hand-write key Tarkir: Dragonstorm cards used in meta decks
5. Add `Earthbend` and `Mobilize` to oracle_parser (high card count, simple pattern)

---

## Files Affected

```
scripts/fetch_scryfall_bulk.sh          -- run first to update local oracle DB
engine/oracle_parser.py                 -- add new mechanic patterns
engine/sos_auto_handlers.py             -- already generated (29 handlers)
engine/<set>_auto_handlers.py           -- generate for each remaining set
engine/card_handlers_verified.py        -- hand-written oracle-verified handlers
C:\temp\build_sos_all_handlers.py       -- reusable pipeline script (generalize to any set)
```

---
## Tracking

Current coverage (2026-05-03):
- SOS: 66/266 non-basic = 24.8% (29 auto + 37 already in engine)
- Other sets: unknown (need bulk fetch to audit properly)
- Total estimated Standard coverage: ~800/4,430 = ~18%
