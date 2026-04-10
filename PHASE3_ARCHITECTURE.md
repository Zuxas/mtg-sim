# MTG-Sim Phase 3+ Architecture
# "SimulationCraft meets Stockfish for Magic: The Gathering"
# Created: 2026-04-09

## Vision

SimulationCraft runs thousands of APL-driven games to find optimal rotations.
Stockfish evaluates positions and searches for optimal moves.
MTG-Sim combines both: APL-driven Monte Carlo simulation with position evaluation.

The result: given any two decks, run 10,000 games where both sides play near-optimally,
and get a statistically significant win rate with per-turn decision breakdowns.

---

## Architecture Layers

### Layer 1 — Card & Data Model ✅ DONE
- `data/card.py`: Card dataclass (name, mana_cost, cmc, type_line, oracle_text, P/T, tags, counters)
- `data/deck.py`: Deck loader (text → Card objects via CardDB)
- `engine/card_db.py`: Scryfall DB (37K cards, 3-layer cache)
- Role tags from oracle text (hate_bear, mana_dork, etb_removal, etc.)
- Keyword parser (flying, haste, trample, deathtouch, lifelink, etc.)

### Layer 2 — Game State Engine ✅ GOLDFISH / 🟡 MATCH SKELETON

#### 2a — GameState (single player, goldfish) ✅
- Full turn structure: untap → upkeep → draw → main1 → combat → main2 → end
- Zone manager (library, hand, battlefield, graveyard, exile)
- Mana pool with color tracking
- ETB triggers, attack triggers, prowess
- Summoning sickness, tapped state
- Fetch/shock land resolution

#### 2b — MatchGameState (two players) 🟡 EXISTS / 🔴 NEEDS REWRITE
Current `TwoPlayerGameState` is a flat struct with parallel arrays.
**Rewrite**: wrap two `GameState` instances + shared state.

```python
class MatchGameState:
    """Two GameState instances + shared game state."""
    
    def __init__(self, deck_a, deck_b, on_play=True, seed=None):
        self.player_a = GameState(deck_a, on_play=True)   # reuse existing engine
        self.player_b = GameState(deck_b, on_play=False)
        self.active_player = 'a' if on_play else 'b'
        self.turn = 0
        self.rng = random.Random(seed)
        self.stack = Stack()           # NEW: spell stack for interaction
        self.combat_state = None       # NEW: CombatState during combat
        self.game_over = False
        self.winner = None
    
    def opponent_of(self, player: str) -> GameState:
        return self.player_b if player == 'a' else self.player_a
    
    def active_gs(self) -> GameState:
        return self.player_a if self.active_player == 'a' else self.player_b
    
    def reactive_gs(self) -> GameState:
        return self.player_b if self.active_player == 'a' else self.player_a
```

**Key insight**: Don't rebuild the engine. Each player gets a real `GameState` with all
existing mechanics (ETB, prowess, fetch lands, etc.). The match layer orchestrates
turn alternation and adds the new concepts (stack, interaction, blocking).

### Layer 3 — Action Priority Lists ✅ GOLDFISH / 🔴 NEEDS MATCH MODE

#### 3a — Goldfish APLs ✅
- `BaseAPL.keep()`, `bottom()`, `main_phase(gs)` 
- 15+ hand-tuned APLs (Boros Energy, Ruby Storm, Humans, etc.)
- `GenericAPL` for untouched decks (curve out, attack)

#### 3b — Match APLs 🔴 NEW
Goldfish APLs only see their own board. Match APLs need opponent awareness.

