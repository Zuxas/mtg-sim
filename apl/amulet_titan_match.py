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
        for c in list(gs.zones.hand):
            if c.name == SPELUNKING and avail >= 3:
                gs.cast_spell(c); self._spelunking_active = True
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

        # 5. Green Sun's Zenith ({X}{G}) — tutor green creature
        for c in list(gs.zones.hand):
            if c.name == GSZ:
                x_val = avail - 1
                if x_val >= 6:  # tutor Titan at X=6
                    gs.zones.hand.remove(c); gs.zones.library.append(c)  # GSZ shuffles back
                    gs.zones.draw(1)  # simulate tutoring Titan
                    avail -= 7
                    gs._log(f"  GSZ X=6: tutor Primeval Titan")
                elif x_val >= 0 and avail >= 1:
                    gs.zones.hand.remove(c); gs.zones.library.append(c)
                    gs.zones.draw(1)
                    gs._log(f"  GSZ X={x_val}: tutor creature")
                    avail = gs.mana_pool.total()
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
                # ETB: search 2 lands → battlefield
                gs.mana_pool.flex += 2  # simulate 2 extra lands
                gs._log(f"  PRIMEVAL TITAN: 6/6 trample ({'HASTE!' if has_haste else 'no haste'})")
                gs._log(f"    ETB: 2 lands to battlefield")
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

    def declare_attackers(self, gs, opponent):
        """Titan attack trigger: search 2 more lands."""
        attackers = [c for c in gs.zones.battlefield
                    if not c.is_land() and c.has(Tag.CREATURE)
                    and not getattr(c, 'summoning_sickness', False)
                    and not getattr(c, 'tapped', False)]
        for a in attackers:
            if a.name == TITAN:
                gs.mana_pool.flex += 2
                gs._log(f"  Titan attack: 2 more lands to battlefield")
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
