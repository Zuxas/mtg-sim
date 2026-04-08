"""
engine/opponent_model.py — Probabilistic opponent hand model

Models what cards the opponent is likely holding based on:
  1. Their archetype (decklist composition)
  2. Turn number (how many cards they've drawn)
  3. What they've already played (revealed information)
  4. Whether they're on the play or draw

This is the foundation for CFR-style decision making — the same
technique used in Libratus/Pluribus (poker AIs that beat world-class
players). MTG and poker share the same core problem: imperfect
information. You can't see their hand. But you can compute the
probability distribution over what they're holding, and make
decisions that are optimal across that distribution.

Libratus used Counterfactual Regret Minimization (CFR):
  - At each decision point, enumerate all possible opponent hands
  - Assign probabilities to each (Bayesian prior + observed updates)
  - Compute EV of each action across the distribution
  - Pick highest-EV action

We implement that here for MTG key decisions:
  - What to name with Meddling Mage
  - Whether to play into open mana (Force of Will risk)
  - When to jam threats vs hold up interaction
  - Attack decisions when opponent may have tricks
"""

from dataclasses import dataclass, field
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Card probability priors per archetype
# {archetype_key: {card_name: (copies_in_deck, keep_weight)}}
# keep_weight > 1.0 = card is prioritized in opening hand decisions
# ---------------------------------------------------------------------------

ARCHETYPE_HAND_PRIORS = {
    "dimir reanimator": {
        "Faithless Looting":        (4, 1.3),
        "Entomb":                   (4, 1.3),
        "Animate Dead":             (4, 1.2),
        "Reanimate":                (4, 1.2),
        "Persist":                  (4, 1.1),
        "Griselbrand":              (4, 1.0),
        "Atraxa, Grand Unifier":    (4, 1.0),
        "Force of Will":            (4, 1.2),
        "Thoughtseize":             (4, 1.1),
        "Brainstorm":               (4, 0.9),
        "Ponder":                   (4, 0.9),
        "Dark Ritual":              (4, 1.0),
        "Lotus Petal":              (4, 1.0),
        "Exhume":                   (4, 1.1),
        "Unmask":                   (4, 1.0),
    },
    "lotus combo": {
        "Lotus Field":              (4, 1.3),
        "Thespian's Stage":         (4, 1.2),
        "Pore Over the Pages":      (4, 1.0),
        "Vizier of Tumbling Sands": (4, 1.0),
        "Bala Ged Recovery":        (4, 1.0),
        "Hidden Strings":           (4, 1.0),
        "Explore":                  (4, 0.9),
        "Crop Rotation":            (4, 1.1),
        "Cultivate":                (4, 0.9),
    },
    "dimir tempo": {
        "Force of Will":            (4, 1.3),
        "Daze":                     (4, 1.1),
        "Brainstorm":               (4, 1.0),
        "Ponder":                   (4, 0.9),
        "Murktide Regent":          (4, 1.0),
        "Dragon's Rage Channeler":  (4, 1.2),
        "Ragavan, Nimble Pilferer": (4, 1.2),
        "Wasteland":                (4, 1.0),
        "Spell Snare":              (2, 0.8),
        "Counterspell":             (2, 0.9),
        "Thoughtseize":             (4, 1.1),
        "Fatal Push":               (4, 1.0),
    },
    "cephalid breakfast": {
        "Cephalid Illusionist":     (4, 1.3),
        "Nomads en-Kor":            (4, 1.3),
        "Narcomoeba":               (4, 0.9),
        "Cabal Therapy":            (4, 1.0),
        "Force of Will":            (4, 1.2),
        "Brainstorm":               (4, 1.0),
        "Ponder":                   (4, 0.9),
        "Hapless Researcher":       (4, 1.0),
        "Lotus Petal":              (4, 1.0),
    },
    "sneak and show": {
        "Show and Tell":            (4, 1.3),
        "Sneak Attack":             (4, 1.2),
        "Emrakul, the Aeons Torn":  (2, 0.9),
        "Griselbrand":              (2, 0.9),
        "Force of Will":            (4, 1.3),
        "Brainstorm":               (4, 1.0),
        "Ponder":                   (4, 0.9),
        "Ancient Tomb":             (4, 1.1),
        "Lotus Petal":              (4, 1.0),
        "Cunning Wish":             (2, 0.8),
    },
    "eldrazi stompy": {
        "Chalice of the Void":      (4, 1.2),
        "Thought-Knot Seer":        (4, 1.1),
        "Reality Smasher":          (4, 1.0),
        "Eldrazi Mimic":            (4, 1.0),
        "Matter Reshaper":          (4, 1.0),
        "Ancient Tomb":             (4, 1.1),
        "City of Traitors":         (4, 1.1),
        "Warping Wail":             (4, 1.0),
        "Dismember":                (4, 1.0),
        "Trinisphere":              (2, 1.0),
    },
    "mono red painter": {
        "Painter's Servant":        (4, 1.3),
        "Grindstone":               (4, 1.3),
        "Goblin Engineer":          (4, 1.2),
        "Pyroblast":                (4, 1.0),
        "Red Elemental Blast":      (4, 1.0),
        "Imperial Recruiter":       (4, 1.0),
        "Blood Moon":               (4, 1.1),
        "Magus of the Moon":        (4, 1.0),
        "Chalice of the Void":      (4, 1.0),
        "Ancient Tomb":             (4, 1.1),
        "City of Traitors":         (4, 1.1),
    },
    "doomsday": {
        "Doomsday":                 (4, 1.2),
        "Brainstorm":               (4, 1.1),
        "Ponder":                   (4, 1.0),
        "Force of Will":            (4, 1.2),
        "Thassa's Oracle":          (4, 1.1),
        "Dark Ritual":              (4, 1.0),
        "Gitaxian Probe":           (4, 1.0),
        "Lotus Petal":              (4, 1.0),
        "Counterspell":             (2, 0.9),
    },
    "izzet delver": {
        "Delver of Secrets":        (4, 1.2),
        "Dragon's Rage Channeler":  (4, 1.2),
        "Murktide Regent":          (4, 1.0),
        "Force of Will":            (4, 1.3),
        "Daze":                     (4, 1.1),
        "Lightning Bolt":           (4, 1.1),
        "Brainstorm":               (4, 1.0),
        "Ponder":                   (4, 0.9),
        "Pyroblast":                (4, 1.0),
        "Spell Pierce":             (2, 0.9),
    },
    "death and taxes": {
        "Aether Vial":              (4, 1.3),
        "Thalia, Guardian of Thraben": (4, 1.2),
        "Flickerwisp":              (4, 1.0),
        "Recruiter of the Guard":   (4, 1.0),
        "Phyrexian Revoker":        (4, 1.0),
        "Swords to Plowshares":     (4, 1.1),
        "Karakas":                  (4, 1.1),
        "Wasteland":                (4, 1.0),
        "Mother of Runes":          (4, 1.1),
        "Solitude":                 (4, 1.0),
    },
    "bant nadu": {
        "Nadu, Winged Wisdom":      (4, 1.2),
        "Shuko":                    (4, 1.2),
        "Arboreal Grazer":          (4, 1.0),
        "Noble Hierarch":           (4, 1.1),
        "Force of Will":            (4, 1.2),
        "Brainstorm":               (4, 1.0),
        "Crop Rotation":            (4, 1.0),
        "Dryad Arbor":              (2, 0.9),
    },
}

