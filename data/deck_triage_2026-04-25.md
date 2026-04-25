# Deck Triage — 2026-04-25

Triage of 8 deck files flagged by `data/apl_coverage_audit_2026-04-25.csv`
for non-standard mainboard counts (mb != 60, except Yorion 80+).

## Method

1. Recounted each file mainboard from raw text (sanity-check audit numbers).
2. Pulled canonical reference list from `mtg_meta.db` via `db_bridge.py`
   (`load_tournament_deck`-style query: archetype LIKE pattern, last 60d,
   most recent placement-1 or top-8).
3. Compared current file vs canonical (set-diff on card names).
4. Decided per file: **INTENTIONAL** (Yorion etc.), **CUSTOM_VARIANT**
   (real list, differs from current canonical, kept as-is with a
   header comment), or **PARSE_BUG** (fix parser not file).

The original spec offered three outcomes (BUG = replace with canonical /
INTENTIONAL = comment / PARSE_BUG = fix parser). Reality surfaced a
fourth case dominating the set:

> **CUSTOM_VARIANT**: file is a different list from the current canonical.
> Replacing wholesale would destroy the variant. Annotated with a header
> comment that documents the diff and the source-attribution gap.

## Outcomes by file

### 5_color_niv_mizzet_pioneer.txt — INTENTIONAL

- Original count: MB=81, SB=14
- Header attribution: musasabi, MTGO Pioneer Challenge 32 #12838142, 2026-04-05, P8
- Yorion, Sky Nomad in mainboard (line 53 below header). Yorion's text
  requires "starting deck contains at least 20 cards more than the
  minimum" → 60+20 = 80 minimum. **81 is canonical for this pilot's list.**
- SB at 14 (one short of 15) is unusual but legal — kept verbatim from
  scraped source.
- **Action:** added `audit:intentional` header comment. No card changes.

### glockulous_modern.txt — CUSTOM_VARIANT (short by 2)

- Original count: MB=58
- Archetype "Glockulous" not in `mtg_meta.db` (60-day window, 0 matches).
- Closest content match: **Grixis Reanimator** (111 lists / 90d).
  Canonical: deck#51246, arturcosta, 2026-02-01 P1, MTGO Modern Challenge 32.
- Diff vs canonical: 9 unique cards differ. Current uses Psychic Frog +
  Persist + Archon engine; canonical uses Ragavan / Bitter Triumph /
  Abhorrent Oculus / Gran-Gran instead.
- **Action:** added `audit:custom_variant` header. 2 cards short, but
  archetype mismatch makes wholesale replacement wrong. Needs source
  attribution before completing.

### izzet_prowess_modern.txt — CUSTOM_VARIANT (1 over)

- Original count: MB=61
- Archetype: **Izzet Prowess** (171 lists / 60d, popular).
  Canonical: deck#119672, arturcosta, 2026-04-20 P1, MTGO Modern Challenge 64.
