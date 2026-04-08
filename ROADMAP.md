# MTG-Sim Roadmap
# What this project should do — organized by layer and priority
# Status key: [x] done | [-] partial | [ ] not started

---

## LAYER 1 — Card & Data Model

[x] Card object with type_line, mana_cost, cmc, power, toughness, oracle_text, colors
[x] Auto-tagging from type_line (land, creature, instant, sorcery, artifact, enchantment)
[x] CMC drop tags (one_drop, two_drop, three_drop)
[x] +1/+1 counter tracking on Card (counters field)
[x] Clone tracking (copying field for Phantasmal Image)
[x] Optional[str] typing for power/toughness
[x] effective_power() / effective_toughness() include counters
[x] Oracle text keyword parser (flying, haste, vigilance, first strike, deathtouch,
    lifelink, hexproof, ward, trample, menace, flash, indestructible, undying, persist)
[x] Role tags from oracle text (hate_bear, mana_dork, pump_lord, etb_draw,
    etb_removal, etb_bounce, etb_token, attack_trigger, disruptor)
[x] Scryfall API integration (3-layer: SQLite -> local bulk JSON -> live API)
[x] Deck loader from plain text (MTGA/MTGO format)
[x] Deck loader from file path
[ ] Color pip validation in can_cast() — currently simplified to CMC-only
[ ] Non-basic land mana type detection (shock lands, dual lands, fetch effects)
[ ] Adventure card support (two-faced: creature + instant/sorcery)
[ ] Split card support (Fire // Ice etc.)
[ ] Saga support (chapter tracking)
[ ] MDFC support (modal double-faced cards — land side vs spell side)
[ ] Companion mechanic (deck construction constraint + one free card)

---

## LAYER 2 — Game State Engine

[x] Full turn structure: untap -> upkeep -> draw -> main1 -> combat -> main2 -> end
[x] Zone manager: library, hand, battlefield, graveyard, exile
[x] Mana pool with color tracking (W U B R G C)
[x] Land play (one per turn)
[x] Land auto-taps for mana based on type_line
[x] Spell casting with mana payment
[x] Permanent vs non-permanent routing (creatures/enchantments to battlefield,
    instants/sorceries to graveyard)
[x] Simplified combat: all creatures attack, sum effective_power for damage
[x] ETB trigger system with recursion guard (_depth)
[x] Lord effects: Champion of the Parish (counter on Human ETB)
[x] Lord effects: Thalia's Lieutenant (anthem on ETB + grow self)
[x] Clone effects: Phantasmal Image copies highest-power creature

[ ] Summoning sickness — creatures can't attack turn they enter
    (currently all creatures attack immediately)
[ ] Tap/untap state tracking on permanents
[ ] Blocking — opponent creatures blocking our attackers (for matchup sim)
[ ] Stack — currently all spells resolve immediately, no responses
[ ] Triggered ability queue — multiple simultaneous ETBs need ordering
[ ] Activated abilities (Aether Vial tick-up, Horizon Canopy draw/sac)
[ ] Aether Vial — counter accumulation per turn, free creature deployment
[ ] Equipment — Kaldra Compleat, Batterskull attaching and equipping
[ ] Tokens — create token permanents (populate, create 2/2 etc.)
[ ] State-based actions — creatures dying at 0 toughness
[ ] Lifelink — gain life equal to damage dealt in combat
[ ] First strike — separate first strike damage step
[ ] Trample — excess combat damage to player when blocked
[ ] Deathtouch — any damage is lethal to blockers
[ ] Flying — can only be blocked by flying/reach
[ ] Vigilance — doesn't tap to attack
[ ] Flash — can be cast at instant speed (relevant for main2 decisions)
[ ] Haste APL awareness — haste creatures should be held for main2 post-combat
    to not telegraph, then attack next turn (currently attacks immediately)

---

## LAYER 3 — Action Priority Lists

[x] BaseAPL abstract class with keep(), bottom(), main_phase() interface
[x] London Mulligan engine (draw 7, keep or shuffle back, bottom n cards)
[x] Generic keep heuristic (land count + hand size)
[x] Generic bottom heuristic (excess lands first, then high CMC)
[x] Humans APL:
    [x] Keep logic (1-drop / Vial requirement, flood rejection)
    [x] Bottom logic (bottom excess lands, bottom high CMC over lords)
    [x] Vial priority (always T1 if no Vial in play)
    [x] Lord priority (Champion > Lieutenant > Thalia)
    [x] Curve filling (cheapest creature first)
    [x] Image sequencing (cast after board has ≥2 power target)
    [x] Non-creature spell cleanup

[ ] Aether Vial counter logic:
    [ ] Increment Vial counter at upkeep each turn
    [ ] Cast creatures via Vial (no mana cost, at instant speed)
    [ ] APL decision: when to put creature onto battlefield via Vial vs cast normally
[ ] Meddling Mage naming logic:
    [ ] What does the APL name? Currently just enters as a 2/2
    [ ] Should name opponent's most dangerous spell based on matchup context
[ ] Kitesail Freebooter target selection:
    [ ] Look at "opponent hand" (simulated draw pile) and take best non-creature/land
[ ] Militia Bugler — look at top 4, pick best 2-power human
[ ] Imperial Recruiter — tutor for optimal target given board state

[ ] New APL: Elves
    [ ] Heritage Druid mana generation (tap 3 elves for GGG)
    [ ] Nettle Sentinel untap on green spell
    [ ] Natural Order target selection (Progenitus vs Craterhoof)
    [ ] Glimpse of Nature draw engine
[ ] New APL: Delver
    [ ] Brainstorm + Ponder library manipulation
    [ ] Daze / Force of Will interaction decisions
    [ ] Wasteland targeting logic
[ ] New APL: Burn (simple but accurate — good calibration target)
[ ] New APL: Lands
    [ ] Crop Rotation target selection
    [ ] Dark Depths + Thespian's Stage assembly
    [ ] Life from the Loam dredge loop
[ ] APL registry — auto-detect deck archetype and assign APL

---

## LAYER 4 — Monte Carlo Runner

[x] run_simulation() — N-game goldfish runner
[x] SimulationResults dataclass
[x] kill_turn_distribution() — {turn: pct} dict
[x] win_by_turn(N) — cumulative win% by turn N
[x] avg_kill_turn(), median_kill_turn()
[x] avg_mulligans(), mull_rate()
[x] on_play / on_draw toggle
[x] mixed_play_draw 50/50 mode
[x] Reproducible runs via seed
[x] Progress reporting every 10%
[x] Runtime and games/sec tracking
[ ] Parallel execution — multiprocessing pool for faster large runs
[ ] Variance tracking — std deviation on kill turn, not just mean
[ ] Confidence intervals — 95% CI on win rate for statistical significance
[ ] Convergence detection — auto-stop when results stabilize
[ ] Per-turn board state snapshots — avg creatures in play, avg damage, avg hand size

---

## LAYER 5 — Race Analysis & Opponent Modeling

[x] OpponentClock dataclass — kill distribution per archetype
[x] Legacy field clocks: Lands, Delver, Elves, Painter, Stoneforge, Hogaak
[x] Modern field clocks: Burn, Affinity, Tron, Murktide, Yawgmoth, Living End, Amulet
[x] race_win_pct() — Monte Carlo race between two kill distributions
[x] field_report() — formatted race analysis vs all opponents
[x] print_field_report()

[ ] Interaction model — opponent disrupts our plan on specific turns
    [ ] Wrath of God clears board on T4 — what's our recovery rate?
    [ ] Thoughtseize on T1 — loses our best card, how does kill turn shift?
    [ ] Counterspell on key spell — recalculate line with that card gone
[ ] Post-board clock adjustment — after sideboarding, both decks shift
[ ] Play/draw adjustment — opponent going first changes their clock
[ ] Matchup-specific disruption profiles per known archetype
[ ] "Dead draw" modeling — some cards are blanks in some matchups
    (Meddling Mage naming wrong thing, Reflector Mage with no targets)

---

## LAYER 6 — Explain Mode (Interactive Walkthrough)

[x] Full turn-by-turn narration with ANSI color output
[x] Hand analysis at mulligan (land count, 1-drops, Vial, lords)
[x] Keep/mull reasoning with specific explanations
[x] Bottom card selection reasoning
[x] Land choice explanation
[x] Spell priority explanation with per-card reasoning strings
[x] Image copy target selection and explanation
[x] Combat summary with per-attacker damage
[x] Board state display with counters and copy annotations
[x] keyword display on cards (flying, hate_bear, etc.)
[x] Held cards explanation (why we couldn't cast)
[x] Interactive mode (--interactive flag, pause each turn)

[ ] Disagreement mode — "I would have done X instead, show me the delta"
[ ] Alternative line explorer — what if we cast Thalia before Lieutenant?
[ ] Opponent hand display (simulated opponent draws)
[ ] Decision tree view — show all options considered, not just chosen one
[ ] Color-coded damage counter (green < 10, yellow 10-15, red 16+)
[ ] Condensed 1-line-per-turn summary mode for fast review
[ ] Export game log to text file

---

## LAYER 7 — Gauntlet Integration

[x] sim_bridge.py — bridges kill distributions into gauntlet tilt overrides
[x] Archetype clock registry (22 archetypes)
[x] APL registry (auto-sim when APL available, else use clock)
[x] Pairwise race matrix computation
[x] Tilt override CSV output
[x] Patch run_pipeline_v3.py ARC_TILT directly
[x] Field mode (no CSV needed, just comma-separated deck names)
[x] run_pipeline_v3.py — Bo3 gauntlet with adaptive match count
[x] Bradley-Terry rating
[x] Tournament simulation (256-player Swiss + top-8)
[x] Tier scoring (composite z-score of WR + BT + tournament conversion)
[x] PDF heatmap report output
[x] Excel workbook output

[ ] Auto-run full pipeline from sim.py (single entry point)
[ ] Legacy-specific field presets (--field legacy_locals auto-loads known field)
[ ] Modern-specific field presets
[ ] Meta weighting — weight opponents by field representation %
    (e.g., if Elves is 30% of your local meta, weight it 3x in analysis)
[ ] Post-board tilt injection — separate G1 and G2/G3 tilts
[ ] Gauntlet CSV auto-generation from MTGTop8/Goldfish scraper

---

## LAYER 8 — Output & Analysis

[x] print_summary() — formatted console output
[x] plot_kill_curve() — matplotlib bar chart with cumulative line
[x] compare_results() — side-by-side variant comparison chart
[x] save_report() — JSON export
[x] Claude API integration (analyze, compare, ask functions)
[x] System prompt tuned for competitive MTG analysis
[x] Context + question injection for targeted analysis

[ ] ANTHROPIC_API_KEY auto-load from .env file
[ ] Deck diff analysis — run variant A vs variant B, Claude compares
    (e.g., "4x Vial vs 3x Vial + 1x Recruiter")
[ ] Mana curve visualization — histogram of CMC distribution
[ ] Land count optimizer — run sim across 18-24 lands, find optimal count
[ ] Web UI — simple Flask/FastAPI frontend for non-CLI use
[ ] Discord bot integration — !sim @Humans report in Team Resolve server

---

## LAYER 9 — Calibration & Validation

[ ] Validate sim kill turns against MTGA log data (your existing log parser)
[ ] Cross-reference goldfish turns against known community benchmarks
[ ] Regression test suite — known hands should produce known outcomes
[ ] Mulligan keep rate validation — compare to published studies
[ ] Variance sanity checks — kill turn std dev should be reasonable

---

## LAYER 10 — Architecture & Polish

[x] Modular structure (data / engine / apl / output)
[x] Shared Scryfall scraper (no duplication with mtg-meta-analyzer)
[x] sys.path bridge to mtg-meta-analyzer
[ ] pyproject.toml / setup.py — installable package
[ ] requirements.txt — pin dependencies
[ ] .env support — ANTHROPIC_API_KEY, SCRYFALL_CACHE_PATH etc.
[ ] Logging — structured log output instead of print statements
[ ] Unit tests for game state engine (pytest)
[ ] Unit test for mulligan keep logic
[ ] GitHub Actions CI — run tests on push
[ ] README overhaul — quickstart, usage examples, architecture diagram

---

## PRIORITY ORDER FOR NEXT SESSIONS

### Immediate (fixes things that affect accuracy now)
1. Summoning sickness — creatures attacking T1 they enter inflates kill turn
2. Aether Vial counter accumulation — biggest missing mechanic for Humans
3. Color pip validation in can_cast() — colorless-only is wrong for multi-color hands
4. Parallel Monte Carlo — 10k games should be instant, not 7 seconds

### Short term (new capability)
5. Elves APL — gives us a second real deck to compare against
6. Meddling Mage naming logic — contextual based on matchup
7. Deck diff (variant A vs B with Claude comparison)
8. .env file loading for API key

### Medium term (project maturity)
9. Blocking model — real combat resolution for matchup sim
10. Interaction model — Thoughtseize / Wrath effects on kill turn
11. Web UI — make this accessible without CLI
12. Discord bot integration — pipe results into Team Resolve server
13. Validation against MTGA log data

### Long term (research-level)
14. Full stack model — opponent draws and plays their deck too
15. Mana base optimizer — simulate across land configurations
16. Sideboard optimizer — which SB cards move the needle most vs this field
17. Format solver — given a format's card pool, what 75 maximizes field equity?
