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

### Izzet Prowess (Worldly Counsel Nick Tokyo) — added 2026-05-10

- Goldfish APL: `apl/izzet_prowess_nick_tokyo_standard.py`
- Match APL:    `apl/izzet_prowess_nick_tokyo_standard_match.py`
- Decklists:    `decks/izzet_prowess_nick_tokyo_standard.txt` (current),
                `decks/izzet_prowess_nick_pt_sos_standard.txt` (PT version)
- Registry:     `izzetprowessstandardtokyo` (alias `prowessnicktokyo`)
- Source:       Nick Odenheimer / Worldly Counsel primer (RC Tokyo update)
- Bo3 sim:      67.8-68.0% FW match WR vs 15-archetype Standard field at N=200,
                +7.4pp over PT consensus (`izzetprowessstandard`), 12-1-2 W/T/L
- Features:     16-matchup MATCHUP_SB_PLANS dict, Crab Control mode toggle
                (`CRAB_CONTROL_MATCHUPS`), Stormchaser L3 leveling helper, Roaring Furnace
                cast logic, Sauna timing approximation, Get Out mode 2 (bounce own),
                Ral combo-kill detection, primer-derived mulligan rules
- Cheat sheet:  `Team Resolve/rcdc_prowess_sb_plans.md` (printable)
- Source guide: `Team Resolve/worldly_council_prowess_guide.md`

### Izzet Looting (3 variants) — added 2026-05-11

- Goldfish APL: `apl/izzet_looting_standard.py` (shared base for all 3 variants)
- Match APL:    `apl/izzet_looting_standard_match.py` (single class, 3 deck files)
- Decklists:
  - `decks/izzet_looting_store_champ_may2026_standard.txt` — Jermey locked Store Champ list
  - `decks/izzet_looting_portland_feb2026_standard.txt` — Jermey Portland 3-2 field-tested
  - `decks/izzet_looting_mcnamara_spotlight_standard.txt` — Scott McNamara Atlanta/Lyon reference
- Registry:     `izzetlootingstorechamp`, `izzetlootingportland`, `izzetlootingmcnamara`
                (aliases: `izzetlooting`, `looting` -> Store Champ)
- Source guides:
  - `Team Resolve/handoffs/2026-05-11_post-compact_looting_session.md` (full context)
  - `Team Resolve/guides/looting_sb_plans_verified.md` (verified per-matchup SB plans)
  - `Team Resolve/guides/looting_portland_side_events.md` (Portland 3-2 + 5 opp lists)
- Bo3 sim:      Portland 64.0% / Store Champ 63.3% / McNamara 56.2% FW Match WR vs
                15-archetype field at N=200, 14/15 coverage. **Jermey tuning beats
                McNamara by ~7-8pp** (Tiger-Seal main, Spell Snare main, Steam Vents
                manabase validated). Head-to-head vs Tokyo Prowess: Portland 50%,
                Store Champ 48% — essentially even when both pilots are well-tuned.
- Features:     11 matchup-keyed MATCHUP_SB_PLANS, Crab Control mode toggle
                (`CRAB_CONTROL_MATCHUPS`), Frostcliff Siege Jeskai/Temur mode
                selection per matchup, Quantum Riddler warp helper ({1}{U} early
                tempo), Tishana's Tidebinder flash on opp end step, primer-derived
                mulligan rules (1-lander on draw with 2 cantrips OK, mirror requires
                cantrips)
- Card-text audit: NO Cori-Steel (banned 2025-06-30), NO Detect Intrusion/Belion
                (Unhinged joke cards), Flow State as sorcery, Voice as creature 1/3,
                Aven at 3 CMC (Snare misses), Monument at 3 CMC (Annul/Abrade hit),
                Sear (4 dmg) kills Sapling Nursery 3/4 reach Treefolk tokens.

### Framework patches landed 2026-05-10

Three pre-existing bugs in `apl/aware_match_apl.py` and `engine/counter_resolver.py`
were patched while building the Tokyo APL. These affect ALL APLs inheriting
AwareMatchAPL, not just Prowess:

1. **`keep` <-> `keep_vs_opp` infinite recursion** (line ~720): default fallback
   re-entered the dispatcher. Patched with `_in_keep_dispatch` re-entrancy guard.
   Pre-fix, any APL that didn't override `keep` would crash on Bo3 sim with
   RecursionError.
2. **MATCH_BOUNCE/MATCH_WIPES non-defensive access** (line ~431): `_lethal_this_turn`
   used `self.MATCH_BOUNCE` directly while line 355 used `getattr(..., set())`.
   APLs without these attributes crashed at lethal calc. Patched to use defensive
   getattr matching the line-355 pattern. Unblocked Bo3 errors on Spellementals,
   Jeskai Control, Jeskai Lute, Dimir Excruciator.
3. **Get Out missing from COUNTER_VALIDITY** in `engine/counter_resolver.py`: counter
   mode wasn't wired. Added with effective cmc=3 gate (prevents over-countering
   1-mana cheap aggro creatures while still firing on priority targets like
   Sapling Nursery / Earthbender Ascension).

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


---

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

## Sequencing Telemetry and Heuristic Distillation

### Purpose

During ARL gauntlet runs, the sim logs sequencing decisions and outcomes at
the per-game level. After sufficient samples accumulate, a distillation pass
converts raw logs into human-readable heuristics. Those heuristics feed two
outputs: APL improvement candidates (reviewed before any code changes) and
Team Resolve playbook entries (the strategy layer for tournament pilots).

All sequencing data is derived from legal plays only. The sim enforces game
rules; no telemetry is collected for illegal actions.

### What gets logged

