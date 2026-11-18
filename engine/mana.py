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
         "{3}{C}"    -> {"generic": 3, "C": 1}        C = colorless ONLY
         "{R/W}"     -> {"generic": 0, "hybrid": [("R", "W")]}
         "{2/W}"     -> {"generic": 0, "hybrid": [("2", "W")]}
         "{G/P}"     -> {"generic": 0, "phyrexian": ["G"]}
         "{G/W/P}"   -> {"generic": 0, "phyrexian": ["GW"]}   (either color, or 2 life)
    The "hybrid" and "phyrexian" keys are present only when the cost has such pips.
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
            parts = pip.split("/")
            if parts[-1] == "P":
                colors = "".join(c for c in parts[:-1] if c in "WUBRG")
                if colors:
                    req.setdefault("phyrexian", []).append(colors)
            elif len(parts) == 2 and parts[1] in "WUBRG" and (parts[0] in "WUBRG" or parts[0] == "2"):
                req.setdefault("hybrid", []).append((parts[0], parts[1]))
            else:
                req["generic"] += 1   # unknown split pip: one mana of any type
    return req


def _land_mana(oracle_text: str):
    """What a land with no basic type makes, from its oracle text.
    Returns a color letter, "C", "flex", or None if the text says nothing."""
    text = (oracle_text or "").lower()
    made = set()
    for clause in re.findall(r"add ([^.\n]*)", text):
        if "any color" in clause or "any type" in clause or "any one color" in clause:
            return "flex"
        made |= {sym.upper() for sym in re.findall(r"\{([wubrgc])\}", clause)}
    colors = made - {"C"}
    if len(colors) > 1:
        return "flex"
    if colors:
        return colors.pop()
    return "C" if made else None


@dataclass
class ManaPool:
    W: int = 0
    U: int = 0
    B: int = 0
    R: int = 0
    G: int = 0
    C: int = 0     # colorless / generic
    flex: int = 0  # any-color mana (Cavern, Ziggurat, Unclaimed Territory)
    cost_reduction: int = 0  # generic cost reduction (affinity, delve, domain, convoke)
    phyrexian_life_ok: bool = True  # APL switch: False = Phyrexian pips must be paid with mana
    life_paid: int = 0       # life owed for Phyrexian pips by the last pay()

    def total(self) -> int:
        return self.W + self.U + self.B + self.R + self.G + self.C + self.flex

    def add(self, color: str, amount: int = 1):
        color = color.upper()
        if color not in COLORS:
            raise ValueError(f"Unknown mana color: {color}")
        setattr(self, color, getattr(self, color) + amount)

    def add_land(self, type_line: str, land_name: str = "", oracle_text: str = ""):
        """
        Add exactly 1 mana based on a land's type line and name.

        oracle_text (optional): for a land with no basic land type, what it
        makes is read from its text -- "Add {C}" gives colorless only (Urza's
        Tower, Eldrazi Temple, utility lands), one color gives that color,
        several colors or "any color" give flex. Without oracle text such a
        land still gives flex, as before.

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
            # Non-basic with no basic type: go by what the card says it makes.
            made = _land_mana(oracle_text)
            if made in (None, "flex"):
                self.flex += 1      # Cavern, Ziggurat, Horizon Canopy, or text unknown
            else:
                self.add(made)
        elif len(found) == 1:
            # Single-type basic or simple dual (e.g. Plains, Badlands-style)
            self.add(found[0])
        else:
            # Dual land (Volcanic Island, Bayou, Tundra, etc.) → flex
            self.flex += 1

    def _plan(self, mana_cost: str, cmc: float):
        """Work out a payment. Returns (remaining pool dict, life paid) or None.

        Order: colored pips (own color, then flex), {C} pips (colorless mana
        only), hybrid pips, Phyrexian pips in their own color if the generic
        part can still be paid, generic, then any Phyrexian pips still unpaid
        from leftover mana, falling back to 2 life each.
        """
        left = dict(W=self.W, U=self.U, B=self.B, R=self.R, G=self.G,
                    C=self.C, flex=self.flex)
        if not mana_cost:
            req = {"generic": int(cmc)}
        else:
            req = parse_cost(mana_cost)

        def take(color):
            """Spend one mana for a pip of `color`: that color, else flex."""
            for src in (color, "flex"):
                if left[src] > 0:
                    left[src] -= 1
                    return True
            return False

        for color in "WUBRG":
            for _ in range(req.get(color, 0)):
                if not take(color):
                    return None
        if left["C"] < req.get("C", 0):
            return None                      # {C} is payable only with colorless
        left["C"] -= req.get("C", 0)

        generic = req.get("generic", 0)
        for first, second in req.get("hybrid", []):
            if first == "2":                 # {2/X}: X, or two generic
                if not (left[second] > 0 and take(second)) and not (left["flex"] > 0 and take(second)):
                    generic += 2
            else:                            # {A/B}: whichever we have more of
                a, b = sorted((first, second), key=lambda c: -left[c])
                if left[a] > 0:
                    left[a] -= 1
                elif not take(b):
                    return None

        generic = max(0, generic - self.cost_reduction)

        # Phyrexian pips take mana of their own color when that still leaves
        # enough for the generic part; otherwise they wait for leftovers / life.
        unpaid = []
        for colors in req.get("phyrexian", []):
            color = next((c for c in colors if left[c] > 0), None)
            if color and sum(left.values()) - 1 >= generic:
                left[color] -= 1
            else:
                unpaid.append(colors)

        for src in ("flex", "C", "W", "U", "B", "R", "G"):   # same order as before
            use = min(left[src], generic)
            left[src] -= use
            generic -= use
        if generic > 0:
            return None

        life = 0
        for colors in unpaid:
            if not any(left[c] > 0 and take(c) for c in colors) and not (left["flex"] > 0 and take(colors[0])):
                if not self.phyrexian_life_ok:
                    return None
                life += 2
        return left, life

    def can_pay(self, mana_cost: str, cmc: float) -> bool:
        """
        Full pip validation: colored, {C}, hybrid and Phyrexian, with flex.
        Flex mana (Cavern/Ziggurat/duals) satisfies any colored pip, used only
        after specific color mana is exhausted. It does not pay {C}.
        A Phyrexian pip with no mana for it costs 2 life unless
        `phyrexian_life_ok` is False.
        """
        if not mana_cost:
            return self.total() >= int(cmc)
        return self._plan(mana_cost, cmc) is not None

    def can_cast(self, mana_cost: str, cmc: float) -> bool:
        """Alias for can_pay — used by game_state."""
        if mana_cost:
            return self.can_pay(mana_cost, cmc)
        return self.total() >= int(cmc)

    def pay(self, mana_cost: str, cmc: float) -> bool:
        """
        Deduct mana with full pip + flex validation.
        Returns True if payment succeeded. `life_paid` is then the life owed
        for Phyrexian pips (0 if none); the caller takes it off the player.
        """
        self.life_paid = 0
        plan = self._plan(mana_cost, cmc)
        if plan is None:
            return False
        left, self.life_paid = plan
        for src, amount in left.items():
            setattr(self, src, amount)
        return True

    def empty(self):
        self.W = self.U = self.B = self.R = self.G = self.C = self.flex = 0
        self.cost_reduction = 0  # reset per-turn cost modifiers

    def __repr__(self):
        parts = [f"{c}:{getattr(self, c)}" for c in "WUBRG" if getattr(self, c) > 0]
        if self.C:    parts.append(f"C:{self.C}")
        if self.flex: parts.append(f"flex:{self.flex}")
        return f"ManaPool({', '.join(parts) or 'empty'})"
