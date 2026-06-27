"""engine/priority_stack.py -- R1 real-stack priority pass loop + shared core.

The whole R1 counterspell-interaction mechanism lives here, isolated from the
legacy synchronous counter window in game_state.cast_spell. This module is
OPT-IN: it is only reachable when an APL declares WANTS_PRIORITY_STACK = True
and cast_spell routes into it (the Integrate phase). Until then it is dead code
and the legacy path stays bit-identical.

Public API
----------
    run_priority_stack(caster_gs, card) -> 'countered' | 'resolved'
        R1 counterspell window. THIN caller of run_priority_pass with the
        counter-specific ask/apply/resolve_top callables.

    run_priority_pass(sides, stack, *, base, owner_gs, first, depth_cap,
                      ask, apply_action, resolve_top) -> terminal | None
        The shared, callable-parameterized APNAP pass/pass -> LIFO resolve loop
        (R2 EXTRACTION). This is exactly R1's pass loop with three behaviors
        injected so a SECOND caller (the R2 combat window) can reuse the same
        machinery instead of mirroring it. Termination is generalized so an
        EMPTY stack still offers priority and breaks on mutual-pass; R1's
        empty-break path is a strict (unreachable) subset, so R1 behavior is
        byte-identical. R2's combat windows are NOT added by this module.

A bounded, 2-player priority pass loop (XMage playPriority reduced to two
players; see design 1.1) that lets each side respond to the top stack object and
resolves the stack top-down (LIFO) once both players pass in succession.

ZERO RANDOMNESS (hard constraint, design 1.1 / abort condition G)
-----------------------------------------------------------------
This module performs NO random() calls of any kind. Every decision is driven by:
  - APL heuristics (apl.priority_action(...), pure board-state logic), and
  - a deterministic land-tap order inside the existing GameState.tap_lands.
There is no shuffle, no sampling, no coin-flip anywhere in this file. With the
gate OFF this code never runs, so it adds zero draws to the shared RNG stream;
with the gate ON it still draws nothing, so determinism is preserved.

R1 SCOPE
--------
Handles ONLY counterspell responses + original-spell resolution. Removal / burn
/ bounce / pump as on-stack responses are deferred to R2 (they would route
through stack.resolve_interaction). The stack here only ever holds the original
spell plus counters stacked on top of it. The run_priority_pass core is the
generalization that lets R2 wire those windows WITHOUT re-mirroring this loop.
"""
from __future__ import annotations

from engine.stack import Stack


# Depth cap: original spell + counter + counter-the-counter, then a hard stop.
# Once the stack holds this many items no further responses are cast; the loop
# is forced to resolve top-down. This bounds the counter war (design 1.1).
DEPTH_CAP = 3


# Instrumentation (test-only): counts how many counters have actually been put
# on the stack by this loop in the current process. The legacy gate-OFF path
# never reaches this module, so this counter only ever moves when R1 truly
# fires. tests/test_r1_control_exercises.py reads it to prove the narrowed
# control APL exercises the priority stack in real match play. Pure integer
# bookkeeping -- no random(), no game-state mutation -> determinism preserved.
COUNTERS_CAST = 0


def reset_fire_count():
    global COUNTERS_CAST
    COUNTERS_CAST = 0


def _other(side: str) -> str:
    """Flip priority between the two seats."""
    return "opp" if side == "caster" else "caster"


def _ask_priority(apl, my_gs, their_gs, stack):
    """Ask an APL whether it wants to respond to the current top of stack.

    Returns (counter_card, target_uid) to cast a counter, or None to pass.

    Defensive by design: APLs that have not implemented the R1 hook (everything
    except the opted-in control APL) have no priority_action, so getattr returns
    a no-op that always passes. This keeps run_priority_stack inert for every
    deck until the APL layer is wired in the Integrate phase.
    """
    if apl is None or my_gs is None:
        return None
    action_fn = getattr(apl, "priority_action", None)
    if action_fn is None:
        return None
    try:
        return action_fn(my_gs, their_gs, stack)
    except TypeError:
        # An APL that defines priority_action with a different arity is treated
        # as "pass" rather than crashing the loop.
        return None


def _pay_for_counter(gs, card) -> bool:
    """Pay a counter's mana cost from the responder's ACTUAL untapped lands.

    Uses the EXISTING GameState.tap_lands machinery, which honors gs.mana_reserve
    (design Seam D, game_state.py:976): tap_lands taps basics first and leaves
    `mana_reserve` lands physically untapped. Because this sim has no untap step,
    lands a control deck reserved on its own turn are still untapped here, and
    after paying the counter the reserved-beyond-cost lands stay untapped -- which
    is exactly what makes the proof's "controller has >= 2 lands STILL untapped"
    assertion reachable (design section 2).

    Returns True iff the cost was paid. No random() is involved: tap_lands uses a
    deterministic basics-first land sort.
    """
    cost = getattr(card, "mana_cost", "") or ""
    cmc = getattr(card, "cmc", 0) or 0
    if not gs.mana_pool.can_cast(cost, cmc):
        # Fill the pool from real untapped lands, honoring mana_reserve.
        gs.tap_lands()
    if not gs.mana_pool.can_cast(cost, cmc):
        return False
    return gs.mana_pool.pay(cost, cmc)


