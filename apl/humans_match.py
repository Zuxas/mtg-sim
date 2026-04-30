"""
apl/humans_match.py — Oracle-audited 5-Color Humans APL (Modern)

Key mechanics modeled:
1. Aether Vial — tick to 2 T1, deploy 2-drops free every turn
2. Champion of the Parish — +1/+1 per Human ETB under your control
3. Thalia's Lieutenant — on ETB: +1/+1 all Humans; each Human ETB pumps it
4. Noble Hierarch — exalted (+1/+0 to lone attacker)
5. Mantis Rider — haste, attack immediately
6. Jirina, Dauntless General — +1/+1 to all Humans when attacking with 3+

Deploy order: Vial T1 > 1-drops (Champion/Hierarch) > Lieutenant > 2-drops > 3-drops
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

CHAMPION    = "Champion of the Parish"
HIERARCH    = "Noble Hierarch"
GUIDE       = "Guide of Souls"
LIEUTENANT  = "Thalia's Lieutenant"
COPPERCOAT  = "Coppercoat Vanguard"
MEDDLING    = "Meddling Mage"
THALIA      = "Thalia, Guardian of Thraben"
JIRINA      = "Jirina, Dauntless General"
MANTIS      = "Mantis Rider"
ADELINE     = "Adeline, Resplendent Cathar"
VIAL        = "Aether Vial"
SENTINEL    = "Esper Sentinel"
IMAGE       = "Phantasmal Image"

# Cards that are Humans (trigger Champion + Lieutenant)
HUMANS = {CHAMPION, HIERARCH, GUIDE, LIEUTENANT, COPPERCOAT, MEDDLING,
          THALIA, JIRINA, MANTIS, ADELINE, SENTINEL}
# Non-humans (Image copies, Mockingbird is a Bird)
NON_HUMANS = {IMAGE}


class HumansMatchAPL(MatchAPL):
    name = "Humans"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._vial_counters = 0      # Aether Vial charge count
        self._vial_on_board = False  # Vial deployed?
        self._champion_bonus = 0     # extra counters on Champion from Humans played

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        humans = sum(1 for c in hand if c.name in HUMANS)
        has_vial = any(c.name == VIAL for c in hand)
        has_champion = any(c.name == CHAMPION for c in hand)
        if lands == 0:
            return False
        if lands > 4:
            return False
        # Snap keep: Vial + 2 Humans + 1 land
        if has_vial and humans >= 2 and lands >= 1:
            return True
        # Good: Champion + 2 Humans + 2 lands
        if has_champion and humans >= 2 and lands >= 2:
            return True
        if humans >= 3 and lands >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        # Keep Vial, 1-drops, and lords; bottom excess lands + high-CMC
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)[3:]
        to_bottom = list(excess_lands)
        # Bottom highest-CMC non-essential cards
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in (VIAL, CHAMPION, HIERARCH, LIEUTENANT)],
                        key=lambda c: -getattr(c, 'cmc', 0))
        for c in filler:
            if len(to_bottom) >= n:
                break
            to_bottom.append(c)
        return to_bottom[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        avail = gs.mana_pool.total()

        # Track Vial state
        self._vial_on_board = any(c.name == VIAL for c in gs.zones.battlefield)

        # 1. Deploy Aether Vial T1 (highest priority — enables free creatures every turn)
        if not self._vial_on_board:
            for c in list(gs.zones.hand):
                if c.name == VIAL and avail >= 1:
                    gs.mana_pool.pay("{1}", 1) if gs.mana_pool.can_pay("{1}", 1) else None
                    gs.zones.hand.remove(c)
                    gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn
                    self._vial_on_board = True
                    self._vial_counters = 0
                    avail = gs.mana_pool.total()
                    gs._log(f"  Aether Vial deployed (T1 priority)")
                    break

        # Tick Vial every turn (target: 2 counters = most Humans)
        if self._vial_on_board:
            self._vial_counters = min(self._vial_counters + 1, 3)

        # 2. Use Vial to deploy a Human for free (if Vial matches a Human in hand)
        if self._vial_on_board and self._vial_counters >= 1:
            vial_targets = [c for c in gs.zones.hand
                           if c.name in HUMANS and getattr(c, 'cmc', 0) == self._vial_counters]
            if vial_targets:
                # Deploy highest-value target via Vial
                deploy_order = [LIEUTENANT, MEDDLING, COPPERCOAT, MANTIS, CHAMPION,
                                HIERARCH, GUIDE, THALIA, JIRINA, ADELINE, SENTINEL]
                for name in deploy_order:
                    target = next((c for c in vial_targets if c.name == name), None)
                    if target:
                        gs.zones.hand.remove(target)
                        gs.zones.battlefield.append(target)
                        target.turn_entered = gs.turn
                        target.summoning_sickness = True
                        self._apply_human_etb_effects(gs, target)
                        gs._log(f"  Vial: deploy {target.name} (CMC {self._vial_counters}, free)")
                        avail = gs.mana_pool.total()
                        break

        # 3. Deploy creatures from hand (cheapest first, lords before bodies)
        deploy_priority = [
            CHAMPION,    # triggers on every Human played after = snowball
            HIERARCH,    # T1 mana accelerant + exalted
            GUIDE,       # T1 lifegain engine
            LIEUTENANT,  # pump all existing Humans + get pumped by future ones
            COPPERCOAT,  # ward 1 protection + human
            MEDDLING,    # disrupt opponent's game plan
            THALIA,      # tax noncreature spells
            SENTINEL,    # draw engine
            JIRINA,      # lord effect on attack
            ADELINE,     # token generator
            MANTIS,      # haste — attack immediately
            IMAGE,       # copy best creature
        ]
        for name in deploy_priority:
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    if name == MANTIS:
                        # Mantis Rider has haste — deploy then attack same turn
                        gs.cast_spell(c)
                        c.summoning_sickness = False  # haste
                        self._apply_human_etb_effects(gs, c)
                        gs._log(f"  Mantis Rider: haste, attacks this turn")
                    elif name == MEDDLING and opponent:
                        # Name opponent's best card
                        best = (max(opponent.zones.hand,
                                    key=lambda x: getattr(x, 'cmc', 0))
                                if opponent.zones.hand else None)
                        gs.cast_spell(c)
                        self._apply_human_etb_effects(gs, c)
                        if best:
                            gs._log(f"  Meddling Mage: name {best.name}")
                    else:
                        gs.cast_spell(c)
                        self._apply_human_etb_effects(gs, c)
                    avail = gs.mana_pool.total()
                    break

    def _apply_human_etb_effects(self, gs, entering_card):
        """Apply lord triggers when a Human enters the battlefield.

        Champion of the Parish: +1/+1 counter per Human ETB.
        Thalia's Lieutenant: on ETB, each other Human gets +1/+1 AND each
          existing Human gives Lieutenant +1/+1.
        """
        is_human = entering_card.name in HUMANS

        if is_human:
            # Champion of the Parish: gains +1/+1
            for c in gs.zones.battlefield:
                if c.name == CHAMPION and c is not entering_card:
                    c.counters += 1
                    self._champion_bonus += 1

            # Thalia's Lieutenant entering: pump all other Humans
            if entering_card.name == LIEUTENANT:
                other_humans = [c for c in gs.zones.battlefield
                                if c.name in HUMANS and c is not entering_card]
                for h in other_humans:
                    h.counters += 1
                # Lieutenant gets +1/+1 per Human already in play
                entering_card.counters += len(other_humans)
                if other_humans:
                    gs._log(f"    Lieutenant ETB: +{len(other_humans)}/+{len(other_humans)} "
                            f"to all, self gets +{len(other_humans)}/+{len(other_humans)}")

            # Any other Human entering: Thalia's Lieutenant on battlefield gets +1/+1
            else:
                for c in gs.zones.battlefield:
                    if c.name == LIEUTENANT and c is not entering_card:
                        c.counters += 1

    def declare_attackers(self, gs, opponent):
        """Attack with everyone. Mantis (haste) attacks even freshly deployed.
        Jirina: if 3+ Humans attack, all Humans get +1/+1 until EOT.
        """
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if not c.has(Tag.CREATURE):
                continue
            if getattr(c, 'tapped', False):
                continue
            # Respect summoning sickness (Mantis has haste set explicitly)
            if getattr(c, 'summoning_sickness', False):
                continue
            attackers.append(c)

        # Noble Hierarch exalted: if exactly 1 attacker, give +1/+0
        hierarchs = sum(1 for c in gs.zones.battlefield if c.name == HIERARCH)
        if len(attackers) == 1 and hierarchs >= 1:
            attackers[0].counters += hierarchs
            gs._log(f"  Exalted: {attackers[0].name} gets +{hierarchs}/+{hierarchs}")

        # Jirina: 3+ Humans attacking → +1/+1 to all attacking Humans
        attacking_humans = [a for a in attackers if a.name in HUMANS]
        if len(attacking_humans) >= 3:
            for c in attacking_humans:
                if c.name == JIRINA or any(x.name == JIRINA for x in gs.zones.battlefield):
                    c.counters += 1
            gs._log(f"  Jirina: +1/+1 to {len(attacking_humans)} attacking Humans")

        return attackers

    def declare_blockers(self, gs, opp, attackers):
        """Block biggest threats. Preserve Hierarch for exalted attacks."""
        assignments = {}
        if not attackers:
            return assignments
        # Block with big creatures, leave Hierarch free for exalted
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and c.name != HIERARCH  # preserve for exalted
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)
                    and safe_power(c) >= 2]
        if not blockers:
            return {}
        biggest = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest) >= 3:
            best_blocker = max(blockers, key=lambda c: safe_toughness(c))
            assignments[id(biggest)] = [best_blocker]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        """Priority: Cavern of Souls > dual lands > basics."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if 'cavern' in n:
                return 0  # uncounterable creatures
            if 'courtyard' in n or 'territory' in n or 'ziggurat' in n:
                return 1  # 5-color fixing
            if 'seachrome' in n:
                return 2  # dual
            return 3
        gs.play_land(min(lands, key=score))