Per game, the sim appends a sequencing event record to
`logs/sequencing/<deck_slug>_<YYYY-MM-DD>.jsonl`. One record per logged event,
one line per record (JSONL format for easy streaming and grep).

**Card-timing events** -- logged whenever a spell is cast:
```json
{
  "type": "card_timing",
  "deck": "boros_energy_match",
  "game_id": "abc123",
  "won": true,
  "card": "Phlage, Titan of Fire's Fury",
  "phase": "main1 | main2 | opp_end_step | combat_trick",
  "turn": 3,
  "on_play": true,
  "opp_archetype": "izzetprowessstandard",
  "board_state": {
    "our_creatures": 2,
    "opp_creatures": 1,
    "our_life": 20,
    "opp_life": 14,
    "mana_available": 3,
    "cards_in_hand": 2
  }
}
```

**Decision-point events** -- logged at key branch points in APL logic:
```json
{
  "type": "decision_point",
  "deck": "boros_energy_match",
  "game_id": "abc123",
  "won": true,
  "decision": "bombardment_sac | attack_into_blocker | hold_mana_open | fetch_basic_vs_shock",
  "choice": "did | did_not",
  "turn": 4,
  "opp_archetype": "selesnyalandfall",
  "board_state": { ... }
}
```

**Mana-hold events** -- logged when APL reserves mana vs taps out:
```json
{
  "type": "mana_hold",
  "deck": "izzet_prowess_nick_tokyo_standard_match",
  "game_id": "abc123",
  "won": true,
  "mana_held": 2,
  "mana_total": 4,
  "reason": "counter_open | removal_open | flash_threat",
  "turn": 3,
  "opp_archetype": "azoriusmomo"
}
```

### Minimum sample threshold

No heuristic is surfaced until it has at least 200 samples on each side of
the decision (did / did_not, or phase A vs phase B). Below that threshold
the data is collected but not reported. This prevents noise from driving
APL changes or playbook entries on small samples.

### Distillation pass

Run manually or triggered automatically when a deck accumulates 1000+ games:

```
python scripts/arl_distill.py <deck_slug> [--min-samples 200] [--min-delta 3.0]
```

The distiller reads all JSONL logs for the deck, groups by decision type and
context, computes win-rate splits, and filters to findings above `--min-delta`
percentage points with at least `--min-samples` on each side.

Output: `docs/sequencing_heuristics/<deck_slug>.md`

Example finding format:
```
## Phlage, Titan of Fire's Fury -- cast timing
Matchup: vs Izzet Prowess Standard (n=847 games)
  main1 (pre-combat):  58.2% WR (n=412)
  main2 (post-combat): 67.4% WR (n=435)
  Delta: +9.2pp post-combat. STRONG SIGNAL.
  Context: effect holds across all board states sampled.
  APL candidate: prefer post-combat Phlage cast vs Prowess when mana allows.
  Playbook note: "Hold Phlage until after combat vs Prowess -- the +9pp WR
  delta is statistically robust over 847 games."

## Goblin Bombardment -- sac decision
Matchup: vs Selesnya Landfall (n=623 games)
  Sac for non-lethal damage:  51.3% WR (n=289)
  Hold for lethal only:       63.8% WR (n=334)
  Delta: +12.5pp lethal-only. STRONG SIGNAL. (already in APL -- validating)
  Playbook note: "Never sac to Bombardment unless it kills them. Current APL
  confirmed correct by data."
```

### APL improvement candidates

Findings above 5pp delta with 300+ samples are automatically appended to
`docs/apl_candidates/<deck_slug>.md` as proposed APL edits. These are
advisory only -- no APL is modified without Jermey reviewing and approving.

Format:
```
## Candidate: boros_energy_match -- 2026-06-25
Source: sequencing telemetry (1,243 games vs Izzet Prowess)
Finding: Post-combat Phlage cast +9.2pp WR vs pre-combat.
Proposed change: In main_phase() vs izzetprowessstandard, defer Phlage
  cast to main_phase2() when mana is available post-combat.
Status: PENDING REVIEW
```

Claude Code can read `docs/apl_candidates/` and propose the actual code diff
for Jermey to approve before committing.

### Playbook pipeline

When Jermey runs the playbook writer (`python write_playbooks.py`), it now
reads sequencing heuristics as an additional source alongside the existing
matchup data and SB plans.

Heuristics above 3pp delta with 200+ samples are injected into the
"Lines and Sequencing" section of the relevant playbook. Format follows the
existing Team Resolve playbook style (navy/gold, portrait, IN/OUT tables,
E.A.D. footer).

Data-sourced lines are tagged `[sim-verified]` so pilots know which tips
come from gauntlet data vs theory. Example playbook entry:

```
LINES VS IZZET PROWESS
[sim-verified] Cast Phlage post-combat, not pre-combat. +9pp WR over 847 games.
[sim-verified] Hold Bombardment for lethal only. +12pp WR over 623 games.
[theory] Lead on Ragavan T1 on the play -- tempo is king in this matchup.
```

### New script: arl_distill.py

Add to the entry point scripts list:

- `scripts/arl_distill.py <deck_slug>` -- distillation pass for one deck.
  Reads JSONL logs, outputs heuristics md and apl_candidates md.
  Flags: `--min-samples N` (default 200), `--min-delta F` (default 3.0),
  `--format-for-playbook` (outputs playbook-ready bullet strings instead of
  full analysis). ASCII-only output, exit 0/1.

### Integration with ARL loop

After each gauntlet run completes (step 8 of the loop iteration), if the
deck now has 1000+ total logged games, the loop auto-runs distillation and
appends any new findings to `arl_status.py` output under "New heuristics
since last check." Jermey sees them on next status pull without having to
run distill manually.