```python
class MatchAPL(BaseAPL):
    """Extended APL interface for two-player games."""
    
    def main_phase(self, gs: GameState, opponent: GameState):
        """Make decisions seeing the opponent's board."""
        ...
    
    def declare_attackers(self, gs: GameState, opponent: GameState) -> list[Card]:
        """Choose which creatures attack. Default: all non-sick."""
        ...
    
    def declare_blockers(self, gs: GameState, opponent: GameState, 
                          attackers: list[Card]) -> dict[Card, Card]:
        """Assign blockers to attackers. Default: optimal blocking algorithm."""
        ...
    
    def respond_to_spell(self, gs: GameState, opponent: GameState,
                          spell: Card) -> Optional[Card]:
        """Respond to opponent casting a spell. Return a response spell or None."""
        ...
    
    def end_step_actions(self, gs: GameState, opponent: GameState):
        """Actions at end of opponent's turn (flash creatures, instants)."""
        ...
```

**Adapter pattern**: existing goldfish APLs work in match mode via a wrapper.
The wrapper calls `main_phase(gs)` and ignores the opponent board.
Hand-tuned match APLs override with opponent-aware logic.

```python
class GoldfishAdapter(MatchAPL):
    """Wraps a goldfish APL to work in match mode."""
    def __init__(self, goldfish_apl: BaseAPL):
        self.inner = goldfish_apl
    
    def main_phase(self, gs, opponent):
        self.inner.main_phase(gs)  # ignore opponent
    
    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield 
                if not c.is_land() and not c.summoning_sickness]
    
    def declare_blockers(self, gs, opponent, attackers):
        return optimal_blocking(gs, attackers)  # algorithm, not APL logic
```

### Layer 4 — Combat + Interaction 🟡 SKELETON / 🔴 NEEDS MAJOR WORK

#### 4a — Combat Engine 🟡 EXISTS / 🔴 NEEDS UPGRADE

Current: biggest blocker blocks biggest attacker. No keywords.

**Upgrade to**:
```python
class CombatResolver:
    """Full combat resolution with keywords and tactical blocking."""
    
    def resolve(self, attackers: list[Card], defending_gs: GameState,
                blocker_assignments: dict[Card, list[Card]]) -> CombatResult:
        """
        1. Check evasion: flying attackers can only be blocked by flying/reach
        2. Check menace: menace creatures need 2+ blockers  
        3. First strike damage step (first_strike + double_strike creatures)
        4. Regular damage step (all non-first-strike)
        5. Trample: excess damage over blocker toughness goes to player
        6. Deathtouch: any damage from deathtouch creature is lethal
        7. Lifelink: attacking player gains life = damage dealt by lifelink creatures
        8. State-based actions: remove creatures with lethal damage
        9. Attack triggers (Adeline tokens, Guide of Souls energy)
        10. Death triggers
        """
```

**Blocking algorithm** (opponent plays to minimize damage):
```
Priority order for blocking decisions:
1. MUST-BLOCK: block a lethal attacker if we can profitably trade
2. PROFITABLE TRADE: our 2/2 blocks their 2/3 (we kill them, we die — but we're ahead on mana)
3. CHUMP BLOCK: sacrifice a 1/1 to prevent 5 damage (when we're low on life)
4. NO BLOCK: take the damage if losing a creature costs more than the life
5. DOUBLE BLOCK: two small creatures gang up on one big one

Key factors:
- Life differential: chump more aggressively when low
- Board advantage: don't trade when ahead on board
- Race math: if we kill them first, don't block at all
- Evasion: can't block flying without flyers/reach
```

#### 4b — Interaction Engine 🔴 NEW

**Simplified stack model** (not full rules-engine complexity):
```python
class Stack:
    """Simplified spell stack for interaction."""
    items: list[StackItem]  # spells/abilities waiting to resolve
    
    def cast(self, spell: Card, targets: list = None):
        """Put a spell on the stack."""
        self.items.append(StackItem(spell, targets))
    
    def respond(self, spell: Card, targets: list = None):
        """Respond to the top spell (counter it, kill in response, etc.)"""
        self.items.append(StackItem(spell, targets))
    
    def resolve(self) -> list[Resolution]:
        """Resolve the stack LIFO (last in, first out)."""
        results = []
        while self.items:
            item = self.items.pop()  # LIFO
            if item.countered:
                results.append(Resolution(item, 'countered'))
            else:
                results.append(self._apply(item))
        return results
```

