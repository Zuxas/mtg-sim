"""
apl/amulet_titan_match.py — Match-aware Amulet Titan APL (Modern)

Key mechanics:
1. Amulet of Vigor: bounce lands ETB untapped → double mana
2. Primeval Titan: 6/6 trample, ETB + attack search 2 lands
3. Spelunking: lands ETB untapped + Titan has haste
4. Arboreal Grazer: T1 ramp (put a land from hand onto battlefield)
5. Summoner's Pact: free tutor for Titan (pay {2}{G}{G} next upkeep or lose)
6. Scapeshift: sacrifice lands to search for key combo lands
7. Boseiju, Who Endures: channel to destroy artifact/enchantment
"""
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TITAN      = "Primeval Titan"
AMULET     = "Amulet of Vigor"
SPELUNKING = "Spelunking"
GRAZER     = "Arboreal Grazer"
PACT       = "Summoner's Pact"
SCAPESHIFT = "Scapeshift"
COLOSSUS   = "Cultivator Colossus"
RUMBLE     = "Malevolent Rumble"
ANALYST    = "Aftermath Analyst"
BOSEIJU    = "Boseiju, Who Endures"

RAMP_CREATURES = {GRAZER, ANALYST}
BOUNCE_LANDS = {"Gruul Turf", "Simic Growth Chamber"}


class AmuletTitanMatchAPL(MatchAPL):
    name = "Amulet Titan"
    win_condition_damage = 20
    max_turns = 10
    _extra_mana = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_amulet = any(c.name == AMULET for c in hand)
        has_titan = any(c.name in {TITAN, PACT} for c in hand)
        has_ramp = any(c.name in {GRAZER, SPELUNKING, RUMBLE} for c in hand)
        if lands == 0: return False
        if has_amulet and lands >= 2: return True
        if has_titan and lands >= 3 and has_ramp: return True
        if lands >= 3 and has_ramp: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (spells + lands[4:])[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        gs.mana_pool.flex += self._extra_mana
        self._extra_mana = 0
        
        # Count Amulets on battlefield
        amulet_count = sum(1 for c in gs.zones.battlefield if c.name == AMULET)
        has_spelunking = any(c.name == SPELUNKING for c in gs.zones.battlefield)

        # 1. Amulet of Vigor
        for c in list(gs.zones.hand):
            if c.name == AMULET and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                amulet_count += 1
                break

        # 2. Arboreal Grazer T1 (extra land drop + body)
        for c in list(gs.zones.hand):
            if c.name == GRAZER and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                extra_lands = [l for l in gs.zones.hand if l.is_land()]
                if extra_lands:
                    gs.zones.hand.remove(extra_lands[0])
                    gs.zones.battlefield.append(extra_lands[0])
                    # With Amulet: bounce land enters untapped = +2 mana
                    if amulet_count > 0 and extra_lands[0].name in BOUNCE_LANDS:
                        gs.mana_pool.flex += 2 * amulet_count
                    else:
                        gs.mana_pool.flex += 1
                break

        # 3. Spelunking (lands ETB untapped + Titan haste)
        for c in list(gs.zones.hand):
            if c.name == SPELUNKING and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                has_spelunking = True
                gs.mana_pool.flex += 1
                break

        # 4. Simulate Amulet + bounce land mana generation
        # With Amulet: each bounce land in hand = play it, ETB untapped, tap for 2, bounce
        # This is the engine that powers T3 Titan
        if amulet_count > 0:
            bounce_in_hand = [c for c in gs.zones.hand if c.name in BOUNCE_LANDS]
            for bounce in bounce_in_hand[:2]:  # max 2 bounce land replays per turn
                gs.mana_pool.flex += 2 * amulet_count  # each Amulet triggers
                self._extra_mana += 1  # carry over for next turn

        # 4. Boseiju channel — destroy opponent's key artifact/enchantment
        if opponent:
            targets = [c for c in opponent.zones.battlefield
                       if not c.is_land() and not c.has(Tag.CREATURE)]
            if targets:
                boseiju = next((c for c in gs.zones.hand if c.name == BOSEIJU), None)
                if boseiju:
                    gs.zones.hand.remove(boseiju)
                    gs.zones.graveyard.append(boseiju)
                    t = targets[0]
                    opponent.zones.battlefield.remove(t)
                    opponent.zones.graveyard.append(t)
                    gs._log(f"  Boseiju channel → destroy {t.name}")

        # 5. Primeval Titan — the win condition
        for c in list(gs.zones.hand):
            if c.name == TITAN and gs.mana_pool.total() >= 6:
                gs.mana_pool.pay("{4}{G}{G}", 6)
                gs.zones.hand.remove(c)
                gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                has_spelunking = any(x.name == SPELUNKING for x in gs.zones.battlefield)
                c.summoning_sickness = not has_spelunking  # haste with Spelunking
                # ETB: search 2 lands (simulate with +2 mana next turn)
                self._extra_mana += 2
                gs._log(f"  Primeval Titan! ({'haste!' if has_spelunking else 'no haste'})")
                break

        # 6. Summoner's Pact — free tutor for Titan
        if not any(c.name == TITAN for c in gs.zones.battlefield):
            for c in list(gs.zones.hand):
                if c.name == PACT:
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    # Simulate finding Titan — add a placeholder
                    gs._log(f"  Summoner's Pact → tutor Titan (must pay {'{2}{G}{G}'} next upkeep)")
                    break

        # 7. Remaining creatures
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and c.name not in {TITAN} and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers): return {}
    def respond_to_spell(self, gs, opponent, spell): return None
    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            if c.name in BOUNCE_LANDS: return 0  # bounce lands first with Amulet
            if 'saga' in c.name.lower(): return 1
            return 3
        gs.play_land(min(lands, key=score))
