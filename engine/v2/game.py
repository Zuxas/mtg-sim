"""The v2 game state machine (spec revision 4).

Game.new(...) -> pending() / legal_actions() / observe(seat) / apply(action) / run(policies).
Every state change goes through engine.v2.reducer.commit (atomic transitions).
"""
from __future__ import annotations

import platform
import random
from itertools import combinations, permutations

from engine.v2 import ENGINE_VERSION
from engine.v2 import abilities as AB
from engine.v2 import actions as A
from engine.v2 import reducer
from engine.v2.cards import definitions, definitions_hash, oracle_file_sha256, validate_deck
from engine.v2.effects import EFFECTS, EffectContext
from engine.v2.effects import facts as effect_facts
from engine.v2.observation import observe as _observe
from engine.v2.ops import op
from engine.v2.rules import casting, combat, replacement, sba
from engine.v2.rules.mana import (Avail, activatable_mana_options, avail_from, can_pay,
                                  payment_assignments, sources_with_options)
from engine.v2.state import GameState

STEPS = ("untap", "upkeep", "draw", "main1", "begin_combat", "declare_attackers", "declare_blockers",
         "first_strike_damage", "combat_damage", "end_combat", "main2", "end", "cleanup")
RNG_ALGORITHM = f"python-random-mt19937/{platform.python_version()}"
_ALT_KEYS = frozenset(AB.SPECTACLE) | frozenset(AB.SUSPEND)
_ACTS: dict = {}
_PRIO_OPS: dict = {}


def _priority_ops(player, passes) -> tuple:
    k = (player, passes)
    ops = _PRIO_OPS.get(k)
    if ops is None:
        ops = _PRIO_OPS[k] = (op("priority", player, passes), op("pending", "priority", player))
    return ops


def _act(cls, *args):
    """Interned action value: actions are frozen, so equal ones may share one object (avoids
    rebuilding the same options on every decision). Bounded."""
    k = (cls, args)
    a = _ACTS.get(k)
    if a is None:
        if len(_ACTS) > 50000:
            _ACTS.clear()
        a = _ACTS[k] = cls(*args)
    return a


class IllegalAction(ValueError):
    pass


class GameOver(RuntimeError):
    pass


def rules_meta() -> dict:
    import json
    import os
    from engine.v2.cards import RR
    return json.load(open(os.path.join(RR, "RULES.json"), encoding="utf-8"))