def _log(gs, msg: str):
    log_fn = getattr(gs, "_log", None)
    if callable(log_fn):
        log_fn(msg)


def _apply_counter(action, gs, priority, stack) -> bool:
    """R1 action-applier: cast a counter onto the stack (counter-specific).

    This is the casting/payment half of R1's original loop body (extracted so a
    SECOND caller can inject its own action-applier -- R2 pump/removal). Returns:
        True  -- a counter was paid for and placed on the stack (the loop resets
                 the pass count and hands priority to the other seat).
        False -- nothing was placed (no card, or the APL mis-judged
                 affordability and could not pay) -> the loop treats it as a pass.
    Byte-identical to R1's inline cast block.
    """
    counter_card, target_uid = action
    if counter_card is not None and _pay_for_counter(gs, counter_card):
        # Counter moves hand -> stack (it goes to graveyard on resolve).
        if counter_card in gs.zones.hand:
            gs.zones.hand.remove(counter_card)
        new_item = stack.cast(counter_card, priority)
        new_item.target_uid = target_uid
        global COUNTERS_CAST
        COUNTERS_CAST += 1
        _log(gs, f"  [priority] {priority} casts {counter_card.name} "
                 f"-> counter uid {target_uid}")
        return True
    # Could not pay (APL mis-judged affordability) -> treat as a pass.
    return False


def _resolve_top(stack, sides, original, caster_gs):
    """Resolve the single top stack item.

    Returns a terminal string ('countered' / 'resolved') when the ORIGINAL spell
    leaves the stack, or None when a counter resolved and the loop should
    continue.
    """
    resolution = stack.resolve_one()
    if resolution is None:
        return "resolved"

    item = resolution.item
    outcome = resolution.outcome      # 'resolved' or 'countered'

    if item.uid == original.uid:
        # The original spell is resolving.
        if outcome == "countered":
            # Move the original to the caster's graveyard; the caller will NOT
            # run the legacy resolve block.
            if item.card in caster_gs.zones.hand:
                caster_gs.zones.hand.remove(item.card)
            caster_gs.zones.graveyard.append(item.card)
            _log(caster_gs, f"  [COUNTERED] {item.card.name}")
            caster_gs.check_state_based_actions()
            return "countered"
        # Survived: leave the card in hand for the legacy resolve block.
        _log(caster_gs, f"  [priority] {item.card.name} resolves")
        return "resolved"

    # The top item is a COUNTER.
    owner_gs = sides[item.caster][0]
    if outcome == "resolved":
        # Check-before-effect: only an UNCOUNTERED counter applies its effect.
        stack.counter(item.target_uid)
        _log(owner_gs, f"  [priority] {item.card.name} resolves "
                       f"-> counters uid {item.target_uid}")
    else:
        # The counter was itself countered -> it does nothing (no target marked).
        _log(owner_gs, f"  [COUNTERED] {item.card.name}")
    # Either way the counter spell goes to its caster's graveyard.
    if owner_gs is not None:
        owner_gs.zones.graveyard.append(item.card)
    return None


