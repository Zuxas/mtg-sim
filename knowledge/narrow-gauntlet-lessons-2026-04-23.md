---
title: Narrow Gauntlet — Izzet Lessons vs 5 Strixhaven Brews
date: 2026-04-23
task_ids: bst9aitvr (pre-fix), b2jtfo2gv (post-fix)
status: root_cause_found_SIM_FRAMEWORK_BROKEN
---

# Narrow Gauntlet Results — Izzet Lessons

## Headline — revised after code inspection

**Root cause: `engine/match_runner.py:137 _simple_play_turn()`
accepts an `apl` parameter and never uses it.** Both Path A (Bo3
via `run_bo3_set` → `run_match` → `_simple_play_turn`) and Path B
(heuristic `run_match_set` → same chain) ignore APLs entirely.

The two-player sim framework plays one land per turn + cheapest-CMC
creatures from hand, for both players, regardless of what APL is
passed in. Spells are NEVER cast in the sim. Triggers never fire.
The handler registry (2,009 entries) is entirely unreached during
matchup simulation.

**The 99.32% cast-weighted coverage milestone was against
card-handler registration, not sim usage.** Handlers are
correctly written but never invoked.

## Raw results (both runs)

| Opp | Pre-fix Match | Post-fix Match (fresh decklist) |
|---|---|---|
| Superior Doomsday | 0.7% | 0.7% |
| Izzet Control | 32.7% | 17.0% |
| Roaming Elementals | 0.4% | 0.4% |
| Azorius Aggro | 2.4% | 0.3% |
| Mono Green Aggro | 5.0% | 1.2% |
| **FWR** | **8.2%** | **4.1%** |

The decklist fix made it marginally worse, not better — consistent
with the new kobayui list being more spell-heavy than the stale
2025-12-30 list. More spells in a sim that can't cast spells =
more dead cards in hand = fewer creatures = more losses.

## Why this explains everything we saw

- **Control decks (Izzet Lessons) lose 95%+:** they have 4-5
  creatures in 60 cards and win via spells. The sim never casts
  spells, so Lessons just plays 4 small creatures across 15 turns
  while opponents swarm with aggro creatures.
- **Aggro decks win hard:** they have 20+ creatures, the sim plays
  creatures, everything works out for aggro.
- **GenericAPL stubs performed "fine":** they're creature-curve
  decks (Roaming Elementals Elemental tribal, Mono Green Aggro
  Llanowar-Elves curve). The sim's generic creature-play heuristic
  happens to approximate their actual plan.
- **Izzet Control matchup was least-bad (17% / 32.7%):** both decks
  are spell-heavy so both equally "lose" access to their gameplan.
  The one with slightly more on-curve creatures wins. Relative
  performance here is noise, not signal.

## What the matchup_matrix data tells us

6,338 tournament matches still stand. **Izzet Lessons at 49.5%
FWR is real-world truth, not sim output.** The deck choice for
May 29 RC remains locked on that basis.

## Tomorrow's work — scope completely changed

**Don't touch the sim framework under the 3-week RC timeline.**
Wiring APLs into `_simple_play_turn` is at minimum a multi-day
engineering project:
- Define what "APL plays a turn" means as an interface
- Adapt BaseAPL + MatchAPL signatures (designed for single-player
  goldfish) to two-player game state
- Thread decisions (main phase, priority windows, responses) through
  the turn cycle
- Validate against at least one hand-tuned matchup before trusting
  the output

That's a February-through-March project, not an April overnight.
It also might not be justified given what RC-prep actually needs:
the tournament matchup_matrix already answers "which deck plays
best in the field."

### Actual revised RC-prep plan

1. **Commit to Izzet Lessons on May 13** per tournament data. Sim
   cannot validate; doesn't need to.
2. **Sideboard work:** per-matchup SB plans for Lessons against the
   top 8 covered-by-data archetypes (Izzet Prowess, Mono Green
   Landfall, Izzet Spellementals, Simic Rhythm, Izzet Lessons
   mirror, plus any fresh post-May-15 entrants). Research via
   tournament-deck inspection + competitive content; validate by
   paper testing. This is how sideboarding has always been done
   pre-sim.
3. **Post May-15-17 RC:** re-run cast-weighted coverage and
   matchup_matrix queries to detect meta shifts from that event.
   Update SB plans accordingly.
4. **Paper-test deadline May 13** as originally planned. 4% stddev
   across matchups in the matchup_matrix data is the property that
   justifies committing this early.

## Overnight inventory (commits on main)

- `7fcecf6` stubs: 3 Strixhaven brews (GenericAPL shims)
- `603a6aa` narrow gauntlet: Izzet Lessons vs 5 post-Strixhaven brews
- `5279c2e` fix: utf-8 stdout for narrow gauntlet launcher
- `a91733b` registry: add missing Standard entries (Lessons, Doomsday, Azorius Aggro)
- `c734973` initial morning report (now superseded by this revision)
- `4da45e7` decks: current Izzet Lessons (post-Strixhaven)

## Recommendations

1. **Do not spend RC prep time fixing the sim.** It's a bigger
   project than the RC window. The sim's current state is useful
   for goldfish/APL-tuning single-deck questions (where the APL IS
   invoked via other code paths) but not for matchup simulation.
2. **File `engine/match_runner.py:_simple_play_turn` APL wiring as
   Known Major Issue.** Future work, not blocker.
3. **For any future claims that "the sim says X about matchup Y,"
   verify what path produced the claim.** Any path that calls
   `run_match` or `run_match_set` gives output unrelated to APLs.
   Goldfish paths (single-deck `sim.py`, `gauntlet_any_deck.py`
   goldfishing) may still be valid since they likely run the APL
   against an empty opponent.
