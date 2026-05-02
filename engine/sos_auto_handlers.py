"""engine/sos_auto_handlers.py -- Auto-generated SOS handlers.
Generated: 2026-05-03 via build_sos_all_handlers.py
Source: Scryfall API (271 oracle cards). Hand-written entries in
card_handlers_verified.py take precedence via setdefault().
"""
from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
from engine.effect_primitives import run_effects

def _etb(effects):
    # effects: list of (prim_name, kwargs) tuples from oracle_parser
    def _h(gs, card):
        from engine.effect_primitives import run_effects as _re
        _re(gs, {"source_card":card,"trigger_event":"etb","chosen_target":None}, effects)
    return _h

def _spell(effects):
    def _h(gs, card):
        from engine.effect_primitives import run_effects as _re
        _re(gs, {"source_card":card,"trigger_event":"spell","chosen_target":None}, effects)
    return _h


# When this creature enters, it deals 3 damage to each opponent and you gain 3 lif
_h_colossus_of_the_blood_age = _etb([["damage_player", {"n": 3, "target": "opp"}], ["gain_life", {"n": 3}]])
# When this creature enters, draw a card. Each player loses 1 life. | Repartee ? Whe
_h_conciliator_s_duelist = _etb([["draw", {"n": 1}]])
# When this creature enters, you may search your library for a basic land card, re
_h_environmental_scientist = _etb([["search_basic_land", {"n": 1}]])
# Jadzi enters prepared. (While it's prepared, you may cast a copy of its spell. D
_h_jadzi__steward_of_fate = _etb([["draw", {"n": 2}]])
# This spell costs {3} less to cast if creatures you control have total toughness 
_h_orysa__tide_choreographer = _etb([["draw", {"n": 2}]])
# Flying | This creature enters with X +1/+1 counters on it. | When this creature ente
_h_pterafractyl = _etb([["gain_life", {"n": 2}]])

# Target creature gains trample and gets +X/+0 until end of turn, where X is 1 plu
_h_ancestral_anger = _spell([["draw", {"n": 1}]])
# Converge ? Archaic's Agony deals X damage to target creature, where X is the num
_h_archaic_s_agony = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# Choose one ? | ? Artistic Process deals 6 damage to target creature. | ? Artistic Pr
_h_artistic_process = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}], ["damage_creature", {"n": 2, "target": "each_opp"}], ["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": ["flying"]}]])
# Return target nonland permanent to its owner's hand. Surveil 1. (Look at the top
_h_banishing_betrayal = _spell([["bounce_to_hand", {}]])
# Duel Tactics deals 1 damage to target creature. It can't block this turn. | Flashb
_h_duel_tactics = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# Repartee ? Whenever you cast an instant or sorcery spell that targets a creature
_h_graduation_day = _spell([["add_counters", {"n": 1, "target": "self"}]])
# Destroy target artifact or creature. You gain 1 life.
_h_grapple_with_death = _spell([["gain_life", {"n": 1}]])
# Put a +1/+1 counter on target creature you control, then double the number of +1
_h_growth_curve = _spell([["add_counters", {"n": 1, "target": "self"}]])
# Heated Argument deals 6 damage to target creature. You may exile a card from you
_h_heated_argument = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# Target player draws 2? cards. (2? = 1, 2? = 2, 2? = 4, 2? = 8, 2? = 16, 2? = 32,
_h_mathemagics = _spell([["draw", {"n": 1}]])
# Create a 3/3 blue and red Elemental creature token with flying. | Surveil 2. (Look
_h_muse_s_encouragement = _spell([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": ["flying"]}]])
# Target creature you control gets +1/+1 until end of turn. You draw a card and ga
_h_oracle_s_restoration = _spell([["draw", {"n": 1}]])
# Put a +1/+1 counter on each creature target player controls. Target creature gai
_h_practiced_offense = _spell([["add_counters", {"n": 1, "target": "self"}]])
# Return up to two target creature cards from your graveyard to your hand. You gai
_h_pull_from_the_grave = _spell([["gain_life", {"n": 2}]])
# Draw three cards, then discard two cards. Add {U}{U}{R}{R}{R}.
_h_rapturous_moment = _spell([["draw", {"n": 3}]])
# As an additional cost to cast this spell, discard a card. | Draw two cards and cre
_h_seize_the_spoils = _spell([["draw", {"n": 2}], ["create_treasure", {"n": 1}]])
# Choose one ? | ? Put two +1/+1 counters on target creature. | ? Exile target creatur
_h_silverquill_charm = _spell([["add_counters", {"n": 1, "target": "self"}], ["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# When you cast this spell while you control a creature, you may copy this spell. | 
_h_social_snub = _spell([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# Choose one ? | ? Draw four cards. | ? Splatter Technique deals 4 damage to each crea
_h_splatter_technique = _spell([["draw", {"n": 4}], ["damage_creature", {"n": 4, "target": "each_opp"}]])
# Destroy target creature with power 3 or greater.
_h_stand_up_for_yourself = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# Exile target nonland permanent and the top card of your library. For each of tho
_h_suspend_aggression = _spell([["exile", {"target": "opp_biggest_creature"}]])
# Converge ? Target player draws X cards, Together as One deals X damage to any ta
_h_together_as_one = _spell([["damage_any", {"n": 1}], ["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# All creatures get -2/-2 until end of turn. | Infusion ? If you gained life this tu
_h_withering_curse = _spell([["destroy_all_creatures", {}]])

for _n,_f in {
    "Colossus of the Blood Age": _h_colossus_of_the_blood_age,
    "Conciliator's Duelist": _h_conciliator_s_duelist,
    "Environmental Scientist": _h_environmental_scientist,
    "Jadzi, Steward of Fate": _h_jadzi__steward_of_fate,
    "Orysa, Tide Choreographer": _h_orysa__tide_choreographer,
    "Pterafractyl": _h_pterafractyl,
}.items(): ETB_EFFECTS.setdefault(_n,_f)

for _n,_f in {
    "Ancestral Anger": _h_ancestral_anger,
    "Archaic's Agony": _h_archaic_s_agony,
    "Artistic Process": _h_artistic_process,
    "Banishing Betrayal": _h_banishing_betrayal,
    "Duel Tactics": _h_duel_tactics,
    "Graduation Day": _h_graduation_day,
    "Grapple with Death": _h_grapple_with_death,
    "Growth Curve": _h_growth_curve,
    "Heated Argument": _h_heated_argument,
    "Mathemagics": _h_mathemagics,
    "Muse's Encouragement": _h_muse_s_encouragement,
    "Oracle's Restoration": _h_oracle_s_restoration,
    "Practiced Offense": _h_practiced_offense,
    "Pull from the Grave": _h_pull_from_the_grave,
    "Rapturous Moment": _h_rapturous_moment,
    "Seize the Spoils": _h_seize_the_spoils,
    "Silverquill Charm": _h_silverquill_charm,
    "Social Snub": _h_social_snub,
    "Splatter Technique": _h_splatter_technique,
    "Stand Up for Yourself": _h_stand_up_for_yourself,
    "Suspend Aggression": _h_suspend_aggression,
    "Together as One": _h_together_as_one,
    "Withering Curse": _h_withering_curse,
}.items(): SPELL_EFFECTS.setdefault(_n,_f)