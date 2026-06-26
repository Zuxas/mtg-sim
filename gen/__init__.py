"""
gen/ -- Automated competitive-deck generation, testing, optimization, and
archetype-discovery pipeline for mtg-sim.

Pipeline stages (each module is independently runnable / importable):
  card_pool      legal + simulatable card pool for a format
  sim_coverage   shared simulatability classifier (factored from scripts/full_audit.py)
  ban_list       authoritative format ban-list override
  package_schema synergy "package" notation schema
  notation       strong card-combination memory (NotationStore)
  mana_solver    Karsten-style mana-base solver, castability-validated
  generator      assemble packages into a legal decklist (DeckCandidate)
  deck_writer    emit decks/auto/<name>_<fmt>.txt + candidate metadata
  apl_cache      decklist-hash keyed auto-APL reuse (cost control)
  fitness        goldfish + race scoring -> FitnessReport
  search         hill-climb + evolutionary optimizer
  parallel_eval  ProcessPoolExecutor fan-out of fitness.evaluate
  lineage        lineage + leaderboard persistence
  discovery      mine strong packages, propose novel archetypes
  meta_synth     assemble a candidate metagame from top decks

All ASCII-only terminal output per CONVENTIONS.md. Artifacts live under
data/auto_pipeline/; generated decks under decks/auto/.
"""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DATA = os.path.join(REPO_ROOT, "data", "auto_pipeline")
AUTO_DECKS_DIR = os.path.join(REPO_ROOT, "decks", "auto")
