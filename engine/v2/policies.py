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


class SimpleAggroPolicy:
    """A simple, untuned, seeded legal player for validation logs (milestone two). It only ever
    returns one of the offered actions and knows only public card types. Plays a land, casts
    what it can (burn at the opponent's face, creatures, Boros Charm's damage mode), activates
    fetch lands, attacks with everything, never blocks, pays for shock lands above 10 life,
    always casts a suspended card, keeps 2-4-land hands. Milestone four (generic, untuned): plots like
    it suspends, floats mana to equip an unattached Equipment, pumps its own creatures, attaches the
    flurry token, makes library decisions at random (seeded). Not tuned for win rate."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)
        from engine.v2.cards import definitions
        defs = definitions()
        self.lands = {n for n, d in defs.items() if d.is_land}
        self.equipment = {n for n, d in defs.items() if "Equipment" in d.subtypes}
        self.pumps = {n for n, d in defs.items() if d.effect_key in ("giant_growth", "mutagenic_growth", "violent_urge")}

    def choose(self, obs, actions):
        kind = obs.pending[0] if obs.pending else ""
        me, opp = obs.seat, 1 - obs.seat
        by = lambda cls: [a for a in actions if isinstance(a, cls)]            # noqa: E731
        names = dict(obs.hand)
        if kind == "mulligan_declare":
            n = sum(1 for _o, nm in obs.hand if nm in self.lands)
            keep = 2 <= n <= 4 or obs.mull_counts[me] >= 2 or not by(A.DeclareMulligan)
            return by(A.DeclareKeep)[0] if keep else by(A.DeclareMulligan)[0]
        if kind == "mulligan_bottom":                                   # bottom spells, keep up to 3 lands
            lands = {o for o, nm in obs.hand if nm in self.lands}
            want_lands_kept = min(3, len(lands))
            def score(a):
                kept_lands = len(lands - set(a.cards))
                return (abs(kept_lands - want_lands_kept), a.cards)
            return min(by(A.BottomCards), key=score)
        if kind == "priority":
            mine_turn = obs.active == me and obs.step in ("main1", "main2")
            if by(A.PlayLand):
                return by(A.PlayLand)[0]
            if mine_turn and not obs.stack:
                fetch = [a for a in by(A.ActivateAbility) if obs.life[me] > 5]
                casts = by(A.ProposeCast) + by(A.Suspend) + by(A.Plot)
                if casts:
                    return self.rng.choice(casts)
                if fetch:
                    return fetch[0]
                float_ = self._float_for_equip(obs, by(A.ActivateManaAbility))
                if float_ is not None:
                    return float_
            if obs.stack and obs.stack[-1].controller == opp:
                burn = [a for a in by(A.ProposeCast) if names.get(a.oid) in ("Lightning Bolt", "Lightning Helix",
                                                                          "Boros Charm", "Skullcrack")]
                if burn and self.rng.random() < 0.5:
                    return burn[0]
            return by(A.PassPriority)[0]
        if kind == "cast_mode":
            modes = by(A.ChooseMode)
            return next((a for a in modes if a.mode == 0), modes[0])
        if kind == "cast_targets":
            opts = by(A.ChooseTargets)
            if obs.stack and obs.stack[-1].name in self.pumps:              # pump spells: own creatures
                mine = [a for a in opts if a.targets[0][0] == "obj" and a.targets[0][1] in
                        {p.oid for p in obs.battlefield if p.controller == me}]
                if mine:
                    return self.rng.choice(mine)
            face = [a for a in opts if a.targets[0] == ("player", opp)]
            foes = [a for a in opts if a.targets[0][0] == "obj" and a.targets[0][1] in
                    {p.oid for p in obs.battlefield if p.controller == opp}]
            return (face or foes or opts)[0]
        if kind == "cast_mana":
            pay = by(A.PayCost)
            return pay[0] if pay else by(A.ActivateManaAbility)[0]
        if kind == "declare_attack":
            return next(a for a in by(A.ChooseAttack) if a.attacks)
        if kind == "declare_block":
            return next(a for a in by(A.ChooseBlock) if a.attacker is None)
        if kind == "entry_payment":
            pays = [a for a in by(A.ChooseEntryPayment) if a.pay]
            return pays[0] if pays and obs.life[me] > 10 else by(A.ChooseEntryPayment)[0]
        if kind == "search_choice":
            found = [a for a in by(A.ChooseSearchResult) if a.oid is not None]
            return found[0] if found else by(A.ChooseSearchResult)[0]
        if kind == "suspend_cast_choice":
            return next((a for a in by(A.ChooseSuspendCast) if a.cast), by(A.ChooseSuspendCast)[0])
        if kind == "arrange":
            return self.rng.choice(by(A.ArrangeCards))
        if kind == "attach_choice":
            return next(a for a in by(A.ChooseAttach) if a.attach)
        return [a for a in actions if not isinstance(a, A.Concede)][0]

    def _float_for_equip(self, obs, mana_acts):
        """Float {1}{R} for an equip when an Equipment is unattached and a creature could carry it."""
        me = obs.seat
        attached = {e for e, _c in obs.attachments}
        free_eq = [p for p in obs.battlefield if p.controller == me and p.name in self.equipment and p.oid not in attached]
        creatures = [p for p in obs.battlefield if p.controller == me and p.power is not None]
        pool = dict(obs.my_pool)
        if not free_eq or not creatures or sum(pool.values()) >= 2 or len(mana_acts) < 2 - sum(pool.values()):
            return None
        red = [a for a in mana_acts if a.color == "R"]
        if not pool.get("R") and red:
            return red[0]
        return mana_acts[0] if pool.get("R") else None
