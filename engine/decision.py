"""
engine/decision.py — CFR-style decision engine for MTG

Implements Counterfactual Regret Minimization (CFR) for key MTG decisions.

Libratus/Pluribus (the poker AIs) used CFR to find Nash equilibrium strategies
in games with imperfect information. The key insight maps directly to MTG:

  POKER:  You can't see their hole cards → model hand probability distribution
          → compute EV of bet/call/fold across all possible opponent hands
          → pick highest EV action

  MTG:    You can't see their hand → model hand probability (OpponentHandModel)
          → compute EV of each line across all possible opponent hands
          → pick highest EV action

CFR works by:
  1. Building a game tree of decision nodes
  2. At each node, computing counterfactual regret:
     "How much better would I have done if I'd chosen action X instead?"
  3. Iterating this across many simulated games
  4. After convergence, the average strategy is Nash equilibrium

For MTG we implement a simplified version:
  - Decision nodes are key choice points (Meddling Mage, attack/wait, etc.)
  - We enumerate the opponent hand distribution (not full tree search)
  - We compute EV of each action weighting by hand probability
  - We return the highest-EV action + its EV for transparency

Key decision nodes currently modeled:
  - meddling_mage_name(): What to name
  - should_play_into_fow(): Risk vs reward of casting into open mana
  - attack_or_wait(): Is the race worth it vs potential combat tricks
  - thalia_timing(): Cast Thalia pre or post other creatures
"""

from engine.opponent_model import OpponentHandModel, ARCHETYPE_HAND_PRIORS


# ---------------------------------------------------------------------------
# Decision: Meddling Mage naming
# ---------------------------------------------------------------------------

# How many turns each named card buys us on average (clock shift)
# These are tuned estimates — CFR would learn these from self-play
MEDDLING_EV_TABLE = {
    # Dimir Reanimator
    "Animate Dead":         2.5,   # naming this stops reanimation entirely
    "Reanimate":            2.5,
    "Entomb":               2.0,   # stops setup, doesn't stop if already entombed
    "Exhume":               2.0,
    "Faithless Looting":    1.0,   # slows setup but doesn't stop combo
    "Dark Ritual":          1.5,   # buying a turn vs fast kills
    "Force of Will":        1.2,   # prevents them protecting their combo

    # Lotus Combo
    "Lotus Field":          3.0,   # naming the engine itself — game over for them
    "Hidden Strings":       2.5,
    "Pore Over the Pages":  2.0,
    "Crop Rotation":        1.5,

    # Dimir Tempo
    "Force of Will":        1.5,
    "Murktide Regent":      1.0,   # removes their win con
    "Brainstorm":           0.8,   # slows them down
    "Daze":                 0.7,

    # Sneak and Show
    "Show and Tell":        3.0,
    "Sneak Attack":         2.5,
    "Emrakul, the Aeons Torn": 1.5,  # naming this doesn't stop Sneak Attack

    # Doomsday
    "Doomsday":             3.5,   # naming the namesake card
    "Thassa's Oracle":      2.0,
    "Brainstorm":           1.0,

    # Cephalid Breakfast
    "Cephalid Illusionist": 3.0,
    "Nomads en-Kor":        3.0,   # naming either piece
    "Cabal Therapy":        1.0,

    # Eldrazi Stompy
    "Chalice of the Void":  2.0,   # prevents locking us out
    "Thought-Knot Seer":    1.0,
    "Trinisphere":          2.0,

    # Mono Red Painter
    "Grindstone":           2.5,
    "Painter's Servant":    2.5,   # naming either piece stops combo

    # Tempo / removal
    "Swords to Plowshares": 1.0,
    "Lightning Bolt":       0.8,
    "Fatal Push":           0.8,
}


def meddling_mage_name(
    model:     OpponentHandModel,
    board:     list = None,    # our current board state (optional)
    turn:      int  = None,
) -> tuple[str, float, list]:
    """
    Compute the optimal Meddling Mage naming decision.

    Returns:
        (best_name, ev_score, ranked_options)

    EV formula:
        EV(name X) = P(X in hand) × turns_gained(X) × P(we_win_given_turns)

    P(we_win_given_turns) is simplified here — higher turns_gained = higher win%
    """
    if turn is not None:
        model.turn = turn

    priors = ARCHETYPE_HAND_PRIORS.get(model.archetype_key, {})
    scored = []

    for card_name in priors:
        p_in_hand = model.p_in_hand(card_name)
        if p_in_hand < 0.05:
            continue   # not worth naming something they probably don't have

        # Get EV of naming this card
        # Try exact match first, then look for partial matches
        ev_if_named = MEDDLING_EV_TABLE.get(card_name, 0.5)

        # Future: check if they've already drawn/played it
        # Also check if they'd have an alternate line around the name

        total_ev = p_in_hand * ev_if_named
        scored.append((card_name, total_ev, p_in_hand, ev_if_named))

    scored.sort(key=lambda x: -x[1])

    if not scored:
        return ("Force of Will", 0.5, [])

    best = scored[0]
    ranked = [(name, round(ev, 3)) for name, ev, _, _ in scored[:8]]
    return (best[0], round(best[1], 3), ranked)


# ---------------------------------------------------------------------------
# Decision: Should we play into open mana (Force of Will / Daze risk)?
# ---------------------------------------------------------------------------

