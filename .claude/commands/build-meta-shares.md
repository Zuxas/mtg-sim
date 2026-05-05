---
description: Recompute META_SHARE_BY_DECK from mtg_meta.db and rebuild the priority queue. Optional args forwarded to the builder (e.g. --days 60 / --from YYYY-MM-DD --to YYYY-MM-DD / --source decks|db|both).
---

Recompute Standard meta shares from the meta-analyzer DB, then rebuild the priority queue so scores reflect current meta.

Steps:
1. Parse `$ARGUMENTS`. Extract window args (`--days`, `--from`, `--to`) for `build_meta_shares.py`. Extract `--source` (default `both` for this command — covers both local decklists and DB-sourced cards) for `build_priority_queue.py`. Any other tokens pass through to `build_priority_queue.py` as-is.
2. Run `python scripts/build_meta_shares.py <window args>` — writes `data/priority_queue/meta_share_by_deck.json` keyed by local deck slug. Default window: last 90 days.
3. Run `python scripts/build_priority_queue.py --source <source> <window args>` — rebuilds `data/priority_queue/standard_matrix_queue.{json,csv}` using the new shares. Sources:
   - `decks` — only cards in local `decks/*_standard.txt` (runnable scope, narrow)
   - `db` — full mtg_meta.db Standard pool in window (comprehensive, but many cards the sim can't actually play)
   - `both` — union, with local decklists winning on archetype name collisions (recommended)
4. Print a short summary: window used, matched archetypes, queue size, count of `missing`-status cards, and the top 10 entries with their severity and handler status.

If step 2 reports fewer than 5 matched archetypes, widen the window before step 3 — a thin share distribution will produce misleading ranks. The default window is appropriate for active Standard; during rotation or post-set-release, a 30-day window is often better.

Do not edit `scripts/build_priority_queue.py` to set shares inline — that file loads from the JSON at startup. Shares belong in data, not code.
