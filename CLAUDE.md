## graphify

This project has a graphify knowledge graph at graphify-out/.

## Ecosystem Sources of Truth
- Website playbooks = PRIMARY source for APL strategy
- Meta-analyzer DB = source for meta % and tournament decklists
- Scryfall local DB (162MB, 37K cards) = oracle text verification
- Titan Bible (uploaded as All_About_Amulet_Titan.txt) = Dom Harvey 2651-line guide

## APL Registry (unified)
- Single source of truth: apl/__init__.py
- Amulet Titan uses file-based deck: decks/amulet_titan_modern.txt

## Amulet Titan APL — FINAL STATE (April 11 2026)

### 1928 lines | avg T7.83 | 90.0% WR | 21.7% mull (5000 games, 4 commits)

Bible-based combo deck with:
- Scapeshift OHKO (fires 41.5%, deterministic kills ~2%)
- Analyst infinite loop (wins ~3-5%, avg T6.7)
- Titan haste via Hanweir (80% rate)
- Titan deploys avg T5.7, 55% by T5, 4.3% T2 deploys
- Saga Ch III Amulet fetch reliable
- Bounce self-return with land drop tracking
- 22 edge cases documented
- Pact safety: 5+ lands with 2+ G-sources OR winning this turn
- Lotus Field: won't play without 2 sac targets
- Bounce won't self-return with <=1 land on BF

### Decklist: decks/amulet_titan_modern.txt (60 main, 15 SB)
- Added: Mycosynth Gardens, Cultivator Colossus, Dryad Arbor main
- Removed: Ghost Quarter, Selesnya Sanctuary, Snow-Covered Forest main

### Remaining improvement targets:
- avg T7.83 → target T6-7 (reduce T10+ tail: 17% of games)
- Bounce chain replay: works but limited by permanent mana base establishment
- Scapeshift deterministic kill: only 2% of Shifts are full OHKO (most are ramp)
- Titan fetch tree: ~10 branches, could expand to 20+
- Construct damage: tokens attack but power scaling needs audit

### Design docs:
- docs/amulet_titan_bible_audit.md — full rewrite spec
- docs/SESSION_STATE_CRITICAL.md — implementation checklist

## Next Up
- Amulet Titan: reduce T10+ tail (better land sequencing, Scapeshift kill rate)
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