def should_play_through_interaction(
    model:          OpponentHandModel,
    spell_value:    float,    # how many turns this spell is worth to us (1.0–4.0)
    our_board_size: int = 0,  # how many creatures we have
    we_have_cavern: bool = False,  # Cavern of Souls makes spell uncounterable
) -> tuple[bool, float, str]:
    """
    Should we cast our key spell into open mana this turn?

    Returns:
        (should_play, ev_delta, reasoning)

    EV(play now) = (1 - P(countered)) × spell_value
                  + P(countered) × lost_tempo_cost
    EV(wait)     = spell_value × P(we_still_win_next_turn)

    We play if EV(play now) > EV(wait).
    """
    # If Cavern of Souls is up, Force and Daze don't work
    if we_have_cavern:
        return (True, spell_value, "Cavern of Souls makes this uncounterable")

    p_interaction = model.p_has_interaction()

    # Cost of being countered: lose spell + the tempo of tapping mana
    tempo_cost = 0.5   # roughly half a turn of tempo lost to failed spell

    # Value of waiting: spell still works, but we lose a turn
    wait_value = spell_value * 0.85  # 15% decay for losing a turn

    ev_play = (1 - p_interaction) * spell_value - p_interaction * tempo_cost
    ev_wait = wait_value

    should_play = ev_play >= ev_wait

    if p_interaction < 0.30:
        reason = f"Low interaction risk ({p_interaction:.0%}) — play through"
    elif p_interaction < 0.55:
        reason = f"Moderate risk ({p_interaction:.0%}) — {'play' if should_play else 'wait'}"
    else:
        reason = f"High interaction risk ({p_interaction:.0%}) — {'force through with Cavern' if we_have_cavern else 'wait for better spot'}"

    return (should_play, round(ev_play - ev_wait, 3), reason)


# ---------------------------------------------------------------------------
# Decision: Attack or wait?
# ---------------------------------------------------------------------------

def attack_ev(
    our_power:      int,
    opponent_life:  int,
    model:          OpponentHandModel,
    turns_left:     int = 5,
    we_can_lethal:  bool = False,
) -> tuple[bool, str]:
    """
    Should we attack this turn?

    Simplified attack/wait decision:
    - If we can lethal, always attack (unless they have an answer)
    - Otherwise, weigh racing value vs blocking value
    - Factor in P(combat trick)
    """
    # P(they have combat trick / removal)
    arch = model.archetype_key
    p_removal = {
        "death and taxes": 0.35,
        "dimir tempo":     0.40,
        "izzet delver":    0.40,
        "eldrazi stompy":  0.20,
        "jeskai control":  0.50,
        "mono red painter":0.15,
        "dimir reanimator":0.20,
    }.get(arch, 0.25)

    # Lethal threat — attack even into removal
    if we_can_lethal:
        if p_removal > 0.60:
            return (True, "Attacking for lethal — accept removal risk")
        return (True, "Attacking for lethal")

    # Urgency: if we're racing, attack every turn
    turns_to_kill = math.ceil(opponent_life / max(1, our_power))
    if turns_to_kill <= turns_left:
        return (True, f"Racing line — T{turns_to_kill} kill, must attack")

    # Non-urgent: consider defensive value
    if p_removal > 0.50:
        return (False, f"High removal risk ({p_removal:.0%}) — hold back")

    return (True, f"Moderate removal risk ({p_removal:.0%}) — attack profitably")


# ---------------------------------------------------------------------------
# High-level: Full decision summary for a turn
# ---------------------------------------------------------------------------

def turn_decision_summary(
    model:          OpponentHandModel,
    hand:           list[str],    # our cards in hand
    board_size:     int = 0,
    mana_available: int = 1,
    we_have_cavern: bool = False,
    opponent_life:  int = 20,
    our_power:      int = 0,
) -> dict:
    """
    Return a full decision summary for the current turn.
    Used by the adaptive APL to make informed decisions.
    """
    result = {}

    # Meddling Mage naming
    if "Meddling Mage" in hand:
        best_name, ev, ranked = meddling_mage_name(model)
        result["meddling_mage"] = {
            "name":    best_name,
            "ev":      ev,
            "ranked":  ranked[:5],
        }

    # Interaction risk for casting spells
    key_spells = [c for c in hand if c not in ("Plains", "Island", "Swamp",
                  "Mountain", "Forest", "Cavern of Souls")]
    if key_spells:
        best_spell = key_spells[0]
        should_play, ev_delta, reason = should_play_through_interaction(
            model, spell_value=2.0, our_board_size=board_size,
            we_have_cavern=we_have_cavern
        )
        result["spell_timing"] = {
            "spell":       best_spell,
            "play_now":    should_play,
            "ev_delta":    ev_delta,
            "reason":      reason,
            "p_countered": round(model.p_has_interaction(), 3),
        }

    # Attack decision
    if our_power > 0:
        we_can_lethal = (our_power >= opponent_life)
        should_attack, atk_reason = attack_ev(
            our_power, opponent_life, model,
            we_can_lethal=we_can_lethal
        )
        result["attack"] = {
            "attack":  should_attack,
            "reason":  atk_reason,
        }

    # Top threats in opponent hand
    result["opp_hand_model"] = {
        "top_cards":      model.top_threats(5),
        "p_interaction":  model.p_has_interaction(),
        "turn":           model.turn,
    }

    return result
