"""
apl/boros_aggro_standard_match.py — Match-aware Boros Aggro APL (Standard)

Boros Aggro deck:
1. T1 Kumano Faces Kakkazan (saga: +1/+1, pings, then 2/2 haste) or Swiftspear
2. Charming Scoundrel: T2 haste, treasure or rummage
3. Phoenix Chick: flying haste, recurs from graveyard
4. Goddric: 4/4 celebrant (first nontoken creature = 3/3 haste dragon)
5. Squee: 2/1 haste, creates 1/1 goblin tokens on attack
6. Lightning Strike / Play with Fire: removal or face burn
7. Monstrous Rage / Witchstalker Frenzy: pump and board control
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

# Card name constants — post-ban Leyline of Resonance Heroic build
# (Arkany1, MTGO 2026-04-18). Key plan: T0 Leyline of Resonance in
# opening hand, T1 Cheeky House-Mouse or Stadium Headliner, then
# pump-spell storm via Turn Inside Out / Full Bore / Honor — each
# spell gets copied by Leyline for double-pump prowess damage.
CHEEKY_HOUSE_MOUSE  = "Cheeky House-Mouse"      # 1/1 haste
STADIUM_HEADLINER   = "Stadium Headliner"       # 2-drop haste
EMBERHEART          = "Emberheart Challenger"   # 2/2 haste prowess
BURNOUT_BASHTRONAUT = "Burnout Bashtronaut"     # 2/2 haste
SLICKSHOT           = "Slickshot Show-Off"      # 3/1 flying prowess
LEYLINE_RESONANCE   = "Leyline of Resonance"    # 0-cost spell-copier
FULL_BORE           = "Full Bore"               # pump
HONOR               = "Honor"                   # pump
MIGHT_OF_MEEK       = "Might of the Meek"       # pump for 1s
TURN_INSIDE_OUT     = "Turn Inside Out"         # +3/-3 reach
BURST_LIGHTNING     = "Burst Lightning"         # burn

ONE_DROPS = {CHEEKY_HOUSE_MOUSE}
BURN_SPELLS = {BURST_LIGHTNING}
# No mainboard creature removal — deck goes under with pump and burn.
# Sideboard has Lightning Helix + Get Lost, added for post-board games.
REMOVAL_SPELLS: set = set()
PUMP_SPELLS = {FULL_BORE, HONOR, MIGHT_OF_MEEK, TURN_INSIDE_OUT}


class BorosAggroStandardMatchAPL(MatchAPL):
    ARCHETYPE = "aggro"
    # SB_PLANS verified against Arkany1 2026-04-18 Boros Heroic list.
    # Sideboard: 2 Get Lost, 3 Lightning Helix, 4 Magebane Lizard,
    # 3 Rest in Peace, 3 Sheltered by Ghosts.
    SB_PLANS = {
        "control": (
            ["3 Lightning Helix", "3 Sheltered by Ghosts",
             "2 Get Lost"],
            ["4 Full Bore", "2 Might of the Meek", "2 Cheeky House-Mouse"],
        ),
        "aggro": (
            ["4 Magebane Lizard", "3 Lightning Helix"],
            ["4 Full Bore", "2 Might of the Meek", "1 Turn Inside Out"],
        ),
        "combo": (
            ["3 Rest in Peace", "2 Get Lost", "3 Lightning Helix"],
            ["4 Full Bore", "2 Might of the Meek", "2 Cheeky House-Mouse"],
        ),
        "ramp": (
            ["4 Magebane Lizard", "3 Lightning Helix",
             "2 Get Lost"],
            ["4 Full Bore", "2 Might of the Meek", "3 Honor"],
        ),
        "tempo": (
            ["3 Lightning Helix", "3 Sheltered by Ghosts",
             "2 Get Lost"],
            ["4 Full Bore", "2 Might of the Meek", "2 Cheeky House-Mouse"],
        ),
    }
    name = "Boros Aggro (Standard)"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        ones = sum(1 for c in hand if c.name in ONE_DROPS)
        burns = sum(1 for c in hand if c.name in BURN_SPELLS)
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        if lands == 0:
            return False
        if lands > 4:
            return False
        # Need a T1 play
        if ones >= 1 and lands >= 1:
            return True
        if lands >= 2 and creatures >= 1 and burns >= 1:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        pool = lands[2:] + spells
        return pool[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        """Boros Heroic: Leyline of Resonance (free in opening hand —
        copies every spell targeting our creatures) + one-drops that
        grow from the pump storm. Turn Inside Out / Full Bore / Honor
        each get doubled by Leyline for massive prowess bursts."""
        # Leyline of Resonance enters from hand for free at game start —
        # cast it before the land drop on turn 1.
        for c in list(gs.zones.hand):
            if c.name == LEYLINE_RESONANCE:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                gs._log("  Leyline of Resonance: free ETB (spell-copier online)")
                break

        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Deploy 1-drop haste creatures (Cheeky House-Mouse)
        for name in (CHEEKY_HOUSE_MOUSE,):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 2. Deploy 2-drops — priority Stadium Headliner (fast clock),
        # then Emberheart (2/2 haste prowess), then Burnout Bashtronaut
        for name in (STADIUM_HEADLINER, EMBERHEART, BURNOUT_BASHTRONAUT):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 3. Slickshot Show-Off (3-drop flying prowess — finisher)
        for c in list(gs.zones.hand):
            if c.name == SLICKSHOT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 4. Pump spells pre-combat. Each pump targets a creature — if
        # Leyline of Resonance is in play, the spell is copied for double
        # effect. The MONSTROUS_RAGE helper was replaced wholesale for
        # this deck; we loop through PUMP_SPELLS in order of best payoff.
        my_creatures = [x for x in gs.zones.battlefield
                        if not x.is_land() and x.has(Tag.CREATURE)
                        and not getattr(x, 'tapped', False)
                        and not getattr(x, 'summoning_sickness', False)]
        has_leyline = any(c.name == LEYLINE_RESONANCE
                           for c in gs.zones.battlefield)
        if my_creatures:
            for pump_name in (TURN_INSIDE_OUT, FULL_BORE,
                              HONOR, MIGHT_OF_MEEK):
                for c in list(gs.zones.hand):
                    if c.name == pump_name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        gs.mana_pool.pay(c.mana_cost, c.cmc)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        gs.noncreature_spells_this_turn += 1
                        # Pump the strongest attacker; Leyline copies
                        # the effect so add 2 counters instead of 1.
                        target = max(my_creatures, key=lambda x: safe_power(x))
                        bump = 2 if has_leyline else 1
                        target.counters = (target.counters or 0) + bump
                        tag = " (Leyline×2)" if has_leyline else ""
                        gs._log(f"  {pump_name} on {target.name}: +{bump}"
                                f"{tag}")
                        break
            # Dead code path — old Monstrous Rage loop retained as
            # no-op shim so the rest of the method still parses.
            for c in list(gs.zones.hand):
                if False:  # never fires, placeholder
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    target = max(my_creatures, key=lambda x: safe_power(x))
                    target.counters = (target.counters or 0) + 1
                    gs._log(f"  Monstrous Rage on {target.name} (+1 counter)")
                    break

        # 8. Burst Lightning face with remaining mana (base 2 dmg).
        for c in list(gs.zones.hand):
            if c.name not in BURN_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            dmg = 2  # Burst Lightning unkicked
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.damage_dealt += dmg
            gs.noncreature_spells_this_turn += 1
            gs._log(f"  {c.name} face: {dmg} ({gs.damage_dealt} total)")

        # 9. Any remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _try_removal(self, gs: GameState, opponent: GameState):
        """Post-board only: Lightning Helix / Get Lost come in from SB."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return
        for c in list(gs.zones.hand):
            if c.name not in REMOVAL_SPELLS:
                continue
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
            # Determine damage — post-board SB spells only (Helix=3)
            dmg = 3 if c.name == "Lightning Helix" else 2
            if dmg < safe_toughness(target):
                continue
            gs.mana_pool.pay(c.mana_cost, c.cmc)
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs.noncreature_spells_this_turn += 1
            if target in opponent.zones.battlefield:
                opponent.zones.battlefield.remove(target)
                opponent.zones.graveyard.append(target)
            gs._log(f"  {c.name} -> kill {target.name}")
            return

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land():
                continue
            if getattr(c, 'summoning_sickness', False):
                continue
            if getattr(c, 'tapped', False):
                continue
            if c.has(Tag.CREATURE):
                attackers.append(c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}  # aggro never blocks — race

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
