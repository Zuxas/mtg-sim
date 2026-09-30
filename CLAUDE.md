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

### Puzzle mining — Track T2 (goldfish lethal puzzles) — 2026-07-03

`scripts/mine_lethal_puzzles.py` mines "you have lethal THIS turn — find the
line" positions out of goldfish games for the analyzer's Puzzle Trainer
(spec `harness/specs/2026-07-03-puzzle-trainer-v0.md`). It hooks a deck APL's
`main_phase` in goldfish; per position it skips trivial on-board lethal, runs a
bounded DFS (500-node budget) for a lethal line that DEPENDS on a specific
main-phase play ("the winning line isn't obvious"), and self-verifies each line
replays to engine-lethal before recording. Lethality oracle is the engine's own
`gs.run_combat()` + `has_won()` on a throwaway fork — NOT a re-summed power
formula (keeps the replay gate independent). Output is a JSONL of candidates
with a one-way `GameState -> analyzer-Scene` dict; the analyzer ingests via
`scripts/import_lethal_puzzles.py -> puzzle_inbox`. Gates (Boros Energy):
T2-G2 42 candidates / 500 games (seed 42); T2-G3 byte-identical across 2 runs;
T2-G1 replay-gated at record time. Test: `tests/test_lethal_miner.py`.
CAVEATS carried in every candidate: puzzle truth = ENGINE truth (inherits sim
card-fidelity limits); goldfish = open board (no blockers / no opp instant
interaction). NEXT: gauntlet slice (real opponent + no-untapped-blocker filter)
reuses this whole pipeline.

### Sim-vs-real SCOREBOARD — 2026-09-29 (read this before judging any engine change)

Spec `harness/specs/2026-09-30-sim-real-scoreboard.md`.
`PYTHONHASHSEED=0 python -m calibration.scoreboard --format modern --since 2026-05-15`
(~80 s) scores the two-player engine (`engine.match_runner.run_match`, seed 42+i,
alternating on_play, NO ComboKillSampler) against REAL match results in the meta DB
(`matches`, read-only, via `db_bridge._resolve_meta_db`). Per cell: sim G1, sim
match (Bo3 without sideboarding, p^2(3-2p)), real WR + Wilson CI, delta, miss,
trust band, mismodel flag. Headline: real-n-weighted mean |delta|, misses,
direction agreement, Pearson r, spread (mean distance from 50%) sim vs real.
Also a FIELD table (format_config share vs real share) and a LIST table (sim
decklist vs real decklists: cosine, missing staples, cards real lists rarely run).
Output `data/scoreboard/<fmt>-<date>-<commit>.json/.md` + `history.csv` (one row per
run -- the trend line for "is the sim getting closer to reality").
Name map `calibration/name_map_modern.json`: explicit, Modern-only (the registry
ignores format -- 'Domain Ramp', 'Jeskai Control', 'Azorius Control', 'Boros Aggro'
resolve to STANDARD lists); add a DB label only when the LIST check backs it.
**First result (commit e439caa, real data 2026-05-15..09-13):** covers 35% of 19,141
real Modern rows (the rest are decks the sim cannot play: 5C Combo, W-U-B-G Goryo's,
Boros Convoke, Simic Neoform, Domain Ramp ...); 21 cells; weighted MAE **21.4pp**;
18/21 outside the real CI; same favourite 6/8; **r = 0.28; the sim is 3.4x too
one-sided** (mean distance from 50%: sim 23pp, real 7pp). Today's three rules fixes
moved the MAE 21.15 -> 21.43 (no closer). **The field in `format_config.py` is
stale:** real post-ban Modern (since 2026-05-09) = Izzet Prowess 9.0%, Eldrazi Tron
8.1%, Izzet Affinity 6.3%, Mono Red Aggro 6.1% (unmodeled), Esper Blink 5.4%
(retired from the model), Boros Energy 4.7% (modeled 14.5%); Death and Taxes and
Temur Crashcade (modeled 5.5% / 3.4%) have NO real lists. Stale sim lists: Belcher
0.27 cosine (old Chancellor Belcher vs real Tameshi Belcher), Neobrand 0.20, Grixis
Reanimator 0.60, Dimir Midrange 0.70. The "no post-ban Modern data" notes below and
in format_config.py are OUT OF DATE.
**Standard (commit a98c6fb, `name_map_standard.json`, 32 decks):** covers 45% of 24,659
real rows; 19 cells; weighted MAE **35.9pp**; 18/19 outside the real CI; same favourite 4/7;
r = 0.30; **5.7x too one-sided**. The sim's control decks can't win: Four-Color Control
wins 0% vs Izzet Lessons (real 47%), 4% vs Izzet Prowess (real 38%); Izzet Prowess beats
Spellementals 94% G1 (real 51%, n=843). Stale Standard lists: Azorius Control 0.19,
Sultai Reanimator 0.29, Azorius Aggro 0.40, Boros Aggro 0.45.
Tests `tests/test_scoreboard.py` (metric math hand-computed; in-memory DB rules).

