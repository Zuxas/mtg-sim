"""apl/boros_aggro_standard.py -- Boros Aggro APL (Standard)

Replaces the template apl/boros_aggro.py with a real-Magic APL that
models the actual play pattern:

  T1: Land, 1-drop (Swiftspear/Phoenix/Epicure), burn face if no attacker
  T2: Land, 2-drop creature OR pre-combat burn for prowess + attack
  T3: Saga (Kumano) for +1/+1 counter, 3-drop creature, burn
  T4+: Curve-out, Monstrous Rage on biggest attacker, post-combat burn

Key real-Magic decisions modeled:
  - Prowess-timing: noncreature spells cast pre-combat pump Swiftspear
    during combat (engine already handles this — we just order casts).
  - Monstrous Rage: applied to the biggest attacker before combat
    damage (+2/+0 trample for the turn). EOT -1/-1 counter ignored in
    goldfish since the creature already did its damage.
  - Burn split: pre-combat burn trades damage for prowess; post-combat
    burn is straight damage with no trigger value.
  - Haste creatures (Phoenix Chick, Bloodthirsty Adversary) attack the
    turn they enter.
  - Damage accounting: track gs.damage_dealt; burn spells add directly
    so we can win via burn when no attackers are available.

Distinct from apl/boros_aggro.py (the minimum-viable template); this
file is picked up preferentially by the analyzer's discovery via the
_standard suffix convention.
"""
from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState
from engine.keywords import KWTag

# ── 1-drops ──────────────────────────────────────────────────────────
SWIFTSPEAR   = "Monastery Swiftspear"
PHOENIX      = "Phoenix Chick"
EPICURE      = "Voldaren Epicure"

# ── 2-drops ──────────────────────────────────────────────────────────
KUMANO       = "Kumano Faces Kakkazan"      # Saga / enchantment
ADVERSARY    = "Bloodthirsty Adversary"     # haste
SCOUNDREL    = "Charming Scoundrel"

# ── 3-drops ──────────────────────────────────────────────────────────
SQUEE        = "Squee, Dubious Monarch"
FELDON       = "Feldon, Ronom Excavator"

# ── 4-drops ──────────────────────────────────────────────────────────
GODDRIC      = "Goddric, Cloaked Reveler"

# ── Burn / pump / removal ───────────────────────────────────────────
PLAY_FIRE    = "Play with Fire"             # {R}: 2 dmg
LIGHTNING    = "Lightning Strike"           # {1}{R}: 3 dmg
RAGE         = "Monstrous Rage"             # {R}: +2/+0 trample
FRENZY       = "Witchstalker Frenzy"        # {1}{R}: 3 to creature/pw

# Mana cost + face damage — used for post-combat burn-to-face decisions
_BURN_DAMAGE = {
    PLAY_FIRE: (1, 2),      # cost 1, deals 2
    LIGHTNING: (2, 3),      # cost 2, deals 3
}

# Creature deploy priority: cheapest first, but haste creatures go
# earliest on their curve turn because they attack that turn.
_CREATURES = (
    SWIFTSPEAR,    # 1, prowess
    PHOENIX,       # 1, flying haste
    EPICURE,       # 1, treasure-like value
    KUMANO,        # 2, Saga (enchantment, not a creature — treated as threat anchor)
    ADVERSARY,     # 2, haste
    SCOUNDREL,     # 2
    SQUEE,         # 3, recursion
    FELDON,        # 3
    GODDRIC,       # 4
)


