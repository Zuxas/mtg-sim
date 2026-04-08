"""apl/eldrazi_tron.py — Eldrazi Tron APL (Modern)
Assemble Tron by T3 → cast Karn/TKS/Reality Smasher for free.
Expedition Map finds missing Tron pieces.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

MINE    = "Urza's Mine"
TOWER   = "Urza's Tower"
PLANT   = "Urza's Power Plant"
MAP     = "Expedition Map"
KARN    = "Karn, the Great Creator"
TKS     = "Thought-Knot Seer"
SMASHER = "Reality Smasher"
DEVOURER= "Devourer of Destiny"
UGIN    = "Ugin, Eye of the Storms"
MIND    = "Mind Stone"
COMMAND = "Kozilek's Command"
FLESHRAKER = "Glaring Fleshraker"

TRON_LANDS = {MINE, TOWER, PLANT}

class EldraziTronAPL(BaseAPL):
    name = "Eldrazi Tron"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands     = [c for c in hand if c.is_land()]
        has_tron  = sum(1 for c in lands if c.name in TRON_LANDS)
        has_map   = any(c.name == MAP for c in hand)
        has_threat= any(c.name in {KARN, TKS, DEVOURER, UGIN} for c in hand)
        if len(lands) == 0: return False
        # Keep if we have 2+ tron pieces or map + threat
        if has_tron >= 2 and has_threat: return True
        if has_map and len(lands) >= 2: return True
        if len(lands) >= 3 and has_threat: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        # Bottom excess non-Tron lands
        non_tron_lands = [c for c in hand if c.is_land() and c.name not in TRON_LANDS]
        return non_tron_lands[:n]

    def _has_tron(self, gs):
        bf_names = {c.name for c in gs.battlefield() if c.is_land()}
        return all(t in bf_names for t in TRON_LANDS)

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # Expedition Map to assemble Tron
        for card in list(gs.hand()):
            if card.name == MAP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                # Simulate fetching the missing Tron piece
                bf_names = {c.name for c in gs.battlefield() if c.is_land()}
                for piece in TRON_LANDS:
                    if piece not in bf_names:
                        from data.card import Card
                        tron_land = Card(name=piece, mana_cost="", cmc=0,
                                        type_line="Land", oracle_text="",
                                        power=None, toughness=None, colors=[])
                        gs.zones.battlefield.append(tron_land)
                        gs._log(f"  Expedition Map → {piece}")
                        break
                break
        # Mind Stone ramp
        for card in list(gs.hand()):
            if card.name == MIND and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
        # Early threats
        for name in (DEVOURER, FLESHRAKER):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Big threats once mana available
        for name in (TKS, KARN, SMASHER, UGIN):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    if card.name == TKS:
                        gs._log("  TKS ETB → exiling their best card")
                    break
        for card in list(gs.hand()):
            if card.name == COMMAND and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
