"""apl/izzet_prowess_standard_match.py -- Izzet Prowess match APL.

Multi-inherits MatchAPL (for match-mode hooks) + IzzetProwessAPL (for
the full AggroAPL turn loop with all its card declarations and
helper state). No need to override main_phase/main_phase2 — the
goldfish APL's implementations are inherited directly.
"""
from apl.match_apl import MatchAPL
from apl.izzet_prowess_standard import IzzetProwessAPL


class IzzetProwessStandardMatchAPL(MatchAPL, IzzetProwessAPL):
    pass
