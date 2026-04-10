# Graph Report - E:\vscode ai project\mtg-sim  (2026-04-10)

## Corpus Check
- 189 files · ~256,100 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1282 nodes · 1624 edges · 92 communities detected
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `GameState` - 33 edges
2. `CardDB` - 26 edges
3. `Zones` - 20 edges
4. `run_explained_game()` - 16 edges
5. `HumansAPL` - 16 edges
6. `MatchGameState` - 14 edges
7. `RulesIndex` - 14 edges
8. `BaseAPL` - 13 edges
9. `RubyStormAPL` - 13 edges
10. `BorosEnergyAPL` - 12 edges

## Surprising Connections (you probably didn't know these)
- `BorosEnergyAPL` --inherits--> `BaseAPL`  [EXTRACTED]
  apl\boros_energy.py →   _Bridges community 0 → community 16_
- `BurnAPL` --inherits--> `BaseAPL`  [EXTRACTED]
  apl\burn.py →   _Bridges community 0 → community 46_
- `DelverAPL` --inherits--> `BaseAPL`  [EXTRACTED]
  apl\delver.py →   _Bridges community 0 → community 6_
- `ElvesAPL` --inherits--> `BaseAPL`  [EXTRACTED]
  apl\elves.py →   _Bridges community 0 → community 44_
