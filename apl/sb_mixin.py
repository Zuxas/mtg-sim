"""Shared mixin for APLs that use sb_plans.py for sideboard premium."""
from apl.sb_plans import get_sb_premium


class SBPlanMixin:
    """Add to any APL to get sb_plans.py lookup for sideboard_premium."""

    def sideboard_premium(self, opp_name: str, format_name: str) -> float:
        return get_sb_premium(self.name, opp_name)

    def keep_vs(self, hand, mulligans, on_play, opp_archetype):
        """Default: no opponent-aware changes — use standard keep()."""
        return self.keep(hand, mulligans, on_play)
