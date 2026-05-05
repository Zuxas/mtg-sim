# engine/_research/

**Status:** RESEARCH-IN-PROGRESS, NOT WIRED INTO SIMULATOR
**Created:** 2026-04-27
**Purpose:** Stash for engine-adjacent code that's been started but not yet
integrated into the live simulator.

## What's here

### card_priority.py (357 lines)

Scoring formulas for ranking which cards to write handlers for next.
Two modes:

- **Bootstrap score** (used before telemetry exists): weighted combination
  of `meta_share_weighted_copies`, `meta_share_sum`, `effect_severity`, and
  `complexity_penalty`.
- **Full score** (telemetry-aware): adds `cast_rate`, `resolve_rate`,
  `opening_hand_rate`, `win_impact_proxy`, and `confidence_penalty`.

Pure functions, no side effects except loading hand-tagged severities
from `data/priority_queue/severities.json` at import time.

Public surface: `CardStats` dataclass, `bootstrap_score()`, `full_score()`,
`score_cards()`, `tag_severity()`, `get_severity()`,
`build_normalized_field_maps()`.

### card_telemetry.py (261 lines)

Append-only JSONL event logger. `TelemetryCollector` class with five
event-recording methods:

- `record_draw(...)` -- card drawn (opening hand or regular draw)
- `record_cast(...)` -- card cast from hand
- `record_resolve(...)` -- spell resolved or countered/fizzled
- `record_zone_transition(...)` -- card moved zones (ETB/death/exile/etc)
- `record_game_end(...)` -- game finished (won/lost/turns/illegal_events)

Default output: `data/telemetry/raw_games.jsonl`. Each line is a single
JSON event with `timestamp_utc`, `run_id`, `match_id`, `game_id`,
`deck_id`, `opponent_deck_id`, `card_name`, `payload`.

## What's NOT here (companion files still in mtg-sim/scripts/, untracked)

These scripts reference card_priority + card_telemetry and form the rest
of the pipeline. Status: also untracked, also not wired in:

- `scripts/build_priority_queue.py` -- builds the priority queue from
  meta-share data + telemetry aggregates
- `scripts/build_meta_shares.py` -- computes `meta_share_sum` and
  `meta_share_weighted_copies` per card from tournament data
- `scripts/cast_weighted_coverage.py` -- coverage analysis weighted by
  cast rate
- `scripts/summarize_telemetry.py` -- aggregates raw JSONL events into
  per-card stats consumable by card_priority.score_cards()
- `scripts/smoke_test_priority_pipeline.py` -- end-to-end smoke test

The 2026-04-27 triage chose to stash only the two engine files (which
were the IMPERFECTIONS-tracked items) and leave the scripts untracked
in scripts/ for now. If/when the pipeline is revived, the scripts move
in alongside the engine files.

## Why it's here

The pipeline is well-designed (clean dataclasses, pure functions,
persistent severity tags from JSON, two scoring modes for cold-start
vs warm-state). It looks like deliberate research, not scratch work.
But:

- Nothing in the live simulator imports card_priority or card_telemetry
- The companion scripts are also untracked
- There's no smoke-test pass on record
- No entry point hooks the telemetry collector into the sim loop

So it's "designed and partially built but not turned on." Stashing it
here makes that status explicit via filesystem location, removes drift-
detect / git status noise, and keeps the work intact for future revival.

## Revival path

When you want to wire this up:

1. **Move files back to engine/** (`mv engine/_research/card_*.py engine/`)
2. **Move companion scripts** (build_priority_queue, build_meta_shares,
   cast_weighted_coverage, summarize_telemetry,
   smoke_test_priority_pipeline) from `scripts/` to wherever they belong
   (probably keep in `scripts/`)
3. **Add a hook in the sim loop** to instantiate `TelemetryCollector` and
   call `record_*` methods at the right turn-loop points. Likely sites:
   - `engine/game_state.py:_draw` -> `record_draw`
   - `engine/game_state.py:cast_spell` -> `record_cast`
   - The stack resolution path -> `record_resolve`
   - `_make_token` / `creatures_died` etc -> `record_zone_transition`
   - End of `run_game` / similar -> `record_game_end`
4. **Run smoke test** (`python scripts/smoke_test_priority_pipeline.py`)
   to confirm the pipeline writes JSONL, aggregates, and produces a
   ranked priority queue
5. **Commit the engine files + scripts + a top-level docs reference**
   in one cohesive commit
6. **Delete this README** (or keep it, updated to "ARCHIVED, see
   commit `<hash>`")

Estimated effort if picking up cold: 60-90 minutes for a working pipeline,
2-4 hours to wire telemetry into all the right sim-loop sites with full
coverage.

## Why it was moved (2026-04-27 context)

The orphan-engine-files entry in `harness/IMPERFECTIONS.md` flagged these
two as "untracked AND no importers" (decision-needed: wire up vs delete).
Deleting would have destroyed real research; wiring up was bigger work
than the imperfection deserved as a quick-win. Stashing under `_research/`
codifies a third option: preserve the work, remove drift noise, make
not-yet-wired status explicit.

This pattern (stash-rather-than-delete) becomes the convention for
future research-in-progress that isn't ready to commit but shouldn't be
lost. New `_research/` subdirs can be added under any module
(`apl/_research/`, `scripts/_research/`, etc.) following the same
convention.

## Lint / drift handling

`harness/scripts/lint-mtg-sim.py` and `harness/scripts/drift-detect.ps1`
should both treat `_research/` paths as out-of-scope:

- **lint-mtg-sim.py**: AST registry checks already only walk
  APL_REGISTRY entries, so files in `_research/` aren't visited.
- **drift-detect.ps1**: load-bearing-WIP check walks `git status --porcelain`
  and looks for importers in `git ls-files "*.py"`. Files in `_research/`
  that get committed will be in `git ls-files`, so they won't show as
  untracked. Files in `_research/` that stay untracked will only fire
  load-bearing-WIP if something tracked imports them, which `_research/`
  by convention doesn't.

If `_research/` ever needs explicit lint/drift exclusion (e.g., to
suppress style checks that don't apply to research code), add a path
filter at that point.
