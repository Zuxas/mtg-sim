# experimental/

Auto-generated match APLs for Standard archetypes. These are **not hand-tuned** and quality varies. Kept visible rather than discarded because they document what a local-model code generator actually produces, and serve as working examples for anyone extending the generator.

## Source

All files in this directory were produced by `gemma_apl_chunked.py`, a tool that feeds deck lists and card context to a local Gemma model (via Ollama) and asks it to emit a `MatchAPL` subclass following the existing hand-written APL conventions.

The generator itself is not part of `mtg-sim`; it lives in the harness ecosystem on the author's machine. Regenerating these files requires that setup — there is no `make regenerate` in this repo. If someone else wants to reproduce the workflow, the relevant pieces are:

- A local Ollama install with a Gemma model pulled (e.g., `gemma2:9b` or later)
- A card database (Scryfall-sourced) to provide card oracle text for the prompt
- The `MatchAPL` base class and existing hand-written APLs as in-context examples

## Status

These are **starting points, not finished APLs.** The generator produces structurally valid code, but:

- Priority rule quality depends on what the model inferred from card text
- No guarantee that priorities follow Magic's rules correctly (timing, targeting, etc.)
- No human has reviewed each line
- Win rates in goldfish / matchup simulation vary widely

## Validated win rates (from file headers at generation time)

| File | WR at validation |
|---|---|
| `esper_pixie_standard_match.py` | 48.0% |
| `izzet_cauldron_standard_match.py` | 26.0% |
| `grixis_discard_standard_match.py` | 25.0% |
| `four_color_overlords_standard_match.py` | 16.0% |
| `azorius_control_standard_match.py` | 14 priority rules (not WR-validated) |
| `jeskai_control_standard_match.py` | 9 priority rules (not WR-validated) |
| `simic_rhythm_standard_match.py` | 8 priority rules (not WR-validated) |
| `izzet_spellementals_standard_match.py` | 1 priority rule (not WR-validated) |
| `simic_jackal_standard_match.py` | 1 priority rule (not WR-validated) |

The spread (16% to 48%) reflects generator quality variance, not the underlying archetype strength. A 16% result means the generated APL is playing poorly, not that Four-Color Overlords is a bad deck.

## How to treat these files

- **As a consumer**: use them only as stubs. Copy to `apl/` (drop the `_standard_match` suffix if you like), hand-tune, and commit the tuned version. Do not assume correctness.
- **As a contributor to the generator**: these are the evidence base. If most generated APLs have the same failure pattern (e.g., ignoring a keyword, missing an obvious priority), that is a prompt or chunking issue to fix upstream.
- **As a recruiter or code reviewer**: these represent the author's actual output from a local-model code-gen tool. They are mixed quality by design, not an attempt to hide low-quality work behind a "real" APL directory.

## Not for production matchup analysis

`run_matchup.py`, `bo3_gauntlet.py`, and similar entrypoints should point at hand-written APLs in `apl/` (not `apl/experimental/`) for anything you want to trust. The experimental files exist to be improved, not to be relied on.
