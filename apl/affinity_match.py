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
        self._artifacts_cast_this_turn = 0   # for Pinnacle Emissary Drone creation
        self._munitions_pending = 0          # Weapons Manufacturing Munitions tokens

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
        self._artifacts_cast_this_turn = 0
        avail = gs.mana_pool.total()

        pinnacle_on_board = any(c.name == PINNACLE for c in gs.zones.battlefield)
        weapons_on_board = any(c.name == WEAPONS for c in gs.zones.battlefield)

        def _on_artifact_enter(is_nontoken=True):
            """Fire ETB triggers when an artifact enters the battlefield."""
            self._artifact_count += 1
            self._kappa_counters += 1  # Kappa gets +1/+1 per artifact ETB
            if weapons_on_board and is_nontoken:
                self._munitions_pending += 1  # Munitions token created

        def _on_artifact_cast():
            """Fire cast triggers when an artifact spell is cast."""
            self._artifacts_cast_this_turn += 1

        # 0. Mox Opal — free mana if metalcraft (3+ artifacts)
        for c in list(gs.zones.hand):
            if c.name == MOX_OPAL:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                _on_artifact_enter(is_nontoken=True)
                if self._artifact_count >= 3:
                    avail += 1
                gs._log(f"  Mox Opal (artifacts: {self._artifact_count}, metalcraft: {self._artifact_count >= 3})")
                break

        # 1. Deploy cheap artifacts (free, ETB triggers Kappa + Weapons Manufacturing)
        for c in list(gs.zones.hand):
            if c.name in ARTIFACTS and getattr(c, 'cmc', 0) == 0:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                _on_artifact_enter(is_nontoken=True)
                _on_artifact_cast()
                gs._log(f"  Deploy {c.name} (artifact #{self._artifact_count})")

        # 2. Weapons Manufacturing ({2}) — creates Munitions tokens on each artifact entering
        # Oracle: "Whenever a nontoken artifact you control enters, create a Munitions token
        # (an artifact token with 'When this token leaves the battlefield, it deals 2 damage')."
        for c in list(gs.zones.hand):
            if c.name == WEAPONS and avail >= 2:
                gs.cast_spell(c); _on_artifact_enter(); _on_artifact_cast()
                avail = gs.mana_pool.total()
                gs._log(f"  Weapons Manufacturing: each artifact entering now creates Munitions (+2 dmg on sac)")
                break

        # 3. Emry ({2}{U} with affinity for artifacts) — cast artifacts from GY
        # Oracle (ETB): "When Emry enters, mill four cards." — puts 4 cards from library to GY
        for c in list(gs.zones.hand):
            if c.name == EMRY:
                gs.mana_pool.cost_reduction = self._artifact_count
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    _on_artifact_enter()
                    # Oracle ETB: mill 4 cards (library -> GY, fills GY for delirium)
                    for _ in range(min(4, len(gs.zones.library))):
                        card = gs.zones.library.pop(0)
                        gs.zones.graveyard.append(card)
                    gs._log(f"  Emry ETB: affinity, mill 4 -> GY ({len(gs.zones.graveyard)} in GY)")
                gs.mana_pool.cost_reduction = 0
                avail = gs.mana_pool.total()
                break

        # 4. Kappa Cannoneer ({5}{U}, ward {4}) — grows on artifact ETB, improvise
        for c in list(gs.zones.hand):
            if c.name == KAPPA:
                gs.mana_pool.cost_reduction = self._artifact_count
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    _on_artifact_enter()
                    c.power = str(4 + self._kappa_counters)
                    c.toughness = str(4 + self._kappa_counters)
                    gs._log(f"  Kappa: {safe_power(c)}/{safe_toughness(c)} (affinity -{self._artifact_count}, ward 4)")
                gs.mana_pool.cost_reduction = 0
                avail = gs.mana_pool.total()
                break

        # 5. Pinnacle Emissary ({3}{U}{R}) — creates 1/1 Drone flying tokens on each artifact cast.
        # Oracle: "Whenever you cast an artifact spell, create a 1/1 colorless Drone artifact
        # creature token with flying." Drone tokens ALSO trigger Kappa + Weapons Manufacturing.
        for c in list(gs.zones.hand):
            if c.name == PINNACLE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                avail = gs.mana_pool.total()
                break
        # Create Drones for all artifact casts so far this turn (if Pinnacle now on board
        # or was already on board). Post-cast is conservative; ideally fires per-cast.
        pinnacle_on_board = any(c.name == PINNACLE for c in gs.zones.battlefield)
        if pinnacle_on_board and self._artifacts_cast_this_turn > 0:
            for _ in range(self._artifacts_cast_this_turn):
                gs._make_token("Drone Token", "1", "1",
                               "Artifact Creature — Drone")
                _on_artifact_enter(is_nontoken=False)  # tokens don't trigger Weapons Mfg
            gs._log(f"  Pinnacle: {self._artifacts_cast_this_turn} Drone token(s) (flying, artifact)")

        # 6. Arcbound Ravager ({2}) — sacrifice artifacts for counters
        for c in list(gs.zones.hand):
            if c.name == RAVAGER and avail >= 2:
                gs.cast_spell(c); _on_artifact_enter(); _on_artifact_cast()
                avail = gs.mana_pool.total()
                gs._log(f"  Ravager: sac artifacts for +1/+1 counters")
                break

        # 6b. Weapons Manufacturing Munitions — convert pending Munitions to face damage.
        # Oracle: "When this token leaves the battlefield, it deals 2 damage to any target."
        # Sacrifice all Munitions tokens at end of main for damage (aggressive line).
        if self._munitions_pending > 0:
            dmg = self._munitions_pending * 2
            gs.damage_dealt += dmg
            gs._log(f"  Weapons Mfg Munitions: sac {self._munitions_pending} tokens → {dmg} face")
            self._munitions_pending = 0

        # 7. Removal with Metallic Rebuke (handled in respond_to_spell)

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
        """Block with largest creatures. Kappa (ward 4) and Ravager soak hits."""
        if not attackers:
            return {}
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if not blockers:
            return {}
        assignments = {}
        blockers_sorted = sorted(blockers, key=lambda c: -safe_toughness(c))
        attackers_sorted = sorted(attackers, key=lambda c: -safe_power(c))
        for atk, blk in zip(attackers_sorted, blockers_sorted):
            assignments[id(atk)] = [blk]
        return assignments

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
