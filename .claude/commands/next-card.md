---
description: Write a handler for the next unhandled card in the specified format
---

Format: parse $ARGUMENTS. Accept `modern`, `standard`, `pioneer`, `legacy`. Default to `modern` if empty. Reject anything else with "Unknown format: <value>".

## Step 1: Pick the next card

**Prelude — self-locate.** If the current working directory basename is not `mtg-sim`, `cd mtg-sim`. If a directory named `mtg-sim` does not exist relative to cwd, STOP with: `Run this command from the vscode ai project workspace or from mtg-sim directly.`

Query mtg_meta.db using the exact SQL below. Substitute `<format>` with the parsed $ARGUMENTS value (lowercase). Do not modify the query structure — both the `card_data` join and the `json_extract` legality filter are mandatory. Cards that were historically legal but rotated out must not be picked.

```sql
SELECT c.name, SUM(dc.quantity) AS copies, COUNT(DISTINCT d.id) AS decks
FROM deck_cards dc
JOIN cards c ON c.id = dc.card_id
JOIN decks d ON d.id = dc.deck_id
JOIN events e ON e.id = d.event_id
JOIN card_data cd ON cd.name = c.name
WHERE LOWER(e.format) = '<format>'
  AND dc.is_sideboard = 0
  AND json_extract(cd.legalities, '$.<format>') = 'legal'
GROUP BY c.name
ORDER BY copies DESC
```

Walk the result rows top-down. For each candidate, run `python scripts/is_handler_registered.py "<card name>"`. Exit code 0 ("YES") means the card is already registered — skip it and continue. Exit code 1 ("NO") means not registered — this is today's card. Do NOT AST-walk or grep the handler files yourself; the script does a live-import against `ETB_EFFECTS` and `SPELL_EFFECTS` which is the only check that catches registrations across all engine modules (produced the Stormchaser's Talent triplicate when we tried prose-driven checks instead).

If the first 500 candidates all return exit code 0, report "No unhandled cards in top 500 for <format>" and stop.

## Step 2: Pull oracle text
Look up the card on Scryfall. If Scryfall is bugged or the text looks wrong, cross-check against any local cache. Print the oracle text before proceeding.

## Step 3: Classify
Decide which category the card falls into:
- **ETB trigger** → register in `_ETB_HANDLERS` or `ETB_EFFECTS`
- **Spell effect** (instant, sorcery, or cast trigger) → register in `_SPELL_HANDLERS` or `SPELL_EFFECTS`
- **Static ability / aura / passive** → do NOT write an ETB stub. Add a comment in card_handlers_verified.py noting the card needs handling via the static-ability path, and move to Step 1 for the next card.
- **Tap/activated ability** → same: comment + skip, don't write a log-only stub.

If the effect matches an existing family in effect_family_registry.py, use the family mapping. Otherwise write a minimal custom handler following the patterns already in card_handlers_verified.py.

## Step 4: Write and register
Write the handler function. Register it in the appropriate dict. If you use edit_block and it fails on whitespace, fall back to Filesystem:write_file.

## Step 5: Verify
Import card_handlers_verified.py and confirm the new handler is in the live registry. Run scripts/smoke_test_priority_pipeline.py to confirm nothing regressed.

## Step 6: Commit

**Precondition — check file history before staging.** Run `git log --oneline -- engine/card_handlers_verified.py | head -1`. If the output is empty, STOP with: `card_handlers_verified.py has no git history — commit it manually first with a baseline message, then re-run /next-card.`

Stage only `engine/card_handlers_verified.py`. Git commit with message `handler: <card name> (<format>)`.

## Step 7: Report
Print:
- Card name and format
- Which family/pattern was used
- Registry size after (ETB + SPELL totals)
- Next card's name if you peeked at the queue

## Rules
- PowerShell: `;` not `&&`
- Temp `.py` files, not `python -c` for anything complex
- Never write a log-only stub for a card whose effect isn't an ETB/cast trigger — skip it with a comment instead
