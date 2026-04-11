# MTG-SIM WORKFLOW OPTIMIZATION GUIDE
# How to split APL audit work across Claude models + ChatGPT

## THE PROBLEM
A full deck APL audit in Opus Extended consumes ~200K+ tokens per deck.
Most of that is mechanical work (reading files, running tests, committing).
Only ~20% needs deep reasoning (interaction discovery, strategic design).

## PHASE BREAKDOWN — 5 phases per deck audit

### PHASE 1: DATA EXTRACTION (Sonnet regular — cheap, fast)
**What:** Read playbook HTML, extract engines/roles/matchups/edges/SB plans.
**Context needed:** Just the playbook file path.
**Output:** A structured markdown doc with all strategic content extracted.

Prompt template:
```
Read E:\vscode ai project\My-Website\modern\{deck}-playbook.html
Extract and organize into a markdown document:
1. All 3 engines (setup/execution/result for each)
2. Role assignments per matchup
3. Matchup matrix (difficulty, role, meta share)
4. All "If X → Do Y" rules from matchup writeups
5. All SB plans (in/out per matchup)
6. All edge cases from the edges section
7. Speed math / kill clocks
8. Lines & Tricks
Save to: E:\vscode ai project\mtg-sim\docs\{deck}_playbook_extract.md
```

Also in this phase:
- Pull oracle text: `python _oracle_pull.py` (already scripted)
- Sync decklist: already done via sync script
- ~5K tokens, 2 minutes

### PHASE 2: INTERACTION ANALYSIS (Opus regular — needs reasoning)
**What:** Cross-reference playbook extract + oracle text. Find holes, edge cases,
card interactions the APL must model. Design the APL architecture.
**Context needed:** The playbook extract doc + oracle text doc (both from Phase 1).
**Output:** An audit doc with numbered interactions + code issue list + APL design spec.

Prompt template:
```
I'm building an APL for {deck} in my MTG simulator.

Here is the playbook strategy extract:
[paste docs/{deck}_playbook_extract.md]

Here is the oracle text for every card in the 75:
[paste docs/{deck}_oracle.txt]

Here is the current APL (if exists):
[paste apl/{deck}_match.py]

Tasks:
1. List every card interaction that must be modeled (P0/P1/P2 priority)
2. List every edge case from oracle text that the playbook doesn't mention
3. Cross-reference current APL — what's missing vs what's correct
4. Design the APL architecture: what methods are needed, what state to track
5. Write the audit doc to docs/{deck}_audit.md
```

~30K tokens, 10 minutes. This is the ONLY phase that needs Opus-level reasoning.

### PHASE 3: APL CODE WRITING (Sonnet Extended — bulk code generation)
**What:** Write the full APL from the Phase 2 design spec.
**Context needed:** The audit doc (interactions + design spec) + oracle text.
**Output:** The complete APL .py file, 500-800+ lines.

Prompt template:
```
Write the complete APL file for {deck} following this design spec:
[paste docs/{deck}_audit.md — interactions + architecture section]

Oracle reference:
[paste docs/{deck}_oracle.txt]

Requirements:
- Target 600+ lines
- Every card in the 75 must have deployment logic
- Matchup detection with role switching
- Per-card removal priority
- Combat math with card-specific triggers
- respond_to_spell for reactive plays
- Proper mulligan from playbook snap keep/mull rules
- Phlage escape if in deck
- All cast triggers vs ETB triggers correct per oracle

Write to: E:\vscode ai project\mtg-sim\apl\{deck}_match.py
```

~50K tokens, 5 minutes. Sonnet Extended is perfect — mechanical code from a clear spec.

### PHASE 4: TESTING & TUNING (Sonnet regular — iteration loops)
**What:** Run matchup tests, adjust values, fix bugs, verify edge cases.
**Context needed:** Just the APL file + test commands.
**Output:** Tuned APL with competitive-accurate matchup numbers.

Prompt template:
```
Test the {deck} APL against audited opponents:
1. Run: python -c "... run_match_set(..., n=1000) ..."
2. Check vs Boros (target from playbook: {difficulty rating})
3. Check vs Prowess (target from playbook: {difficulty rating})
4. If matchup is off by >10%, adjust the relevant mechanic
5. Iterate until within competitive range
6. Commit when stable
```

~15K tokens per iteration, 3-5 iterations typical.

### PHASE 5: GAUNTLET & COMMIT (Sonnet regular — pure execution)
**What:** Run full Bo3 gauntlet, commit results, push.
**Context needed:** Just the gauntlet script + git commands.
**Output:** Committed gauntlet data.

```
Run the gauntlet script, commit with descriptive message, kill python processes.
```

~5K tokens, runs in background while doing other work.

## TOTAL TOKEN COST COMPARISON

### Current (all Opus Extended): ~200K tokens per deck = $$$$$
### Optimized split:
- Phase 1 (Sonnet): ~5K tokens = $
- Phase 2 (Opus): ~30K tokens = $$
- Phase 3 (Sonnet Ext): ~50K tokens = $$
- Phase 4 (Sonnet): ~30K tokens = $
- Phase 5 (Sonnet): ~5K tokens = $
- **Total: ~120K tokens, with only 30K in Opus = ~60% cost reduction**

## CHATGPT USAGE

ChatGPT is useful for tasks that are INDEPENDENT and don't need sim context:
1. **Oracle text research** — "What are all the Scryfall rulings for Phelia?"
2. **Competitive guide summaries** — "Summarize the top 3 Jeskai Blink guides from 2025"
3. **Edge case brainstorming** — "What interactions does Solitude + Ephemerate have?"
4. **Code review** — Paste a completed APL, ask "what card interactions am I missing?"
5. **Playbook error checking** — "Does Unholy Heat target enchantments? The playbook says it does."

ChatGPT CANNOT do:
- File operations on your PC (no Desktop Commander)
- Run sim tests
- Git operations
- Read your existing playbook HTML (needs the content pasted in)

## PARALLEL WORKFLOW

With this split, you can run multiple phases simultaneously:
- While Opus does Phase 2 for Deck A, Sonnet does Phase 1 for Deck B
- While Sonnet Extended writes code for Deck A, Sonnet tests Deck B
- ChatGPT researches oracle rulings for Deck C in parallel

**Theoretical throughput: 3-4 decks per session instead of 1-2**

## SETUP: CLAUDE.md UPDATE

Add to E:\vscode ai project\mtg-sim\claude.md:
```
## APL Audit Workflow (5 phases)
Phase 1: Data extraction (Sonnet) — read playbook, extract strategy, pull oracle
Phase 2: Interaction analysis (Opus) — cross-reference, find holes, design APL
Phase 3: Code writing (Sonnet Extended) — write full APL from spec
Phase 4: Testing (Sonnet) — run matchups, tune values, fix bugs
Phase 5: Gauntlet (Sonnet) — full Bo3 run, commit, push

Context handoff files:
- docs/{deck}_playbook_extract.md (Phase 1 output → Phase 2 input)
- docs/{deck}_oracle.txt (Phase 1 output → Phase 2+3 input)
- docs/{deck}_audit.md (Phase 2 output → Phase 3 input)
- apl/{deck}_match.py (Phase 3 output → Phase 4 input)
```
