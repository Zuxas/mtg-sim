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

### Low Curve Boros Energy (Modern) — added 2026-06-29 (post-ban)

- Deck: `decks/boros_energy_lowcurve_modern.txt` (60+15, Team Resolve primer, post-Phlage)
- Registry: `borosenergylowcurve` in BOTH APL_REGISTRY and MATCH_APL_REGISTRY -> `BorosEnergyMatchAPL`
- Engine fidelity (this commit): Reckless Pyrosurfer battle cry (rule 702.92) now fires in BOTH the
  goldfish path (`GameState._do_combat`) AND the match path (`match_runner._resolve_combat`); the
  Voice-of-Victory mobilize -> Pyrosurfer "11-damage line" is modeled. `_battle_cry_instances` set by
  `card_effects.on_landfall` (per landfall), reset per-turn. Fetch lands now fire landfall twice
  (ETB + fetched land) — a prior latent bug fired ZERO. Tests: `tests/test_pyrosurfer_battlecry_*.py`.
- Calibration coupled in same commit: `AwareMatchAPL.declare_attackers` rewrite moved Selesnya-vs-Prowess
  from a wrong ~77% to 65.3% (in band [60,71.5], PT 62.9). See
  `harness/knowledge/tech/boros-energy-postban-validation-2026-06-29.md`.
- KNOWN gauntlet caveat: opponent-side undermodeling inflates several matchups (Grixis Reanimator APL
  CRASHES every turn -> inverts that known-DOG matchup; tracked in IMPERFECTIONS.md).

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

## Autonomous Research Loop (ARL) + Sequencing Telemetry

These two design specs were moved out of this always-loaded bootstrap (2026-06-29 trim, per Matt-Pocock progressive-disclosure) to cut context cost. They are unbuilt-feature designs, not active steering -- read on demand:

- ARL (loop_state.json spine, iteration cycle, candidate generation, human interface, blockers, entry-point scripts): `docs/arl-spec.md`
- Sequencing telemetry + heuristic distillation (logging schema, distillation pass, APL candidates, playbook pipeline): `docs/sequencing-telemetry-spec.md`