- `GenericAPL` --inherits--> `BaseAPL`  [EXTRACTED]
  apl\generic_apl.py →   _Bridges community 0 → community 31_

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (46): AmuletTitanAPL, apl/amulet_titan.py — Amulet Titan APL (Modern) Amulet of Vigor + bounce lands, BaseAPL, DimirMidrangeAPL, apl/dimir_midrange.py — Dimir Midrange APL (Standard) Thoughtseize effects + Fa, MurktideAPL, dimir_murktide.py — APL for Modern UR Murktide  Key: Ragavan T1 haste, DRC T1 (f, Pre-combat: land, haste creatures, cantrips. (+38 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (31): ABC, BaseAPL, keep(), main_phase(), base_apl.py — Abstract base class for archetype Action Priority Lists  Every arc, Main Phase 2 — after combat. Default: cast anything still in hand.         Overr, Estimated win% improvement from sideboarding against this opponent.         This, Opponent-aware mulligan decision.         Calls keep() by default. Override for (+23 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (17): GameState, Begin a new turn: untap, upkeep, draw. Main phases and combat         are driven, Combat phase — called by APL runner between main phases.                  Correc, Combat with accurate card-specific trigger modeling.          Trigger ordering (, Full game state for one goldfish game.      Attributes     ----------     turn, Track milestone features for richer ML training data., Create a token, place it on the battlefield, fire its ETB triggers., Continuous/static effects that scale with board state.         Called before com (+9 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (29): CombatResult, _find_by_id(), has_keyword(), MatchGameState, MatchResult, MatchSetResults, optimal_blocking(), engine/match_state.py — Two-player game state for matchup simulation  Wraps two (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (30): _adjust_opp_clock(), Bo3GauntletResult, Bo3Result, compute_match_win_pct(), bo3_gauntlet.py — Run a full Bo3 gauntlet for any deck  Usage:     python bo3_ga, engine/bo3.py — Best-of-3 match simulation  Models a full Bo3 match:   - Game 1:, Simulate a Bo3 match.      G1: goldfish race with pre-board decks     G2: post-b, Shift opponent's kill distribution slightly slower post-board.     hate_factor=0 (+22 more)

### Community 5 - "Community 5"
Cohesion: 0.06
Nodes (28): Enum, GameResult, GameState, Phase, game_state.py — Core game state and turn structure for mtg-sim, Phase, game_state.py — Core game state and turn structure for mtg-sim  Manages the full, classify_card() (+20 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (16): DelverAPL, delver.py — APL for UR Delver (Legacy)  Win condition: Flip Delver of Secrets T2, Delver priority:           1. Land (only 1 needed — tempo deck)           2. Thr, GrindingBreachAPL, grinding_breach.py — APL for Modern Grinding Breach (Teg)  Combo: Underworld Bre, Check if we can combo off: Breach + Station in hand/BF + 3 mana + cards in GY., Land, cantrip to find combo, cast enablers., Post-combat: check combo again, cast remaining. (+8 more)

### Community 7 - "Community 7"
Cohesion: 0.1
Nodes (13): CardDB, get_card(), get_oracle(), get_rulings(), _norm(), engine/card_db.py — Local card database from Scryfall oracle cards + rulings  Re, Get full Scryfall card dict by name. Fuzzy matches., Get all official judge rulings for a card. (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.1
Nodes (20): ComboKillSampler, MatchResult, MatchSetResults, engine/match_runner.py — Both-sides simulation framework  Runs two APLs against, Simple turn simulator for a player.     If they have an APL, use it via a stub G, Safely get a card's power as int, handling '*' and None., Simplified combat: attacker sends all non-summoning-sick creatures.     Defender, For combo decks that can't be modeled with simple creature deployment.     Sampl (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.08
Nodes (13): HumansAPL, humans.py — APL for Legacy Humans  Field context: Lands, Delver, Elves, Painter,, Advance opponent model each turn.         Simulates what the opponent plays from, Use CFR decision engine to pick optimal Meddling Mage name., Check if we should cast into open mana., Bottom priority: excess lands → reactive/high-CMC spells → flex slots.         K, Smart land sequencing for Humans.          Priority logic (goldfish, perfect pla, Main Phase 1 (PRE-COMBAT) — Perfect player logic:         Only cast spells that (+5 more)

### Community 10 - "Community 10"
Cohesion: 0.11
Nodes (19): AutoAPLFactory, _build_prompt(), _call_claude(), _clean_code(), _get_api_token(), apl/auto_apl.py — Generate deck-specific APLs using Claude API + playbook data, Boros Energy' → 'BorosEnergy, Get Anthropic API token from Claude Code credentials (persisted).     Falls back (+11 more)

### Community 11 - "Community 11"
Cohesion: 0.11
Nodes (15): auto_trigger(), download_rules(), engine/rules_engine.py — MTG Comprehensive Rules parser + auto-trigger generator, Return all rules starting with num (e.g. '508' returns 508, 508.1, 508.1a ...), Find rules containing the query string (case-insensitive).         Returns {rule, Look up a specific keyword ability (Flying, Haste, Vigilance, etc.), Return rules about triggered abilities (section 603), Rules about enters the battlefield effects (relevant subset of 603) (+7 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (7): zones.py — Zone manager  Tracks all card zones for a single player:   Library, H, Return set of basic land types on battlefield (Plains, Island, etc.)., Draw n cards from top of library to hand. Returns drawn cards., Put a list of cards on the bottom of the library (London Mulligan)., Move a card from hand to battlefield., Cast a non-permanent (instant/sorcery) — goes to graveyard after resolving., Zones

### Community 13 - "Community 13"
Cohesion: 0.17
Nodes (18): C, card_str(), dim(), ExplainHumansAPL, good(), hdr(), info(), label() (+10 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (12): _hypergeometric_p_none(), OpponentHandModel, engine/opponent_model.py — Probabilistic opponent hand model  Models what cards, Tracks probability distribution of cards in opponent's hand.      Updated each t, Get archetype card priors., How many cards has opponent drawn by this point., Probability this card is currently in opponent's hand.          Uses hypergeomet, Update model when opponent plays a card. (+4 more)

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (18): build_matchup_table(), main(), event_simulator.py — Swiss tournament simulator with real field composition  Sim, Run N tournament simulations. Returns stats on our expected performance., Build {opponent: match_win_pct} table.      Priority order:     1. Real match da, Simulate one Swiss round.     player_records: list of (archetype, wins, losses), simulate_event(), simulate_swiss_round() (+10 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (9): BorosEnergyAPL, boros_energy.py — APL for Modern Boros Energy/Ocelot  VERIFIED card interactions, After combat: Ragavan treasure, Phlage bolt, Ocelot lifelink., Guide of Souls: when you attack, pay 3E → +2/+2 flying on an attacker., End step: Ocelot Pride creates Cat token if we gained life., Ajani ETB: create a 2/1 Cat Warrior token., Sacrifice creatures to Goblin Bombardment ONLY if lethal., Pre-combat: land, haste creatures, Arena of Glory haste, Guide pump. (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (19): evaluate(), evaluate_breakdown(), _keyword_multiplier(), print_eval(), engine/evaluator.py — Position evaluation function (Phase 3C)  Scores any board, Score unanswered threats — creatures with no opposing blocker., Score hand size + graveyard relevance + energy., Score the board state. Positive = player A ahead. Range: roughly -20 to +20. (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (9): Card, card.py — Card object model + tag system  Each Card represents one MTG card with, Check if card has all of the given tags., Simplified check — used when no ManaPool available., Full color pip validation against a ManaPool.         Parses mana cost string e., Base power + +1/+1 counters., Base toughness + +1/+1 counters., Populate basic tags from type_line and cmc. (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.14
Nodes (17): compare_field_variants(), compare_variants(), FieldResult, print_field_report(), print_variant_report(), engine/variant.py — Phase 3D variant testing + sideboard optimizer  Swap cards i, Print formatted variant comparison., Win rate against each deck in a field. (+9 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (14): find_playbook(), from_json(), load_all_playbooks(), load_all_tac_guides(), MatchupEntry, parse_playbook(), parse_tac_guide(), PlaybookData (+6 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (15): _get_conn(), get_meta_field(), list_meta_archetypes(), list_saved_decks(), load_saved_deck(), load_tournament_deck(), db_bridge.py — Bridge between mtg-meta-analyzer DB and mtg-sim engine  Pulls sav, Get meta field with archetype shares from tournament data.     Returns dict of { (+7 more)

### Community 22 - "Community 22"
Cohesion: 0.16
Nodes (8): IzzetProwessAPL, apl/izzet_prowess.py — Izzet Prowess APL (Modern)  VERIFIED mechanics:   - Prowe, Flashback Lava Dart from GY: sac a Mountain → 1 damage., Pre-combat: deploy threats, chain prowess spells, bolt face., Post-combat: cast remaining creatures, clean up prowess boosts., Count prowess creatures on the battlefield., Give all prowess creatures +1/+1 until EOT., Cast a free spell (Mutagenic/Bauble/Lava Dart) and trigger prowess.

### Community 23 - "Community 23"
Cohesion: 0.15
Nodes (8): LandsAPL, lands.py — APL for Legacy Lands  Win condition: Dark Depths + Thespian's Stage →, Choose the most useful land to play next., Crop Rotation: sacrifice a land, find Dark Depths or Stage., Elvish Reclaimer: tap + 1G → fetch a land., If Dark Depths + Stage in play, activate Stage → Marit Lage., Post-combat: instant-speed Crop Rotation, Life from the Loam., Lands priority:           1. Land drop (critical — plays 2+ per turn with Explor

### Community 24 - "Community 24"
Cohesion: 0.18
Nodes (5): ruby_storm.py — APL for Modern Ruby Storm (Teg)  Ral flips after 3 instants/sorc, Reset per-turn state only. Ral state persists across turns., Reset per-game state., Ritual cost with Medallion. {1}{R} base, each Medallion -1 generic., RubyStormAPL

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (13): _apply_sb(), Bo3MatchResult, Bo3SetResults, print_bo3_report(), engine/bo3_match.py — Best-of-3 using the real match engine (Phase 3A)  Runs act, Run N Bo3 matches. Returns aggregated results.     mix_play_draw alternates who, Print formatted Bo3 match report., Result of a single Best-of-3 match. (+5 more)

### Community 26 - "Community 26"
Cohesion: 0.17
Nodes (8): ManaPool, parse_cost(), mana.py — Mana pool and cost validation  Tracks floating mana by color and handl, Full color pip validation with flex mana support.         Flex mana (from Cavern, Alias for can_pay — used by game_state., Deduct mana with full pip + flex validation.         Returns True if payment suc, Parse a mana cost string into a dict of requirements.     Returns {"generic": in, Add exactly 1 mana based on a land's type line and name.          Basic lands →

### Community 27 - "Community 27"
Cohesion: 0.23
Nodes (7): runner.py — Monte Carlo simulation runner  Runs N goldfish games for a given dec, Run N goldfish games and return aggregated SimulationResults.      Args:, % of games won on each turn., % of all games won by (and including) turn N., % of games that took at least 1 mulligan., run_simulation(), SimulationResults

### Community 28 - "Community 28"
Cohesion: 0.2
Nodes (14): _conn(), data_quality(), get_all_matchups(), get_guide_content(), get_real_field(), get_real_matchup(), _normalize(), meta_bridge.py — Bridge between mtg-sim and mtg-meta-analyzer database  Pulls re (+6 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (11): CombatSimulator, get_opp_profile(), engine/combat.py — Realistic combat resolver with blocking  Simulates combat bet, Simulate one game. Returns the actual kill turn (or max_turns if we lost)., Get opponent profile, falling back to unknown., Run N games and return kill turn distribution., One-shot: get realistic win% for our deck vs an opponent archetype.     Accounts, Resolve one combat step.      our_attackers: list of [power, toughness] (mutable (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.2
Nodes (11): Quick wrapper to run any playbook deck through the Bo3 gauntlet., list_decks(), load_deck_from_playbook(), main(), sim_any_deck.py — Simulate any deck from playbook data  Uses GenericAPL (CMC-ord, List all available playbooks with their status., Build a Card list from a PlaybookData mainboard dict., Simulate a single deck and return kill distribution. (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.18
Nodes (7): generic_from_playbook(), GenericAPL, apl/generic_apl.py — Plays any MTG deck without archetype-specific knowledge  St, Spend all available mana efficiently.         Priority: creatures over non-creat, Post-combat: cast anything still castable., Create a GenericAPL configured from a PlaybookData object., Bottom excess lands first, then highest CMC non-essential spells.

### Community 32 - "Community 32"
Cohesion: 0.23
Nodes (7): GameEvent, GameEventBus, get_event_bus(), engine/game_events.py — Game event bus for adaptive APL  Provides a simple publi, Lightweight event bus — publish events, subscribers update models., Call at the start of each new game., reset_event_bus()

### Community 33 - "Community 33"
Cohesion: 0.19
Nodes (11): DeckScore, MetaSolution, print_meta_report(), engine/meta_solver.py — Phase 3E meta solver  Given a metagame field, find the o, Print the full meta analysis report., Performance of one deck against the field., Complete meta analysis result., Worker: run N games between two decks. Returns (name_a, name_b, wins_a, wins_b, (+3 more)

### Community 34 - "Community 34"
Cohesion: 0.22
Nodes (10): load_deck_and_apl(), main(), generate_matchup_data.py — Run both-sides sims for all archetype pairs  For each, Run a single matchup between two named decks. Returns result dict., Load a deck and APL by name.     Priority: hand-tuned APL → real stub from DB →, Run our deck vs the entire field. Saves results to JSON., Convert sim results to real_matchup_matrix format for event_simulator.     Forma, run_matchup() (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (6): HogaakAPL, hogaak.py — APL for Golgari Hogaak (Legacy)  Win condition: Fill graveyard T1 →, Hogaak costs: convoke 2 creatures + delve 7 cards.         Relaxed: 2 creatures, Vengevine returns from GY when you cast 2+ creatures in a turn.         Count cr, Post-combat: try Hogaak again with any new creatures., Hogaak priority:           1. Land           2. Stitcher's Supplier (mills 3 on

### Community 36 - "Community 36"
Cohesion: 0.21
Nodes (8): ActionEvaluator, _quick_snap(), engine/action_evaluator.py — Model-driven action selection  Replaces the static, Given a list of candidate Card objects, pick the one that         maximizes P(wi, Return all candidates ranked by P(win), as (card, p) pairs., Fast board snapshot without calling gs.snapshot() (avoids overhead)., Evaluates candidate actions using the ML win probability model.      Usage:, Query model for P(win). Cached by board state hash.

### Community 37 - "Community 37"
Cohesion: 0.22
Nodes (12): adjusted_kill_dist(), build_library(), build_library_g2(), evaluate_hand(), HandEval, engine/combo_model.py — Accurate combo matchup modeling  The real Reanimator mat, Build a 75-card library from maindeck counts., Post-sideboard library: swap in relevant hate, swap out dead cards. (+4 more)

### Community 38 - "Community 38"
Cohesion: 0.23
Nodes (12): analyze(), ask(), _call_claude(), compare(), _format_results(), _get_api_key(), claude_analysis.py — Claude API integration for sim result analysis  Takes a Sim, Compare two simulation results and recommend which build is better.      Args: (+4 more)

### Community 39 - "Community 39"
Cohesion: 0.21
Nodes (11): _do_mulligan(), print_match_report(), engine/match_engine.py — Phase 3A match engine  Runs two MatchAPLs against each, Run a single match between two MatchAPLs.     Returns MatchResult with winner, k, Run N matches between two MatchAPLs. Returns aggregated results.     mix_play_dr, Print a formatted matchup report., Run London mulligan for one player. Returns number of mulligans., Give the reactive player a chance to use instant-speed interaction.     Checks h (+3 more)

### Community 40 - "Community 40"
Cohesion: 0.21
Nodes (11): apply_sideboard_plan(), _fuzzy_match(), get_sb_plan(), _make_sb_card(), parse_sb_string(), engine/sideboard.py — Parse and apply sideboard plans  Handles:   - Parsing mess, Create a Card object for a sideboard card, fetching from Scryfall cache., Look up sb_in / sb_out for a matchup from playbook data.     Returns (sb_in_raw_ (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.21
Nodes (10): collect_training_data(), load_model(), predict_win_prob(), ml/win_prob_model.py — Win probability model trained on per-turn board state sna, Train win probability model. GBM recommended — handles mixed features well., Predict win probability from a mid-game board state snapshot.     This is the li, Convert a turn snapshot to ML feature vector., Collect per-turn snapshot training data.     Each game produces T snapshots (one (+2 more)

### Community 42 - "Community 42"
Cohesion: 0.29
Nodes (10): bo3_win(), _get_sb_premium(), main(), run_matchup.py — Single matchup runner (called by parallel_launcher)  Usage:, Fair matchup: real DB G1 if available, else both-sides combat sim.     G2/G3: G1, Bo3 match win% with correct play/draw state tracking.      MTG rules modeled:, Load our APL and ask for matchup-specific SB premium., Combo matchup:       G1: real DB data if available (preferred), else ComboKillSa (+2 more)

### Community 43 - "Community 43"
Cohesion: 0.24
Nodes (7): get_combo_dist(), get_field(), get_format(), is_combo(), format_config.py — Format-specific field data and combo kill distributions. Fiel, parallel_launcher.py — Launch all matchups as independent subprocesses  Format-a, Pull top decklists for all Modern meta archetypes and test APLs.

### Community 44 - "Community 44"
Cohesion: 0.2
Nodes (5): ElvesAPL, elves.py — APL for Legacy Elves  Win condition: Heritage Druid mana engine → Nat, Heritage Druid: tap 3 elves → GGG.         Fires in a loop — each activation ena, Post-combat: cast any remaining spells., Elves priority:           1. Land           2. Mana dorks (Llanowar/Mystic) firs

### Community 45 - "Community 45"
Cohesion: 0.25
Nodes (8): apply_interaction_to_dist(), get_profile(), InteractionEvent, InteractionSimulator, engine/interaction.py — Opponent interaction model  Models what happens when the, Simulates opponent interaction turn by turn.     Called from the game loop befor, Roll for interaction this turn. Returns list of events that fire.         Cavern, Apply opponent interaction to a goldfish kill distribution.     Returns a new di

### Community 46 - "Community 46"
Cohesion: 0.2
Nodes (4): BurnAPL, burn.py — APL for Modern Burn (mapped from 'Mono Red Aggro' in field)  Every spe, Pre-combat: land, haste creatures., Post-combat: burn face with everything.

### Community 47 - "Community 47"
Cohesion: 0.27
Nodes (9): attack_ev(), meddling_mage_name(), engine/decision.py — CFR-style decision engine for MTG  Implements Counterfactua, Compute the optimal Meddling Mage naming decision.      Returns: (best_name, ev_, Should we cast our key spell into open mana this turn?      Returns:         (sh, Should we attack this turn?      Simplified attack/wait decision:     - If we ca, Return a full decision summary for the current turn.     Used by the adaptive AP, should_play_through_interaction() (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.2
Nodes (9): compare_results(), plot_kill_curve(), print_summary(), stats.py — Stat visualization and reporting  Wraps SimulationResults with matplo, Save full results as JSON for later analysis or Claude API input., Side-by-side bar chart comparing multiple sim runs.     Useful for comparing dec, Bar chart of kill turn distribution.     X = turn number, Y = % of all games won, Print a formatted summary table to stdout. (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (4): standard_aggro.py — Universal APL for Standard aggro decks  Handles: Mono Red, G, Pre-combat: land, haste creatures, pump spells on attackers., Post-combat: burn face, cast remaining creatures., StandardAggroAPL

### Community 50 - "Community 50"
Cohesion: 0.22
Nodes (4): stoneforge.py — APL for Legacy Stoneforge Midrange (UW)  Win condition: Stonefor, Post-combat: flash spells, remaining cantrips., Stoneforge priority:           1. Land (needs 3+ for SFM ability)           2. C, StoneforgeAPL

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (8): _build_cards(), _get_cards_local(), load_deck_from_file(), load_deck_from_text(), _parse_decklist(), deck.py — Deck loader  Converts a plain text decklist into a list of Card object, Load card data from local CardDB (no network calls).     Falls back to Scryfall, Parse a plain text decklist.     Rules:     - // and # lines are comments — skip

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (8): describe_keywords(), get_keywords(), KWTag, keywords.py — Oracle text keyword parser  Parses MTG oracle text to auto-tag car, Parse card.oracle_text and add matching keyword tags to card.tags.     Returns t, Return keyword tags without modifying the card (read-only)., Return a human-readable list of keyword abilities detected., tag_keywords()

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (4): OppCreature, OpponentClock, engine/opponent.py — Simplified opponent model for the blocking sim  Models the, Models an opponent's goldfish kill turn distribution for race sims.

### Community 54 - "Community 54"
Cohesion: 0.36
Nodes (7): field_report(), print_field_report(), race_win_probability(), race.py — Race win probability calculator  Given our SimulationResults and an op, Monte Carlo race simulation.     We win if our kill turn <= opponent's kill turn, Run race analysis against every deck in the field.     Returns a formatted repor, _verdict()

### Community 55 - "Community 55"
Cohesion: 0.32
Nodes (7): collect_rl_experience(), ml/rl_trainer.py — Reinforcement learning via epsilon-greedy self-play  Trains t, Full RL training loop:       1. Collect games with epsilon-greedy exploration, Run one game with epsilon-greedy exploration.     Returns (snapshots, won) where, Collect experience with exploration. Returns (X, y) training pairs., rl_training_loop(), run_exploration_game()

### Community 56 - "Community 56"
Cohesion: 0.29
Nodes (4): Shared mixin for APLs that use sb_plans.py for sideboard premium., Default: no opponent-aware changes — use standard keep()., Add to any APL to get sb_plans.py lookup for sideboard_premium., SBPlanMixin

### Community 57 - "Community 57"
Cohesion: 0.47
Nodes (5): latest_result_per_deck(), main(), print_run(), dashboard.py — Multi-format matchup dashboard Reads all parallel_results JSON fi, Return {deck+format: result_dict} for most recent run of each deck.

### Community 58 - "Community 58"
Cohesion: 0.33
Nodes (3): mulligan.py — London Mulligan logic  London Mulligan rules:   - Draw 7 cards   -, Simulate London Mulligan.      keep_fn may be either:       keep(hand, mulligans, take_opening_hand()

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (5): engine/parallel_match.py — Parallel match simulation using all CPU cores.  Uses, Single worker: run a chunk of matches., Run N matches in parallel across workers. Returns (win_pct_a, avg_turns, dist, e, run_parallel_matchup(), _worker()

### Community 60 - "Community 60"
Cohesion: 0.4
Nodes (5): collect_format_data(), ml/format_transfer.py — Train win prob models for any format/deck combination  T, Full pipeline: collect → train → save for any deck/format., Collect training data for any deck vs its format's field., train_and_save_format_model()

### Community 61 - "Community 61"
Cohesion: 0.4
Nodes (3): parallel_sim.py — Parallel simulation runner using all available CPU cores  Spli, Worker process: simulate one matchup and return results.     Called by multiproc, _worker()

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (1): build_stubs.py — Generate stub_decks.py with real decklists + hardcoded Standard

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (1): monitor.py — Run any sim job and write live output to a log file. Claude watches

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (1): sim.py — Main entry point for MTG Sim  Usage:     python sim.py

### Community 65 - "Community 65"
Cohesion: 0.67
Nodes (1): Test all Pioneer APLs.

### Community 66 - "Community 66"
Cohesion: 0.67
Nodes (1): Test all Standard APLs.

### Community 67 - "Community 67"
Cohesion: 0.67
Nodes (1): trace_game.py — Full turn-by-turn game trace with decision annotations  Runs a s

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (2): get_sb_premium(), Look up SB premium from the pre-built tables.     Falls back to a keyword-based

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (2): get_apl(), Return an APL instance for a deck name or archetype string.

### Community 70 - "Community 70"
Cohesion: 0.67
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Check which Modern field APLs exist and their status.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Verify CardDB fix — should now return real game card data.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Pull consensus 75 for an archetype from tournament data.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): test_match_engine.py — Smoke test for Phase 3A match engine  Loads two decks, wr

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): watch.py — Claude uses this to check job status without timing out. Reads the lo

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Update sim_bridge.py ARCHETYPE_CLOCKS with measured kill distributions.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Query model at contested states where decisions actually matter.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): ml/run_pipeline.py — Full ML pipeline runner 1. Collect richer v3 training data

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Step 1: Collect v3 training data with richer features.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Step 2: Run RL training loop - 3 iterations of epsilon-greedy exploration.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Step 3: Train Modern Boros Energy model (format transfer demo).

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0): 

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (0): 

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (0): 

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Return True to keep this opening hand.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Choose n cards to put on the bottom after a mulligan.

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Make all decisions for the main phase of the current turn.         Call gs.play_

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Normalize card name for fuzzy lookup.

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Probability of drawing 0 copies of a card.         P(X=0) = C(D-N, H) / C(D, H)

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (0): 

## Knowledge Gaps
- **462 isolated node(s):** `bo3_gauntlet.py — Run a full Bo3 gauntlet for any deck  Usage:     python bo3_ga`, `build_stubs.py — Generate stub_decks.py with real decklists + hardcoded Standard`, `Check which Modern field APLs exist and their status.`, `Verify CardDB fix — should now return real game card data.`, `Pull consensus 75 for an archetype from tournament data.` (+457 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 71`** (2 nodes): `check_apls.py`, `Check which Modern field APLs exist and their status.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (2 nodes): `check_missing.py`, `Verify CardDB fix — should now return real game card data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (2 nodes): `consensus_75.py`, `Pull consensus 75 for an archetype from tournament data.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (2 nodes): `test_match_engine.py`, `test_match_engine.py — Smoke test for Phase 3A match engine  Loads two decks, wr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (2 nodes): `test_parallel.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (2 nodes): `watch.py`, `watch.py — Claude uses this to check job status without timing out. Reads the lo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (2 nodes): `update_clocks.py`, `Update sim_bridge.py ARCHETYPE_CLOCKS with measured kill distributions.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (2 nodes): `query_model.py`, `Query model at contested states where decisions actually matter.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (2 nodes): `run_pipeline.py`, `ml/run_pipeline.py — Full ML pipeline runner 1. Collect richer v3 training data`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (2 nodes): `run_step1_collect.py`, `Step 1: Collect v3 training data with richer features.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (2 nodes): `run_step2_rl.py`, `Step 2: Run RL training loop - 3 iterations of epsilon-greedy exploration.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (2 nodes): `run_step3_modern.py`, `Step 3: Train Modern Boros Energy model (format transfer demo).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `check_meta.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `show_results.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `test_adeline.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (1 nodes): `Return True to keep this opening hand.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (1 nodes): `Choose n cards to put on the bottom after a mulligan.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (1 nodes): `Make all decisions for the main phase of the current turn.         Call gs.play_`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (1 nodes): `Normalize card name for fuzzy lookup.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (1 nodes): `Probability of drawing 0 copies of a card.         P(X=0) = C(D-N, H) / C(D, H)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (1 nodes): `train.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MatchAPL` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Why does `HumansAPL` connect `Community 9` to `Community 0`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **What connects `bo3_gauntlet.py — Run a full Bo3 gauntlet for any deck  Usage:     python bo3_ga`, `build_stubs.py — Generate stub_decks.py with real decklists + hardcoded Standard`, `Check which Modern field APLs exist and their status.` to the rest of the system?**
  _462 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.02 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.04 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.07 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.06 - nodes in this community are weakly interconnected._