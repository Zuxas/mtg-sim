---
description: Validate Standard queue handler coverage, spot-check tail, smoke test, short real pass, then full gauntlet if clean
---

Execute these steps in order. STOP and report if any step fails — do not proceed to the next step.

## Step 1: Validate handler coverage for real
Parse `card_handlers_verified.py` AST to extract string keys from the `_SPELL_HANDLERS` and `_ETB_HANDLERS` dict literals specifically — NOT all string constants. Intersect that set with the 953 card names in `data/priority_queue/standard_matrix_queue.json`.

Report:
- Total registered keys in each dict
- Count of the 953 queue cards that have a real registration
- List any queue cards missing a registration

If coverage < 95%, STOP and show me the gap before continuing.

## Step 2: Spot-check tail cards
Grep `card_handlers_verified.py` for handler functions covering these tail cards:
- Visage Bandit
- Zoetic Glyph
- Wylie Duke
- Warmaker Gunship

For each, confirm there's an actual handler body (not a stub, not a `pass`, not a one-line no-op returning None). Report what each handler actually does in 1 line.

If any are stubs or missing, STOP.

## Step 3: Smoke test
Run `python scripts/smoke_test_priority_pipeline.py` with timeout_ms 600000. Confirm it exits 0 and the assertions pass.

If it fails, STOP and show the traceback.

## Step 4: Short real pass (default 5000 games per matchup)
Parse `$ARGUMENTS` for the game count override:
- Empty → use 5000.
- Non-empty and not a positive integer → STOP with `"$ARGUMENTS must be a positive integer — got: <value>"`. Do not pass it to the gauntlet runner.
- Positive integer greater than 20000 → STOP with `"Step 4 is the short validation pass — values greater than 20000 belong in the full gauntlet at Step 5. Re-run without an argument, or with a value ≤ 20000."`.

Kick off a Standard gauntlet at the parsed game count per matchup. Use `start_process` with `timeout_ms: 600000`.

After it finishes, verify:
- `data/telemetry/` has new JSONL files with today's date
- Run `python scripts/summarize_telemetry.py` and check `data/telemetry/card_summary_latest.json` exists
- At least one card's `score_mode` flipped from `bootstrap` to full
- No card that should be casting shows 0 casts (spot-check 3 high-meta-share cards)
- No silent exceptions in the sim log

If any check fails, STOP and report.

## Step 5: Full gauntlet
Only if Step 4 is clean: run the full 100k-per-matchup Standard gauntlet via `parallel_launcher`. Use `timeout_ms: 600000`.

## Step 6: Re-score and report
Rerun `scripts/build_priority_queue.py` against the new telemetry. Diff the top 20 against the previous queue. Report what moved up, what moved down, and anything surprising.

## Rules
- PowerShell: use `;` not `&&`
- For any Python with complex string formatting, write a temp `.py` file and run it with `start_process`, don't use `python -c`
- If an `edit_block` fails on whitespace, fall back to `Filesystem:write_file` or a Python replace script
- Commit any code changes with descriptive messages before moving to the next step
