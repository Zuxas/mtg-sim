"""
engine/evaluator.py — Position evaluation function (Phase 3C)

Scores any board state: positive = player A ahead, negative = player B ahead.
Range: roughly -20 to +20. Analogous to Stockfish centipawns.

Components:
  1. MATERIAL — creature power/toughness weighted by keywords
  2. TEMPO — mana deployed vs wasted
  3. CLOCK — estimated turns to lethal for each player
  4. THREATS — unanswered cards that win if unchecked
  5. RESOURCES — hand size, graveyard value, energy

The eval drives:
  - Blocking decisions (trade when ahead, chump when behind)
  - APL decisions (go all-in vs hold back)
  - Variant comparison (card A vs card B impact on avg eval)
"""

from __future__ import annotations
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness, has_keyword
from data.card import Card, Tag


# Keyword value multipliers
KEYWORD_MULT = {
    'flying':      1.4,
    'deathtouch':  1.5,
    'haste':       1.2,
    'lifelink':    1.3,
    'trample':     1.15,
    'first strike': 1.2,
    'double strike': 1.6,
    'hexproof':    1.3,
    'indestructible': 1.5,
    'menace':      1.1,
    'vigilance':   1.1,
    'reach':       1.05,
}


def _keyword_multiplier(card: Card) -> float:
    """Get combined keyword multiplier for a creature."""
    mult = 1.0
    for kw, m in KEYWORD_MULT.items():
        if has_keyword(card, kw):
            mult *= m
    return mult


def _score_material(gs: GameState) -> float:
    """Score based on creature stats weighted by keywords."""
    score = 0.0
    for c in gs.zones.battlefield:
        if c.is_land():
            continue
        if c.has(Tag.CREATURE):
            p = safe_power(c)
            t = safe_toughness(c)
            base = (p + t) / 2.0
            mult = _keyword_multiplier(c)
            # Summoning sick creatures worth less (can't attack yet)
            if getattr(c, 'summoning_sickness', False):
                mult *= 0.6
            score += base * mult
        else:
            # Non-creature permanents (enchantments, artifacts, planeswalkers)
            score += 1.5  # generic value for being in play
    return score


def _score_tempo(gs: GameState) -> float:
    """Score based on mana efficiency — how much of available mana was used."""
    lands = sum(1 for c in gs.zones.battlefield if c.is_land())
    creatures = sum(1 for c in gs.zones.battlefield if not c.is_land())
    # More creatures per land = better tempo
    if lands == 0:
        return 0.0
    return creatures * 0.3  # each deployed threat is worth tempo