**Interaction categories** (what spells can do to the opponent):
```
REMOVAL:    destroy/exile target creature     (Fatal Push, Solitude, Lightning Bolt)
COUNTER:    counter target spell              (Force of Negation, Spell Pierce, Mystical Dispute)
DISCARD:    opponent discards from hand        (Thoughtseize, Grief)
WRATH:      destroy all creatures             (Supreme Verdict, Terminus)
BOUNCE:     return to hand                    (Teferi, Brazen Borrower)
BURN:       deal damage to player directly    (Lightning Bolt, Galvanic Discharge)
```

**When to interact** (APL-level decision):
```python
def should_counter(self, spell, our_gs, their_gs) -> bool:
    """Decide if we should counter this spell."""
    # Always counter game-winning threats
    if spell.tags.has(Tag.WIN_CON):
        return True
    # Counter if we can't answer it on board
    if spell.is_creature() and effective_power(spell) >= 4:
        if not self.has_removal_in_hand(our_gs):
            return True
    # Don't counter if we're tapped out for our own play
    if our_gs.mana_pool.total() < counter_cost(our_counter):
        return False
    return False
```

### Layer 5 — Match Engine 🟡 SKELETON / 🔴 NEEDS REWRITE

**The core game loop**:
```python
def run_match(apl_a: MatchAPL, deck_a, apl_b: MatchAPL, deck_b,
              on_play=True, max_turns=15, seed=None) -> MatchResult:
    
    mgs = MatchGameState(deck_a, deck_b, on_play, seed)
    
    # Mulligan phase (both players independently)
    mulligan(apl_a, mgs.player_a)
    mulligan(apl_b, mgs.player_b)
    
    for turn in range(1, max_turns + 1):
        mgs.turn = turn
        
        for active in ['a', 'b']:  # both players take a turn
            mgs.active_player = active
            gs = mgs.active_gs()
            opp = mgs.reactive_gs()
            apl = apl_a if active == 'a' else apl_b
            opp_apl = apl_b if active == 'a' else apl_a
            
            # --- BEGINNING OF TURN ---
            gs.untap_all()
            gs.upkeep_triggers()
            if not (turn == 1 and active == 'a' and on_play):
                gs.draw()
            gs.tap_lands()  # calculate available mana
            
            # --- MAIN PHASE 1 ---
            apl.main_phase(gs, opp)
            opp_apl.respond_to_board(opp, gs)  # instant-speed responses
            
            # --- COMBAT ---
            attackers = apl.declare_attackers(gs, opp)
            if attackers:
                blockers = opp_apl.declare_blockers(opp, gs, attackers)
                # Priority window: combat tricks
                apl.combat_tricks(gs, opp, attackers, blockers)
                opp_apl.combat_tricks(opp, gs, attackers, blockers)
                # Resolve damage
                result = CombatResolver().resolve(attackers, opp, blockers)
                apply_combat_result(mgs, result, active)
            
            # --- CHECK WIN ---
            if opp.life <= 0:
                return MatchResult(winner=active, turn=turn, ...)
            
            # --- MAIN PHASE 2 ---
            apl.main_phase2(gs, opp)
            
            # --- END STEP ---
            opp_apl.end_step_actions(opp, gs)  # flash creatures, instants
            gs.cleanup()
    
    # Timeout: whoever dealt more damage wins
    return MatchResult(winner=..., turn=max_turns, ...)
```

### Layer 6 — Monte Carlo Runner ✅ EXISTS / 🟢 MINOR EXTENSION

Existing `parallel_sim.py` handles N-game runs with multiprocessing.
**Extension**: swap `run_match` from match_runner instead of goldfish sim.