class Game:
    def __init__(self, state: GameState):
        self.s = state
        self.actions: list = []
        self.action_transition_index: list = []  # transition count when each action was applied
        self._legal_cache = (None, None)
        self._sba_clean_at = -1          # log length at the last SBA check that found nothing

    # ================================================================ construction
    @classmethod
    def new(cls, deck_a, deck_b, seed: int, starting_mode: str = "explicit", starting_player: int = 0,
            turn_limit: int = 50, check_invariants: bool = False) -> "Game":
        validate_deck(deck_a)
        validate_deck(deck_b)
        defs = definitions()
        rm = rules_meta()
        config = {
            "engine_version": ENGINE_VERSION, "rules_effective": rm["effective_date"], "rules_sha256": rm["sha256"],
            "definitions_hash": definitions_hash(defs), "oracle_file_sha256": oracle_file_sha256(),
            "rng_algorithm": RNG_ALGORITHM, "seed": seed, "starting_mode": starting_mode,
            "starting_player": starting_player, "turn_limit": turn_limit,
            "decks": [list(deck_a), list(deck_b)], "check_invariants": check_invariants,
        }
        s = GameState(config=config, rng=random.Random(seed))       # empty zones by construction
        g = cls(s)
        g._setup()
        return g

    def _commit(self, kind, ops):
        reducer.commit(self.s, kind, ops)

    def _setup(self):
        s = self.s
        ops = [op("create_card", p, name) for p, deck in enumerate(s.config["decks"]) for name in deck]
        ops.append(op("starting_player", s.config["starting_mode"], s.config["starting_player"]))
        self._commit("setup_cards", ops)
        order = (s.starting_player, 1 - s.starting_player)
        ops = [op("shuffle", p) for p in order]                         # CR 103.3
        ops += [op("draw", p) for p in order for _ in range(7)]         # CR 103.5 (7 cards)
        self._commit("setup_draw", ops)
        self._mulligan_next()

    def _order(self):
        return (self.s.starting_player, 1 - self.s.starting_player)

    # ================================================================ public API
    def pending(self):
        return self.s.pending

    @property
    def result(self):
        return self.s.result

    def observe(self, seat: int):
        return _observe(self.s, seat)

    def legal_actions(self) -> list:
        key = len(self.s.log.transitions)
        if self._legal_cache[0] == key:
            return self._legal_cache[1]
        acts = self._compute_legal()
        self._legal_cache = (key, acts)
        return acts

    def apply(self, action) -> None:
        if self.s.result is not None:
            raise GameOver(self.s.result)
        if action not in self.legal_actions():
            raise IllegalAction(f"{action!r} is not a legal action now ({self.s.pending})")
        # One transaction per action: if any transition inside it fails (handler or invariant),
        # the state, RNG, id counters, event log and this action record all return to their
        # values before the action, and the error propagates.
        n, legal_cache, sba_clean_at = len(self.actions), self._legal_cache, self._sba_clean_at
        if not reducer.begin(self.s):
            raise reducer.EngineInvariantError("transaction already open at apply")
        try:
            self.actions.append(action)
            self.action_transition_index.append(len(self.s.log.transitions))
            getattr(self, "_do_" + type(action).__name__)(action)
        except BaseException:
            reducer.rollback(self.s)
            self._legal_cache, self._sba_clean_at = legal_cache, sba_clean_at
            del self.actions[n:]
            del self.action_transition_index[n:]
            raise
        reducer.end(self.s)

    def run(self, policies, max_actions: int = 200000):
        n = 0
        while self.s.result is None:
            p = self.s.pending.player
            pol = policies[p]
            obs = self.observe(p) if getattr(pol, "uses_observation", True) else None
            a = pol.choose(obs, self.legal_actions())
            self.apply(a)
            n += 1
            if n > max_actions:
                raise RuntimeError("action budget exceeded")
        return self.s.result

    # ================================================================ legal actions
    def _compute_legal(self) -> list:
        s = self.s
        pd = s.pending
        if s.result is not None or pd is None:
            return []
        p, k = pd.player, pd.kind
        out: list = []
        if k == "mulligan_declare":
            out = [A.DeclareKeep(p)] + ([A.DeclareMulligan(p)] if s.mull_count[p] < 7 else [])   # CR 103.5
        elif k == "mulligan_bottom":
            n = s.mull_count[p]
            out = [A.BottomCards(p, perm) for perm in permutations(s.zones[(p, "hand")], n)]
        elif k == "priority":
            hand = s.zones[(p, "hand")]
            timing = casting.sorcery_timing_ok(s, p)
            srcs = sources_with_options(s, p)
            avail = avail_from(s, p, srcs)
            out = [_act(A.PassPriority, p)]
            if timing and s.land_played[p] == 0:
                out += [_act(A.PlayLand, p, oid) for oid in hand if casting.can_play_land(s, p, oid)]
            out += [_act(A.ActivateManaAbility, p, oid, c) for oid, opts in srcs for c, _l in opts]
            out += self._activation_actions(p, timing)
            tgt: dict = {}
            out += [_act(A.ProposeCast, p, oid) for oid in hand if casting.can_propose_cast(s, p, oid, avail, timing, tgt)]
            defs, objs = s.def_by_ciid, s.objects
            for oid in hand:
                key = defs[objs[oid].ciid].effect_key
                if key not in _ALT_KEYS:
                    continue
                if key in AB.SPECTACLE and casting.spectacle_ok(s, p) and \
                        casting.can_propose_cast(s, p, oid, avail, timing, tgt, AB.SPECTACLE[key]):
                    out.append(A.ProposeCast(p, oid, "spectacle"))                       # CR 702.137a
                if key in AB.SUSPEND and casting.can_suspend(s, p, oid, timing):
                    out += [A.Suspend(p, oid, asg) for asg in payment_assignments(AB.SUSPEND[key][1], s.pools[p])]
        elif k == "cast_mode":
            e = s.stack[-1]
            key = s.definition(e.ciid, is_ciid=True).effect_key
            out = [A.ChooseMode(p, m) for m in casting.castable_modes(s, key, exclude_sid=e.sid)]
        elif k == "cast_targets":
            e = s.stack[-1]
            key = s.definition(e.ciid, is_ciid=True).effect_key
            out = [A.ChooseTargets(p, t) for t in casting.target_choices(s, key, e.mode, exclude_sid=e.sid)]
        elif k == "cast_mana":
            e = s.stack[-1]
            d = s.definition(e.ciid, is_ciid=True)
            out = self._completing_mana_actions(p, s.open_cast["cost"])
            out += [A.PayCost(p, asg) for asg in payment_assignments(s.open_cast["cost"], s.pools[p])]
        elif k == "declare_attack":
            oid = pd.info[0]
            out = [_act(A.ChooseAttack, p, oid, True), _act(A.ChooseAttack, p, oid, False)]
        elif k == "declare_block":
            b = pd.info[0]
            out = [A.ChooseBlock(p, b, None)] + [A.ChooseBlock(p, b, a) for a in s.attackers
                                                 if a in s.objects and combat.can_block(s, b, a)]
        elif k == "assign_damage":
            a, blockers, power = pd.info
            out = [A.AssignCombatDamage(p, a, div) for div in combat.divisions(power, list(blockers))]
        elif k == "discard":
            n = pd.info[0]
            out = [A.DiscardToHandSize(p, c) for c in combinations(sorted(s.zones[(p, "hand")]), n)]
        elif k == "search_choice":
            c = s.continuation
            out = [A.ChooseSearchResult(p, None)]                         # CR 701.23b: may fail to find
            out += [A.ChooseSearchResult(p, oid) for oid in sorted(s.zones[(p, "library")])
                    if AB.fetch_matches(s, c.data[0], oid)]
        elif k == "suspend_cast_choice":
            out = [A.ChooseSuspendCast(p, False)]                         # "If you don't, it remains exiled."
            oid = s.continuation.data[0]
            if casting.target_choices(s, s.definition(oid).effect_key):  # "if able" (legal targets exist)
                out.append(A.ChooseSuspendCast(p, True))
        elif k == "entry_payment":
            oid = pd.info[0]
            out = [A.ChooseEntryPayment(p, oid, False)]                  # the tapped result is always allowed
            if replacement.can_pay_shock(s, p):
                out.append(A.ChooseEntryPayment(p, oid, True))           # CR 119.4
        elif k == "order_triggers":
            out = [A.OrderTrigger(p, tid) for tid in pd.info]
        elif k == "trigger_targets":
            tid = pd.info[0]
            t = next(x for x in s.pending_triggers if x.tid == tid)
            out = [A.ChooseTriggerTargets(p, tid, (tg,))
                   for tg in casting.options_for_kinds(s, AB.SPEC_BY_KEY[t.key].targets)]
        out.append(_act(A.Concede, p))                                    # always legal
        return out

    def _completing_mana_actions(self, p, cost) -> list:
        """Mana abilities during 601.2g, limited to those after which the announced cost is still
        payable: a choice that made it unpayable would make the cast illegal and be rewound
        (CR 733), and the engine offers only actions with a legal completion (spec 7.4)."""
        s = self.s
        srcs = sources_with_options(s, p)
        opts_all = [opts for _oid, opts in srcs]
        out = []
        for i, (oid, opts) in enumerate(srcs):
            if len(opts) == 1 and opts[0][1] == 0:
                # one free colour: tapping it only moves one mana from a source to the pool,
                # so a payable cost stays payable -- no check needed
                out.append(_act(A.ActivateManaAbility, p, oid, opts[0][0]))
                continue
            rest = tuple(opts_all[:i] + opts_all[i + 1:])
            for c, life in opts:
                pool = dict(s.pools[p])
                pool[c] = pool.get(c, 0) + 1
                if can_pay(cost, Avail(pool, rest, s.life[p] - life)):    # life left after this activation
                    out.append(_act(A.ActivateManaAbility, p, oid, c))
        return out

    def _activation_actions(self, p, timing) -> list:
        """Every completely payable activation (CR 602.2, 118.3): tap / life / sacrifice / pool mana."""
        s = self.s
        out = []
        objs, defs, activated = s.objects, s.def_by_ciid, AB.ACTIVATED
        for oid in s.zones[("bf",)]:
            o = objs[oid]
            if o.controller != p:
                continue
            specs = activated.get(defs[o.ciid].effect_key)
            if not specs:
                continue
            for i, spec in enumerate(specs):
                if (spec.tap and o.tapped) or s.life[p] < spec.life or (spec.sorcery_speed and not timing):
                    continue
                out += [A.ActivateAbility(p, oid, i, asg) for asg in payment_assignments(spec.mana, s.pools[p])]
        return out

    # ================================================================ mulligans (CR 103.5, staged)
    def _mulligan_next(self):
        s = self.s
        for p in self._order():
            if not s.kept[p] and p not in s.mull_declared:
                self._commit("pending", [op("pending", "mulligan_declare", p)])
                return
        self._mulligan_execute()

    def _do_DeclareKeep(self, a):
        self._commit("mulligan_declare", [op("mull_declare", a.player, "keep"), op("keep", a.player)])
        self._mulligan_next()

    def _do_DeclareMulligan(self, a):
        self._commit("mulligan_declare", [op("mull_declare", a.player, "mulligan")])
        self._mulligan_next()

    def _mulligan_execute(self):
        s = self.s
        muls = [p for p in self._order() if s.mull_declared.get(p) == "mulligan"]
        if not muls:
            self._start_game()
            return
        ops = []
        for p in muls:                                                    # simultaneous (one transition)
            ops += [op("move", oid, "library", "end") for oid in list(s.zones[(p, "hand")])]
            ops.append(op("shuffle", p))
            ops += [op("draw", p) for _ in range(7)]
            ops.append(op("mull_count_inc", p))
        ops.append(op("mull_round_reset"))
        ops.append(op("set", "mull_stage", "bottom"))
        ops.append(op("set", "mull_round", tuple(muls)))
        self._commit("mulligan_execute", ops)
        self._mulligan_bottom_next()

    def _mulligan_bottom_next(self):
        s = self.s
        for p in s.mull_round:
            if p not in s.mull_bottoms:
                self._commit("pending", [op("pending", "mulligan_bottom", p, (s.mull_count[p],))])
                return
        ops = []
        for p in s.mull_round:                                            # simultaneous commit
            ops += [op("move", oid, "library", "end") for oid in s.mull_bottoms[p]]
        ops += [op("clear_bottoms"), op("set", "mull_stage", "declare"), op("set", "mull_round", ())]
        self._commit("mulligan_commit", ops)
        if all(s.kept):
            self._start_game()
        else:
            self._mulligan_next()

    def _do_BottomCards(self, a):
        self._commit("mulligan_bottom_choice", [op("store_bottom", a.player, a.cards)])
        self._mulligan_bottom_next()

    def _start_game(self):
        self._enter_step("untap", [op("set", "mull_stage", "done"), op("begin_turn", 1, self.s.starting_player)])

    # ================================================================ turn structure
    def _enter_step(self, step, carry=()):
        """Begin `step`. `carry` = ops ending the previous step (pool emptying, CR 500.5) or
        beginning the turn; they commit in the SAME atomic transition as the step's start."""
        s = self.s
        ops = list(carry) + [op("set", "step", step)]
        if step == "untap":                                               # CR 502.3, no priority (117.3a)
            ops.append(op("untap_all"))           # player read at APPLY time: carry may begin the turn
            self._commit("step", ops)
            self._leave_step()
            return
        if step == "draw":
            if not (s.turn == 1 and s.active == s.starting_player):        # CR 103.8a
                ops.append(op("draw", s.active))                           # CR 504.1
            self._commit("step", ops)
            self._give_priority(s.active)
            return
        if step == "declare_attackers":
            self._commit("step", ops)
            self._attack_next()
            return
        if step == "declare_blockers":
            self._commit("step", ops)
            self._block_next()
            return
        if step in ("first_strike_damage", "combat_damage"):
            self._commit("step", ops)
            self._combat_damage(first_step=(step == "first_strike_damage"))
            return
        if step == "cleanup":
            self._commit("step", ops)
            self._cleanup()
            return
        self._commit("step", ops)
        self._give_priority(s.active)

    def _leave_step(self):
        s = self.s
        carry = [op("empty_pools")]                                        # CR 500.5, 106.4
        if s.step == "end_combat":
            carry.append(op("clear_combat"))
        nxt = self._next_step(s.step)
        if nxt is None:
            self._next_turn(carry)
        else:
            self._enter_step(nxt, carry)

    def _next_step(self, step):
        s = self.s
        if step == "cleanup":
            return None
        if step == "declare_attackers" and not s.attackers:              # CR 508.8
            return "end_combat"
        if step == "declare_blockers":
            return "first_strike_damage" if combat.any_first_strike(s) else "combat_damage"   # CR 510.4
        if step == "first_strike_damage":
            return "combat_damage"
        return STEPS[STEPS.index(step) + 1]

    def _next_turn(self, carry=()):
        s = self.s
        if s.turn >= s.config["turn_limit"]:
            self._commit("game_end", list(carry) + [op("end_game", ("draw", "turn_limit"))])
            return
        self._enter_step("untap", list(carry) + [op("begin_turn", s.turn + 1, 1 - s.active)])

    # ================================================================ priority (CR 117)
    def _give_priority(self, player, passes=0):
        """CR 117.5: state-based actions, then triggered abilities go on the stack (603.3b),
        repeated until neither happens; then `player` receives priority."""
        s = self.s
        while True:
            self._run_sbas()
            if s.result is not None:
                return
            if not s.pending_triggers:
                break
            if not self._stack_triggers(player):
                return                                                    # waiting for a stacking decision
            passes = 0                                                    # the stack changed (CR 117.4)
        ops = list(_priority_ops(player, passes))
        if s.priority_resume is not None:
            ops.append(op("priority_resume", None))
        self._commit("priority", ops)

    def _stack_triggers(self, player) -> bool:
        """Put every pending trigger on the stack, active player's first (APNAP, CR 603.3b).
        Returns False when a player must decide (order or targets); the decision resumes here."""
        s = self.s
        for p in (s.active, 1 - s.active):
            while True:
                mine = [t for t in s.pending_triggers if t.controller == p]
                if not mine:
                    break
                if len(mine) >= 2:
                    self._commit("pending", [op("priority_resume", (player,)),
                                             op("pending", "order_triggers", p, tuple(t.tid for t in mine))])
                    return False
                if not self._stack_one(mine[0], player):
                    return False
        return True

    def _stack_one(self, t, player) -> bool:
        spec = AB.SPEC_BY_KEY[t.key]
        if spec.targets:                                                   # CR 603.3d
            if not casting.options_for_kinds(self.s, spec.targets):
                self._commit("trigger_stack", [op("drop_trigger", t.tid, "no_legal_targets")])
                return True
            self._commit("pending", [op("priority_resume", (player,)),
                                     op("pending", "trigger_targets", t.controller, (t.tid,))])
            return False
        self._commit("trigger_stack", [op("stack_trigger", t.tid)])
        return True

    def _do_OrderTrigger(self, a):
        s = self.s
        t = next(x for x in s.pending_triggers if x.tid == a.tid)
        if not self._stack_one(t, s.priority_resume[0]):
            return
        self._give_priority(s.priority_resume[0])

    def _do_ChooseTriggerTargets(self, a):
        s = self.s
        self._commit("trigger_stack", [op("stack_trigger", a.tid, a.targets)])
        self._give_priority(s.priority_resume[0])

    def _run_sbas(self):
        s = self.s
        # CR 117.5 needs the check before every priority grant; if no transition since the last
        # empty check contained an op that can create an SBA condition, the result cannot differ.
        if self._sba_clean_at >= 0 and s.sba_dirty_at < self._sba_clean_at:
            if s.config["check_invariants"]:                              # verify the skip is sound
                ops, _l = sba.compute(s)
                if ops:
                    raise reducer.EngineInvariantError(f"skipped SBA check would have applied {ops}")
            return
        while s.result is None:
            ops, losers = sba.compute(s)
            if not ops:
                self._sba_clean_at = len(s.log.transitions)
                return
            if losers:
                lost = {p for p, _ in losers}
                if len(lost) == 2:                                        # CR 104.4a
                    ops.append(op("end_game", ("draw", "simultaneous_loss")))
                else:
                    (p, reason), = losers
                    ops.append(op("end_game", ("win", 1 - p, reason)))
            self._commit("sba", ops)

    def _do_PassPriority(self, a):
        s = self.s
        passes = s.passes + 1
        if passes >= 2:                                                   # CR 117.4
            if s.stack:
                if self._resolve_top() and s.result is None:              # False: paused for a choice
                    self._give_priority(s.active)                         # CR 117.3b
            else:
                self._leave_step()
        else:
            self._give_priority(1 - a.player, passes)

    def _do_Concede(self, a):
        self._commit("concede", [op("lose", a.player, "concede"), op("end_game", ("win", 1 - a.player, "concede"))])

    def _do_PlayLand(self, a):
        if replacement.needs_entry_choice(self.s, a.oid):                # CR 614.12: choose before it enters
            self._commit("entry_choice", [op("pending_entry", (a.oid, a.player, "play")),
                                          op("pending", "entry_payment", a.player, (a.oid,))])
            return
        self._commit("play_land", self._land_entry_ops(a.oid, a.player, False) + [op("land_played", a.player)])
        self._give_priority(a.player)                                     # CR 117.3c

    def _land_entry_ops(self, oid, controller, pay) -> list:
        """The land's zone change with its replacement effects applied (one transition)."""
        tapped = replacement.enters_tapped(self.s, oid, controller, pay)
        ops = [op("pay_life", controller, replacement.SHOCK_LIFE)] if pay else []
        return ops + [op("move", oid, "battlefield", "end", controller, tapped)]

    def _do_ChooseEntryPayment(self, a):
        s = self.s
        oid, player, origin = s.pending_entry
        ops = [op("pending_entry", None)] + self._land_entry_ops(oid, player, a.pay)
        if origin == "play":
            self._commit("play_land", ops + [op("land_played", player)])
            self._give_priority(player)
            return
        self._continue_resolution(ops)                                    # S3: a fetched shock land

    def _do_ActivateManaAbility(self, a):
        s = self.s
        life = dict(activatable_mana_options(s, a.player, a.oid))[a.color]
        ops = [op("tap", a.oid)]
        if life:
            ops.append(op("pay_life", a.player, life))                    # CR 119.4 (part of the cost)
        ops.append(op("add_mana", a.player, a.color, 1))
        if s.open_cast is not None:                                       # CR 601.2g, 605.3a
            ops.append(op("record_activation", a.oid, a.color, life))
            self._commit("mana_ability", ops)
            return
        self._commit("mana_ability", ops)
        self._give_priority(a.player)

    def _do_ActivateAbility(self, a):
        """CR 602.2: the ability goes on the stack and its whole cost is paid in ONE atomic
        transition; a sacrificed source leaves the ability on the stack (CR 113.7a)."""
        s = self.s
        o = s.objects[a.oid]
        spec = AB.ACTIVATED[s.definition(a.oid).effect_key][a.index]
        ops = [op("push_ability", a.player, o.ciid, a.oid, spec.key, (), ())]
        ops += [op("spend_mana", a.player, c, n) for c, n in a.assignment]
        if spec.tap:
            ops.append(op("tap", a.oid))
        if spec.life:
            ops.append(op("pay_life", a.player, spec.life))
        if spec.sacrifice:
            ops.append(op("sacrifice", a.oid))
        self._commit("activate", ops)
        self._give_priority(a.player)                                     # CR 117.3c

    # ================================================================ casting (CR 601.2, open transaction)
    def _do_ProposeCast(self, a):
        s = self.s
        key = s.definition(a.oid).effect_key
        cost = AB.SPECTACLE[key] if a.cost == "spectacle" else None
        ops = [op("open_cast", a.oid, a.player, a.cost, cost)]            # CR 601.2a-b
        nxt = "cast_mode" if key in casting.MODAL else ("cast_targets" if casting.target_slots(key) else "cast_mana")
        ops.append(op("pending", nxt, a.player))
        self._commit("cast_propose", ops)

    def _do_ChooseMode(self, a):
        s = self.s
        e = s.stack[-1]
        key = s.definition(e.ciid, is_ciid=True).effect_key
        nxt = "cast_targets" if casting.target_slots(key, a.mode) else "cast_mana"
        self._commit("cast_mode", [op("set_mode", e.sid, a.mode), op("pending", nxt, a.player)])   # CR 601.2b

    def _do_ChooseTargets(self, a):
        self._commit("cast_targets", [op("set_targets", self.s.stack[-1].sid, a.targets),
                                      op("pending", "cast_mana", a.player)])          # CR 601.2c

    def _do_PayCost(self, a):
        s = self.s
        ops = [op("spend_mana", a.player, c, n) for c, n in a.assignment]  # CR 601.2h
        ops.append(op("commit_cast"))                                     # CR 601.2i
        c = s.continuation
        if c is not None and c.kind == "suspend":                         # cast during resolution (CR 608.2g):
            AB.check_continuation(c)                                      # no priority; the trigger finishes
            trig = s.entry(c.sid)
            self._commit("cast", ops)
            self._commit("resolve", [op("set_continuation", None), op("remove_entry", trig.sid),
                                     op("note", "AbilityResolved", trig.sid)])
            if s.result is None:
                self._give_priority(s.active)
            return
        self._commit("cast", ops)
        self._give_priority(a.player)                                     # CR 117.3c

    def _do_Suspend(self, a):
        """CR 116.2f / 702.62a: pay {R}, exile with N time counters; no stack; priority stays."""
        s = self.s
        n, _cost = AB.SUSPEND[s.definition(a.oid).effect_key]
        ops = [op("spend_mana", a.player, c, k) for c, k in a.assignment]
        ops += [op("note", "Suspended", a.oid), op("exile_with_counters", a.oid, "time", n)]
        self._commit("special_action", ops)
        self._give_priority(a.player)

    def _do_ChooseSuspendCast(self, a):
        s = self.s
        c = s.continuation
        AB.check_continuation(c)
        oid = c.data[0]
        if not a.cast:
            self._commit("resolve", [op("set_continuation", None), op("note", "SuspendDeclined", oid),
                                     op("remove_entry", c.sid), op("note", "AbilityResolved", c.sid)])
            if s.result is None:
                self._give_priority(s.active)
            return
        key = s.definition(oid).effect_key                                # "without paying its mana cost"
        nxt = "cast_targets" if casting.target_slots(key) else "cast_mana"
        self._commit("cast_propose", [op("open_cast", oid, a.player, "free", ()), op("pending", nxt, a.player)])

    def rollback_open_cast(self, reason: str, reverse_mana: bool = True):
        """CR 733.1 / 733.2: reverse an illegal or uncompletable proposal. Milestone one
        offers ProposeCast only when completable, so this path is reached only through
        fault injection. The player who had priority retains it (the reverted state
        restores the pre-proposal pending decision)."""
        self._commit("rollback", [op("note", "RollbackReason", reason), op("revert_cast", reverse_mana)])

    # ================================================================ resolution (CR 608)
    def _resolve_ability(self, e) -> bool:
        s = self.s
        if not AB.still_true(s, e):                                       # CR 603.4
            self._commit("resolve", [op("remove_entry", e.sid), op("note", "AbilityRemoved", e.sid)])
            return True
        if e.targets:                                                     # CR 608.2b
            kinds = AB.ability_targets(e.ability)
            legal = [t for t in e.targets if casting.target_still_legal_kinds(s, t, kinds)]
            if not legal:
                self._commit("resolve", [op("remove_entry", e.sid), op("note", "AbilityFizzled", e.sid)])
                return True
        if e.ability == "suspend_cast":                                   # paused: may cast it (CR 702.62a)
            self._commit("resolve_pause", [
                op("set_continuation", AB.continuation("suspend", e.sid, "choose", (e.source,))),
                op("pending", "suspend_cast_choice", e.controller, (e.source,))])
            return False
        if e.ability in AB.FETCH_TYPES:                                   # paused: the searcher chooses
            self._commit("resolve_pause", [
                op("set_continuation", AB.continuation("fetch", e.sid, "search", (e.ability,))),
                op("pending", "search_choice", e.controller, (e.sid,))])
            return False
        ops = AB.RESOLVE[e.ability](AB.context(s, e))
        ops += [op("remove_entry", e.sid), op("note", "AbilityResolved", e.sid)]
        self._commit("resolve", ops)
        return True

    def _do_ChooseSearchResult(self, a):
        s = self.s
        c = s.continuation
        AB.check_continuation(c)
        if a.oid is None:
            self._continue_resolution([op("note", "SearchFoundNothing", c.sid)])
            return
        if replacement.needs_entry_choice(s, a.oid):                     # fetched shock land: choose first
            self._commit("resolve_pause", [
                op("note", "SearchFound", c.sid, a.oid),
                op("set_continuation", AB.continuation("fetch", c.sid, "entry", c.data + (a.oid,))),
                op("pending_entry", (a.oid, a.player, "fetch")),
                op("pending", "entry_payment", a.player, (a.oid,))])
            return
        self._continue_resolution([op("note", "SearchFound", c.sid, a.oid)]
                                  + self._land_entry_ops(a.oid, a.player, False))

    def _continue_resolution(self, ops):
        """Finish a paused fetch: put the card onto the battlefield (if any), THEN shuffle
        (even when nothing was found), remove the ability, give priority (CR 117.3b)."""
        s = self.s
        c = s.continuation
        AB.check_continuation(c)
        e = s.entry(c.sid)
        ops = list(ops) + [op("shuffle", e.controller), op("set_continuation", None),
                           op("remove_entry", e.sid), op("note", "AbilityResolved", e.sid)]
        self._commit("resolve", ops)
        if s.result is None:
            self._give_priority(s.active)

    def _resolve_top(self) -> bool:
        """Resolve the top object; False if it paused for a player's choice."""
        s = self.s
        e = s.stack[-1]
        if e.state == "ability":
            return self._resolve_ability(e)
        d = s.definition(e.ciid, is_ciid=True)
        if d.is_permanent_spell:                                          # CR 608.3a, 110.2
            ops = [op("remove_entry", e.sid), op("move", e.oid, "battlefield", "end", e.controller),
                   op("note", "SpellResolved", e.sid)]
            self._commit("resolve", ops)
            return True
        ok = [casting.slot_still_legal(s, d.effect_key, i, t, e.targets) for i, t in enumerate(e.targets)]
        legal = [t for t, good in zip(e.targets, ok) if good]                              # CR 608.2b
        if e.targets and not legal:
            self._commit("resolve", [op("remove_entry", e.sid), op("move", e.oid, "graveyard", "end"),
                                     op("note", "SpellFizzled", e.sid)])
            return True
        ctx_targets = tuple(t if t[0] != "stack" else ("stack", t[1], s.entry(t[1]).oid) for t in legal)
        slots = tuple(t if good else None for t, good in zip(e.targets, ok))
        ops = EFFECTS[d.effect_key](EffectContext(e.controller, e.oid, ctx_targets, e.mode, slots,
                                                  effect_facts(s, d.effect_key, e)))
        ops += [op("remove_entry", e.sid), op("move", e.oid, "graveyard", "end"),     # CR 608.2n
                op("note", "SpellResolved", e.sid)]
        self._commit("resolve", ops)
        return True

    # ================================================================ combat (CR 508-511)
    def _attack_next(self):
        s = self.s
        for oid in combat.eligible_attackers(s):
            if oid not in s.attack_choices:
                self._commit("pending", [op("pending", "declare_attack", s.active, (oid,))])
                return
        chosen = tuple(sorted(o for o, yes in s.attack_choices.items() if yes))
        self._commit("declare_attackers", [op("declare_attackers", chosen)])            # CR 508.1a, 508.1f
        self._give_priority(s.active)

    def _do_ChooseAttack(self, a):
        self._commit("attack_choice", [op("attack_choice", a.oid, a.attacks)])
        self._attack_next()

    def _block_next(self):
        s = self.s
        for oid in combat.potential_blockers(s):
            if oid not in s.block_choices:
                self._commit("pending", [op("pending", "declare_block", 1 - s.active, (oid,))])
                return
        pairs = tuple(sorted((b, a) for b, a in s.block_choices.items() if a is not None))
        self._commit("declare_blockers", [op("declare_blockers", pairs)])               # CR 509.1a
        self._give_priority(s.active)

    def _do_ChooseBlock(self, a):
        self._commit("block_choice", [op("block_choice", a.blocker, a.attacker)])
        self._block_next()

    def _combat_damage(self, first_step: bool):
        s = self.s
        attackers = [x for x in s.attackers if x in s.objects and s.objects[x].zone == "battlefield"]
        for att in attackers:                                             # CR 510.1c divisions first
            if not combat.deals_damage_now(s, att, first_step) or att in s.divisions:
                continue
            bl = combat.living_blockers(s, att)
            power = s.power(att)
            if len(bl) >= 2 and power > 0:
                self._commit("pending", [op("pending", "assign_damage", s.active, (att, tuple(bl), power))])
                return
        ops = []
        defender = 1 - s.active
        for att in attackers:
            if not combat.deals_damage_now(s, att, first_step):
                continue
            power = s.power(att)
            if power <= 0:
                continue
            if att not in s.blocked:
                ops.append(op("damage_player", att, defender, power))
                continue
            bl = combat.living_blockers(s, att)
            if len(bl) == 1:
                ops.append(op("damage_creature", att, bl[0], power))
            elif len(bl) >= 2:
                ops += [op("damage_creature", att, b, n) for b, n in s.divisions[att] if n > 0]
        for b, att in sorted(s.blocks.items()):
            if b not in s.objects or s.objects[b].zone != "battlefield":
                continue
            if not combat.deals_damage_now(s, b, first_step):
                continue
            power = s.power(b)
            if power > 0 and att in s.objects and s.objects[att].zone == "battlefield":
                ops.append(op("damage_creature", b, att, power))
        if first_step:
            strikers = tuple(sorted(c for c in combat.combat_creatures(s) if combat.strikes_first(s, c)))
            ops += [op("set", "first_strike_done", True), op("set", "first_step_strikers", strikers),
                    op("clear_divisions")]                                # 510.1c: assigned again next step
        self._commit("combat_damage", ops)                                # CR 510.2 simultaneous
        self._give_priority(s.active)

    def _do_AssignCombatDamage(self, a):
        self._commit("damage_division", [op("division", a.attacker, a.division)])
        self._combat_damage(first_step=(self.s.step == "first_strike_damage"))

    # ================================================================ cleanup (CR 514)
    def _cleanup(self):
        s = self.s
        hand = s.zones[(s.active, "hand")]
        if len(hand) > 7:                                                 # CR 514.1
            self._commit("pending", [op("pending", "discard", s.active, (len(hand) - 7,))])
            return
        self._commit("cleanup", [op("cleanup_wear_off")])                 # CR 514.2
        self._leave_step()

    def _do_DiscardToHandSize(self, a):
        self._commit("discard", [op("move", oid, "graveyard", "end") for oid in a.cards])
        self._cleanup()
