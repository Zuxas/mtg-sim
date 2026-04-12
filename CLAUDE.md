## Amulet Titan APL — FULLY RULES-CORRECT (April 2026)

### 2388 lines | 43 commits | Bible-based combo engine

### Goldfish (20 life): 95.7% WR | avg T7.11 | median T7
- T3: 0.2% | T4: 3.3% | T5: 16.2% | T6: 24.6% | T7: 19.8%
- Win by T5: 19.4% | Win by T7: 63.8%

### Realistic (17 life): 95.9% WR | avg T6.81 | median T6
- T3: 0.2% | T4: 5.6% | T5: 20.8% | Win by T5: 26.4%

### Rules corrections applied:
1. Sorcery-speed spells cannot be cast during combat
2. Attack trigger fires in main_phase2 (after combat)
3. Mirrorpool copy ETB: no land plays or haste during combat
4. Land plays respect land drop limit (1/turn + extras)
5. Self-return chains require actual remaining drops (not grazer_in_hand)
6. Self-return replays don't consume extra land drops

### Kill sources
- ~90% combat | ~8% Analyst loop | ~2% Scapeshift OHKO

### Key stats
- Titan deploys avg T4.96 | Haste 80% | Mirrorpool 97%
- Self-returns per game: 4.0 (from legitimate extra drops only)
- Pact deaths: 0.92% (safe Pact with 5+ BF lands)

### Files
- APL: apl/amulet_titan.py (2388 lines)
- Deck: decks/amulet_titan_modern.txt (60+15)

## Next Up
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
