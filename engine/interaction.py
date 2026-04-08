"""
engine/interaction.py — Opponent interaction model

Models what happens when the opponent interacts with our plays:
  - Force of Will: counters our spell, we lose tempo
  - Thoughtseize: strips our best card pre-combat
  - Lightning Bolt / Fatal Push: removes one of our creatures
  - Wasteland: destroys a non-basic, sets us back a land
  - Swords to Plowshares: exiles a creature (no damage to trade)

This converts goldfish win rates into realistic racing win rates by
simulating the tempo loss from interaction each turn.

Each archetype has an interaction profile:
  {interaction_type: (probability_per_turn, effect)}

Effects:
  - "counter":   spell we try to cast this turn gets countered (lose 1 action)
  - "kill_1":    one of our creatures dies (lose power/board)
  - "kill_best": our biggest creature dies
  - "wasteland": lose a land drop
  - "discard":   lose a card from hand
"""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class InteractionEvent:
    event_type:  str     # "counter", "kill_1", "kill_best", "wasteland", "discard"
    turn:        int
    details:     str = ""


# ---------------------------------------------------------------------------
# Archetype interaction profiles
# Format: {archetype_key: [(prob_per_turn, event_type, details), ...]}
# Probabilities represent "chance this interaction happens this turn"
# ---------------------------------------------------------------------------

INTERACTION_PROFILES = {
    "dimir reanimator": [
        (0.35, "counter",  "Force of Will"),      # 4x FoW, high prob early
        (0.20, "discard",  "Thoughtseize"),        # strips our best card
    ],
    "lotus combo": [
        (0.05, "counter",  "Force of Will"),       # they're mostly goldfishing
    ],
    "dimir tempo": [
        (0.40, "counter",  "Force of Will"),       # 4x FoW, very interactive
        (0.25, "counter",  "Daze"),                # tempo-efficient
        (0.20, "kill_1",   "Lightning Bolt"),
        (0.10, "wasteland","Wasteland"),
    ],
    "cephalid breakfast": [
        (0.25, "counter",  "Force of Will"),
        (0.15, "discard",  "Cabal Therapy"),
    ],
    "eldrazi stompy": [
        (0.20, "discard",  "Thought-Knot Seer"),   # ETB hand disruption
        (0.15, "kill_1",   "Warping Wail"),
        (0.10, "counter",  "Warping Wail"),
    ],
    "sneak and show": [
        (0.30, "counter",  "Force of Will"),
        (0.10, "discard",  "Cunning Wish -> Thoughtseize"),
    ],
    "mono red painter": [
        (0.15, "kill_1",   "Pyroblast"),
        (0.10, "counter",  "Pyroblast"),           # vs blue spells we don't have
    ],
    "doomsday": [
        (0.25, "counter",  "Force of Will"),
        (0.10, "counter",  "Counterspell"),
    ],
    "izzet delver": [
        (0.35, "counter",  "Force of Will"),
        (0.25, "counter",  "Daze"),
        (0.25, "kill_1",   "Lightning Bolt"),
        (0.10, "wasteland","Wasteland"),
    ],
    "death and taxes": [
        (0.20, "kill_1",   "Swords to Plowshares"),
        (0.15, "kill_best","Solitude"),
        (0.15, "wasteland","Wasteland"),
        (0.10, "kill_1",   "Karakas"),             # bounces legends
    ],
    "bant nadu": [
        (0.20, "counter",  "Force of Will"),
        (0.15, "kill_1",   "Swords to Plowshares"),
    ],
    "four-color": [
        (0.25, "counter",  "Force of Will"),
        (0.20, "kill_1",   "Swords to Plowshares"),
        (0.15, "kill_best","Teferi, Time Raveler"),
    ],
    "jeskai control": [
        (0.40, "counter",  "Force of Will"),
        (0.30, "counter",  "Counterspell"),
        (0.30, "kill_1",   "Swords to Plowshares"),
        (0.20, "kill_best","Terminus"),
    ],
    "mono red aggro": [
        (0.20, "kill_1",   "Lightning Bolt"),
        (0.15, "kill_1",   "Chain Lightning"),
    ],
    "mono red prison": [
        (0.15, "kill_1",   "Pyroblast"),
        (0.10, "wasteland","Wasteland"),
    ],
    # Modern
    "dimir murktide": [
        (0.30, "counter",  "Force of Negation"),
        (0.25, "kill_1",   "Fatal Push"),
        (0.15, "kill_best","Snapcaster + removal"),
    ],
    "boros energy": [
        (0.20, "kill_1",   "Galvanic Discharge"),
        (0.15, "kill_1",   "Unholy Heat"),
    ],
    "unknown": [
        (0.15, "kill_1",   "removal"),
        (0.10, "counter",  "counterspell"),
    ],
}