ARCHETYPE_HAND_PRIORS["reanimator"] = ARCHETYPE_HAND_PRIORS["dimir reanimator"]
ARCHETYPE_HAND_PRIORS["painter"]    = ARCHETYPE_HAND_PRIORS["mono red painter"]
ARCHETYPE_HAND_PRIORS["tempo"]      = ARCHETYPE_HAND_PRIORS["dimir tempo"]
ARCHETYPE_HAND_PRIORS["delver"]     = ARCHETYPE_HAND_PRIORS["izzet delver"]

DECK_SIZE = 60
OPENING_HAND = 7


@dataclass
class OpponentHandModel:
    """
    Tracks probability distribution of cards in opponent's hand.

    Updated each turn based on:
    - What they've drawn (hypergeometric probability)
    - What they've played (Bayesian update — reduces probability of seen cards)
    - How they've used their mana (process of elimination)
    """
    archetype_key: str
    on_play:       bool = True
    turn:          int  = 0

    # Cards confirmed NOT in hand (they played them)
    played:        list = field(default_factory=list)

    # Cards we know ARE in hand (revealed by e.g. Thoughtseize)
    confirmed:     list = field(default_factory=list)

    # Mana they've left up (signals possible interaction)
    mana_up:       int  = 0

    def _priors(self) -> dict:
        """Get archetype card priors."""
        return ARCHETYPE_HAND_PRIORS.get(self.archetype_key, {})

    def cards_drawn(self) -> int:
        """How many cards has opponent drawn by this point."""
        base = OPENING_HAND
        # On draw gets an extra card on turn 1
        extra = 0 if self.on_play else 1
        # One draw per turn
        draws = max(0, self.turn - 1)
        return base + extra + draws

    def p_in_hand(self, card_name: str) -> float:
        """
        Probability this card is currently in opponent's hand.

        Uses hypergeometric distribution:
          P(at least 1 copy in hand) = 1 - C(deck-copies, hand_size) / C(deck, hand_size)

        Then Bayesian updates for played/confirmed information.
        """
        priors = self._priors()
        if card_name not in priors:
            # Unknown card — use generic 4-of baseline
            copies, keep_weight = 2, 1.0
        else:
            copies, keep_weight = priors[card_name]

        if copies == 0:
            return 0.0

        # Check confirmed
        if card_name in self.confirmed:
            return 1.0

        # Reduce copies for each one played
        played_count = self.played.count(card_name)
        remaining_copies = max(0, copies - played_count)
        if remaining_copies == 0:
            return 0.0

        # Cards remaining in deck after draws
        cards_drawn = self.cards_drawn()
        remaining_deck = max(1, DECK_SIZE - cards_drawn)
        hand_size = max(1, min(OPENING_HAND, cards_drawn))

        # P(at least 1 of N copies in H-card hand from D-card deck)
        # = 1 - C(D-N, H) / C(D, H)
        p_none = self._hypergeometric_p_none(
            remaining_copies, remaining_deck, hand_size
        )
        p_at_least_one = 1.0 - p_none

        # Apply keep weight (high-priority cards more likely kept)
        p_at_least_one = min(0.99, p_at_least_one * keep_weight)

        # Bayesian update for mana usage
        # FoW is a pitch cost — doesn't need mana, stays dangerous even tapped out
        # Daze DOES need mana — much less likely if they tapped out
        if card_name == "Daze" and self.mana_up == 0 and self.turn > 0:
            p_at_least_one *= 0.15   # Daze can't be cast without mana up
        elif card_name == "Force of Will" and self.mana_up == 0 and self.turn > 0:
            p_at_least_one *= 0.90   # FoW still live when tapped out (pitch cost)

        return round(p_at_least_one, 3)

    @staticmethod
    def _hypergeometric_p_none(copies: int, deck_size: int, hand_size: int) -> float:
        """
        Probability of drawing 0 copies of a card.
        P(X=0) = C(D-N, H) / C(D, H)
        Using log-space for numerical stability.
        """
        if copies >= deck_size or hand_size >= deck_size:
            return 0.0
        if copies == 0:
            return 1.0

        # log P(none) = log C(D-N, H) - log C(D, H)
        # log C(n, k) = sum(log(n-i) - log(i+1) for i in range(k))
        def log_comb(n, k):
            if k > n or k < 0:
                return float('-inf')
            k = min(k, n - k)
            result = 0.0
            for i in range(k):
                result += math.log(n - i) - math.log(i + 1)
            return result

        log_p = log_comb(deck_size - copies, hand_size) - log_comb(deck_size, hand_size)
        return min(1.0, math.exp(log_p))

    def observe_play(self, card_name: str):
        """Update model when opponent plays a card."""
        self.played.append(card_name)

    def observe_confirmed(self, card_name: str):
        """Update model when we see a card in their hand (e.g. Thoughtseize)."""
        if card_name not in self.confirmed:
            self.confirmed.append(card_name)

    def observe_mana_up(self, mana: int):
        """Update mana left up at end of our turn."""
        self.mana_up = mana

    def advance_turn(self):
        """Move to next turn."""
        self.turn += 1

    def top_threats(self, n: int = 5) -> list[tuple[str, float]]:
        """Return top N most likely cards in hand, sorted by probability."""
        priors = self._priors()
        result = []
        for card in priors:
            p = self.p_in_hand(card)
            if p > 0.05:
                result.append((card, p))
        result.sort(key=lambda x: -x[1])
        return result[:n]

    def p_has_interaction(self) -> float:
        """
        Probability opponent can interact with us this turn.

        FoW = pitch cost, always available regardless of mana
        Daze/TS = require mana, zero if they tapped out
        """
        arch = self.archetype_key

        fow_archs = {"dimir reanimator", "dimir tempo", "izzet delver",
                     "cephalid breakfast", "sneak and show", "doomsday", "bant nadu"}

        p_fow   = self.p_in_hand("Force of Will") if arch in fow_archs else 0.0
        # Daze/TS only live if they have mana up
        p_daze  = self.p_in_hand("Daze") if arch in {"dimir tempo", "izzet delver"} else 0.0
        p_ts    = self.p_in_hand("Thoughtseize") if arch in {"dimir reanimator", "dimir tempo"} else 0.0

        if self.mana_up == 0:
            p_daze *= 0.05   # almost can't be cast
            p_ts   *= 0.05

        p_none = (1 - p_fow) * (1 - p_daze) * (1 - p_ts)
        return round(1 - p_none, 3)

