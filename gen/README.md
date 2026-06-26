# gen/ -- Automated competitive-deck pipeline (Modern)

Generate -> test -> optimize -> discover, restricted to the format-legal,
engine-simulatable card pool. Built on the existing mtg-sim stack (card DB, mana
engine, goldfish sim, race scoring, auto-APL) rather than reinventing it.

## Pipeline at a glance

| Stage | Module | What it does |
|-------|--------|--------------|
| Pool | `card_pool.py`, `ban_list.py`, `sim_coverage.py` | Modern-legal AND not-banned AND in-DB cards, each tagged simulatable or not |
| Packages | `package_schema.py`, `packages/*.json`, `notation.py` | Reusable synergy bundles + `conjoins_with` graph; strong card-combo memory |
| Build | `mana_solver.py`, `generator.py`, `deck_writer.py` | Assemble packages into a legal 60, solve a castability-validated mana base |
| Score | `apl_cache.py`, `fitness.py` | Auto-generate a cached APL per deck; goldfish + Modern-field race -> one fitness scalar + verdict |
| Optimize | `search.py`, `parallel_eval.py`, `lineage.py` | Hill-climb + evolve; persist lineage + leaderboard |
| Discover | `discovery.py`, `meta_synth.py` | Mine strong packages, propose novel archetypes, synthesize a candidate metagame |
| Integrate | `registry_integration.py` | Register generated decks so `sim.py` / `parallel_sim.py` / `full_audit.py` run them unmodified |

## Drivers (repo root, mirror `sim.py`)

```
python gen_deck.py     --core boros_energy_core --auto [--register]
python gen_optimize.py --core amulet_titan_core --auto --rounds 20 --n 2000
python gen_discover.py --generations 5 --pop 10 --n 1500
```

## Running for real

The scorer runs actual goldfish sims and auto-generates APLs via Claude, so a
populated environment is required:

1. `scripts/fetch_scryfall_bulk.sh` to populate
   `data/rules_reference/scryfall_oracle_cards.json` (needs Scryfall network access).
2. Claude Code creds (or `ANTHROPIC_API_KEY`) for APL generation.

`python gen/smoke.py` and `python tests/test_anchor_amulet.py` exercise the full
real path; both **skip cleanly** when the oracle DB is absent.

## Offline tests (hermetic, no DB / no network)

```
python tests/test_card_pool.py
python tests/test_package_schema.py
python tests/test_mana_solver.py
python tests/test_fitness.py
python tests/test_search.py
python tests/test_discovery.py
```

These use a small fixture DB (`tests/fixtures/`) and injected
sim/APL/evaluator functions, so the pool/ban/classifier logic, mana solver,
fitness math, APL-cache reuse tiers, optimizer, and discovery are all verified
without the 37k-card download.

## Design notes / cost control

- **Always auto-generate an APL, cheaply**: `apl_cache.get_apl_for_candidate`
  keys APLs on the *decklist hash* with a three-tier reuse hierarchy (exact hit /
  package-set sibling / generate). Most search mutations reuse the parent's APL,
  so a whole hill-climb costs ~one generation per package set.
- **Fidelity gate**: a deck the engine cannot pilot faithfully (GenericAPL
  fallback or non-simulatable load-bearing cards) is capped at verdict
  "playable" -- never crowned "strong".
- **Modern field is a race proxy**: there are no two-player Modern match APLs, so
  field win-rate races our kill distribution vs measured `ARCHETYPE_CLOCKS`. It
  is weighted 0.45 in fitness, not dominant.
- `gen/sim_coverage.py` mirrors `scripts/full_audit.py`'s vanilla/HAS_EFFECTS
  classifier; keep the two in sync if the audit's heuristics change.
