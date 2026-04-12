## Amulet Titan APL — FINAL STATE (April 2026)

### 2188 lines | 16 commits | Bible-based combo engine

### Goldfish (20 life): 94.8% WR | avg T7.34 | median T7
- T3: 0.1% | T4: 3.1% | T5: 15.1% | T6: 20.1% | T7: 19.2%
- Win by T5: 18.3% | Win by T7: 57.5%

### Realistic (17 life): 95.4% WR | avg T6.94 | median T7
- T4: 8.1% | T5: 17.0% | T6: 20.6% | T7: 19.3%
- Win by T5: 25.0% | Win by T7: 65.0%

### Kill sources
- 89.6% combat | 8.6% Analyst loop | 1.8% Scapeshift OHKO

### Key engine stats
- Titan deploys avg T5.7 (4.3% T2, 10.5% T3, 17.3% T4)
- Haste rate: 80% | Mirrorpool copy: 97%
- Delirium: 42% | Construct damage: 3-4/turn with 2+ Amulets
- Post-attack mana: avg 21.9 floating | Post-ETB mana: avg 6.7
- Colossus: 130 casts/1000 games (115 from attack trigger)

### Architecture
Bible-based combo deck model — NOT a beatstick:
1. Scapeshift OHKO (1 Amulet + 4 lands → deterministic kill)
2. Analyst infinite loop (Amulet + Lotus + Deeps + Woodland + delirium)
3. Titan haste + Mirrorpool chain (ETB fetches → copy → chain ETBs)
4. Cultivator Colossus chain (7 mana, chains all hand lands)
5. Combat beatdown with dynamic Constructs (fallback)

### Design docs
- docs/amulet_titan_bible_audit.md — full rewrite spec
- Titan Bible: All_About_Amulet_Titan.txt (Dom Harvey, 2651 lines)

## Next Up
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
