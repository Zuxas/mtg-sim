from apl.base_apl import BaseAPL
from apl.mulligan import take_opening_hand, generic_keep, generic_bottom
from apl.humans import HumansAPL
from apl.elves import ElvesAPL
from apl.delver import DelverAPL
from apl.lands import LandsAPL
from apl.painter import PainterAPL
from apl.stoneforge import StoneforgeAPL
from apl.hogaak import HogaakAPL

# Registry: maps archetype key to APL class
APL_REGISTRY = {
    "humans":     HumansAPL,
    "elves":      ElvesAPL,
    "delver":     DelverAPL,
    "ur delver":  DelverAPL,
    "lands":      LandsAPL,
    "painter":    PainterAPL,
    "stoneforge": StoneforgeAPL,
    "hogaak":     HogaakAPL,
    "golgari hogaak": HogaakAPL,
}

def get_apl(deck_name: str, archetype: str = "") -> BaseAPL | None:
    """Return an APL instance for a deck name or archetype string."""
    key = (archetype or deck_name).lower().strip()
    # Strip common prefixes
    for prefix in ["legacy ", "modern ", "pioneer ", "ur ", "uw "]:
        key = key.replace(prefix, "")
    cls = APL_REGISTRY.get(key)
    return cls() if cls else None
