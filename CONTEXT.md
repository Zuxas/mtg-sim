# CONTEXT — mtg-sim

One-paragraph purpose: deterministic MTG simulation engine; goldfish + Bo3 match
sims driven by per-archetype APLs, scored as FWR against the live metagame.

## Vocabulary (as used in THIS repo)
- APL — Action Priority List; Python subclass per archetype defining card-play priority
- MatchAPL / AwareMatchAPL — base classes for 2-player sims; Aware adds OPP_THREAT_MODEL, lethal detection, mana-hold
- goldfish — speed sim: turns to kill a dummy at 20 life
- gauntlet — Bo3 series vs all field archetypes
- FWR — Field-Weighted Win Rate (meta-share-weighted match win %)
- kill_turn — turns to kill (20 life goldfish / 17 realistic)
- matchup / OPP_THREAT_MODEL — per-archetype removal/counter/pump/mana counts
- card_handlers — L1 card-text registry (ETB_EFFECTS, SPELL_EFFECTS)
- ARL — Autonomous Research Loop; loop_state.json is its durable spine
- telemetry / heuristic_distillation — (PLANNED; engine does not yet emit sequencing JSONL)

## Entry points
- sim.py  (--deck <file> --apl <slug> --n <N> --no-chart --no-claude)
- bo3_gauntlet.py (--deck --format --top-n --n-games)  [aggregate FWR only]
- parallel_launcher.py (--deck --format --n --top-n --cores) [per-matchup JSON]
- apl/__init__.py — APL_REGISTRY + MATCH_APL_REGISTRY + get_apl/get_match_apl

## Conventions / gotchas
- Never modify engine/ from automation (P0 human work)
- Defensive APLs: getattr(c,'tapped',False), getattr(self,'MATCH_BOUNCE',set())
- Unregistered deck slugs silently fall back to HumansAPL — register first
- ASCII-only terminal output; seeds for reproducibility

## Key paths
decks/  apl/  apl/auto_apls/  engine/  data/  scripts/  loop_state.json
data via ../mtg-meta-analyzer/data/mtg_meta.db (db_bridge.py / meta_bridge.py)

## Autonomous Research Loop (ARL)
- Spine: loop_state.json (status, mode, target_format, hypothesis, iteration,
  queue, results, promoted, steer_queue, blockers). queue entries carry an `hitl`
  flag; an hitl:true item pauses the loop for human review after it completes.
- Scripts: scripts/arl_loop.py (runner), arl_status.py (read-only),
  arl_steer.py "<directive>", arl_generate_deck.py, arl_generate_apl.py,
  arl_distill.py. The loop NEVER commits to git and NEVER edits engine/.
- Reuses harness/agents/scripts: auto_pipeline, apl_optimizer, tuning_loop,
  agent_hardening (atomic_write_json, LoopController, check_ollama_health).