def run_priority_pass(sides, stack, *, base=None, owner_gs=None, first="opp",
                      depth_cap=DEPTH_CAP, ask=_ask_priority,
                      apply_action=_apply_counter, resolve_top=_resolve_top):
    """Bounded APNAP pass/pass -> LIFO resolve loop -- the shared R1/R2 core.

    This is EXACTLY R1's run_priority_stack while-loop (the body extracted
    verbatim), parameterized on:
      - sides:        {'caster': (gs, apl), 'opp': (gs, apl)}
      - stack:        an engine.stack.Stack already seeded with the base
                      object(s). May be EMPTY (a combat window seeds nothing).
      - base:         the base stack object whose departure is terminal (R1: the
                      original spell). Passed through to resolve_top; may be None.
      - owner_gs:     game state that owns the base object (R1: caster_gs).
      - first:        the seat that receives priority first AND that the loop
                      returns to after a non-terminal resolution (R1: 'opp', the
                      non-active player responding to the active player's spell).
      - depth_cap:    hard stop on stack growth (default DEPTH_CAP=3).
      - ask:          callable(apl, my_gs, their_gs, stack) -> action | None.
      - apply_action: callable(action, gs, priority, stack) -> bool. True iff an
                      object was placed on the stack (reset pass count, flip
                      priority); False iff the action collapsed to a pass.
      - resolve_top:  callable(stack, sides, base, owner_gs) -> terminal | None.

    Returns the terminal string from resolve_top, or None if the stack drained
    to empty with no terminal (the generalized empty-stack exit).

    TERMINATION (generalized, load-bearing). R1's original guard was
    `while not stack.is_empty()`, which ends because resolve_top returns a
    terminal once the base spell leaves the stack. A combat window seeds an
    EMPTY stack and has no base spell, so that exact guard is False on entry ->
    the body would never run -> no player would ever be offered priority -> the
    window would be a silent no-op. So this core instead drives on a
    "rounds since last action" counter (passed_in_succession): the body always
    runs (offering priority even on an empty stack), and ONLY when both players
    pass in succession does it decide -- if the stack is empty it BREAKS, else it
    resolves the top. On R1's path the empty-break is UNREACHABLE: the base spell
    sits on the stack until resolve_top pops it and returns a terminal in the
    same step, so the stack is never empty at the mutual-pass check. R1 is thus a
    strict subset and stays byte-identical (NR-5).

    ZERO random() (unchanged).
    """
    # Opponent of the active player gets the first chance to respond.
    priority = first
    passed_in_succession = 0

    while True:
        gs, apl = sides[priority]
        other_gs = sides[_other(priority)][0]

        action = None
        # Only solicit a response if the stack has room (depth cap) AND this seat
        # actually exists. At/above the cap, all seats are forced to pass so the
        # stack must resolve -- this is the hard stop on the counter war.
        if gs is not None and stack.depth() < depth_cap:
            action = ask(apl, gs, other_gs, stack)

        if action is not None:
            if apply_action(action, gs, priority, stack):
                # A new object on the stack resets the pass count, and priority
                # passes to the other player (the counter-the-counter window).
                passed_in_succession = 0
                priority = _other(priority)
                continue
            # apply_action collapsed to a pass (e.g. could not pay) -> fall
            # through to the pass handling below.

        # This seat passed.
        passed_in_succession += 1
        priority = _other(priority)

        if passed_in_succession >= 2:
            # Both players passed in succession. With an empty stack there is
            # nothing left to resolve -> the window closes (combat path). With a
            # non-empty stack, resolve the top item (LIFO) -- R1 always lands
            # here with the base spell still present.
            if stack.is_empty():
                break
            terminal = resolve_top(stack, sides, base, owner_gs)
            if terminal is not None:
                return terminal
            # A non-terminal resolution (a counter resolving) happened; start a
            # fresh round of priority on the new top, `first` seat responding.
            passed_in_succession = 0
            priority = first

    # Stack drained without an explicit terminal (the generalized empty-stack
    # exit). UNREACHABLE on the R1 path (the base spell always yields a terminal
    # before the stack empties); the thin R1 caller supplies the defensive
    # countered/resolved fallback for that subset.
    return None


def run_priority_stack(caster_gs, card) -> str:
    """Run the R1 priority pass loop for `card` cast by `caster_gs`.

    THIN caller of run_priority_pass with the counter-specific
    ask/apply_action/resolve_top, so R1 behavior is byte-identical.

    Returns:
        'countered' -- the original spell was countered; this function has
                       already moved it to caster_gs.zones.graveyard and run
                       state-based actions. The caller returns immediately.
        'resolved'  -- the original spell survived. This function does NOT move
                       the card or apply effects; the caller falls through to the
                       UNCHANGED legacy resolve block to do the real zone move +
                       effects (the card is still in caster_gs.zones.hand).

    The card stays in caster_gs.zones.hand throughout; the StackItem only
    references it (design 1.1 / 1.3) so the legacy resolve block can be reused
    verbatim for the surviving spell.
    """
    # Resolve the two seats from the match wiring set up by match_engine.
    caster_apl = getattr(caster_gs, "_self_apl", None)
    opp_gs = getattr(caster_gs, "_match_opp", None)
    opp_apl = getattr(caster_gs, "_match_opp_apl", None)

    sides = {
        "caster": (caster_gs, caster_apl),
        "opp": (opp_gs, opp_apl),
    }

    stack = Stack()
    original = stack.cast(card, "caster")     # original spell, tagged to caster

    terminal = run_priority_pass(
        sides, stack,
        base=original,
        owner_gs=caster_gs,
        first="opp",                # opponent of the active player responds first
        depth_cap=DEPTH_CAP,
        ask=_ask_priority,
        apply_action=_apply_counter,
        resolve_top=_resolve_top,
    )
    if terminal is not None:
        return terminal

    # Stack drained without an explicit terminal (defensive). The original is
    # gone from the stack; if it was never countered it resolves normally.
    return "countered" if original.countered else "resolved"
