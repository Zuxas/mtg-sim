"""apl/neoform_combo.py — Neoform / Simic Neoform APL (Modern)
T1-2 combo: Allosaurus Rider (0 mana via green cards) + Neoform/Eldritch Evolution
→ Ghalta/Xenagos → lethal trample.
Modeled as fast combo — GenericAPL won't capture this.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

RIDER    = "Allosaurus Rider"
NEOFORM  = "Neoform"
EVOLVE   = "Eldritch Evolution"
PACT     = "Summoner's Pact"
GENESIS  = "Planar Genesis"
GHALTA   = "Ghalta, Stampede Tyrant"
XENAGOS  = "Xenagos, God of Revels"
ATRAXA   = "Atraxa, Grand Unifier"
VEIL     = "Veil of Summer"
FON      = "Force of Negation"
CONSIGN  = "Consign to Memory"

COMBO_PIECES = {RIDER, NEOFORM, EVOLVE, GENESIS}

class NeoformComboAPL(BaseAPL):
    name = "Neoform"
    win_condition_damage = 20
    max_turns = 8

    def __init__(self):
        self._combo_fired = False

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands      = sum(1 for c in hand if c.is_land())
        has_rider  = any(c.name == RIDER for c in hand)
        has_combo  = sum(1 for c in hand if c.name in {NEOFORM, EVOLVE, GENESIS})
        has_pact   = any(c.name == PACT for c in hand)
        green_cards= sum(1 for c in hand if not c.is_land())
        if lands == 0 and green_cards < 3: return False
        # Ideal: Rider + Neoform + 2 green cards to pitch (Rider costs 0)
        if (has_rider or has_pact) and has_combo >= 1 and green_cards >= 3: return True
        if lands >= 1 and has_combo >= 1 and green_cards >= 3: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        if self._combo_fired:
            return
        self._play_land_if_able(gs)
        # Try to assemble combo: Rider (0 cost if 2+ green in hand) + Neoform
        non_lands = [c for c in gs.hand() if not c.is_land()]
        has_rider = any(c.name == RIDER for c in gs.hand())
        has_combo = any(c.name in {NEOFORM, EVOLVE, GENESIS} for c in gs.hand())
        if has_rider and has_combo and len(non_lands) >= 3:
            # Pitch 2 green cards to cast Rider for free
            rider_card = next(c for c in gs.hand() if c.name == RIDER)
            gs.hand().remove(rider_card)
            gs.zones.battlefield.append(rider_card)
            rider_card.summoning_sickness = True
            gs._log("  Allosaurus Rider (0 cost) → in play")
            # Now Neoform / Eldritch Evolution it into Ghalta
            for card in list(gs.hand()):
                if card.name in {NEOFORM, EVOLVE} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.hand().remove(card) if card in gs.hand() else None
                    token = gs._make_token("Ghalta, Stampede Tyrant", "12", "12", "Creature")
                    token.summoning_sickness = False
                    gs.damage_dealt += 12
                    gs._log("  Neoform → Ghalta (12 trample damage)")
                    self._combo_fired = True
                    return
        # Backup: Summoner's Pact for Rider
        for card in list(gs.hand()):
            if card.name == PACT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Pact puts Rider into hand
                from data.card import Card
                rider = Card(name=RIDER, mana_cost="{4}{G}{G}", cmc=6,
                             type_line="Creature", oracle_text="",
                             power="5", toughness="5", colors=["G"])
                gs.zones.hand.append(rider)
                gs._log("  Summoner's Pact → Allosaurus Rider to hand")
                break