### Fabricated goldfish flying-draw REMOVED — 2026-09-29 (engine, user sign-off)

Spec `harness/specs/2026-09-29-remove-fake-flying-draw.md`. `GameState._do_combat`
ended with "Guide of Souls flying damage trigger: draw a card" for ANY flying
attacker (since 0af1d98) -- no printed card does that. Fake draws per goldfish
game before removal: Izzet Prowess std 5.98, Azorius Blink std 5.36, Sultai
Reanimator 4.71, Esper Raffine 4.37, Dimir Midrange std 4.10, Dimir Midrange
Jermey 3.65, Tokyo Prowess 3.30 ... 40+ lists >= 1.5. Goldfish only: the match
path (`match_runner._resolve_combat`) never had it -- run_match field unchanged
(Boros vs Modern 56.96% exactly). Measured n=2000: Azorius Blink T7.17 -> T8.13,
Tokyo Prowess T8.60 -> T9.02 (win 92.9% -> 89.1%), Sultai Reanimator T9.96 ->
T10.28, Dimir Midrange Jermey T6.23 -> T6.40, Boros Energy unchanged.
**Every goldfish-derived number for a flying deck before 2026-09-29 is
inflated** -- including the bo3_gauntlet race-model FWs quoted below (Tokyo
Prowess 67.8%, Looting 63-64%): re-run before relying on them.
Test `tests/test_no_fake_flying_draw.py` (red on the old code, green now).

### All plain keywords from printed text — 2026-09-29 (engine, user sign-off)

