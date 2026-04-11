## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current


## APL Audit Workflow (5 phases — see docs/WORKFLOW_OPTIMIZATION.md)

Phase 1: Data extraction (Sonnet) — read playbook, extract strategy, pull oracle
Phase 2: Interaction analysis (Opus) — cross-reference, find holes, design APL  
Phase 3: Code writing (Sonnet Extended) — write full APL from design spec
Phase 4: Testing (Sonnet) — run matchups, tune values, fix bugs
Phase 5: Gauntlet (Sonnet) — full Bo3 run, commit, push

Context handoff files (each phase produces input for the next):
- docs/{deck}_playbook_extract.md (P1→P2)
- docs/{deck}_oracle.txt (P1→P2+P3)
- docs/{deck}_audit.md (P2→P3)
- apl/{deck}_match.py (P3→P4)

## Ecosystem Sources of Truth
- Website playbooks (My-Website/modern/*.html) = PRIMARY source for APL strategy
- Meta-analyzer DB = source for meta % and tournament decklists
- Sim decks synced FROM playbooks (17 Modern decks, sync script in repo)
- Scryfall local DB (162MB, 37K cards) = oracle text verification

## Audited Decks (as of April 2026)
- Boros Energy: 767L, gold standard ✅
- Izzet Prowess: 821L, 33 edge cases ✅
- Jeskai Blink: 594L, 50.1% vs Boros (PERFECT) ✅
- Domain Zoo: 395L, needs engine P/T propagation fix ⚠️
- Eldrazi Ramp: 373L, matchups high ⚠️

## Compute
- 24 CPU cores (Ryzen 9 3900XT), RTX 3080 10GB
- ALWAYS kill Python processes after tasks: Get-Process python* | Stop-Process
- GPU sim would need engine rewrite (branching logic not GPU-friendly)
