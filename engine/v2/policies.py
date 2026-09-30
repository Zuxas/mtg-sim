"""Milestone-one policies. A policy gets an immutable Observation, the complete legal
action list, and its OWN seeded RNG (never the game's). It returns one legal action."""
from __future__ import annotations

import random

from engine.v2 import actions as A


class RandomLegalPolicy:
    """Uniform over legal actions except Concede (fuzzing). Symmetry reduction, if any,
    would live here -- the engine always offers the complete set."""

    uses_observation = False       # uniform choice never reads the observation (skips building it)

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def choose(self, obs, actions):
        # The engine always appends Concede last; uniform over the rest (same choice as
        # filtering it out, without rebuilding the list).
        n = len(actions) - 1 if len(actions) > 1 and isinstance(actions[-1], A.Concede) else len(actions)
        return actions[self.rng.randrange(n)]


class BasicScriptedPolicy:
    """Plays a land, casts the most expensive affordable spell, Bolts the biggest creature
    it kills (else face), counters creature spells with mana value >= 3, attacks with
    creatures that no untapped enemy creature can profitably block, blocks to trade or
    chump when facing lethal, keeps 2-5 land hands."""

    LANDS = {"Plains", "Island", "Mountain", "Forest"}

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choose(self, obs, actions):
        kind = obs.pending[0] if obs.pending else ""
        by = lambda cls: [a for a in actions if isinstance(a, cls)]            # noqa: E731
        me = obs.seat
        names = dict(obs.hand)
        if kind == "mulligan_declare":
            lands = sum(1 for _o, n in obs.hand if n in self.LANDS)
            return by(A.DeclareKeep)[0] if 2 <= lands <= 5 or not by(A.DeclareMulligan) else by(A.DeclareMulligan)[0]
        if kind == "mulligan_bottom":
            n = obs.pending[2][0]
            hand = sorted(obs.hand, key=lambda x: (x[1] in self.LANDS, x[0]))
            lands = [o for o, nm in hand if nm in self.LANDS]
            spells = [o for o, nm in hand if nm not in self.LANDS]
            pick = (lands[3:] + spells[::-1] + lands[:3])[:n]
            want = tuple(pick)
            return next((a for a in by(A.BottomCards) if a.cards == want), by(A.BottomCards)[0])
        if kind == "priority":
            if by(A.PlayLand):
                return by(A.PlayLand)[0]
            casts = by(A.ProposeCast)
            stack_opp = [s for s in obs.stack if s.controller != me]
            if stack_opp:
                cs = [a for a in casts if names.get(a.oid) == "Counterspell"]
                if cs:
                    return cs[0]
            main = [a for a in casts if names.get(a.oid) not in ("Counterspell", "Giant Growth")]
            if names and main and not (obs.step not in ("main1", "main2") and
                                       all(names.get(a.oid) == "Lightning Bolt" for a in main)):
                order = {"Serra Angel": 5, "Hill Giant": 4, "Wind Drake": 3, "Divination": 3, "Grizzly Bears": 2,
                         "Youthful Knight": 2, "Raging Goblin": 1, "Lightning Bolt": 0}
                return max(main, key=lambda a: order.get(names.get(a.oid), 0))
            return by(A.PassPriority)[0]
        if kind == "cast_targets":
            opts = by(A.ChooseTargets)
            foes = {p.oid: p for p in obs.battlefield if p.controller != me}
            creature_t = [a for a in opts if a.targets[0][0] == "obj" and a.targets[0][1] in foes]
            if creature_t:
                return max(creature_t, key=lambda a: foes[a.targets[0][1]].power or 0)
            face = [a for a in opts if a.targets[0] == ("player", 1 - me)]
            stack_t = [a for a in opts if a.targets[0][0] == "stack"]
            mine = [a for a in opts if a.targets[0][0] == "obj"]
            return (stack_t or face or mine or opts)[0]
        if kind == "cast_mana":
            pay = by(A.PayCost)
            return pay[0] if pay else by(A.ActivateManaAbility)[0]
        if kind == "declare_attack":
            oid = obs.pending[2][0]
            me_p = next(p for p in obs.battlefield if p.oid == oid)
            blockers = [p for p in obs.battlefield if p.controller != me and not p.tapped and p.power is not None]
            safe = all((b.power or 0) < (me_p.toughness or 0) for b in blockers)
            return next(a for a in by(A.ChooseAttack) if a.attacks == safe)
        if kind == "declare_block":
            opts = by(A.ChooseBlock)
            blocker = next(p for p in obs.battlefield if p.oid == obs.pending[2][0])
            att = {p.oid: p for p in obs.battlefield if p.oid in obs.attackers}
            good = [a for a in opts if a.attacker is not None and (blocker.power or 0) >= (att[a.attacker].toughness or 0)]
            return (good or [a for a in opts if a.attacker is None])[0]
        if kind == "assign_damage":
            return by(A.AssignCombatDamage)[0]
        if kind == "discard":
            return by(A.DiscardToHandSize)[0]
        return [a for a in actions if not isinstance(a, A.Concede)][0]
