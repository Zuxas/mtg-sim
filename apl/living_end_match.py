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

# Cycling creatures — cheap to cycle, large bodies returned by Living End
# Power values used for P/T estimation after Living End resolves.
CYCLERS = {
    # Classic package
    "Street Wraith": 3,               # 3/4, cycle = pay 2 life
    "Monstrous Carabid": 3,           # 3/3, cycle {B/G}
    "Horror of the Broken Lands": 5,  # 5/3, cycle {B}
    "Curator of Mysteries": 4,        # 4/4 flying, cycle {U}
    "Waker of Waves": 5,              # 5/5, cycle {U}
    "Deadshot Minotaur": 3,           # 3/3, cycle {R/G}
    "Architects of Will": 2,          # 2/3, cycling {U/B}
    "Twisted Abomination": 2,         # 5/3, cycle {B}
    "Fierce Empath": 0,               # 1/1, tutor on ETB
    "Overlord of the Balemurk": 4,    # 4/4, cycling
    # Modern canonical 2026 package
    "Generous Ent": 3,                # 4/4 reach, cycle {G}
    "Striped Riverwinder": 5,         # 5/6 hexproof, cycle {U}
    "Colossal Skyturtle": 4,          # 4/4 flying, channel/cycle
}

# Evoke creatures that protect the combo (pitch a colored card, effect + sacrifice)
SUBTLETY = "Subtlety"   # evoke blue: counter target creature/PW spell
ENDURANCE = "Endurance" # evoke green: shuffle GY into library (vs GY hate)

# Force of Negation + Commandeer protect cascade
FON = "Force of Negation"
COMMANDEER = "Commandeer"  # exile 2 blue cards: gain control of noncreature spell


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

        # STEP 1: Cycle creatures to fill graveyard.
        # Street Wraith: cycle = Pay 2 life (oracle: "Cycling — Pay 2 life.")
        # All others: cycle = 1 colored mana (approximate as 1 generic).
        for c in list(gs.zones.hand):
            if c.name in CYCLERS and c in gs.zones.hand:
                if c.name == "Street Wraith":
                    if gs.life > 2:  # don't cycle to death
                        gs.life -= 2
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        gs.zones.draw(1)  # cycling draws a card
                        gs._log(f"  Cycle Street Wraith (pay 2 life)")
                elif avail >= 1:
                    avail -= 1
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.zones.draw(1)  # cycling draws a card
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

                # Living End resolution (oracle-exact order):
                # 1. Each player exiles all creature cards from their GY
                # 2. Each player sacrifices all creatures they control
                # 3. Each player puts their exiled cards onto the battlefield
                # Key: step 2 creatures go to GY AFTER the exile, so they do NOT return.

                our_exiled = [c for c in list(gs.zones.graveyard)
                              if c.has(Tag.CREATURE)]
                opp_exiled = ([c for c in list(opponent.zones.graveyard)
                               if c.has(Tag.CREATURE)] if opponent else [])

                for cr in our_exiled:
                    gs.zones.graveyard.remove(cr)
                    gs.zones.exile.append(cr)
                for cr in opp_exiled:
                    opponent.zones.graveyard.remove(cr)
                    opponent.zones.exile.append(cr)

                our_creatures = [c for c in list(gs.zones.battlefield)
                                 if c.has(Tag.CREATURE) and not c.is_land()]
                opp_creatures = ([c for c in list(opponent.zones.battlefield)
                                  if c.has(Tag.CREATURE) and not c.is_land()]
                                 if opponent else [])

                for cr in our_creatures:
                    gs.zones.battlefield.remove(cr)
                    gs.zones.graveyard.append(cr)
                for cr in opp_creatures:
                    opponent.zones.battlefield.remove(cr)
                    opponent.zones.graveyard.append(cr)

                for cr in our_exiled:
                    gs.zones.exile.remove(cr)
                    gs.zones.battlefield.append(cr)
                    cr.turn_entered = gs.turn
                    cr.summoning_sickness = True
                for cr in opp_exiled:
                    opponent.zones.exile.remove(cr)
                    opponent.zones.battlefield.append(cr)
                    cr.turn_entered = gs.turn

                self._combo_fired = True
                gs._log(f"  Living End: exiled {len(our_exiled)} ours / {len(opp_exiled)} "
                        f"theirs, sac'd {len(our_creatures)} ours / {len(opp_creatures)} theirs")

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
        """Protect cascade from disruption using FON, Subtlety, or Commandeer."""
        if not spell or not opponent:
            return None
        spell_cmc = getattr(spell, 'cmc', 0)

        # Force of Negation: if not our turn, exile blue card to counter noncreature spell
        # Oracle: "If it's not your turn, you may exile a blue card rather than pay mana cost."
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

        # Subtlety: evoke blue card to counter creature/planeswalker spells
        # Oracle: "Evoke — Exile a blue card. Choose up to one target creature/PW spell.
        #          Its controller puts it on top of their library."
        if spell.has(Tag.CREATURE):
            for c in list(gs.zones.hand):
                if c.name == SUBTLETY:
                    blue_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                                  and 'U' in (getattr(x, 'colors', []) or [])]
                    if blue_cards:
                        pitch = blue_cards[0]
                        gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                        gs.zones.hand.remove(c); gs.zones.exile.append(c)
                        # Effect: bounce target creature/PW spell to top of library
                        gs._log(f"  Subtlety evoke: bounce {spell.name} to library")
                        return c

        # Commandeer: exile 2 blue cards to steal a high-value noncreature spell
        # Oracle: "Exile two blue cards: gain control of target noncreature spell."
        if not spell.has(Tag.CREATURE) and spell_cmc >= 4:
            for c in list(gs.zones.hand):
                if c.name == COMMANDEER:
                    blue_cards = [x for x in gs.zones.hand if x != c and not x.is_land()
                                  and 'U' in (getattr(x, 'colors', []) or [])]
                    if len(blue_cards) >= 2:
                        for pitch in blue_cards[:2]:
                            gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                        gs.zones.hand.remove(c); gs.zones.exile.append(c)
                        gs._log(f"  Commandeer: steal {spell.name}")
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
