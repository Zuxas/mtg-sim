## Amulet Titan APL — FINAL STATE (April 2026)

### 2365 lines | 34 commits | Bible-based combo engine

### Goldfish (20 life): 96.5% WR | avg T6.05 | median T6
- T2: 0.4% | T3: 4.6% | T4: 21.0% | T5: 24.9% | T6: 18.6%
- Win by T5: 45.8% | Win by T7: 81.2%

### Realistic (17 life): 96.7% WR | avg T5.78 | median T5
- T2: 0.6% | T3: 5.7% | T4: 27.9% | T5: 24.6%
- Win by T5: 52.5% | Win by T7: 80.0%

### Kill sources
- 79.2% combat | 18.4% Analyst loop | 2.4% Scapeshift OHKO
- Combo total: 20.8% (1 in 5 games wins via infinite combo)

### Key stats
- Avg 2.41 Titan ETBs per game (chaining 2nd/3rd/4th Titans)
- Titan deploys avg T4.96 | Haste 80% | Mirrorpool 97%
- Analyst loop avg T5.5 | Delirium 42%
- Post-attack mana avg 21.9 -> spent on combos+2nd Titan+lands
- GSZ X=2 for Analyst | GSZ X=0 for Dryad Arbor | GSZ X=6 for Titan
- 96% of T8+ games = no Titan by T5 (deck variance, not APL issue)

### Files
- APL: apl/amulet_titan.py (2365 lines)
- Deck: decks/amulet_titan_modern.txt (60+15)

## Next Up
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
