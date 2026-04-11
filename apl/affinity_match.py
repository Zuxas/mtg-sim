"""
apl/affinity_match.py — Oracle-audited Izzet Affinity APL (Modern)

Playbook engines:
A. Pinnacle Emissary Token Flood — creates artifact creature tokens
B. Weapons Manufacturing + Engineered Explosives — sac artifacts for burst damage
C. Urza's Saga + Emry Recursion — Saga constructs + Emry recasts from GY

Key cards: Kappa Cannoneer (ward, grows on artifact ETB), Mox Opal (free mana),
Pinnacle Emissary (token flood), Arcbound Ravager (sac for +1/+1 counters),
Metallic Rebuke (affinity counter), Urza's Saga (constructs + tutor)
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

KAPPA      = "Kappa Cannoneer"
PINNACLE   = "Pinnacle Emissary"
WEAPONS    = "Weapons Manufacturing"
EE         = "Engineered Explosives"
MOX_OPAL   = "Mox Opal"
BAUBLE     = "Mishra's Bauble"
EMRY       = "Emry, Lurker of the Loch"
RAVAGER    = "Arcbound Ravager"
REBUKE     = "Metallic Rebuke"
SAGA       = "Urza's Saga"
SHADOWSPEAR= "Shadowspear"
SKATEBOARD = "Skateboard"

ARTIFACTS = {MOX_OPAL, BAUBLE, EE, SHADOWSPEAR, SKATEBOARD, WEAPONS,
             "Tormod's Crypt", "Claws of Gix", "Welding Jar", "Aether Spellbomb", "Pithing Needle"}


class IzzetAffinityMatchAPL(MatchAPL):
    name = "Izzet Affinity"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._artifact_count = 0
        self._kappa_counters = 0

    def _count_artifacts(self, gs):
        """Count artifacts on battlefield for affinity/metalcraft."""
        return sum(1 for c in gs.zones.battlefield
                  if not c.is_land() and 'artifact' in (getattr(c, 'type_line', '') or '').lower())

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        artifacts = sum(1 for c in hand if c.name in ARTIFACTS or c.name == MOX_OPAL)
        threats = sum(1 for c in hand if c.name in (KAPPA, PINNACLE, EMRY, RAVAGER))
        has_opal = any(c.name == MOX_OPAL for c in hand)
        
        if lands == 0 and not has_opal: return False
        if artifacts >= 2 and threats >= 1: return True
        if has_opal and threats >= 1 and lands >= 1: return True
        if threats >= 2 and lands >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._artifact_count = self._count_artifacts(gs)
        avail = gs.mana_pool.total()

        # 0. Mox Opal — free mana if metalcraft (3+ artifacts)
        for c in list(gs.zones.hand):
            if c.name == MOX_OPAL:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                self._artifact_count += 1
                if self._artifact_count >= 3:
                    avail += 1  # metalcraft: tap for any color
                gs._log(f"  Mox Opal (artifacts: {self._artifact_count}, metalcraft: {self._artifact_count >= 3})")
                break

        # 1. Deploy cheap artifacts (Bauble, Tormod's Crypt, etc.) — fuel affinity + Kappa triggers
        for c in list(gs.zones.hand):
            if c.name in ARTIFACTS and getattr(c, 'cmc', 0) == 0:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                self._artifact_count += 1
                self._kappa_counters += 1  # Kappa gets +1/+1 per artifact ETB
                gs._log(f"  Deploy {c.name} (artifact #{self._artifact_count})")

        # 2. Weapons Manufacturing ({2}) — artifact that creates tokens
        for c in list(gs.zones.hand):
            if c.name == WEAPONS and avail >= 2:
                gs.cast_spell(c); self._artifact_count += 1
                avail = gs.mana_pool.total()
                gs._log(f"  Weapons Manufacturing: artifact token engine")
                break

        # 3. Emry ({2}{U} with affinity for artifacts) — cast artifacts from GY
        for c in list(gs.zones.hand):
            if c.name == EMRY:
                emry_cost = max(1, 3 - self._artifact_count)  # affinity reduces cost
                if avail >= emry_cost:
                    # Manual deploy (bypass can_cast which doesn't know affinity)
                    gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn; c.summoning_sickness = True
                    gs.mana_pool.flex -= min(emry_cost, gs.mana_pool.flex)
                    gs._log(f"  Emry: cost {emry_cost} (affinity -{self._artifact_count})")
                    avail = gs.mana_pool.total()
                    break

        # 4. Kappa Cannoneer ({5}{U}, ward {4}) — grows on artifact ETB
        for c in list(gs.zones.hand):
            if c.name == KAPPA:
                kappa_cost = max(2, 6 - self._artifact_count)  # affinity
                if avail >= kappa_cost:
                    gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                    c.turn_entered = gs.turn; c.summoning_sickness = True
                    gs.mana_pool.flex -= min(kappa_cost, gs.mana_pool.flex)
                    # Set initial size based on artifacts
                    c.power = str(4 + self._kappa_counters)
                    c.toughness = str(4 + self._kappa_counters)
                    gs._log(f"  Kappa: {safe_power(c)}/{safe_toughness(c)} (cost {kappa_cost}, ward 4)")
                    avail = gs.mana_pool.total()
                    break

        # 5. Pinnacle Emissary — token flood
        for c in list(gs.zones.hand):
            if c.name == PINNACLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c); avail = gs.mana_pool.total()
                break

        # 6. Arcbound Ravager ({2}) — sacrifice artifacts for counters
        for c in list(gs.zones.hand):
            if c.name == RAVAGER and avail >= 2:
                gs.cast_spell(c); avail = gs.mana_pool.total()
                gs._log(f"  Ravager: sac artifacts for +1/+1 counters")
                break

        # 7. Removal with Metallic Rebuke
        # (handled in respond_to_spell)

        # 8. Fill curve
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        """Metallic Rebuke — affinity counter ({2}{U} - artifacts)."""
        if not spell: return None
        rebuke_cost = max(1, 3 - self._count_artifacts(gs))
        for c in list(gs.zones.hand):
            if c.name == REBUKE and gs.mana_pool.total() >= rebuke_cost:
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs._log(f"  Metallic Rebuke: counter {spell.name} (cost {rebuke_cost})")
                return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'saga' in n: return 0  # Urza's Saga is priority
            if 'islet' in n or 'canal' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
