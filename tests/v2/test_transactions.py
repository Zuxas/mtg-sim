"""Review fixes (2026-09-30): transactional reducer commits and actions, transition hashes
that cover every state change (spec section 8: every op produces an event), and
observations that show a seat its own staged combat choices with a correct can_attack."""
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2 import reducer
from engine.v2.game import Game
from engine.v2.invariants import InvariantViolation
from engine.v2.ops import op
from engine.v2.policies import BasicScriptedPolicy, RandomLegalPolicy
from engine.v2.record import ReplayMismatch, make_record, replay
from engine.v2.reducer import EngineInvariantError
from tests.v2.decks import BURN_TEST, DECKOUT, RG, WU
from tests.v2.helpers import advance, arrange, at, find, new_game, put, tap_for


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


def deep_state(s) -> str:
    """Everything the engine holds, including fields neither state hash covers."""
    return repr((
        s.full_state_hash(), s.rules_state_hash(),
        list(s.objects), sorted((oid, sorted(vars(o).items())) for oid, o in s.objects.items()),
        sorted(s.retired), sorted(s.instances), sorted(s.def_by_ciid),
        sorted((str(k), list(v)) for k, v in s.zones.items()),
        [sorted(vars(e).items()) for e in s.stack],
        s.rng.getstate(), s.next_ciid, s.next_oid, s.next_prov,
        len(s.log.transitions), s.log.head, len(s.log._hashes),
        s.open_cast, s.mull_bottoms, s.mull_declared, s.attack_choices, s.block_choices, s.divisions,
        s.pools, s.life, s.lost, s.draw_failed, s.land_played,
    ))


def deep(g) -> str:
    return repr((deep_state(g.s), g.s.txn_open, dict(g.s.txn), list(g.actions), list(g.action_transition_index),
                 g._legal_cache[0], g._sba_clean_at))


def mid_game(seed, n=160, decks=(RG, WU)):
    g = Game.new(decks[0], decks[1], seed, starting_player=seed % 2, check_invariants=True)
    pols = [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)]
    for _ in range(n):
        if g.result is not None:
            break
        g.apply(pols[g.pending().player].choose(None, g.legal_actions()))
    assert g.result is None
    return g, pols


# ------------------------------------------------------------------ P1: atomic commits
def test_valid_ops_then_invalid_op_restores_complete_state_and_log():
    g, _ = mid_game(11)
    s = g.s
    land = next(o for o in s.zones[("bf",)] if not s.objects[o].tapped)
    lib_top = s.zones[(0, "library")][0]
    before, head, n = deep(g), s.log.head, len(s.log.transitions)
    ops = [op("shuffle", 0),                                    # RNG + zone list
           op("move", lib_top, "graveyard", "end"),             # objects, retired, next_oid, two zones
           op("tap", land),                                     # object field
           op("add_mana", 0, "R", 2),                           # pools
           op("pending", "priority", 1, (7,)),                  # scalar
           op("move", lib_top, "hand", "end")]                  # INVALID: lib_top was retired by the move above
    assert _raises(EngineInvariantError, lambda: reducer.commit(s, "probe", ops))
    assert deep(g) == before
    assert s.log.head == head and len(s.log.transitions) == n
    g.apply(g.legal_actions()[0])                               # the game continues normally


def test_invariant_failure_after_append_restores_state_and_log():
    g, _ = mid_game(12)
    s = g.s
    before, n = deep(g), len(s.log.transitions)
    # handlers succeed; invariant I3 (pools empty as a step begins) fails after the log append
    assert _raises(InvariantViolation, lambda: reducer.commit(s, "step", [op("add_mana", 0, "G", 1)]))
    assert deep(g) == before and len(s.log.transitions) == n


def test_failed_revert_cast_restores_open_casting_transaction():
    g = new_game()
    advance(g, at("main1", turn=1))
    put(g, 0, "Forest", "battlefield"); put(g, 0, "Mountain", "battlefield")
    bears = put(g, 0, "Grizzly Bears", "hand")
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == bears))
    tap_for(g, 0, "Forest")                                     # records an activation in the open cast
    before = deep(g)
    assert _raises(EngineInvariantError,
                   lambda: reducer.commit(g.s, "rollback", [op("revert_cast", True), op("__fail__")]))
    assert deep(g) == before and g.s.open_cast is not None