def get_profile(archetype_key: str) -> list:
    key = archetype_key.lower()
    if key in INTERACTION_PROFILES:
        return INTERACTION_PROFILES[key]
    for k, v in INTERACTION_PROFILES.items():
        if k in key or key in k:
            return v
    return INTERACTION_PROFILES["unknown"]


# ---------------------------------------------------------------------------
# Interaction simulator — applies to a game state each turn
# ---------------------------------------------------------------------------

class InteractionSimulator:
    """
    Simulates opponent interaction turn by turn.
    Called from the game loop before our main phase resolves.
    """

    def __init__(self, archetype_key: str, seed: int = None):
        self.profile = get_profile(archetype_key)
        self.rng     = random.Random(seed)
        self.events: list[InteractionEvent] = []

    def roll_interaction(self, turn: int,
                          our_hand_size:   int = 5,
                          our_board_size:  int = 0,
                          we_have_cavern:  bool = False) -> list[InteractionEvent]:
        """
        Roll for interaction this turn. Returns list of events that fire.
        Cavern of Souls prevents 'counter' events on Humans.
        """
        events = []
        for prob, event_type, details in self.profile:
            # Cavern of Souls makes our Humans uncounterable
            if event_type == "counter" and we_have_cavern:
                continue

            # Interaction requires the opponent to have the resource
            # Diminish probability if they've interacted heavily already
            recent_events = sum(1 for e in self.events[-3:] if e.turn >= turn - 2)
            adjusted_prob = prob * max(0.3, 1.0 - recent_events * 0.15)

            # "kill" events require us to have creatures
            if "kill" in event_type and our_board_size == 0:
                continue

            if self.rng.random() < adjusted_prob:
                event = InteractionEvent(event_type, turn, details)
                events.append(event)
                self.events.append(event)
                # Only one major interaction per turn (can't FoW + Bolt same turn easily)
                if event_type in ("counter", "kill_best"):
                    break

        return events


# ---------------------------------------------------------------------------
# Apply interaction to kill distribution
# ---------------------------------------------------------------------------

def apply_interaction_to_dist(
    base_dist:      dict,   # {turn: pct} goldfish kill distribution
    archetype_key:  str,
    n_sim:          int = 10000,
    on_play:        bool = True,
    seed:           int = 42,
) -> dict:
    """
    Apply opponent interaction to a goldfish kill distribution.
    Returns a new distribution reflecting realistic tempo losses.

    For each simulated game:
      1. Sample our kill turn from goldfish dist
      2. Simulate interaction events each turn
      3. Each "counter" event adds ~0.5 turns to kill
      4. Each "kill_1" event removes ~1 power, slowing kill by ~0.3 turns
      5. Each "wasteland" adds ~0.4 turns
    """
    rng = random.Random(seed)
    turns_raw = sorted(base_dist.keys())
    weights   = [base_dist[t] for t in turns_raw]
    total_w   = sum(weights)

    sim = InteractionSimulator(archetype_key, seed=seed)
    result_turns = []

    for _ in range(n_sim):
        # Sample our ideal kill turn
        r = rng.random() * total_w
        cumul, ideal = 0, turns_raw[-1]
        for t, w in zip(turns_raw, weights):
            cumul += w
            if r <= cumul:
                ideal = t
                break

        # Simulate interaction delay
        delay = 0.0
        board_size = 0
        hand_size  = 7 - (1 if not on_play else 0)
        cavern      = rng.random() < 0.30  # ~30% of hands have Cavern

        isim = InteractionSimulator(archetype_key, seed=rng.randint(0, 999999))

        for turn in range(1, ideal + 1):
            board_size += rng.randint(0, 2)  # approximate creature deployment
            hand_size   = max(0, hand_size - 1)

            events = isim.roll_interaction(
                turn, hand_size, board_size, cavern
            )
            for ev in events:
                if ev.event_type == "counter":
                    delay += 0.5    # lost a spell this turn
                elif ev.event_type == "kill_1":
                    delay += 0.3    # lost a creature, slightly slower
                elif ev.event_type == "kill_best":
                    delay += 0.6    # lost our best creature
                elif ev.event_type == "wasteland":
                    delay += 0.4    # lost a land, missed mana
                elif ev.event_type == "discard":
                    delay += 0.35   # lost a card from hand

        realistic_kill = ideal + round(delay)
        result_turns.append(min(realistic_kill, 15))

    # Build distribution
    dist = {}
    for t in result_turns:
        dist[t] = dist.get(t, 0) + 1
    return {t: round(v / n_sim * 100, 2) for t, v in sorted(dist.items())}
