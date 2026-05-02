"""
apl/esper_blink_match.py — Match-aware Esper/Orzhov Blink APL (Modern)

Key match mechanics:
1. Solitude: pitch white card to exile creature (FREE removal)
2. Fatal Push: kills CMC ≤2 (or ≤4 with revolt)
3. Thoughtseize: rip best card from opponent's hand (T1 disruption)
4. Ephemerate: blink Solitude/Overlord for double ETB
5. Teferi: bounce permanent + draw
6. Overlord of the Balemurk: ETB mill 4, return creature from GY
7. Flickerwisp: exile and return (removes blockers, re-triggers ETB)
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

SOLITUDE   = "Solitude"
FATAL_PUSH = "Fatal Push"
THOUGHTSEIZE = "Thoughtseize"
EPHEMERATE = "Ephemerate"
TEFERI     = "Teferi, Time Raveler"
OVERLORD   = "Overlord of the Balemurk"
PHELIA     = "Phelia, Exuberant Shepherd"
QUANTUM    = "Quantum Riddler"
FLICKERWISP = "Flickerwisp"
WITCH      = "Witch Enchanter"
EMPEROR    = "Emperor of Bones"
PRISMATIC  = "Prismatic Ending"
CONSIGN    = "Consign to Memory"

REMOVAL = {SOLITUDE, FATAL_PUSH, PRISMATIC}
CREATURES = {SOLITUDE, OVERLORD, PHELIA, QUANTUM, FLICKERWISP, WITCH, EMPEROR}


class EsperBlinkMatchAPL(MatchAPL):
    name = "Esper Blink"
    win_condition_damage = 20
    max_turns = 14

    def __init__(self):
        self._phelia_exile_returns = []  # (card, owner) tuples, returned at end step
        self._revolt_active = False      # True if a permanent left our battlefield this turn
        self._flickerwisp_exiles = []    # (card, owner) to return next end step
        self._finality_creatures = []    # creatures with finality counter, sacrificed at end step

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in CREATURES)
        interaction = sum(1 for c in hand if c.name in REMOVAL or c.name == THOUGHTSEIZE)
        if lands == 0: return False
        if lands > 5: return False
        if threats >= 1 and interaction >= 1 and lands >= 2: return True
        if any(c.name == THOUGHTSEIZE for c in hand) and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        # Revolt is active if any permanent left our battlefield this turn.
        # In Esper Blink, Phelia attacks exile permanents and return them.
        # Ephemerate blinks our own creatures. Revolt is almost always active.
        # Conservative: set revolt = True if we have Phelia, Ephemerate, or any
        # creature that was blinked (end step returns signal prior exile).
        self._revolt_active = bool(self._phelia_exile_returns) or bool(self._flickerwisp_exiles) or any(
            c.name in (FLICKERWISP, EPHEMERATE) for c in gs.zones.graveyard
        )

        # 1. Thoughtseize T1 — rip their best card
        if opponent and gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.life -= 2  # Thoughtseize costs 2 life
                    # Remove opponent's best nonland card
                    opp_nonlands = [x for x in opponent.zones.hand if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: getattr(x, 'cmc', 0))
                        opponent.zones.hand.remove(target)
                        opponent.zones.graveyard.append(target)
                        gs._log(f"  Thoughtseize → discard {target.name}")
                    break

        # 2. Solitude pitch on big threats
        if opponent:
            self._try_solitude_pitch(gs, opponent)

        # 3. Fatal Push on small creatures
        if opponent:
            self._use_fatal_push(gs, opponent)

        # 4. Deploy threats with ETB triggers
        for name in (PHELIA, QUANTUM, OVERLORD, FLICKERWISP, WITCH, EMPEROR):
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    if name == OVERLORD:
                        self._overlord_etb(gs, opponent)
                    elif name == FLICKERWISP and opponent:
                        self._flickerwisp_etb(gs, opponent)
                    elif name == QUANTUM:
                        self._draw(gs, 1)  # ETB draw
                    break

        # 5. Teferi bounce + draw
        for c in list(gs.zones.hand):
            if c.name == TEFERI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if opponent:
                    opp_nonlands = [x for x in opponent.zones.battlefield if not x.is_land()]
                    if opp_nonlands:
                        target = max(opp_nonlands, key=lambda x: safe_power(x))
                        opponent.zones.battlefield.remove(target)
                        opponent.zones.hand.append(target)
                self._draw(gs, 1)  # Teferi -3 draw
                break

        # 6. Ephemerate on Solitude/Overlord for double ETB
        # Oracle (Solitude ETB): "That creature's controller gains life equal to its power."
        if opponent:
            for c in list(gs.zones.hand):
                if c.name == EPHEMERATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    solitudes = [x for x in gs.zones.battlefield if x.name == SOLITUDE]
                    if solitudes:
                        opp_creatures = [x for x in opponent.zones.battlefield
                                         if not x.is_land() and x.has(Tag.CREATURE)]
                        if opp_creatures:
                            gs.cast_spell(c)
                            target = max(opp_creatures, key=lambda x: safe_power(x))
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.exile.append(target)
                            opponent.life += safe_power(target)  # oracle: controller gains life = power
                            gs._log(f"  Eph-Solitude: exile {target.name} (+{safe_power(target)} life)")
                    break

        # 7. Fill curve
        changed = True
        attempts = 0
        while changed and attempts < 15:
            changed = False; attempts += 1
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0))
                if gs.cast_spell(spell): changed = True
                else: break

    def _try_solitude_pitch(self, gs, opponent):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 3: return
        solitude = next((c for c in gs.zones.hand if c.name == SOLITUDE), None)
        if not solitude: return
        white_cards = [c for c in gs.zones.hand
                       if c != solitude and 'W' in (getattr(c, 'mana_cost', '') or '')]
        if not white_cards: return
        pitch = min(white_cards, key=lambda c: safe_power(c) if c.has(Tag.CREATURE) else 0)
        gs.zones.hand.remove(solitude)
        gs.zones.hand.remove(pitch)
        gs.zones.exile.append(pitch)
        gs.zones.battlefield.append(solitude)
        solitude.turn_entered = gs.turn
        solitude.summoning_sickness = True
        if target in opponent.zones.battlefield:
            opponent.zones.battlefield.remove(target)
            opponent.zones.exile.append(target)
        opponent.life += safe_power(target)
        gs._log(f"  Solitude (pitch {pitch.name}) → exile {target.name}")

    def _use_fatal_push(self, gs, opponent):
        """Fatal Push with revolt awareness.

        Oracle (verified Scryfall 2026-04-30):
          "Destroy target creature if it has mana value 2 or less.
           Revolt -- Destroy that creature if it has mana value 4 or less instead
           if a permanent you controlled left the battlefield this turn."
        In Esper Blink: Phelia exiles on attack, Ephemerate blinks -- revolt
        is almost always active. Use MV<=4 when revolt_active.
        """
        mv_cap = 4 if self._revolt_active else 2
        opp_creatures = [c for c in opponent.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)
                         and getattr(c, 'cmc', 0) <= mv_cap]
        if not opp_creatures: return
        target = max(opp_creatures, key=lambda c: safe_power(c))
        if safe_power(target) < 2: return
        for c in list(gs.zones.hand):
            if c.name == FATAL_PUSH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                self._revolt_active = True
                if target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
                gs._log(f"  Fatal Push (revolt={self._revolt_active}): kill {target.name} (MV<={mv_cap})")
                return

    def respond_to_spell(self, gs, opponent, spell):
        """Consign to Memory: counter high-value triggered abilities or colorless spells.
        Oracle (Consign, verified): "Counter target triggered ability or colorless spell."
        Returns card for engine execution (match_engine.py handles mana payment + removal).
        Only counters CMC >= 3 or named high-impact threats.
        """
        if not spell or not opponent:
            return None
        spell_cmc = getattr(spell, 'cmc', 0) if spell else 0
        if not (spell_cmc >= 3 or (spell and spell.name in (
                "Archon of Cruelty", "Primeval Titan", "Emrakul, the Promised End",
                "Atraxa, Grand Unifier", "Summoner's Pact"))):
            return None
        for c in gs.zones.hand:
            if c.name == CONSIGN and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                return c
        return None

    def declare_attackers(self, gs, opponent):
        attackers = []
        for c in gs.zones.battlefield:
            if c.is_land(): continue
            if getattr(c, 'summoning_sickness', False): continue
            if getattr(c, 'tapped', False): continue
            if c.has(Tag.CREATURE): attackers.append(c)

        # Phelia attack trigger: exile opponent's best creature, return at end step
        phelia = next((c for c in attackers if c.name == PHELIA), None)
        if phelia and opponent:
            opp_cr = [c for c in opponent.zones.battlefield
                      if c.has(Tag.CREATURE) and not c.is_land() and safe_power(c) >= 2]
            if opp_cr:
                target = max(opp_cr, key=lambda x: safe_power(x))
                opponent.zones.battlefield.remove(target)
                opponent.zones.exile.append(target)
                self._phelia_exile_returns.append((target, opponent))
                gs._log(f"  Phelia attack: exile {target.name} (returns at end step)")

        # Emperor of Bones: beginning-of-combat trigger + Adapt 2 chain
        # Oracle: "At beginning of combat on your turn, exile up to one target card
        # from a graveyard. {1}{B}: Adapt 2. Whenever +1/+1 counters are put on this
        # creature, put the exiled card onto the battlefield with haste + finality counter.
        # Sacrifice it at beginning of next end step."
        emperor = next((c for c in attackers if c.name == EMPEROR), None)
        if emperor and not getattr(emperor, '_adapted', False):
            all_gy = [c for c in gs.zones.graveyard if c.has(Tag.CREATURE)]
            if opponent:
                all_gy += [c for c in opponent.zones.graveyard if c.has(Tag.CREATURE)]
            if all_gy and gs.mana_pool.flex >= 2:
                exile_target = max(all_gy, key=lambda c: safe_power(c))
                if exile_target in gs.zones.graveyard:
                    gs.zones.graveyard.remove(exile_target)
                elif opponent and exile_target in opponent.zones.graveyard:
                    opponent.zones.graveyard.remove(exile_target)
                gs.mana_pool.flex -= min(2, gs.mana_pool.flex)
                emperor._adapted = True
                exile_target.summoning_sickness = False  # oracle: it gains haste
                exile_target._finality = True
                gs.zones.battlefield.append(exile_target)
                self._finality_creatures.append(exile_target)
                attackers.append(exile_target)
                gs._log(f"  Emperor Adapt: reanimate {exile_target.name} with haste+finality")

        return attackers

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        solitudes = [c for c in gs.zones.battlefield
                     if c.name == SOLITUDE and not getattr(c, 'tapped', False)]
        if solitudes:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [solitudes[0]]
        return assignments

    def _flickerwisp_etb(self, gs, opponent):
        """Exile another target permanent, return at beginning of next end step.
        Oracle: 'When Flickerwisp enters, exile another target permanent. Return
        that card to the battlefield under its owner's control at the beginning
        of the next end step.'
        Targets opponent's highest-power permanent to disrupt combat/effects.
        """
        if not opponent: return
        opp_perms = [c for c in opponent.zones.battlefield if not c.is_land()]
        if not opp_perms:
            opp_perms = list(opponent.zones.battlefield)
        if not opp_perms: return
        target = max(opp_perms, key=lambda x: safe_power(x))
        opponent.zones.battlefield.remove(target)
        opponent.zones.exile.append(target)
        self._flickerwisp_exiles.append((target, opponent))
        gs._log(f"  Flickerwisp ETB: exile {target.name} (returns next end step)")

    def _overlord_etb(self, gs, opponent):
        """Each player mills 4, return creature from any GY to hand.
        Oracle: 'When Overlord of the Balemurk enters, each player mills four
        cards. Return up to one target creature card from a graveyard to your hand.'
        """
        for _ in range(4):
            if gs.zones.library:
                gs.zones.graveyard.append(gs.zones.library.pop(0))
        if opponent:
            for _ in range(4):
                if opponent.zones.library:
                    opponent.zones.graveyard.append(opponent.zones.library.pop(0))
        our_creatures = [c for c in gs.zones.graveyard if c.has(Tag.CREATURE)]
        opp_creatures = [c for c in (opponent.zones.graveyard if opponent else [])
                         if c.has(Tag.CREATURE)]
        candidates = our_creatures + opp_creatures
        if not candidates: return
        target = max(candidates, key=lambda c: safe_power(c))
        if target in gs.zones.graveyard:
            gs.zones.graveyard.remove(target)
        elif opponent and target in opponent.zones.graveyard:
            opponent.zones.graveyard.remove(target)
        gs.zones.hand.append(target)
        gs._log(f"  Overlord ETB: mill 4 each, return {target.name} to hand")

    def end_step_actions(self, gs, opponent):
        """Return Phelia-exiled and Flickerwisp-exiled permanents at end step."""
        for card, owner in self._phelia_exile_returns:
            if card in owner.zones.exile:
                owner.zones.exile.remove(card)
                owner.zones.battlefield.append(card)
                card.summoning_sickness = False
                gs._log(f"  Phelia exile return: {card.name} -> opp battlefield")
        self._phelia_exile_returns.clear()

        for card, owner in self._flickerwisp_exiles:
            if card in owner.zones.exile:
                owner.zones.exile.remove(card)
                owner.zones.battlefield.append(card)
                card.summoning_sickness = False
                gs._log(f"  Flickerwisp exile return: {card.name} -> opp battlefield")
        self._flickerwisp_exiles.clear()

        # Finality counter: sacrifice creatures reanimated by Emperor of Bones
        for card in list(self._finality_creatures):
            if card in gs.zones.battlefield:
                gs.zones.battlefield.remove(card)
                gs.zones.graveyard.append(card)
                gs._log(f"  Finality sacrifice: {card.name}")
        self._finality_creatures.clear()

    def _draw(self, gs, n):
        """Draw with Quantum Riddler static.
        Oracle: 'As long as you have one or fewer cards in hand, if you would draw
        one or more cards, you draw that many cards plus one instead.'
        """
        quantum_on_board = any(c.name == QUANTUM for c in gs.zones.battlefield)
        if quantum_on_board and len(gs.zones.hand) <= 1:
            n += 1
        gs.zones.draw(n)

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = c.name.lower()
            if 'marsh' in n or 'strand' in n or 'delta' in n: return 0
            if 'godless' in n or 'hallowed' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
