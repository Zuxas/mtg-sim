"""
mana.py — Mana pool and cost validation

Tracks floating mana by color and handles casting cost checks
with full color pip validation.

Colors: W U B R G C (colorless/generic)
"""

import re
from dataclasses import dataclass, field


COLORS = {"W", "U", "B", "R", "G", "C"}

# Regex to extract all pips from a mana cost string like "{2}{W}{U}"
_PIP_RE = re.compile(r"\{([^}]+)\}")


def parse_cost(mana_cost: str) -> dict:
    """
    Parse a mana cost string into a dict of requirements.
    Returns {"generic": int, "W": int, "U": int, ...}
    e.g. "{2}{W}{U}" -> {"generic": 2, "W": 1, "U": 1}
         "{R}{R}"    -> {"generic": 0, "R": 2}
         "{X}"       -> {"generic": 0}   (X treated as 0 in goldfish)
    """
    req = {"generic": 0}
    for pip in _PIP_RE.findall(mana_cost.upper()):
        if pip in COLORS:
            req[pip] = req.get(pip, 0) + 1
        elif pip.isdigit():
            req["generic"] += int(pip)
        elif pip == "X":
            pass  # X = 0 in goldfish sim
        elif "/" in pip:
            # Hybrid mana e.g. {W/U} — treat as the first color for simplicity
            first = pip.split("/")[0]
            if first in COLORS:
                req[first] = req.get(first, 0) + 1
            else:
                req["generic"] += 1
        # Phyrexian mana {W/P} — treat as 0 (can pay life instead)
    return req


@dataclass
class ManaPool:
    W: int = 0
    U: int = 0
    B: int = 0
    R: int = 0
    G: int = 0
    C: int = 0     # colorless / generic
    flex: int = 0  # any-color mana (Cavern, Ziggurat, Unclaimed Territory)

    def total(self) -> int:
        return self.W + self.U + self.B + self.R + self.G + self.C + self.flex

    def add(self, color: str, amount: int = 1):
        color = color.upper()
        if color not in COLORS:
            raise ValueError(f"Unknown mana color: {color}")
        setattr(self, color, getattr(self, color) + amount)

    def add_land(self, type_line: str, land_name: str = ""):
        """
        Add exactly 1 mana based on a land's type line and name.

        Basic lands → their color.
        Dual lands (two basic land subtypes, e.g. Volcanic Island) → 1 flex.
        Fetchlands → 1 flex (they find any dual/basic, color is accessible).
        Wasteland / Ghost Quarter → 1 C (colorless only).
        Cavern / Ziggurat / Unclaimed Territory → 1 flex (any color for creatures).
        """
        t = type_line.lower()
        n = land_name.lower()

        # Fetchlands — should be handled by GameState._resolve_fetch() now.
        # If we still see one here, give 1 flex as fallback.
        FETCH_NAMES = {
            "flooded strand", "polluted delta", "bloodstained mire",
            "windswept heath", "wooded foothills", "scalding tarn",
            "misty rainforest", "verdant catacombs", "arid mesa",
            "marsh flats", "prismatic vista", "fabled passage",
        }
        if n in FETCH_NAMES:
            self.flex += 1
            return

        # Wasteland / Strip Mine → colorless only
        if n in {"wasteland", "strip mine", "ghost quarter", "rishadan port"}:
            self.add("C")
            return

        # Count how many basic land types appear in the type line
        BASIC_TYPES = {
            "plains": "W", "island": "U", "swamp": "B",
            "mountain": "R", "forest": "G",
        }
        found = [(color) for word, color in BASIC_TYPES.items() if word in t]

        if len(found) == 0:
            # Non-basic with no basic type (Cavern, Ziggurat, Horizon Canopy, etc.)
            self.flex += 1
        elif len(found) == 1:
            # Single-type basic or simple dual (e.g. Plains, Badlands-style)
            self.add(found[0])
        else:
            # Dual land (Volcanic Island, Bayou, Tundra, etc.) → flex
            self.flex += 1

    def can_pay(self, mana_cost: str, cmc: float) -> bool:
        """
        Full color pip validation with flex mana support.
        Flex mana (from Cavern/Ziggurat/Unclaimed Territory) satisfies
        any colored pip, used only after specific color mana is exhausted.
        """
        if not mana_cost:
            return self.total() >= int(cmc)

        req = parse_cost(mana_cost)
        remaining = dict(W=self.W, U=self.U, B=self.B,
                         R=self.R, G=self.G, C=self.C,
                         flex=self.flex)

        # Pay each colored pip — try specific color first, then flex
        for color in ("W", "U", "B", "R", "G"):
            needed = req.get(color, 0)
            have = remaining.get(color, 0)
            if have >= needed:
                remaining[color] -= needed
            else:
                # Use flex to cover the shortfall
                shortfall = needed - have
                if remaining["flex"] >= shortfall:
                    remaining[color] = 0
                    remaining["flex"] -= shortfall
                else:
                    return False  # Can't satisfy this pip

        # Check generic requirement
        total_left = sum(remaining.values())
        return total_left >= req.get("generic", 0)

    def can_cast(self, mana_cost: str, cmc: float) -> bool:
        """Alias for can_pay — used by game_state."""
        if mana_cost:
            return self.can_pay(mana_cost, cmc)
        return self.total() >= int(cmc)

    def pay(self, mana_cost: str, cmc: float) -> bool:
        """
        Deduct mana with full pip + flex validation.
        Returns True if payment succeeded.
        """
        if not self.can_pay(mana_cost, cmc):
            return False

        req = parse_cost(mana_cost) if mana_cost else {"generic": int(cmc)}

        # Pay colored pips — specific color first, flex as fallback
        for color in ("W", "U", "B", "R", "G"):
            needed = req.get(color, 0)
            have = getattr(self, color)
            if have >= needed:
                setattr(self, color, have - needed)
            else:
                used_flex = needed - have
                setattr(self, color, 0)
                self.flex -= used_flex

        # Pay generic with whatever's left (flex, then C, then WUBRG)
        generic = req.get("generic", 0)
        for color in ("flex", "C", "W", "U", "B", "R", "G"):
            if generic <= 0:
                break
            available = getattr(self, color)
            use = min(available, generic)
            setattr(self, color, available - use)
            generic -= use

        return True

    def empty(self):
        self.W = self.U = self.B = self.R = self.G = self.C = self.flex = 0

    def __repr__(self):
        parts = [f"{c}:{getattr(self, c)}" for c in "WUBRG" if getattr(self, c) > 0]
        if self.C:    parts.append(f"C:{self.C}")
        if self.flex: parts.append(f"flex:{self.flex}")
        return f"ManaPool({', '.join(parts) or 'empty'})"
