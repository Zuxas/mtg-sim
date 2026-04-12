## Amulet Titan APL — FINAL STATE (April 2026)

### 2209 lines | 18 commits | Bible-based combo engine

### Goldfish (20 life): 94.8% WR | avg T7.38 | median T7
- T3: 0.1% | T4: 2.8% | T5: 14.6% | T6: 20.2% | T7: 19.1%
- Win by T5: 17.4% | Win by T7: 56.8%

### Realistic (17 life): 95.3% WR | avg T6.95 | median T7
- T4: 8.0% | T5: 16.9% | T6: 20.6% | T7: 19.3%
- Win by T5: 24.9% | Win by T7: 64.8%

### Kill sources
- ~90% combat | ~9% Analyst loop | ~2% Scapeshift OHKO

### Key engine stats
- Titan deploys avg T5.7 (4.3% T2, 10.5% T3, 17.3% T4)
- Haste rate: 80% | Mirrorpool copy: 97%
- Delirium: 42% | Construct damage: 3-4/turn with 2+ Amulets
- Post-attack mana: avg 21.9 floating (88% have 5+ for Mirrorpool)
- Post-ETB mana: avg 6.7 floating (combo kills attempted here)
- Colossus: 130 casts/1000 games (115 from attack trigger excess)

### Architecture
Bible-based combo deck with 5 kill lines:
1. Scapeshift OHKO (1 Amulet + 4 lands -> deterministic kill)
2. Analyst infinite loop (Amulet + Lotus + Deeps + Woodland + delirium)
3. Titan haste + Mirrorpool chain (ETB -> copy -> chain ETBs)
4. Cultivator Colossus chain (7 mana, chains all hand lands)
5. Combat beatdown with dynamic Constructs (fallback)

### Files
- APL: apl/amulet_titan.py (2209 lines)
- Deck: decks/amulet_titan_modern.txt (60 main, 15 SB)
- Docs: docs/amulet_titan_bible_audit.md, docs/SESSION_STATE_CRITICAL.md
- Source: All_About_Amulet_Titan.txt (Dom Harvey, 2651 lines)

## Next Up
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