def _score_clock(gs_a: GameState, gs_b: GameState) -> float:
    """
    Score based on race math — who kills whom first.
    Being 1 turn faster = +2 points.
    """
    # Player A's clock (turns to kill B)
    power_a = sum(safe_power(c) for c in gs_a.zones.battlefield
                  if not c.is_land() and not getattr(c, 'summoning_sickness', False))
    clock_a = max(1, -(-gs_b.life // max(1, power_a))) if power_a > 0 else 99

    # Player B's clock (turns to kill A)
    power_b = sum(safe_power(c) for c in gs_b.zones.battlefield
                  if not c.is_land() and not getattr(c, 'summoning_sickness', False))
    clock_b = max(1, -(-gs_a.life // max(1, power_b))) if power_b > 0 else 99

    # Positive = A is faster (ahead on clock)
    diff = clock_b - clock_a
    # Cap the advantage so it doesn't dominate
    return max(-6, min(6, diff * 2.0))


def _score_threats(gs: GameState, opp_gs: GameState) -> float:
    """Score unanswered threats — creatures with no opposing blocker."""
    score = 0.0
    our_creatures = [c for c in gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and not getattr(c, 'summoning_sickness', False)]
    opp_creatures = [c for c in opp_gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]

    for c in our_creatures:
        p = safe_power(c)
        is_evasive = has_keyword(c, 'flying') or has_keyword(c, 'menace')

        # Can opponent block this?
        can_block = False
        for opp in opp_creatures:
            if has_keyword(c, 'flying') and not (has_keyword(opp, 'flying') or has_keyword(opp, 'reach')):
                continue
            if safe_toughness(opp) > 0:
                can_block = True
                break

        if not can_block or is_evasive:
            score += p * 0.5  # unanswered threat premium
        if p >= 4:
            score += 1.0  # big creature bonus
    return score


def _score_resources(gs: GameState) -> float:
    """Score hand size + graveyard relevance + energy."""
    hand_value = len(gs.zones.hand) * 0.3
    # Graveyard cards with flashback/escape/etc. have value
    gy_value = 0
    for c in gs.zones.graveyard:
        oracle = (getattr(c, 'oracle_text', '') or '').lower()
        if 'flashback' in oracle or 'escape' in oracle or 'unearth' in oracle:
            gy_value += 0.2
    energy_value = getattr(gs, 'energy', 0) * 0.1
    return hand_value + gy_value + energy_value


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------

# Weights (tunable — calibrate against known matchup data)
W_MATERIAL  = 1.0
W_TEMPO     = 0.5
W_CLOCK     = 2.0
W_THREATS   = 1.5
W_RESOURCES = 0.3


def evaluate(gs_a: GameState, gs_b: GameState) -> float:
    """
    Score the board state. Positive = player A ahead. Range: roughly -20 to +20.
    
    Analogous to Stockfish centipawns:
      +8  = up a Sheoldred + 3 cards (winning)
       0  = both have 2-turn clocks (even)
      -5  = they have lethal, you need a topdeck (losing)
    """
    material  = _score_material(gs_a) - _score_material(gs_b)
    tempo     = _score_tempo(gs_a) - _score_tempo(gs_b)
    clock     = _score_clock(gs_a, gs_b)
    threats   = _score_threats(gs_a, gs_b) - _score_threats(gs_b, gs_a)
    resources = _score_resources(gs_a) - _score_resources(gs_b)

    total = (material  * W_MATERIAL +
             tempo     * W_TEMPO +
             clock     * W_CLOCK +
             threats   * W_THREATS +
             resources * W_RESOURCES)
    return round(total, 2)


def evaluate_breakdown(gs_a: GameState, gs_b: GameState) -> dict:
    """Return evaluation with component breakdown for debugging."""
    material  = _score_material(gs_a) - _score_material(gs_b)
    tempo     = _score_tempo(gs_a) - _score_tempo(gs_b)
    clock     = _score_clock(gs_a, gs_b)
    threats   = _score_threats(gs_a, gs_b) - _score_threats(gs_b, gs_a)
    resources = _score_resources(gs_a) - _score_resources(gs_b)

    return {
        'total': round(material * W_MATERIAL + tempo * W_TEMPO +
                       clock * W_CLOCK + threats * W_THREATS +
                       resources * W_RESOURCES, 2),
        'material':  round(material * W_MATERIAL, 2),
        'tempo':     round(tempo * W_TEMPO, 2),
        'clock':     round(clock * W_CLOCK, 2),
        'threats':   round(threats * W_THREATS, 2),
        'resources': round(resources * W_RESOURCES, 2),
        'raw': {
            'material': round(material, 2),
            'tempo': round(tempo, 2),
            'clock': round(clock, 2),
            'threats': round(threats, 2),
            'resources': round(resources, 2),
        },
        'board_a': {
            'creatures': sum(1 for c in gs_a.zones.battlefield if not c.is_land()),
            'power': sum(safe_power(c) for c in gs_a.zones.battlefield if not c.is_land()),
            'life': gs_a.life,
            'hand': len(gs_a.zones.hand),
        },
        'board_b': {
            'creatures': sum(1 for c in gs_b.zones.battlefield if not c.is_land()),
            'power': sum(safe_power(c) for c in gs_b.zones.battlefield if not c.is_land()),
            'life': gs_b.life,
            'hand': len(gs_b.zones.hand),
        },
    }


def print_eval(gs_a: GameState, gs_b: GameState,
               name_a: str = "Player A", name_b: str = "Player B"):
    """Print a formatted evaluation breakdown."""
    bd = evaluate_breakdown(gs_a, gs_b)
    score = bd['total']
    leader = name_a if score > 0 else name_b if score < 0 else "Even"
    
    print(f"\n  EVAL: {score:+.1f} ({leader})")
    print(f"    Material:  {bd['material']:+.1f}")
    print(f"    Tempo:     {bd['tempo']:+.1f}")
    print(f"    Clock:     {bd['clock']:+.1f}")
    print(f"    Threats:   {bd['threats']:+.1f}")
    print(f"    Resources: {bd['resources']:+.1f}")
    a = bd['board_a']
    b = bd['board_b']
    print(f"    {name_a}: {a['creatures']}c {a['power']}p {a['life']}hp {a['hand']}h")
    print(f"    {name_b}: {b['creatures']}c {b['power']}p {b['life']}hp {b['hand']}h")
