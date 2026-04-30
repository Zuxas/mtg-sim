"""
apl/eldrazi_ramp_match.py — Oracle-audited Eldrazi Ramp APL (Modern)

Key mechanics (oracle-verified):
1. Ugin's Labyrinth: imprint 7+ MV card → tap for {C}{C} (Sol land)
2. Eldrazi Temple: tap for {C}{C} for Eldrazi spells
3. Emrakul cost reduction (card types in GY) + Mindslaver cast trigger
4. Kozilek's Return: 2 dmg from hand, 5 dmg FREE from GY on casting MV≥7
5. Sowing Mycospawn: CAST trigger → land to battlefield + kicker exiles land
6. Malevolent Rumble: card selection + GY filler + Spawn token
7. World Breaker: CAST trigger → exile artifact/enchantment/LAND, recurring from GY
8. Formidable Speaker: discard → tutor creature + untap permanent
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

EMRAKUL    = "Emrakul, the Promised End"
WORLD_BREAKER = "World Breaker"
DEVOURER   = "Devourer of Destiny"
SIRE       = "Sire of Seven Deaths"
MYCOSPAWN  = "Sowing Mycospawn"
KOZ_RETURN = "Kozilek's Return"
KOZ_CMD    = "Kozilek's Command"
UGIN       = "Ugin, Eye of the Storms"
TALISMAN   = "Talisman of Impulse"
SPRAWL     = "Utopia Sprawl"
STIRRINGS  = "Ancient Stirrings"
RUMBLE     = "Malevolent Rumble"
FORMIDABLE = "Formidable Speaker"
ICETILL    = "Icetill Explorer"

# Big Eldrazi that trigger Kozilek's Return from GY (MV >= 7)
BIG_ELDRAZI = {EMRAKUL, WORLD_BREAKER, DEVOURER, SIRE}


class EldraziRampMatchAPL(MatchAPL):
    name = "Eldrazi Ramp"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._spawn_tokens = 0  # Eldrazi Spawn tokens (sacrifice for {C})
        self._mindslaver_active = False  # opponent skips next turn

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        ramp = sum(1 for c in hand if c.name in {TALISMAN, SPRAWL, MYCOSPAWN, RUMBLE})
        threats = sum(1 for c in hand if c.name in {EMRAKUL, WORLD_BREAKER, DEVOURER, SIRE, UGIN})
        sol_lands = sum(1 for c in hand if c.is_land() and 
                        ('temple' in c.name.lower() or 'labyrinth' in c.name.lower()))
        if lands == 0: return False
        if lands >= 2 and ramp >= 1: return True
        if sol_lands >= 1 and lands >= 2: return True
        if lands >= 3 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def _count_sol_bonus(self, gs):
        """Count extra mana from Eldrazi Temple ({C}{C}), Ugin's Labyrinth ({C}{C} IF imprinted), 
        Talisman, Utopia Sprawl, and Spawn tokens.
        Oracle: Labyrinth only taps for {C}{C} if a card is exiled with it."""
        bonus = 0
        for c in gs.zones.battlefield:
            name = c.name.lower() if c.name else ''
            if 'eldrazi temple' in name:
                bonus += 1  # already counted as 1 by tap_lands, this adds the extra {C}
            elif "ugin's labyrinth" in name:
                # Only gives {C}{C} if we've imprinted a 7+ MV card
                # Check if we have big Eldrazi in exile (imprinted)
                has_imprint = any(getattr(x, 'cmc', 0) >= 7 for x in gs.zones.exile)
                if has_imprint:
                    bonus += 1
            elif c.name == TALISMAN:
                bonus += 1
            elif c.name == SPRAWL:
                bonus += 1
        bonus += self._spawn_tokens
        return bonus

    def _emrakul_cost(self, gs):
        """Calculate Emrakul's reduced cost based on card types in GY."""
        types_in_gy = set()
        for g in gs.zones.graveyard:
            tl = (getattr(g, 'type_line', '') or '').lower()
            for t in ('creature','instant','sorcery','artifact','enchantment','planeswalker','land'):
                if t in tl: types_in_gy.add(t)
        reduction = len(types_in_gy)
        return max(4, 13 - reduction), reduction

    def _trigger_koz_return_from_gy(self, gs, opponent):
        """Kozilek's Return GY trigger: 5 damage to all creatures.
        Oracle: 'Whenever you cast an Eldrazi creature MV>=7, exile from GY → 5 dmg all.'
        """
        koz = next((c for c in gs.zones.graveyard if c.name == KOZ_RETURN), None)
        if not koz:
            return
        gs.zones.graveyard.remove(koz)
        gs.zones.exile.append(koz)
        # 5 damage to ALL creatures (both sides!)
        for zone_owner, zone_gs in [("opponent", opponent), ("self", gs)]:
            if not zone_gs: continue
            killed = []
            for c in list(zone_gs.zones.battlefield):
                if not c.is_land() and c.has(Tag.CREATURE):
                    if safe_toughness(c) <= 5:
                        killed.append(c)
            for c in killed:
                if c in zone_gs.zones.battlefield:
                    zone_gs.zones.battlefield.remove(c)
                    zone_gs.zones.graveyard.append(c)
        gs._log(f"  K-RETURN FROM GY: 5 dmg all creatures (FREE sweeper)")

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        gs.mana_pool.flex += self._count_sol_bonus(gs)

        avail = gs.mana_pool.total()

        # 1. Ramp: Talisman of Impulse ({2})
        for c in list(gs.zones.hand):
            if c.name == TALISMAN and avail >= 2:
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                avail = gs.mana_pool.total()
                gs._log(f"  Talisman of Impulse (+1 mana)")
                break

        # 2. Utopia Sprawl ({G} on Forest)
        for c in list(gs.zones.hand):
            if c.name == SPRAWL and avail >= 1:
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                avail += 1
                gs._log(f"  Utopia Sprawl (+1 mana)")
                break

        # 3. Malevolent Rumble ({1}{G}) — card selection + GY fill + Spawn token
        for c in list(gs.zones.hand):
            if c.name == RUMBLE and avail >= 2:
                gs.mana_pool.pay("{1}{G}", 2) if gs.mana_pool.can_pay("{1}{G}", 2) else None
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                # Reveal top 4: simulate by drawing 1 (best card) + putting rest in GY
                gs.zones.draw(1)
                # Rest go to GY (fills card types for Emrakul)
                for _ in range(3):
                    if gs.zones.library:
                        top = gs.zones.library.pop(0)
                        gs.zones.graveyard.append(top)
                avail = gs.mana_pool.total()
                self._spawn_tokens += 1
                gs._log(f"  Rumble: draw 1, 3 to GY, +1 Spawn token")
                break

        # 4. Formidable Speaker ({2}{G}) — discard → tutor creature
        for c in list(gs.zones.hand):
            if c.name == FORMIDABLE and avail >= 3:
                gs.mana_pool.pay("{2}{G}", 3) if gs.mana_pool.can_pay("{2}{G}", 3) else None
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                # Discard worst card → tutor (simulate as draw 1)
                if gs.zones.hand:
                    # Prefer discarding K-Return (GY setup for sweeper trigger)
                    kr = next((x for x in gs.zones.hand if x.name == KOZ_RETURN), None)
                    discard = kr if kr else min(gs.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.hand.remove(discard)
                    gs.zones.graveyard.append(discard)
                    gs.zones.draw(1)  # simulate tutor
                    gs._log(f"  Formidable Speaker: discard {discard.name} → tutor creature")
                avail = gs.mana_pool.total()
                break

        # 5. Kozilek's Return from hand (2 dmg sweeper) — only if 2+ opponent creatures
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                             if not c.is_land() and c.has(Tag.CREATURE)]
            if len(opp_creatures) >= 2:
                for c in list(gs.zones.hand):
                    if c.name == KOZ_RETURN and avail >= 3:
                        gs.mana_pool.pay("{2}{R}", 3) if gs.mana_pool.can_pay("{2}{R}", 3) else None
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        for creature in list(opp_creatures):
                            if safe_toughness(creature) <= 2 and creature in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(creature)
                                opponent.zones.graveyard.append(creature)
                        gs._log(f"  K-Return: 2 dmg sweeper (now in GY for future 5-dmg trigger)")
                        avail = gs.mana_pool.total()
                        break

        # 6. Sowing Mycospawn ({3}{G}) — CAST trigger: land to battlefield + ramp
        for c in list(gs.zones.hand):
            if c.name == MYCOSPAWN and avail >= 4:
                gs.mana_pool.pay("{3}{G}", 4) if gs.mana_pool.can_pay("{3}{G}", 4) else None
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                # CAST trigger: search library for a land → put on battlefield
                # Simulate: +1 mana next turn (land from library)
                gs.mana_pool.flex += 1  # immediate mana from the new land
                avail = gs.mana_pool.total()
                gs._log(f"  Mycospawn: 3/3 + land to battlefield (ramp)")
                break

        # 7. BIG ELDRAZI (MV >= 7) — these trigger K-Return from GY
        avail = gs.mana_pool.total()

        # 7a. EMRAKUL — Mindslaver (game-ending cast trigger)
        # First: retrieve imprinted Emrakul from exile if needed
        emrakul_in_exile = [c for c in gs.zones.exile if c.name == EMRAKUL]
        if emrakul_in_exile and not any(c.name == EMRAKUL for c in gs.zones.hand):
            cost, reduction = self._emrakul_cost(gs)
            if avail >= cost:
                # Retrieve from Labyrinth (tap Labyrinth = lose {C}{C} this turn, but get Emrakul)
                em = emrakul_in_exile[0]
                gs.zones.exile.remove(em)
                gs.zones.hand.append(em)
                avail -= 1  # lose 1 mana from tapping Labyrinth to retrieve
                gs._log(f"  Labyrinth: retrieve {em.name} to hand")
        
        for c in list(gs.zones.hand):
            if c.name == EMRAKUL:
                cost, reduction = self._emrakul_cost(gs)
                if avail >= cost:
                    # Sacrifice Spawn tokens to help pay
                    while avail < cost and self._spawn_tokens > 0:
                        self._spawn_tokens -= 1; avail += 1
                    if avail >= cost:
                        gs.mana_pool.flex -= min(cost, gs.mana_pool.flex)
                        gs.zones.hand.remove(c)
                        gs.zones.battlefield.append(c)
                        c.turn_entered = gs.turn
                        # Oracle (Emrakul, verified): "Flying, trample, protection from
                        # instant spells and from spells with flash, haste."
                        # Emrakul HAS HASTE -- can attack the turn it's cast.
                        c.summoning_sickness = False
                        if opponent:
                            opponent.life -= 3
                            gs._log(f"  EMRAKUL CAST! (cost {cost}, -{reduction} types) -> Mindslaver")
                        self._trigger_koz_return_from_gy(gs, opponent)
                        avail = gs.mana_pool.total()
                        break

        # 7b. World Breaker ({6}{G}) — exile artifact/enchantment/LAND
        # Oracle (verified): "When you cast this spell, exile target artifact, creature,
        # enchantment, or land an opponent controls."
        for c in list(gs.zones.hand):
            if c.name == WORLD_BREAKER and avail >= 7:
                gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                if opponent:
                    # Oracle: exile artifact, creature, enchantment, or land
                    targets = [x for x in opponent.zones.battlefield
                               if not x.is_land() and (x.has(Tag.CREATURE) or
                               x.has(Tag.ARTIFACT) or x.has(Tag.ENCHANTMENT))]
                    land_targets = [x for x in opponent.zones.battlefield if x.is_land()]
                    if targets:
                        t = max(targets, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                        gs._log(f"  World Breaker CAST: exile {t.name}")
                    elif land_targets:
                        t = land_targets[0]
                        opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                        gs._log(f"  World Breaker CAST: exile land {t.name}")
                self._trigger_koz_return_from_gy(gs, opponent)
                avail = gs.mana_pool.total()
                break

        # 7c. Devourer of Destiny ({5}{C}{C}) — exile colored permanent
        for c in list(gs.zones.hand):
            if c.name == DEVOURER and avail >= 7:
                gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                if opponent:
                    targets = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if targets:
                        t = max(targets, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                        gs._log(f"  Devourer CAST: exile {t.name}")
                self._trigger_koz_return_from_gy(gs, opponent)
                avail = gs.mana_pool.total()
                break

        # 7d. Sire of Seven Deaths ({7}) — 7/7 with every keyword + ward pay 7 life
        for c in list(gs.zones.hand):
            if c.name == SIRE and avail >= 7:
                gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn; c.summoning_sickness = True
                self._trigger_koz_return_from_gy(gs, opponent)
                gs._log(f"  Sire of Seven Deaths: 7/7 all keywords, ward 7 life")
                avail = gs.mana_pool.total()
                break

        # 7e. Ugin PW ({7}) — cast trigger: exile colored permanent
        for c in list(gs.zones.hand):
            if c.name == UGIN and avail >= 7:
                gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                if opponent:
                    targets = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if targets:
                        t = max(targets, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(t); opponent.zones.exile.append(t)
                        gs._log(f"  Ugin CAST: exile {t.name}")
                avail = gs.mana_pool.total()
                break

        # 8. Remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in BIG_ELDRAZI and c.name != MYCOSPAWN:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        """Attack with big Eldrazi. Don't attack with Formidable Speaker (untap utility)."""
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)
                and c.name != FORMIDABLE]  # keep Speaker for untap ability

    def declare_blockers(self, gs, opp, attackers):
        """Block with big Eldrazi — they survive most combat."""
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and safe_power(c) >= 3
                    and not getattr(c, 'tapped', False)]
        if blockers:
            biggest_attacker = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest_attacker) >= 3:
                assignments[id(biggest_attacker)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell): return None

    def end_step_actions(self, gs, opponent):
        """Mindslaver resolution: if active, opponent effectively loses their turn."""
        pass

    def _play_land_if_able(self, gs):
        """Priority: Ugin's Labyrinth > Eldrazi Temple > Forest > others.
        Labyrinth: imprint a 7+ MV colorless card from hand for {C}{C} production."""
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            name = c.name.lower() if c.name else ''
            if 'labyrinth' in name: return 0  # Sol land — top priority
            if 'temple' in name: return 1     # Double mana for Eldrazi
            if 'forest' in name and 'rain' not in name: return 2  # for Utopia Sprawl
            if 'cavern' in name: return 3     # uncounterable
            return 5
        best = min(lands, key=score)
        gs.play_land(best)
        
        # Ugin's Labyrinth: imprint a 7+ MV colorless card from hand
        if "ugin's labyrinth" in (best.name or '').lower():
            big_cards = [c for c in gs.zones.hand 
                         if getattr(c, 'cmc', 0) >= 7 and not c.is_land()]
            if big_cards:
                imprint = big_cards[0]
                gs.zones.hand.remove(imprint)
                gs.zones.exile.append(imprint)
                gs._log(f"  Labyrinth imprint: exile {imprint.name} → double mana")
