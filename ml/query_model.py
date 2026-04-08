"""Query model at contested states where decisions actually matter."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from ml.win_prob_model import load_model, predict_win_prob

model = load_model()

print("Marginal card values at CONTESTED states (where decisions matter)")
print("=" * 65)

# T1 vs Reanimator — contested, P(win) ~22%
base_t1_rean = {
    "turn": 1, "damage_dealt": 0, "creatures_in_play": 0, "total_power": 0,
    "lands_in_play": 1, "hand_size": 7, "life": 20, "energy": 0, "mulligans": 0,
    "has_thalia,_guardian_of_thraben": 0, "has_champion_of_the_parish": 0,
    "has_thalia's_lieutenant": 0, "has_adeline,_resplendent_cathar": 0,
    "has_guide_of_souls": 0, "has_cavern_of_souls": 0,
    "has_esper_sentinel": 0, "has_kytheon,_hero_of_akros": 0,
    "hand_creatures": 4, "hand_lands": 3,
}

print("\nvs Dimir Reanimator — T1 keep decision:")
base = predict_win_prob(base_t1_rean, "dimir reanimator", model=model)
print(f"  Base (no plays yet):          {base:.1f}%")

# Play Champion T1
with_champ = {**base_t1_rean, "has_champion_of_the_parish": 1,
              "creatures_in_play": 1, "total_power": 2,
              "hand_size": 6, "hand_creatures": 3}
p = predict_win_prob(with_champ, "dimir reanimator", model=model)
print(f"  After T1 Champion:            {p:.1f}%  ({p-base:+.1f}%)")

# Play Guide of Souls T1 instead
with_guide = {**base_t1_rean, "has_guide_of_souls": 1,
              "creatures_in_play": 1, "total_power": 1, "energy": 0,
              "hand_size": 6, "hand_creatures": 3}
p2 = predict_win_prob(with_guide, "dimir reanimator", model=model)
print(f"  After T1 Guide of Souls:      {p2:.1f}%  ({p2-base:+.1f}%)")

print("\nvs Dimir Reanimator — T2 board decisions:")
base_t2 = {**base_t1_rean, "turn": 2, "damage_dealt": 2,
           "creatures_in_play": 1, "total_power": 2,
           "has_champion_of_the_parish": 1, "hand_size": 6, "hand_creatures": 3}
base2 = predict_win_prob(base_t2, "dimir reanimator", model=model)
print(f"  Base (1 creature, 2 dmg):     {base2:.1f}%")

# Add Thalia T2
with_thalia = {**base_t2, "has_thalia,_guardian_of_thraben": 1,
               "creatures_in_play": 2, "total_power": 4,
               "hand_size": 5, "hand_creatures": 2}
p = predict_win_prob(with_thalia, "dimir reanimator", model=model)
print(f"  + Thalia T2:                  {p:.1f}%  ({p-base2:+.1f}%) [taxes their Dark Ritual]")

# Add Guide of Souls T2 instead
with_guide2 = {**base_t2, "has_guide_of_souls": 1, "energy": 1,
               "creatures_in_play": 2, "total_power": 3,
               "hand_size": 5, "hand_creatures": 2}
p2 = predict_win_prob(with_guide2, "dimir reanimator", model=model)
print(f"  + Guide of Souls T2:          {p2:.1f}%  ({p2-base2:+.1f}%) [faster clock]")

# Mulligan impact vs different opponents
print("\nMulligan cost by opponent:")
for opp in ["dimir reanimator", "dimir tempo", "mono red aggro", "jeskai control"]:
    no_mull = {**base_t1_rean, "mulligans": 0, "hand_size": 7, "hand_creatures": 4}
    one_mull = {**base_t1_rean, "mulligans": 1, "hand_size": 6, "hand_creatures": 3}
    two_mull = {**base_t1_rean, "mulligans": 2, "hand_size": 5, "hand_creatures": 2}
    p0 = predict_win_prob(no_mull, opp, model=model)
    p1 = predict_win_prob(one_mull, opp, model=model)
    p2 = predict_win_prob(two_mull, opp, model=model)
    print(f"  vs {opp:<25}  0 mull: {p0:.0f}%   1 mull: {p1:.0f}% ({p1-p0:+.0f}%)   2 mull: {p2:.0f}% ({p2-p0:+.0f}%)")

# On play vs on draw at T1
print("\nOn play vs on draw (modeled as extra land in hand):")
for opp in ["dimir reanimator", "dimir tempo", "eldrazi stompy"]:
    on_play = {**base_t1_rean, "hand_creatures": 4, "hand_lands": 3}
    on_draw = {**base_t1_rean, "hand_creatures": 3, "hand_lands": 4}   # extra card = extra land
    pp = predict_win_prob(on_play, opp, model=model)
    pd = predict_win_prob(on_draw, opp, model=model)
    print(f"  vs {opp:<25}  play: {pp:.0f}%   draw: {pd:.0f}% ({pd-pp:+.0f}%)")
