"""
apl/abzan_enchantment_standard_match.py — Abzan Enchantment Aggro APL (Standard)

Abzan (WBG) enchantment-based aggro deck.
T1: Hopeless Nightmare (discard) or Deep-Cavern Bat (discard + fly)
T2: Optimistic Scavenger (grows from each enchantment entering)
T3: Sheltered by Ghosts on Scavenger (exile creature + ward + grows Scavenger)
Nowhere to Run: removal enchantment, triggers Scavenger
Preacher of the Schism: lifelink, makes vampire tokens on attack
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

OPTIMISTIC_SCAVENGER  = "Optimistic Scavenger"
DEEP_CAVERN_BAT       = "Deep-Cavern Bat"
GLISSA_SUNSLAYER      = "Glissa Sunslayer"
SHELTERED_BY_GHOSTS   = "Sheltered by Ghosts"
NOWHERE_TO_RUN        = "Nowhere to Run"
HOPELESS_NIGHTMARE    = "Hopeless Nightmare"
CALIX                 = "Calix, Guided by Fate"
ENDURING_INNOCENCE    = "Enduring Innocence"
PREACHER              = "Preacher of the Schism"
ZORALINE              = "Zoraline, Cosmos Caller"
ANOINT                = "Anoint with Affliction"
FINAL_VENGEANCE       = "Final Vengeance"
EXORCISE              = "Exorcise"
GET_LOST              = "Get Lost"

ENCHANTMENTS = {SHELTERED_BY_GHOSTS, NOWHERE_TO_RUN, HOPELESS_NIGHTMARE}
ONE_DROPS    = {DEEP_CAVERN_BAT, HOPELESS_NIGHTMARE}
REMOVAL_SPELLS = {ANOINT, FINAL_VENGEANCE, EXORCISE, GET_LOST, SHELTERED_BY_GHOSTS, NOWHERE_TO_RUN}


class AbzanEnchantmentStandardMatchAPL(MatchAPL):
    name = "Abzan Enchantment Aggro Standard"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._scavenger_counters = 0  # track Optimistic Scavenger +1/+1 counters

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.has(Tag.CREATURE))
        enchantments = sum(1 for c in hand if c.name in ENCHANTMENTS)
        if lands == 0: return False
        if lands == 1 and creatures == 0: return False
        if lands > 4: return False
        if creatures >= 1 and enchantments >= 1 and 2 <= lands <= 3: return True
        if creatures >= 2 and 2 <= lands <= 3: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        """Enchantment aggro: deploy Scavenger, pump with enchantments, attack."""
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. T1: Hopeless Nightmare (discard opponent) or Deep-Cavern Bat
        for name in (HOPELESS_NIGHTMARE, DEEP_CAVERN_BAT):
            for c in list(gs.zones.hand):
                if c.name != name: continue
                if not gs.mana_pool.can_cast(c.mana_cost, c.cmc): continue
                if name == HOPELESS_NIGHTMARE:
                    gs.cast_spell(c)
                    self._scavenger_pump(gs)
                    if opponent:
                        opp_nonlands = [x for x in opponent.zones.hand if not x.is_land()]
                        if opp_nonlands:
                            worst = min(opp_nonlands, key=lambda x: getattr(x, 'cmc', 0))
                            opponent.zones.hand.remove(worst)
                            opponent.zones.graveyard.append(worst)
                            gs._log(f"  Hopeless Nightmare: opponent discards {worst.name}")
                elif name == DEEP_CAVERN_BAT:
                    gs.cast_spell(c)
                    if opponent:
                        opp_nonlands = [x for x in opponent.zones.hand if not x.is_land()]
                        if opp_nonlands:
                            best = max(opp_nonlands, key=lambda x: getattr(x, 'cmc', 0))
                            opponent.zones.hand.remove(best)
                            opponent.zones.exile.append(best)
                            gs._log(f"  Bat ETB: exile {best.name} from opponent's hand")
                break

        # 2. Optimistic Scavenger — grows from each enchantment entering
        for c in list(gs.zones.hand):
            if c.name == OPTIMISTIC_SCAVENGER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Scavenger deployed: grows with each enchantment")
                break

        # 3. Sheltered by Ghosts — aura on best creature (exile their creature + ward)
        for c in list(gs.zones.hand):
            if c.name == SHELTERED_BY_GHOSTS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                my_creatures = [x for x in gs.zones.battlefield
                                if x.has(Tag.CREATURE) and not x.is_land()]
                if not my_creatures: break
                gs.cast_spell(c)
                self._scavenger_pump(gs)
                if opponent:
                    opp_cr = [x for x in opponent.zones.battlefield
                              if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        target = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                        gs._log(f"  Sheltered by Ghosts: exile {target.name} + ward on creature")
                break

        # 4. Nowhere to Run — removal enchantment, triggers Scavenger
        if opponent:
            opp_cr = [x for x in opponent.zones.battlefield
                      if not x.is_land() and x.has(Tag.CREATURE)]
            if opp_cr:
                for c in list(gs.zones.hand):
                    if c.name == NOWHERE_TO_RUN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                        target = max(opp_cr, key=lambda x: safe_power(x))
                        gs.cast_spell(c)
                        self._scavenger_pump(gs)
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                        gs._log(f"  Nowhere to Run: kill {target.name} (enchantment trigger)")
                        break

        # 4b. Additional removal spells
        if opponent:
            self._use_removal(gs, opponent)

        # 5. Glissa Sunslayer — first strike + deathtouch
        for c in list(gs.zones.hand):
            if c.name == GLISSA_SUNSLAYER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Glissa: 3/3 first strike deathtouch")
                break

        # 6. Preacher of the Schism — lifelink, creates vampire on attack
        for c in list(gs.zones.hand):
            if c.name == PREACHER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Preacher: lifelink, makes vampire tokens on attack")
                break

        # 7. Calix — planeswalker, enchantment synergy
        for c in list(gs.zones.hand):
            if c.name == CALIX and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Calix deployed: enchantment synergy engine")
                break

        # 8. Zoraline, Enduring Innocence, remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _use_removal(self, gs: GameState, opponent: GameState):
        """Use removal spells on opponent's creatures."""
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures:
            return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2:
            return

        # Get Lost — {1}{W}, destroys any nonland permanent
        for c in list(gs.zones.hand):
            if c.name == GET_LOST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Get Lost -> destroy {target.name}")
                return

        # Anoint with Affliction — {1}{B}, exiles creature with MV 3 or less
        if getattr(target, 'cmc', 0) <= 3:
            for c in list(gs.zones.hand):
                if c.name == ANOINT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                    gs._log(f"  Anoint with Affliction -> exile {target.name}")
                    return

        # Final Vengeance — {B}, destroys creature (sacrifice a creature + discard)
        my_creatures = [x for x in gs.zones.battlefield
                        if x.has(Tag.CREATURE) and not x.is_land()]
        hand_cards = [x for x in gs.zones.hand if x.name != FINAL_VENGEANCE]
        if my_creatures and hand_cards:
            for c in list(gs.zones.hand):
                if c.name == FINAL_VENGEANCE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    # Sacrifice weakest creature
                    sac = min(my_creatures, key=lambda x: safe_power(x))
                    # Discard cheapest card
                    discard = min(hand_cards, key=lambda x: getattr(x, 'cmc', 0))
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if sac in gs.zones.battlefield:
                        gs.zones.battlefield.remove(sac)
                        gs.zones.graveyard.append(sac)
                    if discard in gs.zones.hand:
                        gs.zones.hand.remove(discard)
                        gs.zones.graveyard.append(discard)
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                    gs._log(f"  Final Vengeance -> destroy {target.name} (sac {sac.name}, discard {discard.name})")
                    return

        # Exorcise — {1}{W}, exiles enchantment or creature token
        is_token = getattr(target, 'is_token', False)
        is_enchantment = target.has(Tag.ENCHANTMENT) if hasattr(target, 'has') else False
        if is_token or is_enchantment:
            for c in list(gs.zones.hand):
                if c.name == EXORCISE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.noncreature_spells_this_turn += 1
                    if target in opponent.zones.battlefield:
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.exile.append(target)
                    gs._log(f"  Exorcise -> exile {target.name}")
                    return

    def _scavenger_pump(self, gs):
        """Optimistic Scavenger gets +1/+1 for each enchantment entering."""
        for c in gs.zones.battlefield:
            if c.name == OPTIMISTIC_SCAVENGER:
                self._scavenger_counters += 1
                try:
                    c.power = str(int(c.power) + 1)
                    c.toughness = str(int(c.toughness) + 1)
                except (ValueError, TypeError):
                    pass
                gs._log(f"  Scavenger trigger: now {c.power}/{c.toughness}")

    def declare_attackers(self, gs, opponent):
        """Attack with everything — aggro deck wants to apply pressure."""
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if not c.has(Tag.CREATURE): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            attackers.append(c)

        # Preacher attack trigger: create 1/1 vampire token (simulated as +1 damage)
        for a in attackers:
            if a.name == PREACHER:
                gs.life += 1  # lifelink on Preacher
                gs._log(f"  Preacher attacks: lifelink + vampire token")

        return attackers

    def declare_blockers(self, gs, opp, attackers):
        """Block aggressively — Glissa with first strike + deathtouch kills anything."""
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)]
        if not blockers: return assignments

        # Glissa blocks anything and kills it (first strike + deathtouch)
        glissa = [b for b in blockers if b.name == GLISSA_SUNSLAYER]
        if glissa:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [glissa[0]]
                return assignments

        # Otherwise block if favorable trade
        biggest = max(attackers, key=lambda c: safe_power(c))
        if safe_power(biggest) >= 3:
            best = max(blockers, key=lambda c: safe_toughness(c))
            if safe_toughness(best) > safe_power(biggest):
                assignments[id(biggest)] = [best]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'heath' in n or 'flats' in n or 'catacombs' in n or 'rainforest' in n: return 0
            if 'garden' in n or 'grave' in n or 'crypt' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