def test_op_without_an_event_is_rejected_and_rolled_back():
    g, _ = mid_game(13)
    before = deep(g)
    reducer._DISPATCH["silent_probe"] = (lambda s, evs: setattr(s, "passes", 99), (("passes", reducer._same),))
    try:
        assert _raises(EngineInvariantError, lambda: reducer.commit(g.s, "probe", [op("silent_probe")]))
    finally:
        del reducer._DISPATCH["silent_probe"]
    assert deep(g) == before


# ------------------------------------------------------------------ P1: atomic actions
def _twins(seed, n):
    """Two identical games driven by the same action sequence."""
    g1, pols = mid_game(seed, n)
    g2 = Game.new(RG, WU, seed, starting_player=seed % 2, check_invariants=True)
    for a in g1.actions:
        g2.apply(a)
    assert deep_state(g1.s) == deep_state(g2.s)
    return g1, g2, pols


def _commit_count(g, action):
    count = [0]
    real = g._commit

    def counting(kind, ops):
        count[0] += 1
        real(kind, ops)
    g._commit = counting
    try:
        g.apply(action)
    finally:
        del g._commit
    return count[0]


def _apply_failing_at(g, action, k):
    """Apply `action`, raising right after its k-th transition committed."""
    count = [0]
    real = g._commit

    def failing(kind, ops):
        real(kind, ops)
        count[0] += 1
        if count[0] == k:
            raise RuntimeError("injected failure")
    g._commit = failing
    try:
        g.apply(action)
        return False
    except RuntimeError:
        return True
    finally:
        del g._commit


def test_failure_inside_a_multi_transition_action_restores_state_and_action_record():
    g1, g2, pols = _twins(21, 120)
    checked = 0
    for _ in range(300):
        if g1.result is not None:
            break
        a = pols[g1.pending().player].choose(None, g1.legal_actions())
        pre = deep(g1)
        k = _commit_count(g2, a)                                # g2 applies it for real
        if k >= 2:
            for fail_at in sorted({1, k // 2 + 1, k}):
                assert _apply_failing_at(g1, a, fail_at)
                assert deep(g1) == pre, (a, fail_at, k)
            checked += 1
        g1.apply(a)
        assert deep_state(g1.s) == deep_state(g2.s)
        assert g1.actions == g2.actions and g1.action_transition_index == g2.action_transition_index
    assert checked >= 20, checked


def test_shadow_failing_commit_restores_state_in_every_real_context():
    """Before every real commit (setup, mulligans, casting, combat, SBAs, deck-out), run the
    same ops plus a failing op as an independent transaction and require a full restore.
    This exercises every handler's journaling in the contexts the engine really uses."""
    real = reducer.commit
    covered = Counter()

    def shadow(s, kind, ops):
        outer, outer_open = s.txn, s.txn_open
        s.txn, s.txn_open = {}, False
        before = deep_state(s)
        assert _raises(EngineInvariantError, lambda: real(s, kind, list(ops) + [op("__fail__")]))
        assert deep_state(s) == before, (kind, [o.name for o in ops])
        s.txn, s.txn_open = outer, outer_open
        covered.update(o.name for o in ops)
        real(s, kind, ops)

    reducer.commit = shadow
    try:
        for seed in range(3):
            Game.new(RG, WU, 900 + seed, starting_player=seed % 2, check_invariants=True).run(
                [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 50)])
        Game.new(RG, WU, 950, check_invariants=True).run([BasicScriptedPolicy(), BasicScriptedPolicy()])
        Game.new(RG, WU, 900, check_invariants=True).run(                  # includes a damage division
            [RandomLegalPolicy(900), RandomLegalPolicy(950)])
        Game.new(BURN_TEST, BURN_TEST, 970, check_invariants=True).run(     # life gain (Lightning Helix)
            [RandomLegalPolicy(3), RandomLegalPolicy(4)])
        Game.new(DECKOUT, DECKOUT, 960, turn_limit=30, check_invariants=True).run(
            [RandomLegalPolicy(1), RandomLegalPolicy(2)])
        g = new_game()                                              # CR 733 revert path (fault injection)
        advance(g, at("main1", turn=1))
        put(g, 0, "Forest", "battlefield"); put(g, 0, "Mountain", "battlefield")
        bears = put(g, 0, "Grizzly Bears", "hand")
        g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == bears))
        tap_for(g, 0, "Forest")
        g.rollback_open_cast("fault injection")
        for scenario in _shadow_scenarios():                        # card-level tests, re-run under shadow
            scenario()
    finally:
        reducer.commit = real
    never = set(reducer.HANDLERS) - set(covered)
    assert never <= {"untap"}, sorted(never)                        # "untap" has no milestone-one caller


