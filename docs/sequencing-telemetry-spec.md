# Sequencing Telemetry + Heuristic Distillation -- design spec

> Moved out of mtg-sim/CLAUDE.md 2026-06-29 (progressive-disclosure trim). Read when working on telemetry/distillation.

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