```python
def run_matchup(deck_a, deck_b, apl_a, apl_b, n=10000, 
                mix_play_draw=True, seed=42) -> MatchupResult:
    """Run N matches between two decks. Return win rates + kill turn distributions."""
    results = parallel_run(run_match, n, deck_a, deck_b, apl_a, apl_b, 
                           mix_play_draw=mix_play_draw, seed=seed)
    return MatchupResult(
        win_rate_a=results.a_wins / n,
        avg_kill_turn=mean(results.kill_turns),
        kill_dist_a=results.a_kill_distribution(),
        kill_dist_b=results.b_kill_distribution(),
        play_draw_split=results.play_draw_breakdown(),
    )
```

### Layer 7 — Evaluation Function 🔴 NEW (THE STOCKFISH BRAIN)

```python
def evaluate(gs_a: GameState, gs_b: GameState) -> float:
    """
    Score the board state. Positive = player A ahead. Range: roughly -20 to +20.
    
    Components:
    1. MATERIAL: sum of (power + toughness) / 2 for each creature, weighted by keywords
       - Flying creature worth ~1.3x ground creature (evasion premium)
       - Deathtouch creature worth ~1.5x its stats (removal on a body)
       - Haste creature worth ~1.2x (immediate impact)
    
    2. TEMPO: mana deployed vs mana available
       - Each unspent mana = -0.1 (wasted tempo)
       - Each creature with summoning sickness = 0.5x (can't contribute yet)
    
    3. CLOCK: estimated turns to lethal for each player
       - clock_a = ceil(gs_b.life / max(1, total_attacking_power_a))
       - clock_b = ceil(gs_a.life / max(1, total_attacking_power_b))
       - Score += (clock_b - clock_a) * 2  (being 1 turn faster = +2 points)
    
    4. THREATS: cards that demand an answer
       - Creature with 4+ power and no opposing blocker = +2 per
       - Planeswalker in play = +3
       - Combo piece visible = +4 (opponent must interact or lose)
    
    5. RESOURCES: hand size + graveyard value + energy/counters
       - Each card in hand = +0.3
       - Each relevant card in graveyard (flashback, escape) = +0.1
    """
    material = _score_material(gs_a) - _score_material(gs_b)
    tempo    = _score_tempo(gs_a) - _score_tempo(gs_b)
    clock    = _score_clock(gs_a, gs_b)
    threats  = _score_threats(gs_a, gs_b) - _score_threats(gs_b, gs_a)
    resource = _score_resources(gs_a) - _score_resources(gs_b)
    
    # Weights (tunable — these are starting points)
    return (material * 1.0 + tempo * 0.5 + clock * 2.0 + 
            threats * 1.5 + resource * 0.3)
```

**Calibration**: run known matchups through the evaluator and check if the eval score
at key turns correlates with actual win rates from Monte Carlo sim.

### Layer 8 — Variant Testing + SB Optimizer 🔴 NEW

```python
def compare_variants(base_deck, swaps: list[tuple[Card, Card]], 
                     opponent_deck, n=5000) -> VariantReport:
    """
    Swap cards in and out, re-sim, compare win rates.
    Answer: "is 4 Phlage better than 3 Phlage + 1 Bolt?"
    
    swaps = [("Phlage, Titan of Fire's Fury", "Lightning Bolt")]
    """
    base_result = run_matchup(base_deck, opponent_deck, n=n)
    
    for card_out, card_in in swaps:
        variant = base_deck.replace(card_out, card_in)
        var_result = run_matchup(variant, opponent_deck, n=n)
        delta = var_result.win_rate - base_result.win_rate
        # Report: "+1.3% win rate with Bolt over 4th Phlage vs Boros Energy"

def optimize_sideboard(mainboard, sideboard, field: dict[str, float],
                       n_per_matchup=2000) -> SBPlan:
    """
    For each matchup in the field, try all possible SB configurations.
    Find the SB plan that maximizes field-weighted win rate.
    
    field = {"Boros Energy": 0.20, "Izzet Prowess": 0.10, ...}
    """
```

### Layer 9 — Meta Solver 🔴 NEW (ENDGAME)