def _shadow_scenarios():
    """Milestone-two card tests whose commits exercise the new ops (each re-run under shadow)."""
    from tests.v2 import test_activated as S2
    from tests.v2 import test_alt_costs as S6
    from tests.v2 import test_replacement as S4
    from tests.v2 import test_duration as S5
    from tests.v2 import test_modes_targets as S7
    from tests.v2 import test_search as S3
    from tests.v2 import test_triggers as T
    return [S6.test_upkeep_removes_the_last_counter_and_the_card_is_cast_free,
            S6.test_declining_the_suspend_cast_leaves_it_exiled,
            S6.test_spectacle_cost_is_fixed_for_the_whole_cast,
            S6.test_roiling_vortex_punishes_a_spell_cast_without_mana,
            S7.test_boros_charm_mode_1_indestructible_for_permanents_controlled_at_resolution,
            S7.test_searing_blaze_with_one_legal_target_still_resolves,
            S5.test_skullcrack_stops_life_gain_and_damage_prevention_this_turn,
            S5.test_double_strike_second_step_uses_first_step_snapshot,
            S5.test_roiling_vortex_r_ability_stops_only_opponents_gaining_life,
            S3.test_fetched_shock_land_asks_for_its_entry_payment,
            S3.test_failure_to_find_still_shuffles,
            S4.test_sacred_foundry_choice_happens_before_the_move_commits,
            S4.test_inspiring_vantage_tapped_with_three_other_lands,
            S2.test_pain_land_mana_while_casting_is_recorded_with_its_life_cost,
            S2.test_canyon_draw_needs_its_whole_cost_and_survives_its_sacrifice,
            S2.test_rollback_reverses_a_pain_land_activation_including_its_life,
            T.test_multiple_prowess_triggers_need_an_ordering_decision,
            T.test_goblin_guide_reveals_and_moves_a_land_to_hand,
            T.test_targeted_trigger_chooses_targets_when_it_is_put_on_the_stack,
            T.test_trigger_with_no_legal_targets_is_removed_from_the_stack]


# ------------------------------------------------------------------ P1: hashes cover every change
def _head_after(ops, seed=5):
    g = Game.new(RG, WU, seed)
    reducer.commit(g.s, "probe", ops)
    return g.s.log.head


def test_different_pending_states_give_different_transition_hashes():
    heads = {_head_after([op("pending", "priority", 0)]), _head_after([op("pending", "priority", 1)]),
             _head_after([op("pending", "priority", 0, (3,))]), _head_after([op("pending", "discard", 0)]),
             _head_after([op("pending", None, 0)])}
    assert len(heads) == 5


def test_every_formerly_silent_op_changes_the_transition_hash():
    base = [op("pending", "priority", 0)]
    variants = {
        "land_played": ([op("land_played", 0)], [op("land_played", 1)]),
        "attack_choice": ([op("attack_choice", 5, True)], [op("attack_choice", 5, False)]),
        "block_choice": ([op("block_choice", 5, 9)], [op("block_choice", 5, None)]),
        "division": ([op("division", 9, ((5, 1), (6, 2)))], [op("division", 9, ((5, 2), (6, 1)))]),
        "store_bottom": ([op("store_bottom", 0, (41, 42))], [op("store_bottom", 0, (42, 41))]),
    }
    for name, (x, y) in variants.items():
        assert _head_after(base + x) != _head_after(base + y), name
    for name in ("mull_round_reset", "clear_bottoms", "clear_combat", "clear_draw_failed", "empty_pools",
                 "untap_all"):
        extra = [op(name, 0)] if name == "clear_draw_failed" else [op(name)]
        assert _head_after(base) != _head_after(base + extra), name


