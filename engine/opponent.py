"""
opponent.py — Basic opponent clock model

Models an opponent deck as a clock — how much damage they deal per turn,
or when they "go off" (combo/lock). Used to calculate race win probability
against a simulated field.

Each opponent archetype defines:
  - kill_distribution: {turn: probability} of winning that turn
  - interaction_turns: turns where they cast disruptive spells

Legacy field for Zuxas's locals:
  Lands, Delver, Elves, Painter, Stoneforge, Golgari Hogaak
"""

from dataclasses import dataclass, field
from typing import Optional
import random


@dataclass
class OpponentClock:
    """
    Represents an opponent archetype's goldfish kill distribution.
    kill_distribution: {turn: pct_of_games} — must sum to ~100
    interaction: list of turns where interaction is likely (disrupts our plan)
    """
    name: str
    kill_distribution: dict[int, float]   # {turn: pct}
    interaction_turns: list[int] = field(default_factory=list)
    combo: bool = False   # True = they go off once vs grind each turn

    def sample_kill_turn(self) -> Optional[int]:
        """Sample a kill turn from the distribution. Returns None if they miss."""
        roll = random.random() * 100
        cumulative = 0.0
        for turn in sorted(self.kill_distribution):
            cumulative += self.kill_distribution[turn]
            if roll <= cumulative:
                return turn
        return None  # didn't kill within modeled turns

    def win_probability_by_turn(self, turn: int) -> float:
        """Probability opponent has already won by this turn."""
        return sum(
            pct for t, pct in self.kill_distribution.items() if t <= turn
        ) / 100.0


# ---------------------------------------------------------------------------
# Legacy field clocks (based on known goldfish data + community benchmarks)
# ---------------------------------------------------------------------------

# Lands — Dark Depths combo, T2-3 Marit Lage or grind with Loam
LANDS = OpponentClock(
    name="Lands",
    kill_distribution={
        2: 5.0,   # T2 Marit Lage (Elvish Spirit Guide + Crop Rotation)
        3: 25.0,  # T3 Marit Lage standard line
        4: 30.0,  # T4 combo or beats
        5: 20.0,
        6: 12.0,
        7: 5.0,
        8: 3.0,
    },
    interaction_turns=[1, 2, 3],
    combo=True,
)

# Delver — UR Delver, tempo deck, kills T4-5 behind disruption
DELVER = OpponentClock(
    name="Delver",
    kill_distribution={
        3: 8.0,
        4: 30.0,
        5: 32.0,
        6: 18.0,
        7: 8.0,
        8: 4.0,
    },
    interaction_turns=[1, 2, 3, 4],
    combo=False,
)

# Elves — combo/aggro, T2-3 kills common
ELVES = OpponentClock(
    name="Elves",
    kill_distribution={
        2: 15.0,
        3: 40.0,
        4: 25.0,
        5: 12.0,
        6: 5.0,
        7: 3.0,
    },
    interaction_turns=[],
    combo=True,
)

# Painter — Grindstone combo, T2-3 with Imperial Recruiter or Goblin Engineer
PAINTER = OpponentClock(
    name="Painter",
    kill_distribution={
        2: 8.0,
        3: 28.0,
        4: 30.0,
        5: 20.0,
        6: 10.0,
        7: 4.0,
    },
    interaction_turns=[2, 3],
    combo=True,
)

# Stoneforge — Midrange, T4-5 with Batterskull / Kaldra Compleat
STONEFORGE = OpponentClock(
    name="Stoneforge",
    kill_distribution={
        3: 5.0,
        4: 20.0,
        5: 35.0,
        6: 25.0,
        7: 10.0,
        8: 5.0,
    },
    interaction_turns=[1, 2, 3, 4],
    combo=False,
)

# Golgari Hogaak — Graveyard aggro, T3-4 Hogaak
HOGAAK = OpponentClock(
    name="Golgari Hogaak",
    kill_distribution={
        2: 10.0,
        3: 35.0,
        4: 30.0,
        5: 15.0,
        6: 7.0,
        7: 3.0,
    },
    interaction_turns=[],
    combo=False,
)

# Full locals field
LEGACY_FIELD = {
    "Lands":           LANDS,
    "Delver":          DELVER,
    "Elves":           ELVES,
    "Painter":         PAINTER,
    "Stoneforge":      STONEFORGE,
    "Golgari Hogaak":  HOGAAK,
}
