# Conventions

This repo follows the conventions defined in the [claude-harness](https://github.com/Zuxas/claude-harness) template repo. The canonical convention document is:

https://github.com/Zuxas/claude-harness/blob/main/CONVENTIONS.md

Read that first. It covers ASCII-only terminal output, idempotent scripts, line endings, exit codes, env-var configuration, and knowledge block frontmatter — all of which apply here.

## mtg-sim-specific additions

### APL format

Action Priority Lists live in `apl/` as plain Python modules. Each file defines one or more APL classes that inherit from `MatchAPL` (or `BaseAPL` for non-match contexts). The file's module-level docstring should describe the deck's game plan in turn-by-turn terms. Card names are declared as `MODULE_LEVEL_CONSTANTS = "Exact Card Name"` at the top of the file to avoid string drift.

Experimental / auto-generated APLs go under `apl/experimental/` with its own [README](./apl/experimental/README.md) describing provenance. Do not mix hand-tuned and auto-generated APLs in the same directory.

### Cross-project dependency

`mtg-sim` imports `from scrapers.scryfall import get_cards_data` which lives in the sibling repo [mtg-meta-analyzer](https://github.com/Zuxas/mtg-meta-analyzer). For a fresh clone to run, both repos must be checked out as sibling directories:

```
your-dev-dir/
├── mtg-sim/                     <- this repo
└── mtg-meta-analyzer/           <- required; clone alongside
```

This coupling is tracked as an open issue on the repo; see the "Decouple scrapers dependency" issue for the proposed long-term fix.

### Test invocation

Tests are stand-alone scripts (not pytest). Invoke as:

```bash
python tests/test_match_engine.py
```

Each test sets `sys.path` up to the repo root before importing, so any working directory works.

### Scripts

`scripts/` holds utilities, diagnostics, and build tools. Everything in `scripts/` should be runnable as `python scripts/<name>.py` from the repo root. Scripts compute their repo-root via `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` rather than relying on cwd.

`scripts/scratch/` is gitignored and holds workflow-specific helpers not intended for public use.
