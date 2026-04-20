# MTG-SIM APL AUDIT — PHASE RUNNER
# Open the right Claude model, paste the phase prompt, go.
# Each phase produces a handoff file that the next phase reads.

## HOW TO USE
# 1. Pick the deck you want to audit from the queue below
# 2. Open Claude in the model listed for that phase
# 3. Paste the prompt for that phase (copy from this file)
# 4. The output file becomes input for the next phase

## AUDIT QUEUE (decks with playbooks but unaudited APLs)
# Priority order based on meta share:
#   1. Eldrazi Tron (238L) — has playbook + APL
#   2. Izzet Affinity (231L) — has playbook + APL
#   3. Goryo's Vengeance (193L) — has playbook + APL
#   4. Amulet Titan (163L) — has playbook + APL
#   5. Dimir Oculus — has playbook, NO APL yet
#   6. Glockulous — has playbook, NO APL yet
#   7. Living End — has playbook, NO APL yet
#   8. Ruby Storm — has playbook, NO APL yet
#   9. Yawgmoth — has playbook, NO APL yet
#   10. UW Blink — has playbook, NO APL yet
#   11. UW Control — has playbook, NO APL yet
#   12. Neoform — has playbook, NO APL yet

#═══════════════════════════════════════════════════════════════
# PHASE 1 — DATA EXTRACTION (Sonnet regular)
# Time: ~2 min | Tokens: ~5K
# What: Read playbook HTML, extract all strategic content
#═══════════════════════════════════════════════════════════════

# PROMPT (paste into Sonnet):
"""
I need you to extract strategic content from an MTG playbook HTML file
for my simulator's APL development.

Read the file at: <your-playbook-dir>\modern\{DECK}-playbook.html

Extract into a structured markdown document at:
docs\{DECK}_playbook_extract.md

Include these sections:
1. ENGINES — copy each engine's Setup/Execution/Result verbatim
2. ENGINE PRIORITY ORDER — which engine to pursue first
3. SPEED MATH — kill clocks and damage calculations
4. LINES & TRICKS — every trick with its tag (Stack/Sequence/Combat/Avoid)
5. MULLIGAN GUIDE — snap keep, snap mull, borderline conditions
6. ROLE ASSIGNMENTS — beatdown/tempo/control per matchup
7. MATCHUP MATRIX — table of opponent, meta share, difficulty, role
8. MATCHUP WRITEUPS — for each matchup: the dynamic, play vs draw, SB plan, If X → Do Y
9. EDGE CASES — every oracle-verified edge case
10. SB CARD-BY-CARD — each SB card's role and which matchups it comes in

Also run this oracle text pull:
cd <repo-root>
python docs/pull_oracle.py {DECK}
(if script doesn't exist, write one that loads the deck and dumps oracle text)

Output files:
- docs/{DECK}_playbook_extract.md (strategy)
- docs/{DECK}_oracle.txt (oracle text)
"""

#═══════════════════════════════════════════════════════════════
# PHASE 2 — INTERACTION ANALYSIS (Opus regular)
# Time: ~10 min | Tokens: ~30K
# What: Cross-reference playbook + oracle, design APL architecture
# THIS IS THE ONLY PHASE THAT NEEDS OPUS
#═══════════════════════════════════════════════════════════════

# PROMPT (paste into Opus):
"""
I'm building a match-aware APL for {DECK} in my MTG Modern simulator.
The APL file goes at: apl\{DECK}_match.py

Read these two files I prepared:
1. docs\{DECK}_playbook_extract.md (strategy)
2. docs\{DECK}_oracle.txt (oracle text)

If an existing APL exists, also read:
3. apl\{DECK}_match.py

Then produce:

A. INTERACTION LIST — every card interaction that must be modeled
   Format: ### {N}. {Interaction Name} (P0/P1/P2)
   Include: oracle text quote, pilot perspective, opponent perspective

B. EDGE CASES — interactions the playbook doesn't mention but oracle implies
   (e.g., timing windows, cast vs ETB triggers, keyword interactions)

C. APL DESIGN SPEC — architecture for the APL:
   - What instance variables to track (energy, tokens, domain, etc.)
   - Method list with signatures and responsibilities
   - Mulligan logic from playbook snap keep/mull rules
   - Deployment priority order per matchup role
   - Removal targeting priority
   - Combat math (which triggers fire on attack, which on damage)
   - respond_to_spell reactive plays
   - Role detection logic (how to identify opponent archetype)

D. CODE ISSUES — if existing APL exists, list every gap vs the design spec

Write output to: docs\{DECK}_audit.md

IMPORTANT CONTEXT:
- The sim engine uses: GameState, Card (with Tag.CREATURE), safe_power(), safe_toughness()
- APL class extends MatchAPL with methods: keep(), bottom(), main_phase_match(), 
  declare_attackers(), declare_blockers(), respond_to_spell(), end_step_actions()
- See existing gold standard: apl/izzet_prowess_match.py (821 lines)
- Target: 600+ lines for the APL
- Boros Energy playbook says this matchup is: {DIFFICULTY}
"""

