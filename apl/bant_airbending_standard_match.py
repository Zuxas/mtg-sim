"""
apl/bant_airbending_standard_match.py -- Bant Airbending match APL (Standard 2026)

Cyprien Tron PT SOS list. W/G/U Avatar-themed flying tempo deck.

Decklist core:
  Llanowar Elves {G}:         1/1 mana dork
  Badgermole Cub {1G}:        ETB / attack trigger; generates double mana (landfall)
  Bramble Familiar {G}:       ramp and draw
  Aang, Swift Savior {2U}:    3/2 flying; draw on attack; primary evasion threat
  Aang, at the Crossroads {1WU}: 2/3 flying; protects other Avatars
  Appa, Steadfast Guardian {4WG}: 5/5 flying; protects your creatures
  Doc Aurlock, Grizzled Genius {2U}: 2/2; reduces costs of Avatar spells
  Interdimensional Web Watch {1U}: enchantment value engine
  Airbender Ascension {1WU}:  gives flying + ward {2} to creatures you control

Sideboard: Seam Rip (destroy enchantment/artifact), Avatar's Wrath (4 damage to non-Avatars),
           Rest in Peace, Get Lost, Disdainful Stroke, Cavern of Souls, Bovine Intervention

Role vs matchups:
  vs Aggro:        race with flying evasion; Appa blocks wide boards
  vs Midrange:     tempo; Aang draws cards to rebuild after removal
  vs Control:      Cavern of Souls makes Avatars uncounterable; grind with Doc Aurlock
  vs Landfall:     race in the air; their ground creatures can't block Aang/Appa
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.bant_airbending_standard import BantAirbendingAPL

AANG_SAVIOR   = "Aang, Swift Savior"
AANG_CROSS    = "Aang, at the Crossroads"
APPA          = "Appa, Steadfast Guardian"
DOC_AURLOCK   = "Doc Aurlock, Grizzled Genius"
BADGERMOLE    = "Badgermole Cub"
LLANOWAR      = "Llanowar Elves"
BRAMBLE       = "Bramble Familiar"
AIRBEND_ASC   = "Airbender Ascension"

SEAM_RIP      = "Seam Rip"
AVATARS_WRATH = "Avatar's Wrath"
REST_IN_PEACE = "Rest in Peace"
GET_LOST      = "Get Lost"
DISDAINFUL    = "Disdainful Stroke"
BOV_INTERVENT = "Bovine Intervention"
BEZA          = "Beza, the Bounding Spring"

# Evasion threats — attack into open boards; can't be profitably blocked by ground
FLYING_THREATS = {AANG_SAVIOR, AANG_CROSS, APPA}

# Priority targets to answer before they establish their engine
KILL_PRIORITY = (
    "Gran-Gran",              # Monument enabler
    "Stormchaser's Talent",   # Prowess engine
    "Mightform Harmonizer",   # Combo kill piece
    "Icetill Explorer",       # Landfall chain engine
)


class BantAirbendingStandardMatchAPL(AwareMatchAPL, BantAirbendingAPL):
    name = "Bant Airbending"
    ARCHETYPE = "tempo"

    # No counterspells in main deck; tap out every turn for threats
    COUNTER_COST  = 0
    COUNTER_CARDS = {DISDAINFUL}  # sideboard only

    # No main-deck instant removal; Avatar's Wrath only in sideboard
    MATCH_REMOVAL = {}
    MATCH_EXILE   = {GET_LOST}

    SB_PLANS = {
        "aggro": (
            # vs Red/Burn: Avatar's Wrath sweeps ground creatures; Beza gains life
            [AVATARS_WRATH, AVATARS_WRATH, BEZA, BEZA, BOV_INTERVENT],
            [AIRBEND_ASC, AIRBEND_ASC, "Interdimensional Web Watch", "Interdimensional Web Watch",
             BRAMBLE],
        ),
        "control": (
            # vs Control: Disdainful Stroke for big spells; Cavern makes Avatars uncounterable
            [DISDAINFUL, DISDAINFUL, "Cavern of Souls"],
            [REST_IN_PEACE, REST_IN_PEACE, SEAM_RIP],
        ),
        "combo": (
            # vs Izzet Lessons: Rest in Peace + Disdainful; race with flying
            [REST_IN_PEACE, REST_IN_PEACE, DISDAINFUL, DISDAINFUL, SEAM_RIP],
            ["Interdimensional Web Watch", "Interdimensional Web Watch", AIRBEND_ASC,
             AIRBEND_ASC, BRAMBLE],
        ),
        "ramp": (
            # vs Landfall: Disdainful Stroke for big payoffs; race in the air
            [DISDAINFUL, DISDAINFUL, AVATARS_WRATH, BEZA],
            [AIRBEND_ASC, BRAMBLE, "Interdimensional Web Watch", REST_IN_PEACE],
        ),
        "midrange": (
            # vs Golgari/Dimir: Get Lost for threats; Seam Rip for enchantments
            [GET_LOST, SEAM_RIP, SEAM_RIP, DISDAINFUL],
            [REST_IN_PEACE, REST_IN_PEACE, AIRBEND_ASC, BRAMBLE],
        ),
    }

    # Tap out completely every turn — no mana to hold up (no instant interaction)
    def reserve_mana(self, gs: GameState, opponent: GameState):
        gs.mana_reserve = 0

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        # No instant-speed removal in main deck; skip base class kill logic
        # Avatar's Wrath is sorcery-speed, handled in main phase
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Avatar's Wrath: deal 4 damage to each non-Avatar creature (post-board)
        # Fire if >=3 non-flying creatures that would block our fliers
        non_fliers = [c for c in opp_creatures
                      if not any(kw in getattr(c, 'oracle_text', '').lower()
                                 for kw in ['flying', 'reach'])
                      and safe_toughness(c) <= 4]
        if len(non_fliers) >= 3:
            for card in gs.zones.hand:
                if card.name == AVATARS_WRATH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    for victim in list(non_fliers):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.graveyard.append(victim)
                    gs._log(f"  [pre-combat] Avatar's Wrath dealt 4 to {len(non_fliers)} non-Avatars")
                    return
