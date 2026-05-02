"""
apl/grixis_reanimator_match.py — Grixis Reanimator (Modern)

Combo: Unmarked Grave (nonlegendary to GY) + Persist (reanimate) → Abhorrent Oculus.
       Hard-cast Archon of Cruelty if mana allows.
Key:
- Unmarked Grave: Oracle "Search library for nonlegendary card, put in GY, shuffle."
- Persist: Oracle "Return target nonlegendary creature card from GY to battlefield
           with a -1/-1 counter." Bypasses Oculus's cast-cost exile requirement.
- Archon ETB/attack: opponent sacs permanent + discards + loses 3 life; we draw + gain 3.
- Abhorrent Oculus: 2/2 flying. At each opponent's upkeep: manifest dread.

Kill distribution (from format_config.py): T2 15%, T3 45%, T4 30%, T5 10%.
As opponent: routed to ComboKillSampler via format_config 'combo' set.
"""
from apl.match_apl import MatchAPL
from data.card import Tag
from engine.match_state import safe_power

ARCHON = "Archon of Cruelty"
OCULUS = "Abhorrent Oculus"
GRAVE = "Unmarked Grave"
PERSIST = "Persist"
THOUGHTSEIZE = "Thoughtseize"

REANIMATE_TARGETS = {OCULUS}


def _is_legendary(card):
    return 'Legendary' in (getattr(card, 'type_line', '') or '')


class GrixisReanimatorMatchAPL(MatchAPL):
    name = "Grixis Reanimator"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        has_tutor = any(c.name == GRAVE for c in hand)
        has_reanimate = any(c.name == PERSIST for c in hand)
        has_target = any(c.name in REANIMATE_TARGETS for c in hand)
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0: return False
        if (has_tutor or has_reanimate) and lands >= 1: return True
        if has_target and lands >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        high_cmc = sorted([c for c in hand if not c.is_land()],
                          key=lambda c: -getattr(c, 'cmc', 0))
        lands = [c for c in hand if c.is_land()]
        return (lands[3:] + high_cmc)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Thoughtseize ({B}) — T1/T2 disruption
        # Oracle: "Target player reveals hand. You choose nonland card, they discard it.
        #          You lose 2 life."
        if opponent and gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.life -= 2  # oracle: you lose 2 life
                    if opponent.zones.hand:
                        best = max(opponent.zones.hand,
                                   key=lambda x: getattr(x, 'cmc', 0))
                        opponent.zones.hand.remove(best)
                        opponent.zones.graveyard.append(best)
                        gs._log(f"  Thoughtseize: discard {best.name} (-2 life)")
                    break

        # 2. Unmarked Grave ({1}{B}) — put best nonlegendary creature in GY
        # Oracle: "Search your library for a nonlegendary card, put it in your
        #          graveyard, then shuffle."
        gy_has_nl_creature = any(
            c.has(Tag.CREATURE) and not _is_legendary(c) for c in gs.zones.graveyard
        )
        if not gy_has_nl_creature:
            for c in list(gs.zones.hand):
                if c.name == GRAVE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    nl_creatures = [x for x in gs.zones.library
                                    if x.has(Tag.CREATURE) and not _is_legendary(x)]
                    if nl_creatures:
                        tgt = max(nl_creatures, key=lambda x: getattr(x, 'cmc', 0))
                        gs.zones.library.remove(tgt)
                        gs.zones.graveyard.append(tgt)
                        gs._log(f"  Unmarked Grave: put {tgt.name} in GY")
                    break

        # 3. Persist ({1}{B}) — reanimate nonlegendary creature from GY
        # Oracle: "Return target nonlegendary creature card from your graveyard to the
        #          battlefield with a -1/-1 counter on it."
        # Key: bypasses Abhorrent Oculus's additional cast cost (exile 6 from GY).
        gy_targets = [c for c in gs.zones.graveyard
                      if c.has(Tag.CREATURE) and not _is_legendary(c)]
        if gy_targets:
            for c in list(gs.zones.hand):
                if c.name == PERSIST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    tgt = max(gy_targets, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.graveyard.remove(tgt)
                    gs.zones.battlefield.append(tgt)
                    tgt.turn_entered = gs.turn
                    tgt.summoning_sickness = True
                    # -1/-1 counter reduces P/T by 1 each
                    try:
                        tgt.power = str(max(0, int(tgt.power) - 1))
                        tgt.toughness = str(max(0, int(tgt.toughness) - 1))
                    except (ValueError, TypeError):
                        pass
                    self._trigger_etb(gs, opponent, tgt)
                    gs._log(f"  Persist: reanimate {tgt.name} (with -1/-1 counter)")
                    break

        # 4. Hard-cast Archon of Cruelty ({6}{B}{B}) — 8 mana, late game threat
        for c in list(gs.zones.hand):
            if c.name == ARCHON and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._trigger_etb(gs, opponent, c)
                break

        # 5. Abhorrent Oculus ({2}{U}) direct cast — requires exiling 6 from GY
        for c in list(gs.zones.hand):
            if c.name == OCULUS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                exile_pool = [x for x in gs.zones.graveyard][:6]
                if len(exile_pool) >= 6:
                    for ex in exile_pool:
                        gs.zones.graveyard.remove(ex)
                        gs.zones.exile.append(ex)
                    gs.cast_spell(c)
                    gs._log(f"  Oculus: direct cast (exile 6 from GY)")
                break

        # 6. Fill curve
        self._cast_all_castable(gs)

    def _trigger_etb(self, gs, opponent, card):
        """Archon of Cruelty ETB: opponent sacs + discards + loses 3; we draw + gain 3.
        Oracle: 'Whenever this creature enters or attacks, target opponent sacrifices a
        creature or planeswalker of their choice, discards a card, and loses 3 life.
        You draw a card and gain 3 life.'
        Note: opponent 'chooses' — we model as they keep best, sac weakest.
        """
        if card.name != ARCHON or not opponent:
            return
        opp_perms = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]
        if opp_perms:
            sac = min(opp_perms, key=lambda x: safe_power(x))
            opponent.zones.battlefield.remove(sac)
            opponent.zones.graveyard.append(sac)
        if opponent.zones.hand:
            discard = min(opponent.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
            opponent.zones.hand.remove(discard)
            opponent.zones.graveyard.append(discard)
        opponent.life -= 3
        gs.zones.draw(1)
        gs.life += 3
        gs._log(f"  Archon ETB: opp sac+discard-3life, we draw+3life")

    def declare_attackers(self, gs, opponent):
        attackers = [c for c in gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and not getattr(c, 'summoning_sickness', False)
                     and not getattr(c, 'tapped', False)]
        # Archon attack trigger fires same as ETB
        if opponent:
            for c in attackers:
                if c.name == ARCHON:
                    self._trigger_etb(gs, opponent, c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'strand' in n or 'flats' in n: return 0
            if 'grave' in n or 'shrine' in n or 'fountain' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
