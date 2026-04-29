"""
apl/living_end_match.py — Living End APL (Modern)

Win mechanic:
1. Cycle Street Wraith / Monstrous Carabid / Horror of the Broken Lands /
   Curator of Mysteries / Waker of Waves to fill graveyard (all have cycling).
2. Cast Violent Outburst ({1}{R}{G}, cascade 3) or Ardent Plea ({1}{W}{U},
   cascade 2). Cascade exiles until CMC < 3/2, hits Living End (CMC 0).
3. Living End resolves: each player sacrifices all creatures; each player
   returns all creature cards from their GY to the battlefield.

Result T3-4: opponent board wiped, we get 4-7 cycling creatures (3-5 power
each) on the battlefield. Typical cascade window: T3 on play / T3-4 on draw.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

LIVING_END      = "Living End"
VIOLENT_OUT     = "Violent Outburst"
ARDENT_PLEA     = "Ardent Plea"
SHARDLESS       = "Shardless Agent"
CASCADE_SPELLS  = {VIOLENT_OUT, ARDENT_PLEA, SHARDLESS}
CASCADE_COST    = {VIOLENT_OUT: 3, ARDENT_PLEA: 3, SHARDLESS: 3}

# Cycling creatures — cheap to cycle ({1} or {B/G}), large bodies
CYCLERS = {
    "Street Wraith": 3,       # 3/4, cycle {2B}
    "Monstrous Carabid": 3,   # 3/3, cycle {B/G}
    "Horror of the Broken Lands": 3,  # 5/3, cycle {B}
    "Curator of Mysteries": 4,        # 4/4 flying, cycle {U}
    "Waker of Waves": 5,      # 5/5, cycle {U}
    "Deadshot Minotaur": 3,   # 3/3, cycle {R/G}
    "Architects of Will": 2,  # 2/3, cycling {U/B}
    "Twisted Abomination": 2, # 5/3, cycle {B}
    "Fierce Empath": 0,       # 1/1, tutor on ETB
    "Overlord of the Balemurk": 4,    # 4/4, cycling
}

# Force of Negation protects the cascade
FON = "Force of Negation"


class LivingEndMatchAPL(MatchAPL):
    name = "Living End"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._combo_fired = False

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        has_cascade = any(c.name in CASCADE_SPELLS for c in hand)
        has_cyclers = sum(1 for c in hand if c.name in CYCLERS)
        if lands == 0:
            return False
        if lands > 5:
            return mulligans >= 1  # too mana-flooded
        # Good keep: cascade + at least 1 cycler + 2+ lands
        if has_cascade and has_cyclers >= 1 and lands >= 2:
            return True
        # Acceptable: 2+ cyclers + land (can find cascade)
        if has_cyclers >= 2 and lands >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        # Bottom excess lands; keep cascade spells + cyclers
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[3:]
        # Bottom non-cascade non-cycler non-creature spells last
        filler = [c for c in hand if not c.is_land() and c not in to_bottom
                  and c.name not in CASCADE_SPELLS and c.name not in CYCLERS]
        return (to_bottom + filler)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        avail = gs.mana_pool.total()

        if self._combo_fired:
            # Post-combo: just attack with large creatures
            return

        # STEP 1: Cycle creatures to fill graveyard
        # Cycling costs 1-2 mana or is free. Model as: move cyclers from hand
        # to GY (they don't enter battlefield; just get cycled).
        for c in list(gs.zones.hand):
            if c.name in CYCLERS and c in gs.zones.hand:
                # Pay cycling cost (approximate: 1 mana each)
                if avail >= 1:
                    avail -= 1
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs._log(f"  Cycle {c.name} to GY")

        # STEP 2: Fire cascade when we have mana + cascade spell
        # T3+ on play (Violent Outburst = {1RG}), T3+ on draw
        gy_cyclers = [c for c in gs.zones.graveyard if c.name in CYCLERS]
        cascade_in_hand = [c for c in gs.zones.hand if c.name in CASCADE_SPELLS]

        if cascade_in_hand and avail >= 3 and len(gy_cyclers) >= 2:
            cascade = cascade_in_hand[0]
            # Cast the cascade spell -> cascade hits Living End (CMC 0)
            if gs.mana_pool.can_cast(cascade.mana_cost, cascade.cmc):
                gs.cast_spell(cascade)
                gs._log(f"  {cascade.name}: cascade -> Living End!")

                # Living End resolution:
                # 1. Both players sacrifice all creatures
                our_creatures = [c for c in gs.zones.battlefield
                                 if c.has(Tag.CREATURE) and not c.is_land()]
                opp_creatures = ([c for c in opponent.zones.battlefield
                                  if c.has(Tag.CREATURE) and not c.is_land()]
                                 if opponent else [])

                for cr in our_creatures:
                    gs.zones.battlefield.remove(cr)
                    gs.zones.graveyard.append(cr)
                for cr in opp_creatures:
                    if opponent:
                        opponent.zones.battlefield.remove(cr)
                        opponent.zones.graveyard.append(cr)

                # 2. Return all creature cards from GY to battlefield
                our_gy_creatures = [c for c in list(gs.zones.graveyard)
                                    if c.has(Tag.CREATURE)]
                for cr in our_gy_creatures:
                    gs.zones.graveyard.remove(cr)
                    gs.zones.battlefield.append(cr)
                    cr.turn_entered = gs.turn
                    cr.summoning_sickness = True  # entered this turn

                # Opponent's GY creatures come back too (Living End is symmetrical)
                if opponent:
                    opp_gy_creatures = [c for c in list(opponent.zones.graveyard)
                                        if c.has(Tag.CREATURE)]
                    for cr in opp_gy_creatures:
                        opponent.zones.graveyard.remove(cr)
                        opponent.zones.battlefield.append(cr)
                        cr.turn_entered = gs.turn

                self._combo_fired = True
                our_back = len(our_gy_creatures)
                opp_back = len(opp_gy_creatures) if opponent else 0
                gs._log(f"  Living End: wiped {len(opp_creatures)} opp, "
                        f"returned {our_back} ours / {opp_back} theirs")

    def declare_attackers(self, gs, opponent):
        # Post-combo: attack with all non-summoning-sick creatures
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        if not attackers:
            return {}
        # Block biggest attacker with biggest blocker
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if not blockers:
            return {}
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(blockers, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Force of Negation — protect cascade from disruption."""
        if not spell or not opponent:
            return None
        # Only protect our own cascade (our life total not at risk from this)
        # In match context: counter opponent's counterspell targeting our cascade
        for c in list(gs.zones.hand):
            if c.name == FON and gs.mana_pool.total() < 2:
                blue_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                              and 'U' in (getattr(x, 'colors', []) or [])]
                if blue_cards:
                    pitch = blue_cards[0]
                    gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                    gs.zones.hand.remove(c); gs.zones.exile.append(c)
                    gs._log(f"  Force of Negation: counter {spell.name}")
                    return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        # Prioritize fetchlands, then duals, then basics
        def score(c):
            n = (c.name or '').lower()
            if any(x in n for x in ('strand', 'delta', 'tarn', 'mire', 'catacombs',
                                     'foothills', 'flats', 'rainforest', 'heath')):
                return 0
            if any(x in n for x in ('vents', 'grave', 'garden', 'foundry', 'shrine')):
                return 1
            return 3
        gs.play_land(min(lands, key=score))
