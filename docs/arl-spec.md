# Autonomous Research Loop (ARL) -- design spec

> Moved out of mtg-sim/CLAUDE.md 2026-06-29 (progressive-disclosure trim). Read when working on the ARL.

## Autonomous Research Loop (ARL)

### What it is

The ARL is a long-running agentic workflow that explores the MTG metagame
autonomously: generating candidate decklists, writing APL stubs, running
gauntlet sims, evaluating results, mutating toward higher FWR, and logging
everything. Jermey is the human-as-interrupt-handler, not the
human-as-approver. The loop runs until paused; Jermey can check status,
steer direction, or spot-check results at any time without stopping it.

### State file

All loop state lives in `loop_state.json` at the repo root. This is the
spine -- it survives pauses, crashes, and model context resets.

Schema:

```json
{
  "status": "running | paused | idle",
  "mode": "explore | optimize | refactor | format_expand",
  "target_format": "standard | modern | pioneer | legacy",
  "hypothesis": "plain-text description of what the loop is currently testing",
  "iteration": 42,
  "queue": [
    {
      "id": "deck_slug",
      "deck_file": "decks/candidate_042.txt",
      "apl_file": "apl/candidate_042_match.py",
      "status": "pending | running | done | error",
      "fwr": null,
      "notes": ""
    }
  ],
  "results": [
    {
      "id": "deck_slug",
      "deck_file": "decks/candidate_042.txt",
      "fwr": 61.4,
      "vs_field": {"izzetprowessstandard": 58.2, "selesnyalandfall": 67.1},
      "hypothesis": "what was being tested",
      "verdict": "promote | mutate | discard",
      "notes": ""
    }
  ],
  "promoted": ["deck_slug_a", "deck_slug_b"],
  "steer_queue": [],
  "last_updated": "2026-06-25T14:32:00Z",
  "blockers": []
}
```

### Loop iteration (one cycle)

1. Read `loop_state.json`. If `status == paused`, exit cleanly and print status.
2. Pull next item from `queue` where `status == pending`.
3. If queue is empty, generate next batch (see "Generating candidates" below).
4. Set item `status = running`, write state.
5. Ensure deck file exists. If not, generate it from `mtg_meta.db` using the
   current hypothesis as guidance.
6. Ensure APL file exists. If not, write a stub using the nearest existing APL
   as a template, wiring card constants from the deck file's oracle text.
7. Smoke-test: `python sim.py <deck_slug> --games 100`. If crash, log to
   `blockers`, set item `status = error`, skip to next item.
8. Full gauntlet: `python bo3_gauntlet.py <deck_slug> --games 200`.
   Parse FWR from stdout.
9. Evaluate: if FWR > promote_threshold (default 60%), mark `verdict = promote`
   and add to `promoted`. If 55-60%, mark `mutate` and enqueue variants.
   Below 55%, mark `discard`.
10. Write result to `results`, set item `status = done`, update `last_updated`.
11. Check `steer_queue` for pending directives. If present, apply (update
    hypothesis, clear queue, requeue), log the steer.
12. Loop to step 2.

### Generating candidates

When the queue is empty, generate the next batch based on `mode`:

- **explore**: query `mtg_meta.db` for archetypes in `target_format` with
  >0.5% meta share that have no entry in `promoted` yet. Pull a tournament
  decklist for each. Enqueue up to 5 at a time.
- **optimize**: take the top entry in `promoted`, generate 3-5 variants
  (swap 2-4 cards using meta-bridge data for likely upgrades), enqueue.
- **format_expand**: switch `target_format` to the next format, reset
  `promoted`, run explore mode.
- **refactor**: do not run gauntlets. Instead, propose structural changes
  (file reorganization, engine improvements, APL base class refactors).
  Write proposals to `docs/refactor_proposals/` and pause for review.

### Human interface

Two entry points. No other interaction required during a run.

**Status check** (`python scripts/arl_status.py`):
- Prints current mode, hypothesis, iteration count
- Prints top 5 promoted decks by FWR with matchup breakdowns
- Prints current queue (next 3 items)
- Prints any active blockers
- Prints last steer applied and when

**Steer** (`python scripts/arl_steer.py "<directive>"`):
- Appends directive to `steer_queue` in `loop_state.json`
- Loop picks it up at end of current iteration
- Examples:
  - `python scripts/arl_steer.py "switch to modern, focus on tempo shells"`
  - `python scripts/arl_steer.py "pause after current iteration"`
  - `python scripts/arl_steer.py "discard candidate_042, mana base is wrong"`
  - `python scripts/arl_steer.py "set promote_threshold to 58"`

**Pause/resume**:
- `python scripts/arl_steer.py "pause"` -- sets `status = paused` on next
  clean iteration boundary (never mid-sim)
- `python scripts/arl_steer.py "resume"` -- sets `status = running`, loop
  picks up from current queue position

### What the loop does NOT do without explicit steering

- Does not modify `engine/` files (engine changes are P0 human work)
- Does not delete existing APLs or deck files
- Does not commit to git (Jermey commits after reviewing promoted results)
- Does not run more than 200 games per matchup without a steer directive
- Does not promote a deck above threshold without at least 2 gauntlet runs

### Blockers (auto-pause conditions)

The loop sets `status = paused` and logs to `blockers` if:
- A deck file cannot be generated (archetype not in DB, 0 tournament samples)
- An APL stub crashes smoke-test and auto-fix fails after 2 attempts
- FWR variance between two gauntlet runs on the same deck exceeds 8pp
- `steer_queue` contains "pause" directive

`arl_status.py` shows the blocker and suggested resolution when paused.
Jermey resolves manually, then steers "resume".

### Entry point scripts to build

When implementing the ARL, create these files:

- `scripts/arl_loop.py` -- main loop runner (run in terminal, Ctrl-C safe,
  writes clean state on interrupt)
- `scripts/arl_status.py` -- read-only status dump, no side effects
- `scripts/arl_steer.py "<directive>"` -- inject a steer directive
- `scripts/arl_generate_deck.py <archetype> <format>` -- standalone deck
  generator (wraps db_bridge.py + meta_bridge.py), used by loop and standalone
- `scripts/arl_generate_apl.py <deck_file>` -- standalone APL stub writer,
  uses nearest archetype APL as template

All scripts follow CONVENTIONS.md: ASCII-only output, sys.path from repo
root, exit codes 0/1, no emoji or unicode in terminal output.

---