Spec `harness/specs/2026-09-29-keywords-from-printed-text.md`. The haste
predicate now covers flying, reach, menace, trample, shadow, fear, intimidate,
first/double strike, deathtouch, lifelink, vigilance, defender, indestructible,
hexproof (incl. "hexproof from X"), shroud, flash (`_PRINTED_KEYWORDS`). Ward,
protection, prowess, undying, persist, dredge, unblockable and role tags stay
regex. Tag diff across all deck files: 87 cards lose >= 1 tag, 0 gain. Creatures
that matter: Guide of Souls (flying, 11 Boros lists), DRC / Psychic Frog
(flying -- DRC's delirium flying is still granted dynamically in goldfish),
Scion of Draco (5 colour grants), Kellan / Expressive Firedancer / Burnout
Bashtronaut / Urdnan (double strike), Preacher (lifelink). **Found on the way:**
`GameState` combat has a FABRICATED "Guide of Souls flying trigger: draw a card"
on ANY flying attacker (since 0af1d98) -- Guide's false flying made Boros draw
~1.5 free cards per goldfish game (3,016 in 2,000 games -> 0 now). Not removed
(logged: IMPERFECTIONS goldfish-fake-flying-draw) -- it still fires for real
fliers (Delver, DRC at delirium, Slickshot). **Measured:** goldfish Boros Energy
T4.832 -> T4.942 (the fake draw), Izzet Maestro T5.425 -> T5.866, Boros Aggro
T4.437 -> T4.685; Boros vs the Modern field (run_match) 57.32% -> 56.96%.
Tests `tests/test_keywords_printed_text.py`; pytest 125 passed, same 3 failures /
4 errors. `mono_red_aggro_standard` never kills in goldfish (pre-existing).

### Haste only from a printed keyword + Dash — 2026-09-29 (engine, user sign-off)

Spec `harness/specs/2026-09-29-haste-from-printed-keyword.md`. `engine/keywords.py`
tagged `KWTag.HASTE` from `\bhaste\b` anywhere in the oracle text, so every card
that MENTIONS haste had it: Ragavan (Dash reminder; cast for {R} and attacked
that turn), Badgermole Cub (14 decks, earthbend land), Bloodghast (conditional),
Emperor of Bones, Ardyn, Greasefang, Rootha, Summon: Brynhildr, Xenagos. Now a
predicate (`_PREDICATE_RULES` / `_has_printed_keyword`): haste only when it is a
whole comma-separated keyword token on a line, reminder text stripped. Dash is
real: `GameState.cast_spell_dash` (beside `cast_spell_warp`; `_DASH_CARDS` =
Ragavan {1}{R}) pays the cost, counts as a spell, no summoning sickness, marked
`_dashed`; returns to hand at the end step in BOTH paths (`_tick_dash` goldfish,
`_run_end_step` match). `BorosEnergyMatchAPL._should_dash_ragavan`: dash when
turn > 1, 2+ mana and the opponent has no untapped creature; else hardcast {R}
(87 dashes in 180 test games). `card_specs.ragavan.dash` routes through it.
**Measured (PYTHONHASHSEED=0):** Boros goldfish n=2000 avg kill T4.592 -> T4.832
(median 4 -> 5, by-T4 51.7% -> 38.0%); Boros vs the modeled Modern field through
`run_match` (18 decks, n=200 each, same seeds, pre-fix commit in a worktree)
field-weighted 58.04% -> 57.32% (-0.72pp; cells within noise, combo races down
most). **Note:** `bo3_gauntlet.py --deck "Boros Energy"` silently loads
`--deck-file`'s default `decks/humans_legacy.txt` and is a goldfish-race model --
it cannot measure an engine change for Boros (86.1% both runs); pass
`--deck-file` explicitly. NOT fixed (logged): the same regex class for other
keywords (~40 creatures: flying on DRC / Guide of Souls / Psychic Frog, trample on
Scion of Draco ...) -- many are conditional grants needing handlers.
Tests: `tests/test_haste_printed_keyword.py` (H1 tags on real oracle text, H2 dash
goldfish + match). pytest 123 passed (was 119 + 4 new), same 3 pre-existing
failures / 4 collection errors.

### Puzzle mining — gauntlet slice (real opponent board) — 2026-09-29

`scripts/mine_gauntlet_puzzles.py` mines the same "lethal THIS turn" puzzles
from TWO-PLAYER games: our deck (seat A, default Boros Energy) vs every
non-combo deck in the format field (spec
`harness/specs/2026-09-29-gauntlet-lethal-puzzles.md`). No engine edits:
`match_runner._run_player_turn` is wrapped in the miner process only; at each
of our turns the TwoPlayerGameState is deepcopy-forked and main-phase-1 lines
(decision_api PLAY_LAND/CAST) are searched with a scripted `LinePilot`. The
ORACLE is the engine's own full turn on the fork (draw, line, combat with the
defender's real blocks + response windows, win check) -- one fork + one turn
per node gives both "kills?" and the next legal actions. Caps: opp life <= 12,
120 nodes, depth 6, one puzzle per game; the empty line (just attack) must NOT
kill. The scene exports the opponent's board (tapped = attacked last turn) AND
hand, revealed, because the kill is verified against exactly that hand.
**Engine finding (FIXED later 2026-09-29, see the haste section above):** the keyword regex tagged haste on any
text that MENTIONS haste -- Ragavan (dash reminder, and cmc 1 so it attacks
the turn it is cast for {R}), Bloodghast (conditional), Emperor of Bones,
Badgermole Cub, Xenagos. The miner drops any line that casts a creature
whose haste is not PRINTED (`printed_haste`): 563 lines dropped in the 3300-game
run. See IMPERFECTIONS `haste-tag-from-reminder-text`. Results (seed 42,
PYTHONHASHSEED=0): 990 games -> 8 (0.8%, the <=1000-game yield gate FAILED,
reported not loosened); 3300 games -> 23 engine-proven kills (all with >=1
untapped opposing blocker, 7 the Boros pilot itself missed), then two checks
the engine cannot make: `survives_best_blocks` (the opponent's k blockers take
our k biggest attackers -- the sim defender blocks by heuristic; the search
prefers a line that passes) and `hand_threats` (instant / flash / evoke /
channel in the revealed hand unless our Voice of Victory stops spells; Aether
Vial + a creature). Pre-fix engine: 16 CLEAN, 7 flagged (3 weak block; 4 hold
Solitude / Dismember / Vial + creature). **Re-mined on the haste-fixed engine
(current `data/gauntlet_candidates.jsonl`): 24 kills -> 17 CLEAN -> `--out`, 7
flagged -> `<out>_flagged.jsonl` (4 weak block, 3 real answer in hand); 0
fake-haste lines left.** ~150 s. Gates in `tests/test_gauntlet_miner.py`:
printed-haste, hand-threat and best-block units, G4 no perturbation (240 games
identical with/without the hook), G5 byte-identical, G1/G2/G3 on every
candidate via an independent re-played game (current batch: 24/24). Output `data/gauntlet_candidates.jsonl`
(gitignored run artifact) -> analyzer `python -m scripts.import_lethal_puzzles <jsonl>
[--commit]`.
```
PYTHONHASHSEED=0 python scripts/mine_gauntlet_puzzles.py --games-per-opp 300 --seed 42
```

### REAL Modern field + real decklists — 2026-09-29 (supersedes the 2026-06-30 estimate below)

Spec `harness/specs/2026-09-30-field-and-lists-refresh.md`. Commits 228b3fc, 03e841e (lists),
dadf88a (scoreboard after lists), 9d9fa76 (field).
- **UPDATE same day (d570d9c, 015f947; spec 2026-09-30-field-registry-stub-fix):** registry
  entries `izzetprowess`/`prowess`/`esperblink`/`domainzoo`/`domain` now load their
  `decks/*_modern.txt` (were `data.stub_decks` keys) -> Izzet Prowess 9.0 + Esper Blink 5.4
  re-added: field = 14 decks, ~57% of real appearances. Grixis Reanimator stays out (registry
  proxies it to the Goryo's list on purpose). Boros vs field 56.00 -> 56.46. STILL OPEN: the
  Standard field key "Izzet Prowess" and Legacy "Dimir Tempo" resolve format-blind to another
  format's deck (`izzetprowessstandard` exists but that key never reaches it).
- `FORMATS["modern"]["field"]` = REAL match-appearance shares (mtg_meta.db `matches`,
  2026-05-15..09-13), 12 decks, ~42% of real appearances (before the update above). A key enters only if
  `load_deck_and_apl(key, "modern")` loads the name map's `deck_file` AND `get_match_apl(key)`
  is the mapped MatchAPL. **Izzet Prowess (real #1, 9.0%), Esper Blink 5.4%, Grixis Reanimator,
  Domain Zoo are LEFT OUT: their registry key loads a stub/other list** (Grixis Reanimator even
  loaded a different list inside the OLD field). Fix = registry work, then re-add.
- Label gap: `matches` (mtgmelee) uses colour-prefixed labels (Gruul Eldrazi 165, Mono Blue
  Belcher 204, Tameshi Belcher 179) while decklists (mtgtop8) say Eldrazi Ramp / Landless
  Belcher -> those decks show 0 real appearances until name_map_modern.json maps them.
- Real lists swapped in (medoid real decklist, provenance in the file header; old lists in
  `decks/archive/*_pre-2026-09-29.txt`): Modern Dimir Midrange (cosine 0.70 -> 0.95), Standard
  Izzet Control (0.59 -> 0.81). 9 other stale lists FAILED the pilot-compatibility check (the
  APL has card-specific logic for cards the real list dropped): Mono Red Aggro, Eldrazi Ramp,
  Living End; Standard Azorius Aggro, Boros Aggro, Jeskai Control, Dimir Midrange, Azorius
  Momo, Sultai Control -> "needs APL work". Skipped as stub/curated: Grixis Reanimator, Belcher,
  Azorius Control, Four-Color Control.
- Effect: scoreboard Modern MAE 21.43 -> 21.57, Standard unchanged (no real cell for Izzet
  Control). Boros Energy vs field 56.96% (old) -> 57.36% (lists) -> 56.00% (real field).
  Overconfidence (sim 3.4x / 5.7x too one-sided) is still the dominant error.

### Post-ban Modern field refresh (data/coverage) — 2026-06-30  (SUPERSEDED 2026-09-29, see above)

The modeled Modern field in `format_config.py` was refreshed for the May-2026
B&R (BANNED Phlage + Lotus Field; UNBANNED Umezawa's Jitte + Violent Outburst).

- **No live source data.** `mtg_meta.db` has NO post-ban Modern data — its most
  recent Modern event is 2026-04-24 (pre-ban) and the `untapped_*` tables are
  Arena-only. The new `field` is therefore a **documented best-estimate**, not a
  pulled snapshot: pre-ban DB 30-day baseline (1591 decks) + transparent
  per-ban deltas. The derivation is written into the `format_config.py` modern
  comment block. Re-pull once post-ban tournament data lands.
- **Ban hygiene:** removed Phlage from `boros_energy_modern` (4), `domain_zoo_modern`
  (3), `jeskai_blink_modern` (4), `jeskai_control_modern` (1); removed Lotus
  Field from `amulet_titan_modern` (2). Replacements keep each list legal at its
  prior count (Amulet stays at its audit:intentional 61).
- **Unban representation:** `living_end_modern` + new `temur_crashcade_modern`
  run Violent Outburst; `boros_energy_modern` + new `death_and_taxes_modern` run
  Umezawa's Jitte.
- **New archetypes (deck FILE + BOTH registries + STUB synthetic MatchAPL):**
  - `deathandtaxes` / `dnt` -> `DeathAndTaxesMatchAPL` (`decks/death_and_taxes_modern.txt`) — Jitte payoff.
  - `temurcrashcade` / `crashcade` -> `TemurCrashcadeMatchAPL` (`decks/temur_crashcade_modern.txt`) — Violent Outburst cascade.
  - Both stubs follow the (now-retired) 2026-06-29 broodscale synthetic-matchup
    pattern: they play as generic creature/tempo decks so gauntlets RUN; their
    numbers are NOT primer-validated. Promote before trusting any cell.
    (2026-07-02: `apl/gruul_broodscale_match.py` itself was PROMOTED to a real
    hand-written combo APL + real June list; the old stub deck is archived at
    `decks/archive/gruul_broodscale_modern_synthetic_stub_2026-06-29.txt`.)
- **Retired from field** (deck files + registry kept): Esper Blink (folded into
  the shrunken Jeskai Blink shell), Jeskai Control (Phlage-dependent, fell out
  of top-18). Boros Energy share 21.2->14.5; Jeskai Blink 10.6->3.0; Living End
  2.7->6.5.
- **Validation:** all 18 modeled decks load (60/15 or audit-marked) and resolve
  in BOTH `APL_REGISTRY` + `MATCH_APL_REGISTRY`; both new decks are clean 60/15
  with zero unresolved cards; no banned card lines remain in any modern deck.
  Scope was data/coverage only — no engine/APL-fidelity changes.

### Match mulligan keep-routing — landed, then reverted to crude default (2026-07-01)

`engine/match_runner._do_mulligan_runner` routes `run_match` opening hands through each
deck's real `keep()`/`bottom()` (London, seeded via `gs.rng`), with three modes
(`crude` / `london_crude` / `keep`) selected by `_mull_mode`. The Boros+Amulet first-slice
production flip was **reverted**: `_KEEP_ROUTED_APLS` is now empty, so the production default
is `crude` for every deck. The 5-mode attribution (spec Amendment 2) found the slice's only
production effect was a +1.89pp London-vs-Vancouver mechanic artifact that inflated Boros field
WR ~1.7pp and did NOT unstarve combo assembly. The routing machinery is retained (B0 for the WR
mulligan sweep; enables a future symmetric full-field flip after the id()-ordering predecessor).
keep-mode stays reachable via `MULL_MODE` / `MULL_MODE_A/B` env overrides. Findings:
`harness/knowledge/tech/mull-routing-falsification-2026-07-01.md`.

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
- KNOWN gauntlet caveat: opponent-side undermodeling makes several cells unreliable. They are flagged
  in `mismodeled_matchups.py` (combo/reanimator cells -- Goryo's/Grixis, Living End, Amulet Titan
  [added 2026-07-09], Broodscale, Belcher, Neobrand, Ruby Storm, Temur Crashcade -- each with a per-cell
  direction; read the flag, do not assume) and the gauntlet drivers (full_field_gauntlet, bo3_gauntlet,
  gauntlet_any_deck) print an inline `[!MISMODEL ...]` flag + legend. **When analyzing matchups or deck
  choice, DOWN-WEIGHT any flagged cell** -- trust its direction, not its number. Combo-sampler routing
  was prototyped to fix this and REJECTED (see IMPERFECTIONS combo-decks-not-sampled-in-gauntlet-run_match).
- AFFINITY CELL CONTESTED (2026-07-10 decomposition; `izzet affinity` note_2026_07_10): the bo3
  `_run_fair` field cell (base 42.7 / Low Curve 48.0 g1) reads ~15-25pp BELOW current-engine run_match
  MATCH (63.0) and live paper (72.7, n=23), both of which put Boros FAVORED. So the old "Affinity
  INFLATED" read is CONTESTED / possibly INVERTED (the bo3 cell may be DEFLATED; direction NOT flipped
  at n=23); build effect base->lowcurve is only ~+5pp. Do NOT treat the bo3 Affinity cell as a CONFIRMED
  liability. Broader open question: the bo3 `_run_fair` path DIVERGES from run_match (~15-25pp; which
  side is wrong is unresolved -- bo3 may under-rate OR run_match may over-rate) -- IMPERFECTIONS
  bo3-run_fair-vs-run_match-divergence.

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

## Verification & Hot-Zone Protocol

- **State verification first.** Before starting any work, state how you will verify it.
- **Verify after.** After finishing, run that verification and report the results -- evidence, not just assertion.
- **Hot zones require sign-off.** Before changing any code in a hot zone, ASK first and explain the blast radius (what breaks if it's wrong, and how far it reaches). Hot zones in this project: the engine core (`engine/match_runner.py`, `engine/game_state.py`, stack/priority/combat), the oracle handlers (`card_handlers_verified.py` / card_specs), and the APL registry (`apl/__init__.py`). A change to any of these shifts every downstream goldfish/gauntlet result.
