"""
apl/amulet_titan_match.py — Oracle-audited Amulet Titan APL (Modern)

Playbook engines:
A. Amulet + Bounce Land Mana — Amulet makes bounce lands enter untapped = double mana
B. Primeval Titan Kill — Titan ETB/attack fetches 2 lands, with haste = immediate kill
C. Scapeshift + Amulet Burst — sac X lands, get X bounce lands, all untapped with Amulet

Key oracle:
- Amulet of Vigor: permanents you control enter untapped (bounce lands = tap before return)
- Bounce lands (Gruul Turf etc): ETB return a land, tap for 2 mana
- Primeval Titan: ETB + attack → search 2 lands → battlefield
- Spelunking: lands enter untapped + creatures have haste
- Scapeshift: sac X lands → search X lands → all enter simultaneously
- Green Sun's Zenith: tutor green creature for {X}{G}
- Summoner's Pact: free tutor (pay {2}{G}{G} next upkeep or lose)
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TITAN      = "Primeval Titan"
AMULET     = "Amulet of Vigor"
SPELUNKING = "Spelunking"
SCAPESHIFT = "Scapeshift"
GRAZER     = "Arboreal Grazer"
GSZ        = "Green Sun's Zenith"
PACT       = "Summoner's Pact"
RUMBLE     = "Malevolent Rumble"
COLOSSUS   = "Cultivator Colossus"
ANALYST    = "Aftermath Analyst"
SAGA       = "Urza's Saga"

BOUNCE_LANDS = {"Gruul Turf", "Simic Growth Chamber"}


class AmuletTitanMatchAPL(MatchAPL):
    name = "Amulet Titan"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._amulet_active = False
        self._spelunking_active = False
        self._pact_due = False  # Summoner's Pact payment due next upkeep
        self._extra_land_drops = 0

    def _has_haste_source(self, gs):
        """Check for haste (Spelunking or Hanweir Battlements)."""
        return self._spelunking_active or any(
            'hanweir' in (c.name or '').lower() or 'arena' in (c.name or '').lower()
            for c in gs.zones.battlefield if c.is_land())

    def _bounce_land_bonus(self, gs):
        """With Amulet: each bounce land = 2 extra mana (enters untapped, tap for 2 before return).
        With Spelunking: same effect. Total per bounce land with enabler = 3 mana (1 from tap_lands + 2 bonus)."""
        if not self._amulet_active and not self._spelunking_active:
            return 0
        return sum(2 for c in gs.zones.battlefield if c.name in BOUNCE_LANDS)

    def keep(self, hand, mulligans, on_play):
        """Playbook: Keep Amulet + bounce land + threat. Mull hands without acceleration."""
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_amulet = any(c.name == AMULET for c in hand)
        has_spelunking = any(c.name == SPELUNKING for c in hand)
        has_bounce = any(c.name in BOUNCE_LANDS for c in hand)
        threats = sum(1 for c in hand if c.name in (TITAN, SCAPESHIFT, COLOSSUS, GSZ, PACT))
        has_grazer = any(c.name == GRAZER for c in hand)
        
        if lands == 0: return False
        if (has_amulet or has_spelunking) and has_bounce and lands >= 2: return True
        if has_grazer and lands >= 3 and threats >= 1: return True
        if threats >= 1 and lands >= 3: return True
        if has_amulet and lands >= 2 and threats >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[5:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._amulet_active = any(c.name == AMULET for c in gs.zones.battlefield)
        self._spelunking_active = any(c.name == SPELUNKING for c in gs.zones.battlefield)
        gs.mana_pool.flex += self._bounce_land_bonus(gs)
        avail = gs.mana_pool.total()

        # Summoner's Pact upkeep — pay {2}{G}{G} or lose the game
        if self._pact_due:
            self._pact_due = False
            if avail >= 4:
                avail -= 4
                gs._log(f"  Pact payment: paid {{2}}{{G}}{{G}}")
            else:
                gs.life = -999  # can't pay = lose
                gs._log(f"  Pact payment FAILED — game loss!")
                return

        # 1. Amulet of Vigor ({1}) — critical enabler
        for c in list(gs.zones.hand):
            if c.name == AMULET and avail >= 1:
                gs.cast_spell(c); self._amulet_active = True
                avail = gs.mana_pool.total() + self._bounce_land_bonus(gs)
                gs._log(f"  AMULET: bounce lands now enter untapped!")
                break

        # 2. Spelunking ({2}{G}) — lands enter untapped + haste
        # Oracle ETB: "draw a card, then you may put a land card from your hand onto
        # the battlefield."
        for c in list(gs.zones.hand):
            if c.name == SPELUNKING and avail >= 3:
                gs.cast_spell(c); self._spelunking_active = True
                gs.zones.draw(1)  # ETB draw
                extra = [x for x in gs.zones.hand if x.is_land()]
                if extra and not gs.land_played:
                    gs.zones.hand.remove(extra[0])
                    gs.zones.battlefield.append(extra[0])
                    extra[0].turn_entered = gs.turn
                    gs._log(f"  Spelunking ETB: land {extra[0].name} to battlefield")
                avail = gs.mana_pool.total()
                gs._log(f"  Spelunking: lands untapped + creatures haste")
                break

        # 3. Arboreal Grazer ({G}) — extra land drop
        for c in list(gs.zones.hand):
            if c.name == GRAZER and avail >= 1:
                gs.cast_spell(c)
                # Put a land from hand onto battlefield
                extra_lands = [x for x in gs.zones.hand if x.is_land()]
                if extra_lands:
                    land = extra_lands[0]
                    gs.zones.hand.remove(land); gs.zones.battlefield.append(land)
                    land.turn_entered = gs.turn
                    gs._log(f"  Grazer: extra land drop ({land.name})")
                avail = gs.mana_pool.total() + self._bounce_land_bonus(gs)
                break

        # 4. Malevolent Rumble ({1}{G}) — card selection + Spawn token
        for c in list(gs.zones.hand):
            if c.name == RUMBLE and avail >= 2:
                gs.mana_pool.pay("{1}{G}", 2) if gs.mana_pool.can_pay("{1}{G}", 2) else None
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs.zones.draw(1)  # simulate finding best card
                for _ in range(3):
                    if gs.zones.library:
                        gs.zones.graveyard.append(gs.zones.library.pop(0))
                avail = gs.mana_pool.total()
                gs._log(f"  Rumble: draw 1, 3 to GY, +1 Spawn")
                break

        # 5. Green Sun's Zenith ({X}{G}) — tutor green creature to battlefield
        # Oracle: "Search library for green creature with mana value X or less, put it
        # onto the battlefield, then shuffle. Shuffle Green Sun's Zenith into its library."
        for c in list(gs.zones.hand):
            if c.name == GSZ and avail >= 1:
                x_val = avail - 1  # reserve 1 for {G}
                candidates = [x for x in gs.zones.library
                              if x.has(Tag.CREATURE) and getattr(x, 'cmc', 0) <= x_val
                              and 'G' in (getattr(x, 'colors', []) or [])]
                if candidates:
                    target = max(candidates, key=lambda x: getattr(x, 'cmc', 0))
                    cost = getattr(target, 'cmc', 0) + 1  # X = target CMC, +1 for {G}
                    gs.mana_pool.flex -= min(cost, gs.mana_pool.flex)
                    gs.zones.hand.remove(c)
                    gs.zones.library.remove(target)
                    gs.zones.library.append(c)  # GSZ shuffles back into library
                    # Put directly onto battlefield (oracle: not into hand)
                    gs.zones.battlefield.append(target)
                    target.turn_entered = gs.turn
                    target.summoning_sickness = not self._has_haste_source(gs)
                    self._trigger_creature_etb(gs, opponent, target)
                    avail = gs.mana_pool.total() + self._bounce_land_bonus(gs)
                    gs._log(f"  GSZ X={x_val}: {target.name} onto battlefield!")
                break

        # 6. Summoner's Pact ({0}) — free tutor, pay next upkeep
        if not self._pact_due:
            for c in list(gs.zones.hand):
                if c.name == PACT:
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs.zones.draw(1)  # simulate tutor
                    self._pact_due = True
                    gs._log(f"  Summoner's Pact: FREE tutor (must pay {{2}}{{G}}{{G}} next upkeep)")
                    break

        avail = gs.mana_pool.total() + self._bounce_land_bonus(gs)

        # 7. PRIMEVAL TITAN ({4}{G}{G}) — THE win condition
        for c in list(gs.zones.hand):
            if c.name == TITAN and avail >= 6:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                c.power = '6'; c.toughness = '6'
                has_haste = self._has_haste_source(gs)
                c.summoning_sickness = not has_haste
                self._trigger_creature_etb(gs, opponent, c)
                break

        # 8. Scapeshift ({2}{G}{G}) — sacrifice lands, get that many
        for c in list(gs.zones.hand):
            if c.name == SCAPESHIFT and avail >= 4:
                lands_on_board = sum(1 for x in gs.zones.battlefield if x.is_land())
                if lands_on_board >= 4:
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    # With Amulet: each new bounce land = 2 mana
                    new_mana = lands_on_board * (2 if self._amulet_active else 1)
                    gs.mana_pool.flex += new_mana
                    gs._log(f"  Scapeshift: sac {lands_on_board} lands, get {lands_on_board} new (+{new_mana} mana)")
                break

        # 9. Fill remaining
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in (TITAN, COLOSSUS):
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)

    def _trigger_creature_etb(self, gs, opponent, card):
        """Fire ETB triggers for key Amulet Titan creatures."""
        if card.name == TITAN:
            # Oracle: "When this creature enters or attacks, search your library for up to
            # two land cards, put them onto the battlefield, then shuffle."
            # With Amulet: bounce lands enter untapped = extra mana.
            gs.mana_pool.flex += 2 * (2 if self._amulet_active else 1)
            has_haste = self._has_haste_source(gs)
            gs._log(f"  Primeval Titan ETB: 2 lands to battlefield ({'HASTE!' if has_haste else 'no haste'})")
        elif card.name == COLOSSUS:
            # Cultivator Colossus: put land from hand → repeat while lands in hand
            while True:
                lands_in_hand = [x for x in gs.zones.hand if x.is_land()]
                if not lands_in_hand: break
                land = lands_in_hand[0]
                gs.zones.hand.remove(land)
                gs.zones.battlefield.append(land)
                land.turn_entered = gs.turn
                gs.zones.draw(1)
                gs._log(f"  Colossus ETB: land {land.name} to battlefield + draw")

    def declare_attackers(self, gs, opponent):
        """Titan attack trigger: search 2 more lands (same as ETB)."""
        attackers = [c for c in gs.zones.battlefield
                    if not c.is_land() and c.has(Tag.CREATURE)
                    and not getattr(c, 'summoning_sickness', False)
                    and not getattr(c, 'tapped', False)]
        for a in attackers:
            if a.name == TITAN:
                self._trigger_creature_etb(gs, opponent, a)
        return attackers

    def declare_blockers(self, gs, opp, attackers): return {}
    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if c.name in BOUNCE_LANDS and self._amulet_active: return 0
            if 'saga' in n: return 1
            if 'forest' in n: return 2
            if c.name in BOUNCE_LANDS: return 3
            return 4
        gs.play_land(min(lands, key=score))