```python
def solve_meta(format: str, field: dict[str, float], 
               candidate_decks: list, n_per_pair=5000) -> MetaSolution:
    """
    Given a metagame field, find the optimal deck + 75 configuration.
    
    1. Run every candidate deck against every field deck
    2. Compute field-weighted win rates
    3. Optimize each deck's 75 via variant testing
    4. Re-run with optimized 75s
    5. Compute Nash equilibrium (no deck can improve by changing)
    
    Output: ranked list of decks with field-weighted win rates,
    optimal 75 for each, and recommended sideboard plans.
    """
```

This is the "format solved" endgame — the equivalent of Stockfish proving
a forced win from a specific position. In MTG terms: given this field,
this is the best deck with the best 75 and the best sideboard plan.

### Layer 10 — Output + Integration ✅ PARTIAL / 🟡 EXTEND

- `output/stats.py`: formatted console output ✅
- `reports/`: PDF heatmaps, Excel workbooks ✅
- `output/claude_analysis.py`: Claude API integration ✅
- Team Resolve website integration (inject sim data into playbooks) 🟡
- Web dashboard (Flask/FastAPI frontend) 🔴
- Discord bot (pipe results to Team Resolve server) 🔴

---

## Implementation Priority

### Phase 3A — Minimum Viable Match (2-3 sessions)
1. Rewrite `MatchGameState` wrapping two `GameState` instances
2. Create `MatchAPL` interface + `GoldfishAdapter`
3. Upgrade combat: flying, first strike, trample, deathtouch, lifelink
4. Smart blocking algorithm (trade/chump/race decision tree)
5. Wire into `run_match()` / `run_match_set()`
6. Validate: Boros Energy vs Izzet Prowess should be ~55-45

### Phase 3B — Interaction Layer (2-3 sessions)
7. Simplified stack model (cast → respond → resolve)
8. Removal spells (Fatal Push, Lightning Bolt, Solitude)
9. Counterspells (Force of Negation, Spell Pierce)
10. Discard (Thoughtseize, Grief)
11. Match APL `respond_to_spell()` / `should_counter()` logic
12. Validate: adding interaction should shift win rates by 3-8%

### Phase 3C — Evaluation Function (1-2 sessions)
13. `evaluate(gs_a, gs_b) -> float` with 5 components
14. Calibrate weights against known matchup data
15. Use eval to drive blocking decisions (trade when ahead, chump when behind)
16. Use eval to drive APL decisions (go all-in vs hold back)

### Phase 3D — Variant Testing + SB Optimizer (1-2 sessions)
17. `compare_variants()` — swap cards, re-sim, compare
18. `optimize_sideboard()` — best SB plan for a field
19. Claude API analysis of variant deltas

### Phase 3E — Meta Solver (2-3 sessions)
20. Full meta simulation (every deck vs every deck)
21. Field-weighted optimization
22. Nash equilibrium search
23. Output: "play this deck with this 75 at this RC"

---

## Key Design Decisions

### Why APL-driven (SimulationCraft) over search-driven (Stockfish)?
MTG has hidden information (opponent's hand) and massive branching factor.
Pure search is intractable. APLs encode expert knowledge efficiently.
The eval function adds Stockfish-style reasoning WHERE IT MATTERS:
combat math, interaction timing, and variant comparison.

### Why wrap GameState instead of rebuilding?
836 lines of battle-tested goldfish engine. ETB triggers, prowess, fetch lands,
summoning sickness — all working. Don't rewrite. Wrap and extend.

### Why simplified stack instead of full rules engine?
Full MTG rules engine (layers, timestamps, replacement effects) is a multi-year project.
Simplified stack handles 90% of competitive interaction:
cast → counter? → resolve. That's enough for accurate matchup data.

### What about combo decks?
ComboKillSampler already handles this. Combo decks don't interact in combat —
they sample a kill turn from a distribution. Keep this for Storm, Living End,
Goryo's Vengeance. Only model full two-player games for creature/midrange/control.