class BorosAggroStandardAPL(SBPlanMixin, BaseAPL):
    name = "Boros Aggro"
    win_condition_damage = 20
    max_turns = 12

    # ------------------------------------------------------------------
    # Turn bookkeeping
    # ------------------------------------------------------------------

    def reset_game(self):
        self._rage_applied_this_turn = False

    def reset_turn(self):
        self._rage_applied_this_turn = False

    # ------------------------------------------------------------------
    # Mulligan
    # ------------------------------------------------------------------

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        creatures = sum(1 for c in hand if c.name in _CREATURES and not _is_enchantment(c))
        burn = sum(1 for c in hand if c.name in _BURN_DAMAGE)
        # Aggro mulligan heuristic: 2-3 lands + at least 2 threats or
        # 1 threat + 2 burn. No-lander always shipped.
        if lands == 0:
            return False
        if lands >= 6:
            return False
        if 2 <= lands <= 4 and creatures + burn >= 3 and creatures >= 1:
            return True
        if lands == 1 and creatures >= 2 and burn >= 2:
            return True   # one-lander with critical mass — keep when desperate
        return mulligans >= 2

    def bottom(self, hand, n):
        # Ship excess lands first, then heaviest non-creature spells.
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 3:
            return lands[3:][:n]
        # Otherwise drop the top-end creature to dig for early drops
        tops = [c for c in hand if c.name in (GODDRIC, FELDON, SQUEE)]
        return tops[:n] + lands[3:][:max(0, n - len(tops))]

    # ------------------------------------------------------------------
    # Main phase 1 (pre-combat)
    # ------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        """Pre-combat play order: land, haste + prowess creatures,
        then Kumano (for +1/+1 counter on board), then pre-combat burn
        (pumps prowess for combat), then Monstrous Rage on biggest
        attacker."""
        if gs.turn == 1:
            self.reset_game()
        self.reset_turn()

        # 1. Land drop
        self._play_land_if_able(gs)

        # 2. Creatures — cheapest first. Haste/prowess creatures deployed
        # pre-combat so they attack this turn.
        for name in _CREATURES:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                # Give haste to creatures that have it intrinsically
                if name in (PHOENIX, ADVERSARY):
                    card.summoning_sickness = False
                    if KWTag.HASTE not in card.tags:
                        card.tags.add(KWTag.HASTE)
                # Kumano is a Saga — model its ETB: +1/+1 counter on the
                # biggest creature we already control.
                if name == KUMANO:
                    self._apply_kumano_etb(gs)
                break

        # 3. Pre-combat burn — pumps Swiftspear prowess during combat,
        # plus direct face damage. Order cheapest-first so we save
        # 2-cost burn for post-combat if Swiftspear is out.
        self._cast_burn(gs, pre_combat=True)

        # 4. Monstrous Rage on the biggest attacker (if we have one and
        # it's not summoning sick).
        self._try_rage(gs)

    # ------------------------------------------------------------------
    # Main phase 2 (post-combat)
    # ------------------------------------------------------------------

    def main_phase2(self, gs: GameState):
        """Post-combat: any burn we held back now goes face for direct
        damage. Also drop creatures we couldn't fit pre-combat."""
        # Remaining burn → face
        self._cast_burn(gs, pre_combat=False)

        # Any leftover mana: deploy more creatures for next turn
        for name in _CREATURES:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                gs.cast_spell(card)
                break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _cast_burn(self, gs: GameState, pre_combat: bool):
        """Cast burn spells. Pre-combat prioritizes pumping prowess;
        post-combat prioritizes max damage per mana."""
        order = (PLAY_FIRE, LIGHTNING) if pre_combat else (LIGHTNING, PLAY_FIRE)
        # Also include Witchstalker Frenzy if mana allows (hits face when
        # a creature we control has a +1/+1 counter — common after Kumano)
        for name in order:
            for card in list(gs.hand()):
                if card.name != name:
                    continue
                if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    continue
                cost, dmg = _BURN_DAMAGE[name]
                gs.cast_spell(card)
                gs.damage_dealt += dmg
                gs._log(f"  {name}: {dmg} damage to face "
                        f"({gs.damage_dealt} total)")
                break

    def _try_rage(self, gs: GameState):
        """Cast Monstrous Rage on the biggest attackable creature we
        control, if we have Rage in hand and mana for {R}."""
        if self._rage_applied_this_turn:
            return
        for card in list(gs.hand()):
            if card.name != RAGE:
                continue
            if not gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                continue
            # Find the biggest attacker — highest base power, non-sick
            attackers = [
                c for c in gs.zones.creatures_on_battlefield()
                if not c.summoning_sickness or KWTag.HASTE in c.tags
            ]
            if not attackers:
                return
            # Prefer Swiftspear (prowess stacks with Rage) then biggest power
            attackers.sort(
                key=lambda c: (c.name == SWIFTSPEAR, _power_of(c)),
                reverse=True,
            )
            target = attackers[0]
            gs.cast_spell(card)
            # Apply +2/+0 + trample for combat this turn.
            target.counters += 2
            if KWTag.TRAMPLE not in target.tags:
                target.tags.add(KWTag.TRAMPLE)
            self._rage_applied_this_turn = True
            gs._log(f"  Monstrous Rage: {target.name} +2/+0 trample "
                    f"(now {_power_of(target) + target.counters}/)")
            return

    def _apply_kumano_etb(self, gs: GameState):
        """Kumano Faces Kakkazan ETB: put a +1/+1 counter on target
        creature you control. We pick the creature most likely to
        attack (non-sick, highest power)."""
        targets = [
            c for c in gs.zones.creatures_on_battlefield()
            if c.name != KUMANO
        ]
        if not targets:
            return
        # Prefer Swiftspear (prowess), then highest power
        targets.sort(
            key=lambda c: (c.name == SWIFTSPEAR, _power_of(c)),
            reverse=True,
        )
        targets[0].counters += 1
        gs._log(f"  Kumano ETB: +1/+1 counter on {targets[0].name}")


def _is_enchantment(card):
    return "enchantment" in (getattr(card, "type_line", "") or "").lower()


def _power_of(card) -> int:
    try:
        return int(card.power or "0")
    except (ValueError, TypeError):
        return 0