def test_replay_detects_a_divergent_pending_state():
    g = Game.new(RG, WU, 31)
    g.run([RandomLegalPolicy(3), RandomLegalPolicy(4)])
    rec = make_record(g)
    replay(rec)
    real = reducer._DISPATCH["pending"]
    seen = [0]

    def divergent(s, evs, kind, player, info=()):
        seen[0] += 1
        if seen[0] == 40 and kind == "priority":
            info = tuple(info) + (99,)                   # same decision kind + player, different state
        return real[0](s, evs, kind, player, info)
    reducer._DISPATCH["pending"] = (divergent, real[1])
    try:
        assert _raises(ReplayMismatch, lambda: replay(rec))
    finally:
        reducer._DISPATCH["pending"] = real


# ------------------------------------------------------------------ P2: observations
def test_can_attack_accounts_for_active_player_controller_tapped_and_sickness():
    g = new_game()
    advance(g, at("main1", active=0, turn=3))
    bears = put(g, 0, "Grizzly Bears", "battlefield")
    opp_bears = put(g, 1, "Youthful Knight", "battlefield")
    goblin = put(g, 0, "Raging Goblin", "battlefield")          # haste

    def view(oid, seat=0):
        return next(p for p in g.observe(seat).battlefield if p.oid == oid).can_attack

    assert view(bears) is False                                  # summoning sick (entered this turn)
    assert view(goblin) is True                                  # haste
    arrange(g, [op("begin_turn", g.s.turn + 1, 0)])              # next turn of player 0: sickness gone
    assert view(bears) is True and view(bears, seat=1) is True   # same answer for either viewer
    assert view(opp_bears) is False                              # controller is not the active player
    arrange(g, [op("tap", bears)])
    assert view(bears) is False                                  # tapped
    arrange(g, [op("untap", bears), op("begin_turn", g.s.turn + 1, 1)])
    assert view(bears) is False                                  # not the active player's creature
    assert view(opp_bears) is True                               # now it is the active player's


def test_observation_shows_only_the_seats_own_staged_combat_choices():
    g = new_game()
    advance(g, at("main1", active=0, turn=3))
    att = put(g, 0, "Grizzly Bears", "battlefield")
    blk = put(g, 1, "Youthful Knight", "battlefield")
    arrange(g, [op("attack_choice", att, True), op("block_choice", blk, att),
                op("division", att, ((blk, 2),))])
    me, opp = g.observe(0), g.observe(1)                          # player 0 is active (attacking)
    assert me.my_attack_choices == ((att, True),) and me.my_divisions == ((att, ((blk, 2),)),)
    assert me.my_block_choices == ()
    assert opp.my_block_choices == ((blk, att),)
    assert opp.my_attack_choices == () and opp.my_divisions == ()


def test_staged_attack_choice_visible_mid_declaration_in_a_real_game():
    g = new_game()
    advance(g, at("main1", active=0, turn=3))
    a1 = put(g, 0, "Grizzly Bears", "battlefield")
    a2 = put(g, 0, "Hill Giant", "battlefield")
    arrange(g, [op("begin_turn", g.s.turn + 2, 0)])              # both creatures are no longer sick
    advance(g, lambda g: g.pending().kind == "declare_attack")
    first = g.pending().info[0]
    g.apply(A.ChooseAttack(0, first, True))
    assert g.pending().kind == "declare_attack"                  # second creature still to decide
    assert g.observe(0).my_attack_choices == ((first, True),)
    assert g.observe(1).my_attack_choices == ()
    assert {a1, a2} >= {first}


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"[ok] {name}")
            except Exception as e:                                   # noqa: BLE001
                failures += 1
                print(f"[FAIL] {name}: {type(e).__name__}: {e}")
    print(f"TRANSACTION/HASH/OBSERVATION FAILURES: {failures}")
    sys.exit(1 if failures else 0)
