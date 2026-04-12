## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current


## Ecosystem Sources of Truth
- Website playbooks = PRIMARY source for APL strategy
- Meta-analyzer DB = source for meta % and tournament decklists
- Scryfall local DB (162MB, 37K cards) = oracle text verification
- Titan Bible (uploaded as All_About_Amulet_Titan.txt) = Dom Harvey 2651-line guide

## APL Registry (unified)
- Single source of truth: apl/__init__.py
- get_apl(name) goldfish APL (52 keys)
- get_match_apl(name) MatchAPL with fallback (34 match keys)

## Amulet Titan APL — COMPLETE REWRITE (April 11 2026)

### Status: 1854L | avg T7.49 | 91.7% WR | 21.7% mull (5000 games, COMMITTED)

Bible-based combo deck model with:
- Scapeshift OHKO (fires 41.5%, kills 2.2%)
- Analyst infinite loop wins (~5%)
- Titan haste via Hanweir (67% rate)
- Saga Ch III Amulet fetch
- Bounce self-return chaining
- 22 edge cases

### Remaining targets:
- avg T7.49 to T5-6 (more Scapeshift kills, better burst chains)
- Add Mycosynth Gardens to stub deck
- Multiple bounce replays per turn
- Deeper Titan fetch decision tree
- Mirrorpool spell copy

## Compute
- 24 CPU cores, RTX 3080 10GB
- ALWAYS kill Python processes after tasks

## Next Up
- Amulet Titan: improve kill speed
- Domain Zoo: fix P/T propagation
- Deep audit 9 basic match APLs
