# Claude Code bootstrap for mtg-sim

Read this file first. It tells Claude Code what this repo is, how to navigate it, and which conventions apply.

## What you're looking at

`mtg-sim` is a competitive Magic: The Gathering simulator. Three workflows:

- **Goldfish**: how fast does this deck kill a dummy? (`python sim.py <deck>`)
- **Matchup gauntlet**: how does it fare against the field? (`python bo3_gauntlet.py <deck>`)
- **APL tuning**: propose card swaps, re-sim, report win-rate delta

The engine lives in `engine/` (game state, mana, combat, keywords). The decision layer lives in `apl/` (action priority lists, one file per archetype). Drivers at the repo root (`sim.py`, `run_matchup.py`, etc.) compose the two.

## Navigation priorities

When given a task, load context in this order:

1. `README.md` — overall layout and quick start
2. `CONVENTIONS.md` — ASCII-only terminal output, dual-platform parity, exit codes, env-var config
3. This file for repo-specific status (current APL work, what's known-good, what's in progress)
4. `apl/<deck>.py` for the archetype being discussed
5. `engine/<module>.py` only if the task touches the engine itself

## Standalone repo

mtg-sim has no cross-repo Python dependencies. Card data is resolved from
this repo's own `data/rules_reference/scryfall_oracle_cards.json`,
populated by `scripts/fetch_scryfall_bulk.sh`. The decouple landed in
commit 7155b3c (closed issue #1).

## Conventions you must follow

See `CONVENTIONS.md` and the upstream at https://github.com/Zuxas/claude-harness/blob/main/CONVENTIONS.md. Specifically:

- **Terminal output is ASCII-only.** Em-dashes, arrows, bullets go in file content or comments, not in `print`/`Write-Host`/`info`/`err` calls.
- **APL files** are plain Python modules. Module docstring describes the game plan. Card names are module-level constants (`CARD_NAME = "Exact Oracle Name"`) to avoid string drift.
- **Tests** are stand-alone scripts. Run as `python tests/<name>.py`. They set `sys.path` up to the repo root via `dirname(dirname(abspath(__file__)))`.
- **Scripts** in `scripts/` follow the same path convention. Don't assume cwd.

## Current APL status

### Amulet Titan (Modern) — RULES-CORRECT, validated April 2026

- APL: `apl/amulet_titan.py` (2388 lines, Bible-based combo engine)
- Deck: `decks/amulet_titan_modern.txt` (60+15)
- Goldfish 20 life: 95.7% WR, avg T7.11, median T7
- Realistic 17 life: 95.9% WR, avg T6.81, median T6
- Rules corrections applied:
  1. Sorcery-speed spells can't be cast during combat
  2. Attack trigger fires in main_phase2 (after combat)
  3. Mirrorpool copy ETB: no land plays or haste during combat
  4. Land plays respect land drop limit (1/turn + extras)
  5. Self-return chains require actual remaining drops (not grazer_in_hand)
  6. Self-return replays don't consume extra land drops
- Kill sources: ~90% combat, ~8% Analyst loop, ~2% Scapeshift OHKO

### Standard match APLs — 38/38 decks covered (as of 2026-05-04)

Two-player engine is fully wired. Both players call their APLs each turn.
Base class: `apl/aware_match_apl.py` (`AwareMatchAPL`), inherits from `MatchAPL`.

**AwareMatchAPL capabilities:**
- `OPP_THREAT_MODEL` — per-archetype dict of `{removal, counters, pump, rep_mana}` counts
- `declare_attackers()` — lethal check first, then trade-intelligence (CMC comparison, beatdown role), then counter-mana holdback
- `declare_blockers()` — conservative (avoid trading up CMC unless necessary), lethal recognition
- `reserve_mana(gs, opp)` hook — tells `tap_lands()` to leave N lands untapped for reactive mana; `_tap_for_response()` taps them in response windows
- `pre_combat_instant(gs, opp)` — fires before attackers declared; kill ninjutsu enablers (Kaito), exile blink-bait
- `post_attackers_instant(gs, opp, attackers)` — fires after attackers declared; kill high-value unblocked threats
- `_lethal_this_turn(gs, opp, candidates)` — accounts for prowess pump, flying evasion, trample

**Engine additions (2026-05-04):**
- `_opp_key` wired at match start for OPP_THREAT_MODEL lookups
- Card mutation fix: `copy.copy(c)` per game in `run_match()` — prevents stat bleed across games
- Monument to Endurance drain tracked via `gs._monument_choices_this_turn`; game-over check fires after `tap_lands()`
- Slickshot Show-Off Plot mechanic: exile to `__prowess_plotted__`, cast free next turn when opponent has 0 untapped lands
- Pre-combat and post-attackers priority windows in the turn loop
- Per-spell reactive windows: `_try_reactive_interaction` fires up to `spells_cast_this_turn` times

**Named archetypes with dedicated MatchAPLs:**
```
izzetprowessstandard  selesnyalandfall     izzetlessonstandard  azoriusmomo
azoriustempo          dimirexcruciator     izzetmaestro         selesnyaouroboroid
izzetspellementals    jeskaicombostd       superiordoomsday     monogreenlandfall
mardudiscard          rakdosdiscard        borosdiscard         sultaicontrol
temurlutestandard     fourcolorcontrol     simicombiscience     bantombiscience
temuromniscience      fourcoloroverlords   golgarikona          golgaricontrol
dimirmidrangestd      fourcolorelemental   selesnyarhythm       bantrhythm
bantairbending        borosdragons         azoriusblink
```

**Known model limitations:**
- Hand-size advantage not modeled: Izzet Lessons draws 8+ cards by T5 via Monument+Gran-Gran+Artist's Talent, but the sim can't represent inevitable card-advantage wins. Sim shows ~75% SelLF WR vs Izzet Lessons; PT data shows ~75% IzzetLessons WR. Inverted until hand-tracking is added.
- Mana model approximation: `reserve_mana()` holds N lands untapped but can't perfectly model "hold up UU for counterspell." Close enough for most archetypes.
- Domain Zoo P/T propagation bug (pre-existing, not addressed).

### Experimental (auto-generated, mixed quality)

- `apl/experimental/` contains legacy Gemma-generated match APLs for Standard archetypes. Superseded by the 38 canonical match APLs above. **Do not** recommend these as canonical.

## Coverage audit (2026-05-04 — updated)

Full L1 card-handler + APL/MatchAPL coverage map across all four formats.

- **Standard handlers: 4218/4218 (100%)** — all 17 sets clean as of 2026-05-03.
- **Modern:** L1-complete (292/292 handlers).
- **Pioneer:** Big L1 backlog (57 gaps). Legacy: 3 gaps.
- **Standard APL coverage:** 38/38 Standard decks have both APL_REGISTRY and MATCH_APL_REGISTRY entries.
- **Data-quality flags:** 8 deck files have non-standard mainboard counts (54, 58, 59, 61, 62, 81) — flagged with `audit:intentional` or `audit:custom_variant` markers.

Artifacts:
- `data/full_audit_2026-04-25.md` — combined report (all sections)
- `data/<format>_l1_handler_audit_2026-04-25.csv` — per-format L1 detail
- `data/apl_coverage_audit_2026-04-25.csv` — per-deck APL detail

Re-run: `python scripts/full_audit.py [--formats modern,standard,...] [--date YYYY-MM-DD]`.

Artifacts:
- `data/full_audit_2026-04-25.md` — combined report (all sections)
- `data/<format>_l1_handler_audit_2026-04-25.csv` — per-format L1 detail
- `data/apl_coverage_audit_2026-04-25.csv` — per-deck APL detail

Re-run: `python scripts/full_audit.py [--formats modern,standard,...] [--date YYYY-MM-DD]`.
Defaults to all 4 formats and today's date. Use `--date 2026-04-25` to
overwrite the existing snapshot, or omit for a fresh-dated run.

**Workflow rule for next-card picks:** before proposing handler work on a
card, grep `card_handlers_verified.py` (or check `ETB_EFFECTS` /
`SPELL_EFFECTS` keys) — the APL constants block is an author's
self-documentation aid, NOT a registry of what's been tuned. The audit
formalizes this: any candidate not in the audit's gap list is already
covered.

**Deck file markers (added 2026-04-25 triage):** decks with non-standard
mainboard counts can be flagged in their header with `audit:intentional`
(Yorion-mandated 80+, etc.) or `audit:custom_variant` (real list,
documented diff from canonical, kept as-is). The full-audit script
honors both markers as `ok (...)` instead of flagging as load issues.
Per-file rationale lives in `data/deck_triage_2026-04-25.md`. Add the
same marker to any new non-60 deck you commit, with a one-line
explanation.