#═══════════════════════════════════════════════════════════════
# PHASE 3 — CODE WRITING (Sonnet Extended)
# Time: ~5 min | Tokens: ~50K
# What: Write the full APL from the Phase 2 design spec
#═══════════════════════════════════════════════════════════════

# PROMPT (paste into Sonnet Extended):
"""
Write the complete APL file for {DECK} in my MTG simulator.

Read the design spec: docs\{DECK}_audit.md
Read oracle text: docs\{DECK}_oracle.txt
Read the deck list: decks\{DECK}_modern.txt

Write the full APL to: apl\{DECK}_match.py

Requirements:
- Follow the design spec's method list and architecture exactly
- Target 600+ lines
- Every card in the 75 must have deployment/usage logic
- Include matchup detection with role switching (beatdown/tempo/grind)
- Per-card removal priority from the audit doc
- Combat math with all attack/damage triggers from oracle text
- respond_to_spell for any reactive plays identified in the audit
- Mulligan from the playbook's snap keep/mull rules
- Phlage escape if in deck (hardcast sacrifice → escape permanent)
- All cast triggers vs ETB triggers correct per oracle
- Track relevant state (energy, tokens, counters, domain count, etc.)

Reference for style/structure: apl\izzet_prowess_match.py
"""

#═══════════════════════════════════════════════════════════════
# PHASE 4 — TESTING & TUNING (Sonnet regular)
# Time: ~5 min per iteration, 3-5 iterations | Tokens: ~30K
# What: Run matchup tests, tune values, fix bugs
#═══════════════════════════════════════════════════════════════

# PROMPT (paste into Sonnet):
"""
Test and tune the {DECK} APL in my MTG simulator.

The APL is at: apl\{DECK}_match.py
The project is at: <repo-root>

Run these matchup tests (1000 games each):
```python
import sys; sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0,'.')
from data.deck import load_deck_from_file
from engine.match_engine import run_match_set
from apl.{DECK}_match import {CLASS}
from apl.boros_energy_match import BorosEnergyMatchAPL
from apl.izzet_prowess_match import IzzetProwessMatchAPL
da,_ = load_deck_from_file('decks/boros_energy_modern.txt')
db,_ = load_deck_from_file('decks/izzet_prowess_modern.txt')
dc,_ = load_deck_from_file('decks/{DECK}_modern.txt')
r1 = run_match_set({CLASS}(), dc, BorosEnergyMatchAPL(), da, n=1000, seed=42)
r2 = run_match_set({CLASS}(), dc, IzzetProwessMatchAPL(), db, n=1000, seed=42)
```

Target win rates from Boros playbook:
- vs Boros: {TARGET from playbook difficulty rating}
- vs Prowess: {TARGET}

If matchup is off by >10%, adjust the relevant mechanic and retest.
Common fixes: deployment speed, removal priority, burst damage calc, 
lifelink/lifegain amounts, summoning sickness (no haste unless Arena).

After stable results, commit:
git add apl/{DECK}_match.py docs/; git commit -m "..."

ALWAYS kill Python processes after: Get-Process python* | Stop-Process -Force
"""

#═══════════════════════════════════════════════════════════════
# PHASE 5 — GAUNTLET & SHIP (Sonnet regular)
# Time: ~10 min (runs in background) | Tokens: ~5K
#═══════════════════════════════════════════════════════════════

# PROMPT (paste into Sonnet):
"""
Run the full Bo3 gauntlet for {DECK} in my MTG simulator at <repo-root>

Write and run this gauntlet script with 24 CPU cores:
[standard gauntlet script from previous sessions]

After complete:
1. Kill all Python processes
2. Commit with descriptive message including field avg and key matchups
3. Delete the gauntlet script

ALWAYS: Get-Process python* | Stop-Process -Force after the gauntlet
"""
