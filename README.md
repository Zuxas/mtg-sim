# MTG Simulator

A Modern-format-aware deck simulator inspired by SimulationCraft.
Goldfish simulator → archetype APL → Monte Carlo runner → Claude-powered analysis.

## Structure

```
mtg-sim/
├── data/         # Card objects, Scryfall ingestion, deck loader
├── engine/       # Game state, turn structure, zone manager, mana pool
├── apl/          # Action priority lists per archetype
├── output/       # Stat aggregation, deck diff, Claude API integration
```

## Phase 1 — Data Layer (current)
- `data/card.py`     Card object model + tag system
- `data/scryfall.py` Scryfall API fetcher
- `data/deck.py`     Deck loader (text list → Card objects)

## Phase 2 — Game State Engine
- `engine/game_state.py`
- `engine/zones.py`
- `engine/mana.py`

## Phase 3 — APL + Monte Carlo
- `apl/base_apl.py`
- `apl/humans.py`
- `engine/runner.py`

## Phase 4 — Output + Claude Integration
- `output/stats.py`
- `output/claude_analysis.py`
