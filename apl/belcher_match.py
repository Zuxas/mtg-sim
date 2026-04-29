"""
apl/belcher_match.py — Goblin Charbelcher / Landless Belcher (Modern)

Combo: zero lands in deck + Goblin Charbelcher activation = mill until land
not found = deal damage equal to cards revealed. With Sea Gate Restoration
(land face), win T2 consistently.

Kill distribution (from format_config.py): T2 20%, T3 50%, T4 30%.
As opponent: routed to ComboKillSampler via format_config 'combo' set.
"""
from apl.match_apl import MatchAPL
from data.card import Tag


class BelcherMatchAPL(MatchAPL):
    name = "Belcher"
    win_condition_damage = 20
    max_turns = 5

    def keep(self, hand, mulligans, on_play):
        lands = sum(1 for c in hand if c.is_land())
        return lands == 0 or mulligans >= 2  # want zero real lands

    def bottom(self, hand, n):
        # Put lands on bottom — want landless hand
        lands = [c for c in hand if c.is_land()]
        return (lands + [c for c in hand if not c.is_land()])[:n]

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        self._cast_all_castable(gs)

    def respond_to_spell(self, gs, opponent, spell):
        # Disrupting Shoal — pitch spell of same MV to counter (simplified)
        if not spell or not opponent:
            return None
        for c in list(gs.zones.hand):
            if c.name == "Disrupting Shoal":
                spell_mv = getattr(spell, 'cmc', 0)
                pitch = next((x for x in gs.zones.hand
                              if x != c and getattr(x, 'cmc', -1) == spell_mv), None)
                if pitch:
                    gs.zones.hand.remove(pitch); gs.zones.exile.append(pitch)
                    gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                    gs._log(f"  Disrupting Shoal: counter {spell.name} (pitch {pitch.name})")
                    return c
        return None

    def end_step_actions(self, gs, opponent): pass
