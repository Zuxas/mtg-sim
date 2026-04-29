"""
apl/jeskai_blink_match.py — Oracle-audited Jeskai Blink APL (Modern)

Playbook engines (from Team Resolve):
A. Phelia Attack Loop — exile own ETB creature on attack, re-enter at end step
B. Solitude + Ephemerate — free evoke exile + blink for 2-3 creature exiles
C. Teferi Lock — opponents sorcery-speed only, -3 bounce+draw

Key oracle mechanics:
- Phelia: Flash, attack trigger exiles nonland permanent, returns at end step
- Solitude: Evoke (exile white card), ETB exile creature, Lifelink
- Ephemerate: {W} blink + Rebound (free blink next upkeep)
- Phlage: hardcast 3 dmg sacrifice, escape {R}{R}{W}{W}+exile5 = permanent 6/6
- Consign: {U} counter triggered ability or colorless spell, Replicate {1}
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RAGAVAN    = "Ragavan, Nimble Pilferer"
PHELIA     = "Phelia, Exuberant Shepherd"
PHLAGE     = "Phlage, Titan of Fire's Fury"
SOLITUDE   = "Solitude"
QUANTUM    = "Quantum Riddler"
CASEY      = "Casey Jones, Vigilante"
CONSIGN    = "Consign to Memory"
GALVANIC   = "Galvanic Discharge"
PRISMATIC  = "Prismatic Ending"
EPHEMERATE = "Ephemerate"
TEFERI     = "Teferi, Time Raveler"
WRATH      = "Wrath of the Skies"
MARCH      = "March of Otherworldly Light"
FABLE      = "Fable of the Mirror-Breaker"

ETB_CREATURES = {SOLITUDE, PHLAGE, QUANTUM, CASEY}
REMOVAL = {SOLITUDE, GALVANIC, PRISMATIC, CONSIGN, MARCH}

# Matchup detection: cards that indicate opponent archetype
PROWESS_INDICATORS = {"Monastery Swiftspear", "Dragon's Rage Channeler", "Slickshot Show-Off",
                       "Cori-Steel Cutter", "Lava Dart"}
BOROS_INDICATORS = {"Guide of Souls", "Ocelot Pride", "Goblin Bombardment",
                     "Ajani, Nacatl Pariah", "Phlage, Titan of Fire's Fury"}
COMBO_INDICATORS = {"Amulet of Vigor", "Primeval Titan", "Neoform", "Living End",
                     "Grinding Station", "Underworld Breach"}
CONTROL_INDICATORS = {"Counterspell", "Supreme Verdict", "Teferi, Hero of Dominaria",
                       "Snapcaster Mage"}


class JeskaiBlinkMatchAPL(MatchAPL):
    name = "Jeskai Blink"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._phelia_counters = 0
        self._ephemerate_rebound = False
        self._energy = 0  # energy counter tracking
        # Casey discard-3-next-upkeep is INT (number of pending discard-3
        # triggers, since multiple Casey ETBs from blinks accumulate per
        # oracle "at your next upkeep, discard three cards"). Pre-2026-04-29
        # fix: was boolean — multi-blink Casey only fired one discard.
        self._casey_discards_pending = 0
        # Phelia attack-trigger exile creatures that need to return at the
        # next end step. Oracle: "Return that card to the battlefield under
        # its owner's control at the beginning of the next end step."
        # Pre-2026-04-29 fix: opp creatures Phelia-exiled stayed permanently
        # exiled (log claimed "returns at end step" but no return logic).
        self._phelia_exile_returns = []  # list of (card, owner)
        self._treasures = 0  # from Ragavan combat damage
        self._role = "beatdown"  # beatdown, tempo_control, or grind

    def _detect_role(self, opponent):
        """Detect role from playbook: Beatdown vs Tempo Control vs Grind.
        Playbook: 'Against aggro you're tempo control. Against combo/control, race.'
        """
        if not opponent:
            return "beatdown"
        opp_names = {c.name for c in opponent.zones.battlefield if not c.is_land()}
        if opp_names & PROWESS_INDICATORS:
            return "tempo_control"  # stabilize first, then close
        if opp_names & COMBO_INDICATORS:
            return "beatdown"  # race their combo
        if opp_names & CONTROL_INDICATORS:
            return "grind"  # grind value, don't overextend
        if opp_names & BOROS_INDICATORS:
            return "tempo_control"  # respect their burn clock
        return "beatdown"  # default: press advantage

    def keep(self, hand, mulligans, on_play):
        """Matchup-aware mulligan from playbook.
        vs Aggro: need interaction + threat (Solitude/Galvanic + Phelia)
        vs Control: need threats that dodge counters (Ragavan, plotted creatures)
        vs Combo: need clock + disruption (Consign + creatures)
        """
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in (RAGAVAN, PHELIA, QUANTUM, CASEY, SOLITUDE))
        interaction = sum(1 for c in hand if c.name in REMOVAL or c.name == EPHEMERATE)
        blink_package = sum(1 for c in hand if c.name in (EPHEMERATE, PHELIA))
        phlage = sum(1 for c in hand if c.name == PHLAGE)
        
        if lands == 0: return False
        if lands > 5: return False
        
        # Ideal: 2-3 lands, threat, interaction, optional blink piece
        if lands >= 2 and threats >= 1 and interaction >= 1: return True
        # Solitude + Ephemerate is a snap keep (2-for-0 removal)
        if any(c.name == SOLITUDE for c in hand) and any(c.name == EPHEMERATE for c in hand):
            if lands >= 2: return True
        # Phelia + ETB creature is a snap keep (value engine)
        if any(c.name == PHELIA for c in hand) and any(c.name in ETB_CREATURES for c in hand):
            if lands >= 2: return True
        # Two threats + lands is keepable
        if threats >= 2 and lands >= 2: return True
        # Phlage in hand with lands (guaranteed value: 3 dmg + 3 life even if answered)
        if phlage >= 1 and lands >= 3 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        
        # Detect role for strategic decisions
        self._role = self._detect_role(opponent)
        
        # Casey Jones: discard 3 random at upkeep (deferred from last turn).
        # Multiple Casey ETBs in same prior turn (cast + blinks) accumulate
        # — N pending casts means N * 3 discards total at next upkeep.
        total_discards = self._casey_discards_pending * 3
        self._casey_discards_pending = 0
        discarded = 0
        for _ in range(total_discards):
            if gs.zones.hand:
                # Discard worst card (simulate "random" as lowest value)
                worst = min(gs.zones.hand, key=lambda c: self._card_value(c))
                gs.zones.hand.remove(worst)
                gs.zones.graveyard.append(worst)
                discarded += 1
        if discarded:
            gs._log(f"  Casey Jones upkeep: discard {discarded} cards")

        # Ephemerate Rebound — free blink at upkeep
        if self._ephemerate_rebound:
            self._ephemerate_rebound = False
            self._blink_best_etb(gs, opponent)
            gs._log(f"  Ephemerate REBOUND: free blink")

        avail = gs.mana_pool.total()

        # 1. SOLITUDE EVOKE — free creature exile (pitch white card)
        if opponent:
            opp_threats = [c for c in opponent.zones.battlefield
                          if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 2]
            if opp_threats:
                for c in list(gs.zones.hand):
                    if c.name == SOLITUDE:
                        # Solitude evoke requires pitching a WHITE card from hand
                        # (oracle: "Evoke—Exile a white card from your hand").
                        # Pre-2026-04-29 fix: this picked any non-land which
                        # frequently evoked illegally with Galvanic / Consign /
                        # Ragavan as "pitch" when no white card was available.
                        white_cards = [x for x in gs.zones.hand
                                      if x != c and not x.is_land()
                                      and 'W' in (getattr(x, 'colors', []) or [])]
                        if white_cards:
                            pitch = white_cards[0]
                            gs.zones.hand.remove(pitch)
                            gs.zones.exile.append(pitch)
                            gs.zones.hand.remove(c)
                            # Solitude enters → ETB exile their best creature
                            target = max(opp_threats, key=lambda x: safe_power(x))
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.exile.append(target)
                                # Opponent gains life = target's power (oracle)
                                opponent.life += safe_power(target)
                            gs._log(f"  Solitude EVOKE: exile {target.name} (pitched {pitch.name})")
                            # Solitude dies (evoke sacrifice) → goes to GY
                            gs.zones.graveyard.append(c)
                            # But if we have Ephemerate, blink Solitude BEFORE it dies!
                            eph = next((x for x in gs.zones.hand if x.name == EPHEMERATE), None)
                            if eph and gs.mana_pool.can_cast(eph.mana_cost, eph.cmc):
                                # Pay Ephemerate's {W} (pre-2026-04-29 fix:
                                # this was a free cast — only checked avail >= 1
                                # without calling mana_pool.pay, so Ephemerate
                                # in the Solitude+Ephemerate stack cost no mana).
                                gs.mana_pool.pay(eph.mana_cost, eph.cmc)
                                gs.zones.hand.remove(eph)
                                gs.zones.exile.append(eph)  # rebound exile
                                self._ephemerate_rebound = True
                                # Solitude re-enters → exile ANOTHER creature
                                gs.zones.graveyard.remove(c)
                                gs.zones.battlefield.append(c)
                                c.turn_entered = gs.turn; c.summoning_sickness = True
                                opp_threats2 = [x for x in opponent.zones.battlefield
                                               if not x.is_land() and x.has(Tag.CREATURE)]
                                if opp_threats2:
                                    t2 = max(opp_threats2, key=lambda x: safe_power(x))
                                    opponent.zones.battlefield.remove(t2)
                                    opponent.zones.exile.append(t2)
                                    opponent.life += safe_power(t2)
                                    gs._log(f"  Ephemerate Solitude: exile {t2.name} (Solitude STAYS, rebound next turn)")
                            break

        avail = gs.mana_pool.total()

        # 2. Galvanic Discharge — energy-based removal
        if opponent:
            opp_creatures = [c for c in opponent.zones.battlefield
                            if not c.is_land() and c.has(Tag.CREATURE)]
            if opp_creatures:
                for c in list(gs.zones.hand):
                    if c.name == GALVANIC and avail >= 1:
                        gs.mana_pool.pay("{R}", 1) if gs.mana_pool.can_pay("{R}", 1) else None
                        gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                        gs.energy = getattr(gs, 'energy', 0) + 3
                        target = max(opp_creatures, key=lambda x: safe_power(x))
                        energy_to_spend = min(gs.energy, safe_toughness(target))
                        gs.energy -= energy_to_spend
                        if energy_to_spend >= safe_toughness(target):
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.graveyard.append(target)
                            gs._log(f"  Discharge: kill {target.name} (spent {energy_to_spend}E)")
                        avail = gs.mana_pool.total()
                        break

        # 3. Deploy creatures: Ragavan (haste T1), Phelia (flash 2/2)
        for name in (RAGAVAN, PHELIA):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == CASEY:
                        self._draw(gs, 3)
                        gs._log(f"  Casey Jones ETB: draw 3 (discard 3 next upkeep)")
                    break

        # 4. Quantum Riddler ({3}{U}{U}) — 4/6 flying, ETB draw 1
        for c in list(gs.zones.hand):
            if c.name == QUANTUM and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._draw(gs, 1)
                gs._log(f"  Quantum Riddler: 4/6 flying, draw 1")
                break

        # 5. Casey Jones ({1}{R}{R}) — ETB draw 3, schedule discard 3 next upkeep
        # Pre-2026-04-29 fix: this site did not increment
        # _casey_discards_pending — Casey cast here gave free draw 3 with no
        # discard penalty.
        for c in list(gs.zones.hand):
            if c.name == CASEY and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                self._draw(gs, 3)
                self._casey_discards_pending += 1
                gs._log(f"  Casey Jones: draw 3 (pending discards={self._casey_discards_pending})")
                break

        # 6. Teferi ({1}{W}{U}) — opponents sorcery-speed, -3 bounce+draw
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_nonlands = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.hand.append(target)
                        gs._log(f"  Teferi -3: bounce {target.name} + draw")
                self._draw(gs, 1)
                break

        # 7. Phlage — hardcast as removal OR escape from GY as finisher
        # Escape: {R}{R}{W}{W} + exile 5 = permanent 6/6
        gy_phlages = [c for c in gs.zones.graveyard if c.name == PHLAGE]
        other_gy = len(gs.zones.graveyard) - len(gy_phlages)
        if gy_phlages and other_gy >= 5 and gs.mana_pool.total() >= 4:
            phlage = gy_phlages[0]
            for _ in range(5):
                non_phlage = [x for x in gs.zones.graveyard if x.name != PHLAGE]
                if non_phlage:
                    gs.zones.graveyard.remove(non_phlage[0])
                    gs.zones.exile.append(non_phlage[0])
            gs.zones.graveyard.remove(phlage)
            gs.zones.battlefield.append(phlage)
            phlage.turn_entered = gs.turn; phlage.summoning_sickness = True
            # ETB: 3 damage + 3 life
            if opponent:
                gs.damage_dealt += 3
            gs.life += 3
            gs._log(f"  PHLAGE ESCAPE: 6/6 permanent + 3 dmg + 3 life")
        else:
            # Hardcast Phlage from hand (3 damage + 3 life, then sacrifice)
            for c in list(gs.zones.hand):
                if c.name == PHLAGE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    if opponent:
                        opp_cr = [x for x in opponent.zones.battlefield
                                 if not x.is_land() and x.has(Tag.CREATURE) and safe_toughness(x) <= 3]
                        if opp_cr:
                            t = max(opp_cr, key=lambda x: safe_power(x))
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.graveyard.append(t)
                            gs._log(f"  Phlage hardcast: kill {t.name} + 3 life (sacrifice)")
                        else:
                            gs.damage_dealt += 3
                            gs._log(f"  Phlage hardcast: 3 face + 3 life (sacrifice)")
                    else:
                        gs.damage_dealt += 3
                    gs.life += 3
                    gs.zones.graveyard.append(c)  # sacrifice → GY for escape later
                    break

        # 8. Ephemerate on ETB creature (if not used on Solitude already)
        for c in list(gs.zones.hand):
            if c.name == EPHEMERATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                self._blink_best_etb(gs, opponent)
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.exile.append(c)
                self._ephemerate_rebound = True
                gs._log(f"  Ephemerate: blink ETB creature (rebound next turn)")
                break

        # 9. Wrath of the Skies — board wipe when behind
        # Oracle: {X}{W}{W}, get X energy, pay energy to destroy MV <= energy paid
        if opponent and self._should_wrath(gs, opponent):
            for c in list(gs.zones.hand):
                if c.name == WRATH and gs.mana_pool.total() >= 3:
                    x_val = gs.mana_pool.total() - 2  # {X}{W}{W}
                    self._energy += x_val
                    energy_to_spend = min(self._energy, 3)  # usually X=1-3 is enough
                    self._energy -= energy_to_spend
                    gs.mana_pool.pay("{W}{W}", 2) if gs.mana_pool.can_pay("{W}{W}", 2) else None
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    # Destroy all creatures with MV <= energy spent (both sides!)
                    for zone_owner, zone_gs in [("opponent", opponent), ("self", gs)]:
                        killed = []
                        for cr in list(zone_gs.zones.battlefield):
                            if cr.has(Tag.CREATURE) and not cr.is_land():
                                if getattr(cr, 'cmc', 0) <= energy_to_spend:
                                    killed.append(cr)
                        for cr in killed:
                            if cr in zone_gs.zones.battlefield:
                                zone_gs.zones.battlefield.remove(cr)
                                zone_gs.zones.graveyard.append(cr)
                    gs._log(f"  Wrath of the Skies X={x_val}: destroy MV<={energy_to_spend} creatures")
                    break

        # 10. March of Otherworldly Light — exile permanent (pitch white to reduce cost)
        if opponent:
            problem_permanents = [c for c in opponent.zones.battlefield
                                 if not c.is_land() and (c.has(Tag.CREATURE) or 
                                 getattr(c, 'type_line', '') and 'enchantment' in (getattr(c, 'type_line', '') or '').lower())]
            if problem_permanents:
                for c in list(gs.zones.hand):
                    if c.name == MARCH:
                        target = max(problem_permanents, key=lambda x: safe_power(x))
                        target_mv = getattr(target, 'cmc', 0)
                        # March's oracle: "As an additional cost to cast this
                        # spell, you may exile ANY NUMBER of WHITE cards from
                        # your hand. This spell costs {2} less to cast for
                        # each card exiled this way."
                        # Pre-ce492dc: pitched any non-land (illegal).
                        # Post-ce492dc/46e6160: white-only + 2-pitch cap.
                        # Oracle audit 2026-04-29: there's NO 2-cap — "any
                        # number." Removing the cap. White-only filter stays
                        # because oracle requires WHITE cards specifically.
                        base_cost = target_mv + 1
                        white_pitch = [x for x in gs.zones.hand
                                       if x != c and not x.is_land()
                                       and 'W' in (getattr(x, 'colors', []) or [])]
                        pitch_count = min(len(white_pitch),
                                          int((base_cost - 1) // 2))
                        effective_cost = max(1, base_cost - pitch_count * 2)
                        if gs.mana_pool.total() >= effective_cost:
                            for i in range(pitch_count):
                                if white_pitch:
                                    p = white_pitch.pop(0)
                                    gs.zones.hand.remove(p); gs.zones.exile.append(p)
                            gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                            if target in opponent.zones.battlefield:
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.exile.append(target)
                            gs._log(f"  March: exile {target.name} (pitched {pitch_count})")
                        break

        # 10b. Prismatic Ending ({X}{W}) — CONVERGE removal
        # Oracle (verified Scryfall 2026-04-29):
        #   "Converge — Exile target nonland permanent if its mana value
        #    is less than or equal to the number of colors of mana spent
        #    to cast this spell."
        #
        # Pre-2026-04-29 model (db68d8a) was WRONG: it scaled cost by
        # target.cmc (cost = mv + 1), conflating mana paid with converge
        # threshold. The actual mechanic: pay {X}{W} where X is generic
        # mana, then count DISTINCT COLORS spent across the cast. Threshold
        # is the color count, not the mana amount.
        #
        # Mana model: engine ManaPool tracks W/U/B/R/G/C/flex independently
        # but has no native colors-spent-on-cast tracking. We approximate
        # by counting the distinct colors in the pool that we could plausibly
        # spend on this cast: 1 for W (mandatory pip) plus one per other
        # color we have at least 1 mana of. flex (Cavern-style any-color)
        # can stand in for any color we lack.
        # Jeskai max practical converge = 3 (W/U/R available; B/G are off-color).
        if opponent:
            opp_perms = [x for x in opponent.zones.battlefield
                         if not x.is_land()]
            if opp_perms:
                mp = gs.mana_pool
                w_pool = mp.W + mp.flex  # W pip can be paid by W or flex
                if w_pool >= 1 and mp.total() >= 1:
                    # Reserve 1 mana for the {W} pip; the rest pays {X}.
                    other_colors_have = [col for col in 'UBRG'
                                         if getattr(mp, col, 0) > 0]
                    flex_after_w = max(0, mp.flex - (1 if mp.W < 1 else 0))
                    # Each non-W color we want to spend costs 1 generic mana
                    # (paid as that color, satisfying X). Cap at Jeskai's
                    # natural color access (3 = W/U/R).
                    extra_distinct_avail = len(other_colors_have) + flex_after_w
                    max_converge = 1 + min(mp.total() - 1, extra_distinct_avail)
                    max_converge = min(max_converge, 3)
                    # Pick LARGEST target we can kill at our converge level,
                    # not smallest -- removes biggest opp threat efficiently.
                    candidates = [p for p in opp_perms
                                  if int(getattr(p, 'cmc', 99)) <= max_converge]
                    if candidates:
                        target = max(candidates,
                                     key=lambda x: int(getattr(x, 'cmc', 0)))
                        tgt_mv = int(getattr(target, 'cmc', 0))
                        # Pay {X}{W}: total mana spent = max(1, tgt_mv).
                        # The pre-fix code (db68d8a) called
                        # mp.pay("{X}{W}", tgt_mv + 1), which due to a
                        # ManaPool.pay quirk only actually deducts the {W}
                        # pip (X parses to 0 in parse_cost; cmc param is
                        # ignored when mana_cost is set). We preserve that
                        # mana-drain semantics here so this commit isolates
                        # the CONVERGE-target-selection fix from any
                        # mana-bookkeeping change. The X-drain quirk is a
                        # separate engine issue (Phase C).
                        cost_to_pay = max(1, tgt_mv)
                        for c in list(gs.zones.hand):
                            if c.name == PRISMATIC and mp.total() >= cost_to_pay:
                                try:
                                    mp.pay(c.mana_cost, cost_to_pay)
                                except Exception:
                                    continue
                                gs.zones.hand.remove(c)
                                gs.zones.graveyard.append(c)
                                opponent.zones.battlefield.remove(target)
                                opponent.zones.exile.append(target)
                                gs._log(f"  Prismatic Ending CONVERGE={tgt_mv}: "
                                        f"exile {target.name}")
                                break

        # 10c. Fable of the Mirror-Breaker ({2}{R}) — saga, always cast on curve
        # Pre-2026-04-29: never cast despite being in deck (0 references in
        # match APL). Saga chapters tick automatically via engine
        # _fable_mirror_breaker_etb. Always-cast: Ch1 loot/treasure +
        # Ch2 token + Ch3 transform = 3-mana 6-loyalty saga, premier value.
        for c in list(gs.zones.hand):
            if c.name == FABLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs._log(f"  Fable of the Mirror-Breaker: cast (saga ticks Ch1->III)")
                break

        # 11. Solitude HARDCAST ({3}{W}{W}) — when we have 5+ mana and want to keep cards
        if opponent and gs.mana_pool.total() >= 5:
            for c in list(gs.zones.hand):
                if c.name == SOLITUDE:
                    opp_cr = [x for x in opponent.zones.battlefield
                             if not x.is_land() and x.has(Tag.CREATURE)]
                    if opp_cr:
                        gs.mana_pool.pay("{3}{W}{W}", 5) if gs.mana_pool.can_pay("{3}{W}{W}", 5) else None
                        gs.zones.hand.remove(c)
                        gs.zones.battlefield.append(c)
                        c.turn_entered = gs.turn; c.summoning_sickness = True
                        target = max(opp_cr, key=lambda x: safe_power(x))
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.exile.append(target)
                            opponent.life += safe_power(target)
                        gs._log(f"  Solitude HARDCAST: exile {target.name} (3/2 lifelink stays)")
                        break

        # 12. Fill remaining mana with creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name != PHLAGE and c.name != SOLITUDE:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    # Casey Jones ETB: draw 3, defer discard 3
                    if c.name == CASEY:
                        self._draw(gs, 3)
                        self._casey_discards_pending += 1
                        gs._log(f"  Casey Jones: draw 3 (discard 3 next upkeep, pending={self._casey_discards_pending})")
                    # Quantum Riddler ETB: draw 1
                    elif c.name == QUANTUM:
                        self._draw(gs, 1)
                        gs._log(f"  Quantum Riddler: 4/6 flying, draw 1")

    def _blink_best_etb(self, gs, opponent):
        """Blink the best ETB creature on our battlefield.

        Priority: Solitude (exile creature) > Phlage (3 dmg + 3 life) >
        Quantum (draw) > Casey (draw 3). Falls through to next priority
        if the chosen card's ETB cannot fire (e.g., Solitude with no opp
        creature target). Pre-2026-04-29 fix: early-returned after
        targeting any matching name even when the blink did nothing,
        silently skipping the rest of the priority chain.
        """
        etb_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and c.name in ETB_CREATURES]
        if not etb_creatures:
            return
        for name in (SOLITUDE, PHLAGE, QUANTUM, CASEY):
            target = next((c for c in etb_creatures if c.name == name), None)
            if not target:
                continue
            blinked = False
            if name == SOLITUDE and opponent:
                opp_cr = [x for x in opponent.zones.battlefield
                         if not x.is_land() and x.has(Tag.CREATURE)]
                if opp_cr:
                    t = max(opp_cr, key=lambda x: safe_power(x))
                    opponent.zones.battlefield.remove(t)
                    opponent.zones.exile.append(t)
                    opponent.life += safe_power(t)
                    gs._log(f"  Blink Solitude: exile {t.name}")
                    blinked = True
            elif name == PHLAGE:
                if opponent:
                    gs.damage_dealt += 3
                gs.life += 3
                gs._log(f"  Blink Phlage: 3 dmg + 3 life")
                blinked = True
            elif name == QUANTUM:
                self._draw(gs, 1)
                gs._log(f"  Blink Quantum Riddler: draw 1")
                blinked = True
            elif name == CASEY:
                self._draw(gs, 3)
                self._casey_discards_pending += 1
                gs._log(f"  Blink Casey Jones: draw 3 (pending discards={self._casey_discards_pending})")
                blinked = True
            if blinked:
                return  # only return on actual blink; else try next priority

    def declare_attackers(self, gs, opponent):
        """Role-aware attack decisions + Phelia/Ragavan/Phlage triggers.
        Playbook: 'Against aggro, be selective. Against control, press hard.'
        """
        all_creatures = [c for c in gs.zones.battlefield
                        if not c.is_land() and c.has(Tag.CREATURE)
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        
        attackers = []
        
        # Role-based attack filtering
        if self._role == "tempo_control" and opponent:
            # Only attack with evasive/value creatures, hold back blockers
            opp_power = sum(safe_power(c) for c in opponent.zones.battlefield
                          if c.has(Tag.CREATURE) and not c.is_land())
            for c in all_creatures:
                p = safe_power(c)
                # Always attack with flying/evasive creatures
                if c.name in (QUANTUM, PHELIA):  # both have evasion value
                    attackers.append(c)
                # Attack with big threats
                elif p >= 4:
                    attackers.append(c)
                # Attack with Ragavan (haste, treasure value)
                elif c.name == RAGAVAN:
                    attackers.append(c)
                # Hold back Solitude as blocker (3/2 lifelink)
                elif c.name == SOLITUDE and opp_power >= 4:
                    pass  # block instead
                else:
                    attackers.append(c)
        else:
            # Beatdown / Grind: attack with everything
            attackers = all_creatures
        
        # PHELIA ATTACK TRIGGER: exile own ETB creature → re-enter at end step
        # Oracle: "Whenever Phelia attacks, exile up to one other target nonland permanent.
        #          Return at beginning of next end step. +1/+1 counter if under your control."
        phelia = next((c for c in attackers if c.name == PHELIA), None)
        if phelia and opponent:
            # Can also exile OPPONENT creatures (playbook trick)
            # Priority: blink own ETB > exile opponent's best threat
            own_etb = [c for c in gs.zones.battlefield
                      if c.has(Tag.CREATURE) and c.name in ETB_CREATURES and c != phelia]
            if own_etb:
                self._blink_best_etb(gs, opponent)
                self._phelia_counters += 1
                # Oracle: +1/+1 counter on Phelia when an own permanent was exiled
                # (Pre-2026-04-29 fix: counter was tracked in _phelia_counters
                # but never applied to phelia.counters — Phelia stayed a 1/1
                # forever, losing significant combat damage.)
                phelia.counters += 1
                gs._log(f"  Phelia attack: blink own {own_etb[0].name} (Phelia now {phelia.counters} counters)")
            elif opponent:
                # Exile opponent's best creature. Oracle: return at next end
                # step under owner's control. Pre-2026-04-29 fix: card stayed
                # in opp.zones.exile permanently — log claimed "returns at end
                # step" but no return logic existed. Now tracked in
                # _phelia_exile_returns and returned in end_step_actions.
                opp_cr = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land() and safe_power(c) >= 2]
                if opp_cr:
                    target = max(opp_cr, key=lambda x: safe_power(x))
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.exile.append(target)
                    self._phelia_exile_returns.append((target, opponent))
                    gs._log(f"  Phelia attack: exile opponent's {target.name} (returns at end step)")
        
        # RAGAVAN COMBAT DAMAGE TRIGGER (handled here for logging)
        # Oracle: "Whenever Ragavan deals combat damage to a player, create a Treasure token
        #          and exile top card of that player's library. Until end of turn, may cast it."
        for a in attackers:
            if a.name == RAGAVAN:
                # Treasure creation happens on DAMAGE (combat resolution), not here
                # But we log intent and track treasure anticipation
                pass
        
        # PHLAGE ATTACK TRIGGER: 3 damage + 3 life
        for a in attackers:
            if a.name == PHLAGE:
                if opponent:
                    # Target opponent's creature or face
                    opp_cr = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land() and safe_toughness(x) <= 3]
                    if opp_cr:
                        target = max(opp_cr, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.graveyard.append(target)
                        gs._log(f"  Phlage attack: kill {target.name} + 3 life")
                    else:
                        gs.damage_dealt += 3
                        gs._log(f"  Phlage attack: 3 face + 3 life ({gs.damage_dealt} total)")
                gs.life += 3
        
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and not getattr(c, 'tapped', False)
                    and safe_toughness(c) >= 3]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        """Consign to Memory: counter triggered abilities.
        Playbook: 'Counter Archon ETB, Snapcaster flashback trigger, 
        Summoner's Pact upkeep trigger (they lose the game).'
        Also: Galvanic Discharge as instant-speed removal in response.
        """
        if not spell or not opponent:
            return None
        # Consign to Memory — counter triggered abilities or colorless spells
        for c in list(gs.zones.hand):
            if c.name == CONSIGN and gs.mana_pool.total() >= 1:
                # Only counter high-value triggers/spells
                spell_cmc = getattr(spell, 'cmc', 0)
                if spell_cmc >= 3 or spell.name in ("Archon of Cruelty", "Primeval Titan",
                    "Emrakul, the Promised End", "Summoner's Pact"):
                    gs.mana_pool.pay("{U}", 1) if gs.mana_pool.can_pay("{U}", 1) else None
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs._log(f"  Consign to Memory: counter {spell.name}")
                    return c
        return None

    def end_step_actions(self, gs, opponent):
        """End step: return creatures Phelia exiled this turn to their owners.

        Oracle: "Return that card to the battlefield under its owner's
        control at the beginning of the next end step."

        Pre-2026-04-29 fix: this was `pass` with a misleading docstring
        claiming "already handled in blink_best_etb" — but blink_best_etb
        only handles OWN ETB blinks (re-trigger), not the OPP creatures
        Phelia exiled in declare_attackers. So opp creatures stayed
        permanently exiled. Now properly returned at end of turn.
        """
        if not self._phelia_exile_returns:
            return
        for card, owner in self._phelia_exile_returns:
            if card in owner.zones.exile:
                owner.zones.exile.remove(card)
                owner.zones.battlefield.append(card)
                card.summoning_sickness = False  # was already on the field
                gs._log(f"  Phelia exile return: {card.name} -> opp battlefield")
        self._phelia_exile_returns.clear()

    def _draw(self, gs, n):
        """Wrapper around gs.zones.draw(n) that applies Quantum Riddler's
        static replacement effect.

        Oracle (Quantum Riddler, verified Scryfall 2026-04-29):
          "As long as you have one or fewer cards in hand, if you would
           draw one or more cards, you draw that many cards plus one
           instead."

        APL-side workaround for an engine gap (no static replacement
        framework). We check (a) Quantum Riddler in our battlefield AND
        (b) hand size <= 1 BEFORE the draw, and add +1 to n if both hold.
        Per oracle the check is on the draw-event creator's hand state,
        evaluated when the draw would occur. We approximate as
        pre-draw-hand-size check, which matches the oracle for any
        single-event draw.
        """
        if n <= 0:
            return
        if (len(gs.zones.hand) <= 1
                and any(c.name == QUANTUM for c in gs.zones.battlefield
                        if not c.is_land())):
            n += 1
            gs._log(f"  Quantum Riddler static: +1 to draw "
                    f"(hand <= 1, drew {n})")
        gs.zones.draw(n)

    def _card_value(self, c):
        """Rate a card's value for discard decisions (Casey Jones)."""
        if c.is_land(): return 1
        if c.name == SOLITUDE: return 10
        if c.name == EPHEMERATE: return 9
        if c.name == PHELIA: return 8
        if c.name == PHLAGE: return 7
        if c.name == QUANTUM: return 7
        if c.name in REMOVAL: return 6
        if c.name == RAGAVAN: return 5
        return 3

    def _should_wrath(self, gs, opponent):
        """Decide when to cast Wrath of the Skies.
        Playbook: Use Wrath when behind on board — never when ahead.
        Oracle: {X}{W}{W}, get X energy, pay energy to destroy artifacts/creatures/enchantments 
        with MV <= energy paid.
        """
        if not opponent:
            return False
        our_creatures = sum(1 for c in gs.zones.battlefield 
                          if c.has(Tag.CREATURE) and not c.is_land())
        their_creatures = sum(1 for c in opponent.zones.battlefield 
                            if c.has(Tag.CREATURE) and not c.is_land())
        # Only wrath if they have significantly more creatures
        if their_creatures >= our_creatures + 2:
            return True
        # Or if they have a single huge threat we can't answer otherwise
        big_threats = [c for c in opponent.zones.battlefield 
                      if c.has(Tag.CREATURE) and safe_power(c) >= 5]
        if big_threats and our_creatures <= 1:
            return True
        return False

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            name = c.name.lower() if c.name else ''
            if 'arena' in name: return 0
            if 'foundry' in name or 'vents' in name: return 1
            return 3
        gs.play_land(min(lands, key=score))