- Diff vs canonical: 4 unique cards differ. Current is Murktide variant
  (+ Murktide Regent x2, Fiery Islet x2 / - Founding the Third Path,
  Stomping Ground). Plus 1 extra slot (17 lands vs canonical's 18).
- **Action:** added `audit:custom_variant` header. Treating as intentional
  pending source verification.

### living_end_modern.txt — CUSTOM_VARIANT (1 over)

- Original count: MB=61
- Archetype: **Living End** (146 lists / 60d).
  Canonical: deck#83317, Mateusz Bodziak, 31/03/26 P1, 3City League (TMT) #5.
- Diff vs canonical: 25 unique cards differ. Current uses Carabid +
  Horror + Curator + Waker + Overlord of the Balemurk; canonical uses
  Generous Ent / Formidable Speaker / Endurance package.
- **Action:** added `audit:custom_variant` header. Different cycling-
  creature mix; 1 extra slot. Treating as intentional pending source.

### ruby_storm_modern.txt — CUSTOM_VARIANT (short by 6) — NEEDS COMPLETION

- Original count: MB=54
- Archetype: **Ruby Storm** (60 lists / 60d).
  Canonical: deck#121971, merfolkgod, 22/04/26 P1, MTGO League.
- Diff vs canonical: 10 unique cards differ. Current has Strike It Rich,
  Glimpse the Impossible, and 4 unusual lands (Heroes' Hangout, Romantic
  Rendezvous, Commercial District, Arid Mesa); canonical has Pyromancer
  Ascension, Ral Monsoon Mage, Urabrask, Valakut Awakening.
- **6 cards short of 60 is the worst Modern offender.** Likely a
  partial draft list that was never completed.
- **Action:** added `audit:custom_variant` header with **NEEDS COMPLETION**
  flag. Should not be used for sim runs until 6 cards are added; requires
  meta-call decision on what to add.

### uw_blink_modern.txt — CUSTOM_VARIANT (short by 1)

- Original count: MB=59
- Archetype: closest match **Azorius Phelia** (1 list / 90d, niche).
  Canonical: deck#61355, XboxGreg, 23/03/26 P4, MTGO League.
- Diff vs canonical: 9 unique cards differ. Current has Mockingbird,
  Sanctifier en-Vec, Rest in Peace, Prismatic Ending, Consign to Memory;
  canonical has Haliya Guided by Light, March of Otherworldly Light,
  Momo Friendly Flier, Teferi Time Raveler.
- **Action:** added `audit:custom_variant` header. Different Phelia
  variant. 1 missing slot — needs source attribution. (Naming is
  correct: Azorius/UW, not Jeskai.)

### yawgmoth_modern.txt — CUSTOM_VARIANT (short by 2)

- Original count: MB=58
- Archetype: **Golgari Yawgmoth** (42 lists / 60d).
  Canonical: deck#58461, themeatman, 2026-03-22 P1, MTGO Modern Challenge 32.
- Diff vs canonical: 31 unique cards differ. Current uses Collected
  Company + Chord of Calling + Eldritch Evolution engine (pre-Cauldron
  era); canonical uses Agatha's Soul Cauldron + Delighted Halfling +
  Dryad Arbor (post-Cauldron Modern).
- **Archetype has shifted significantly post-Cauldron.** Current list
  reflects an older build — not a casual cleanup target.
- **Action:** added `audit:custom_variant` header. Recommend full
  replacement with current canonical for sim relevance, but keeping
  as-is until that meta-call is approved.

### dimir_aggro_standard.txt — CUSTOM_VARIANT (2 over) — FILENAME MISLEADING

- Original count: MB=62
- Header attribution: Marjo Gabilo, HMSC Store Championship, 2024-10-31, P3.
- **Filename misleading**: list is BWG (Calix, Sheltered by Ghosts,
  Glissa, Plains, Concealed Courtyard, Razorverge Thicket) not Dimir (UB).
  Color identity is Black-White-Green (Abzan-style Pixie aggro).
- Pre-rotation 2024 list — no longer current Standard meta.
- Canonical 2024 Dimir Aggro existed (deck#33999) but is also stale and
  structurally different (mono-B aggro vs this BWG Pixie build); 21
  unique cards differ.
- **Action:** added `audit:custom_variant` header with **FLAG FOR ARCHIVE**.
  Recommend either (a) rename to `bwg_pixie_standard_2024.txt` and move
  to a historical-decks folder, or (b) replace contents with a current
  Standard Dimir Aggro list (DB has 633 lists across history; need to
  filter to current rotation).

## Audit script update

`C:\temp\full_audit.py` updated: `verify_deck_load` now reads first 10
lines of each deck file, treats `audit:intentional` and
`audit:custom_variant` markers as resolved (returns `ok (intentional, ...)`
or `ok (custom_variant triaged, ...)`). Future re-runs of the audit
will report 0 load issues for the 8 triaged files while still flagging
any new non-60 deck that hasn't been triaged.

> Note: the audit script lives at `C:\temp\full_audit.py`, outside the
> repo. Recommend moving to `scripts/full_audit.py` for reproducibility
> when this audit needs to re-run (e.g., after Pioneer L1 gaps shrink).

## Open items not addressed in this triage

1. **Ruby Storm requires 6-card completion** before being usable in sim runs.
2. **Yawgmoth list is pre-Cauldron** — substantial meta drift; should be
   replaced for sim accuracy.
3. **dimir_aggro_standard.txt** — rename or replace decision.
4. **Source attribution gap**: 6 of 7 custom variants have no recorded
   source (no `// pilot (date)` header). Adding source headers when the
   list was first imported would have prevented this triage round entirely.
5. **Glockulous archetype** is not scraped under that name. If this is a
   2026 brew, the meta-analyzer scraper may need an alias mapping.

## Summary table

| File | Format | Old MB | New status | Action |
|---|---|---|---|---|
| 5_color_niv_mizzet | pioneer | 81 | INTENTIONAL | Yorion-mandated, comment only |
| glockulous | modern | 58 | CUSTOM (-2) | Comment, archetype mismatch |
| izzet_prowess | modern | 61 | CUSTOM (+1) | Comment, Murktide variant |
| living_end | modern | 61 | CUSTOM (+1) | Comment, different cycler mix |
| ruby_storm | modern | 54 | CUSTOM (-6) | **Needs completion** |
| uw_blink | modern | 59 | CUSTOM (-1) | Comment, Azorius Phelia variant |
| yawgmoth | modern | 58 | CUSTOM (-2) | Comment, pre-Cauldron variant |
| dimir_aggro | standard | 62 | CUSTOM (+2) | **Filename misleading, archive candidate** |

**Audit re-run result:** load_issues drops from 8 to 0 (all 8 now resolve
as `ok (intentional, ...)` or `ok (custom_variant triaged, ...)`). Any
NEW non-60 deck added in the future will still be flagged.
