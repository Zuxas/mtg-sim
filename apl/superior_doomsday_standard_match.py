"""apl/superior_doomsday_standard_match.py -- Superior Doomsday match APL.

Multi-inherits MatchAPL + SuperiorDoomsdayAPL (ControlAPL shell).
"""
from apl.match_apl import MatchAPL
from apl.superior_doomsday_standard import SuperiorDoomsdayAPL


class SuperiorDoomsdayStandardMatchAPL(MatchAPL, SuperiorDoomsdayAPL):
    pass
