"""
engine/opponent.py — Simplified opponent model for the blocking sim

Models the opponent as a curve of creatures that enter the battlefield
and block during combat. Not a full game engine — just enough to model
the tempo cost of running into real opposition.

Each archetype has:
  - A creature curve: {turn: [(power, toughness)]} — what they play
  - Removal density: probability of removing one of our creatures per turn
  - A combat strategy: how they assign blockers

This converts goldfish win rates into realistic racing win rates.
"""

from dataclasses import dataclass, field
from typing import Optional
import random


@dataclass
class OppCreature:
    power:     int
    toughness: int
    turn_played: int = 0

    @property
    def alive(self) -> bool:
        return self.toughness > 0


# ---------------------------------------------------------------------------
# Archetype opponent profiles
# {turn: list of (power, toughness) creatures played that turn}
# Based on real deck knowledge of what these archetypes play
# ---------------------------------------------------------------------------

OPPONENT_PROFILES = {
    # Legacy
    "dimir reanimator": {
        # They're combo — play cheap looting spells, not creatures
        # Occasionally have a zombie token or early threat
        "curve": {},
        "removal_per_turn": 0.15,   # Force of Will / Thoughtseize disruption
        "combo_kill_turns": {1: 5.0, 2: 40.0, 3: 35.0, 4: 15.0, 5: 5.0},
    },
    "lotus combo": {
        "curve": {},
        "removal_per_turn": 0.05,
        "combo_kill_turns": {1: 8.0, 2: 42.0, 3: 30.0, 4: 12.0, 5: 8.0},
    },
    "dimir tempo": {
        # DRC T1, Murktide T3, Ragavan T1
        "curve": {
            1: [(1, 1), (1, 1)],    # DRC + Ragavan
            3: [(5, 5)],             # Murktide Regent
        },
        "removal_per_turn": 0.40,   # Force of Will, Daze, Brainstorm effects
        "combo_kill_turns": None,
    },
    "cephalid breakfast": {
        "curve": {
            1: [(0, 3)],             # Cephalid Illusionist (0/3)
        },
        "removal_per_turn": 0.10,
        "combo_kill_turns": {2: 20.0, 3: 40.0, 4: 25.0, 5: 15.0},
    },
    "eldrazi stompy": {
        # Reality Smasher T3, TKS T4, Endbringer T6
        "curve": {
            1: [(2, 1)],             # Eldrazi Mimic
            2: [(3, 2)],             # Matter Reshaper
            3: [(4, 4), (4, 4)],     # Thought-Knot Seer
            4: [(5, 5)],             # Reality Smasher
        },
        "removal_per_turn": 0.20,   # TKS exile, Warping Wail
        "combo_kill_turns": None,
    },
    "sneak and show": {
        "curve": {},
        "removal_per_turn": 0.10,
        "combo_kill_turns": {3: 25.0, 4: 35.0, 5: 25.0, 6: 10.0, 7: 5.0},
    },
    "mono red painter": {
        # Goblin Engineer T2, Painter's Servant T2, Grindstone combo T2-3
        "curve": {
            1: [(1, 1)],             # Small red one-drop
            2: [(2, 2), (1, 3)],     # Goblin Engineer, Painter's Servant
        },
        "removal_per_turn": 0.15,
        "combo_kill_turns": {2: 10.0, 3: 30.0, 4: 35.0, 5: 20.0, 6: 5.0},
    },
    "doomsday": {
        "curve": {
            1: [(2, 1)],             # Ponder / early setup creature
        },
        "removal_per_turn": 0.20,   # Force of Will
        "combo_kill_turns": {2: 15.0, 3: 40.0, 4: 30.0, 5: 10.0, 6: 5.0},
    },
    "izzet delver": {
        "curve": {
            1: [(1, 1), (1, 1)],    # Delver + DRC
            3: [(3, 2), (3, 2)],    # Murktide
        },
        "removal_per_turn": 0.35,   # Lightning Bolt, Brainstorm
        "combo_kill_turns": None,
    },
    "death and taxes": {
        "curve": {
            1: [(1, 1), (2, 1)],    # Aether Vial, Thalia
            2: [(2, 1), (2, 2)],    # Various taxers
            3: [(2, 3), (3, 2)],    # Flickerwisp, Recruiter
        },
        "removal_per_turn": 0.25,   # Swords to Plowshares, Karakas
        "combo_kill_turns": None,
    },
    "bant nadu": {
        "curve": {
            2: [(2, 2)],
            3: [(3, 3), (5, 5)],    # Nadu triggers chain
        },
        "removal_per_turn": 0.20,
        "combo_kill_turns": {3: 20.0, 4: 40.0, 5: 25.0, 6: 15.0},
    },
    "four-color": {
        "curve": {
            1: [(1, 1)],
            2: [(2, 1)],
            3: [(3, 2), (2, 4)],
        },
        "removal_per_turn": 0.35,
        "combo_kill_turns": None,
    },
    "jeskai control": {
        "curve": {
            5: [(4, 5)],             # Snapcaster or Monastery Mentor late
        },
        "removal_per_turn": 0.50,   # Swords, Force, Counterspell
        "combo_kill_turns": None,
    },
    "mono red aggro": {
        "curve": {
            1: [(2, 1), (1, 1)],    # Goblin Guide, Eidolon
            2: [(2, 2), (2, 1)],
        },
        "removal_per_turn": 0.20,   # Bolt
        "combo_kill_turns": None,
    },
    "mono red prison": {
        "curve": {
            1: [(2, 2)],             # Magus of the Moon
            2: [(4, 3)],             # Rabblemaster
        },
        "removal_per_turn": 0.15,
        "combo_kill_turns": None,
    },
    # Modern
    "elves": {
        "curve": {
            1: [(1, 1), (1, 1), (1, 1)],
            2: [(2, 2), (3, 3)],
            3: [(6, 6)],             # Craterhoof or big Elf
        },
        "removal_per_turn": 0.05,
        "combo_kill_turns": {2: 15.0, 3: 40.0, 4: 25.0, 5: 15.0, 6: 5.0},
    },
    "hogaak": {
        "curve": {
            1: [(1, 1)],
            2: [(3, 3)],
            3: [(8, 8)],             # Hogaak
        },
        "removal_per_turn": 0.05,
        "combo_kill_turns": {2: 10.0, 3: 35.0, 4: 30.0, 5: 15.0, 6: 7.0, 7: 3.0},
    },
    "lands": {
        "curve": {
            4: [(20, 20)],           # Marit Lage token
        },
        "removal_per_turn": 0.10,   # Punishing Fire, Wasteland disruption
        "combo_kill_turns": {3: 5.0, 4: 25.0, 5: 35.0, 6: 25.0, 7: 10.0},
    },
    "painter": {
        "curve": {
            2: [(1, 3), (2, 2)],
        },
        "removal_per_turn": 0.15,
        "combo_kill_turns": {2: 8.0, 3: 28.0, 4: 30.0, 5: 20.0, 6: 10.0, 7: 4.0},
    },
    "stoneforge": {
        "curve": {
            2: [(1, 2)],             # Stoneforge Mystic
            4: [(4, 4)],             # Equipped creature
        },
        "removal_per_turn": 0.30,
        "combo_kill_turns": None,
    },
    "delver": {
        "curve": {
            1: [(1, 1)],
            3: [(3, 2)],
        },
        "removal_per_turn": 0.30,
        "combo_kill_turns": None,
    },
    "unknown": {
        "curve": {
            2: [(2, 2)],
            4: [(3, 3)],
        },
        "removal_per_turn": 0.20,
        "combo_kill_turns": None,
    },
}

# Alias mapping
for alias, target in [
    ("golgari hogaak", "hogaak"),
    ("izzet delver", "izzet delver"),
]:
    if alias not in OPPONENT_PROFILES and target in OPPONENT_PROFILES:
        OPPONENT_PROFILES[alias] = OPPONENT_PROFILES[target]
