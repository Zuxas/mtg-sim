# Minimal Priority / Stack Loop -- Design (read before any implementation)

Status: DESIGN ONLY. No engine code written. This doc is for orchestrator
review before implementation.

Goal: a deterministic 2-player priority + stack loop that can faithfully
replicate a counterspell interaction (cast spell -> opponent responds ->
counter resolves first -> original spell removed from the stack and never
resolves), grounded in our real engine and patterned on XMage (MIT) and
open-mtg (MIT). Pattern reference only -- no code copied; mechanisms are
described as approaches.

A note on the citations: XMage method/field names below were read via a
page-summarizer over the real files (paths cited), not pasted verbatim.
Treat them as the approach, not as exact signatures.

---

## 1. What exists today vs what is missing

### What exists in our engine

- `engine/stack.py` -- a `Stack` class (LIFO list of `StackItem`) with
  `cast()`, `respond()`, `counter_top()`, `resolve_one()`, `resolve_all()`,
  plus `classify_card()` and `resolve_interaction()` that applies an effect
  to the two `GameState`s. **This class is effectively vestigial.** It is a
  passive data structure; nothing drives it with a priority loop. In
  `engine/match_engine.py` it is imported only to borrow `StackItem` /
  `Resolution` as a vehicle to call `resolve_interaction()` inline
  (match_engine.py:133-139) -- spells are never actually pushed, ordered,
  and resolved LIFO against each other.

- `engine/counter_resolver.py` -- `try_counter_spell(...)`, a **single
  reactive window**. Called from `GameState.cast_spell` after mana is paid,
  before the spell resolves (game_state.py:1353-1369). It is guarded by
  `self._in_counter_window` so it fires exactly once per cast and
  **explicitly forbids counter-the-counter** (see the comment at
  game_state.py:1348-1353 and counter_resolver.py:168-181). It picks the
  cheapest legal counter via a value heuristic.

- `engine/match_engine.py` -- the turn loop. "Interaction" happens at fixed
  hard-coded windows, not via priority:
  - after main phase: `_try_reactive_interaction(...)` looped
    `spells_cast_this_turn` times (match_engine.py:267-272),
  - `pre_combat_instant` (286-289),
  - `post_attackers_instant` (340-346),
  - `end_step_actions` (392-394).
  Mana is never untapped per turn for the reactive player; both
  `counter_resolver._tap_lands_for_response` and `match_engine._tap_for_response`
  fill the pool from all lands as an approximation (counter_resolver.py:100-119,
  match_engine.py:67-77).

- `engine/interaction.py` -- a legacy *probabilistic* tempo model
  (`InteractionSimulator`, per-archetype "counter/kill/discard" dice). Not a
  stack at all; it converts goldfish kill curves into "realistic" ones. It is
  orthogonal to this design and is mentioned only so it is not confused with
  real interaction.

### What is missing (the gap this design fills)

1. No priority object. There is no notion of "who currently holds priority"
   or "both players passed in succession."
2. The stack is never the unit of resolution. Each spell resolves inline at
   its cast site (cast_spell) or at a fixed phase hook; multiple objects are
   never on the stack simultaneously.
3. No counter-the-counter, and no response-to-trigger. The single-window
   guard (`_in_counter_window`) structurally prevents the responder's
   counter from itself being responded to.
4. Countering is positional, not by identity (see section 6.4) -- correct
   only because exactly one spell is ever "on the stack" at a time.

### Why adopt a real loop (the payoff -- not a rebuild of what works)

A genuine priority/stack loop **subsumes** the single-window hack and yields,
for free, the interactions the current code cannot represent:
- counter-the-counter (Counterspell -> Spell Pierce -> Dispel),
- responding to a triggered ability before it resolves,
- multiple instants stacked and resolving top-down in the correct order,
- holding priority to add a second spell before the first resolves.
It also fixes the counter-by-position correctness bug (section 6.4). The
existing fixed windows (`pre_combat_instant`, `post_attackers_instant`,
`end_step_actions`) become *moments where the loop is entered*, not bespoke
interaction code.

---

## 2. Reference essence -- the four required questions

Each answer cites the XMage path (pattern) and the matching spot in our
engine, plus the open-mtg lighter reference where relevant.

### 2.1 How priority passes between players

XMage (`Mage/src/main/java/mage/game/GameImpl.java`, `playPriority`): the
active player is made current
(`state.getPlayerList().setCurrent(activePlayerId)`), then priority
circulates with `getPlayerList().getNext()`. Each player has a `passed`
flag (`Player.isPassed()`); passing advances to the next player.

open-mtg (`game.py`): the same idea, reduced to two players. A single
`player_with_priority` variable, each player has a `passed_priority`
boolean, and on "Pass" it sets `player.passed_priority = True` and hands
priority to `active_player.get_opponent()`.

Our engine today: no equivalent. Closest analog is the fixed-order calls in
the turn loop (match_engine.py:198 `for active in [...]`) -- but that is
turn order, not priority within a step.

### 2.2 How the stack resolves top-down after both pass

XMage (`GameImpl.playPriority` + `allPassed()`): `allPassed()` returns true
only when every responsive player `isPassed()` and `canRespond()` checks
clear -- i.e. all players passed in succession with no intervening action.
When `allPassed()` is true and the stack is non-empty, the game calls
`stack.resolve(game)` (`Mage/src/main/java/mage/game/stack/SpellStack.java`):
`peek()` the top object, call `top.resolve(game)`, then `resetPassed()` so
priority restarts from the active player for the new top object. A `finally`
block force-removes the resolved object if it is still present.

open-mtg (`game.py`): when
`players[0].passed_priority and players[1].passed_priority and stack_is_empty`
it advances the phase; resolution of a non-empty stack is only stubbed
(open-mtg is sorcery-speed; its value here is purely the pass-loop shape).

Our engine today: `Stack.resolve_one()` / `resolve_all()` exist
(stack.py:91-105) but are never called from a priority loop;
`resolve_interaction()` is invoked inline.

### 2.3 How instant-speed responses get a window

XMage: the window IS the priority loop. After any spell is cast or ability
put on the stack, `resetPassed()` is called and priority returns to the
active player, then circulates. Every player gets a chance to act before the
top resolves; taking an action (`activateAbility()`, `cast()`) calls
`game.getPlayers().resetPassed()` (`PlayerImpl`), reopening the window so the
new top object can itself be responded to.

Our engine today: the "window" is the one-shot `try_counter_spell` call
inside cast_spell (game_state.py:1353-1369) plus the fixed phase hooks. There
is no re-opening: once the responder acts, the guard prevents a further round.

### 2.4 How a counterspell removes a target spell from the stack

XMage:
- The card (`Mage.Sets/src/mage/cards/c/Counterspell.java`) is an instant
  `{U}{U}` whose spell ability uses `CounterTargetEffect` with a `TargetSpell`
  -- the target is chosen at cast time and is a *spell object on the stack*.
- On resolution, `CounterTargetEffect.apply()`
  (`Mage/src/main/java/mage/abilities/effects/common/CounterTargetEffect.java`)
  iterates `getTargetPointer().getTargets(game, source)` and calls
  `game.getStack().counter(targetId, source, game)` for each, returning true
  if any succeeded.
- `SpellStack.counter(...)` (`SpellStack.java`) locates the object **by id**
  and removes it via `remove(...)` -> `super.remove(spell)`. The countered
  spell is removed from the stack and never resolves (goes to graveyard per
  rules).

Our engine today: `Stack.counter_top()` sets `items[-2].countered = True`
(stack.py:86-89) -- positional, and `resolve_interaction` treats COUNTER as a
no-op because the counter is "already handled" (stack.py:277-279). In the
live path, `try_counter_spell` simply returns True and cast_spell sends the
original card straight to the graveyard, skipping resolution
(game_state.py:1363-1369). No stack object is matched by identity.

---

## 3. The minimal 2-player reduction

XMage's machinery is N-player-general (`PlayerList.getNext()`, iterate all
players in `allPassed()`). For exactly two players, deterministic, it
collapses to a tiny state machine:

State carried during a priority sequence:
- `stack`: ordered list of stack objects (LIFO; append = push, pop last = top).
- `priority`: 'a' or 'b' -- who must act or pass now.
- `passed_in_succession`: int in {0,1,2}. Reset to 0 whenever anyone acts.

Loop (one "priority sequence", e.g. entered at a step or after a spell is
cast):

```
priority = active_player
passed_in_succession = 0
loop:
    action = APL_for(priority).priority_action(view)   # None means "pass"
    if action is None:
        passed_in_succession += 1
        if passed_in_succession == 2:
            if stack non-empty:
                resolve_top()                 # 2.2
                passed_in_succession = 0
                priority = active_player       # restart after resolution
                continue
            else:
                return                         # step ends, no one wants to act
        else:
            priority = other(priority)         # 2.1: pass to opponent
            continue
    else:
        perform(action)                        # push spell/ability onto stack
        passed_in_succession = 0               # 2.3: any action reopens window
        priority = active_player               # active player gets priority next
        continue
```

Mapping to XMage concepts:
- `allPassed()` (iterate all players) -> `passed_in_succession == 2`.
- `PlayerList.getNext()` / `setCurrent(active)` -> `other()` / `priority = active_player`.
- `resetPassed()` on action or after resolve -> `passed_in_succession = 0`.

Determinism: no RNG inside the loop. Given identical game state and identical
APL policies, the sequence is reproducible. The only inputs are
`priority_action` returns, which must be pure functions of the visible state
(see section 5).

This loop is entered at each point in the turn where players currently get a
fixed hook: beginning of each step/phase, and specifically the existing
moments in match_engine.py (after main spells, pre-combat, post-attackers,
end step). Those hooks become "enter the priority loop here."

---

## 4. The stack object (replacing positional with identity)

Reuse `StackItem` (stack.py:33-42) with two additions to make identity-based
countering possible:

- a stable per-object `id` (monotonic int assigned at push; deterministic).
- `target_item_id` on a counter's StackItem, set at cast time to the id of
  the spell it points at (XMage's `TargetSpell` chosen at cast, resolved in
  `CounterTargetEffect.apply`).

`resolve_top()`:
1. `item = stack.pop()` (the top).
2. If `item.countered`: discard (to graveyard), do nothing. (matches
   "removed, never resolves").
3. Else dispatch by `interaction_type`:
   - COUNTER: find the still-on-stack object whose `id == item.target_item_id`;
     if present and still a legal target, mark it `countered = True` (do NOT
     pop it now -- it is removed when it would have resolved, i.e. it stays
     marked and is discarded when reached, OR is removed immediately; either
     is fine for 2-player as long as it never resolves). The clean choice:
     remove it from the stack list by id immediately (mirrors XMage
     `SpellStack.counter` removing by id). If the target id is gone (already
     resolved/countered), the counter "fizzles" -- no effect.
   - everything else (REMOVAL, BURN, BOUNCE, WRATH, DISCARD, PUMP, NONE):
     delegate to the existing `resolve_interaction()` (stack.py:227-323),
     which already mutates the two GameStates correctly.
4. After resolving, run state-based actions (lethal damage, 0-toughness)
   then re-enter the loop with priority at the active player.

This is the smallest change that gets correctness: the only genuinely new
rule logic is "counter removes target object by id"; all other effects reuse
`resolve_interaction`.

---

## 5. APL decision interface (where the cost actually lands)

The loop is trivial. The integration cost is the decision hook. Today APLs
act at *fixed* hooks: `main_phase_match`, `pre_combat_instant`,
`post_attackers_instant`, `declare_blockers`, `combat_trick`,
`end_step_actions`, and `respond_to_spell` (used by
`_try_reactive_interaction`, match_engine.py:105). A priority loop instead
asks, repeatedly, at every window: "act or pass?"

Minimal new hook on the APL base (`apl/match_apl.py` / `aware_match_apl.py`):

```
def priority_action(self, gs, opp, stack):
    # Return an Action (cast X targeting Y / activate Z) or None to pass.
    # Must be a pure function of the visible state: no RNG, no global mutation.
    ...
```

- An `Action` is a small record: kind (cast/activate), the card, optional
  target(s), and (for counters) the target stack-item id.
- Default implementation: `return None` (always pass). This makes the loop a
  no-op for every APL that has not opted in -- the engine behaves as a
  pass-pass-resolve pipe and existing decks are unaffected at sorcery speed.
- Existing reactive logic is adapted, not rewritten: the body of
  `try_counter_spell` (pick cheapest legal value-positive counter) becomes the
  COUNTER branch of `priority_action`; `respond_to_spell` becomes the
  removal/burn branch. The selection heuristics already exist
  (counter_resolver.py:122-183) -- they move, they are not invented.
- Termination guarantee: an APL must not return an action it cannot legally
  perform (no mana / illegal target), or the loop could spin. The engine
  validates each action; an illegal action is treated as a pass and logged.
  This is the one invariant the APL contract must hold.

Relationship to current fixed hooks: keep `main_phase_match` (sorcery-speed
active-player development) as-is; replace the four *reactive* windows with a
single "enter priority loop" at each of those points. The active player also
gets priority first inside the loop, so active-player instants and
hold-priority lines become expressible without new hooks.

---

## 6. Counterspell walk-through (the acceptance test for this design)

Scenario: A casts Llanowar Elves (creature). B holds Counterspell ({U}{U}, up).

1. A has priority in main 1; `priority_action` returns "cast Llanowar Elves".
   Push StackItem(id=1, caster=a, type=NONE/creature). `passed=0`,
   priority -> a (active).
2. A has priority again, passes (nothing more to do). `passed=1`,
   priority -> b.
3. B has priority with stack=[Elves]. `priority_action` returns "cast
   Counterspell, target_item_id=1". Push StackItem(id=2, caster=b,
   type=COUNTER, target_item_id=1). `passed=0`, priority -> a (active).
4. A passes (no response). `passed=1`, priority -> b.
5. B passes. `passed=2` -> resolve_top.
   - Top = id=2 (Counterspell). Not countered. COUNTER branch: find id=1 on
     stack, remove it by id (mark/discard). Counterspell -> graveyard.
   - `passed=0`, priority -> a.
6. A passes, B passes -> resolve_top. Stack now empty (Elves was removed).
   Loop returns; step ends. Llanowar Elves never resolved -> it is in A's
   graveyard, never entered the battlefield.

Counter-the-counter (the thing today's code cannot do) is now automatic: at
step 4, instead of passing, A could cast Dispel targeting id=2; the same loop
handles it with no special case.

### 6.4 The one real correctness fix vs current code

Current `counter_top()` marks `items[-2]` -- the object directly beneath the
top. That is correct ONLY because the engine never has more than one spell on
the stack at once. With a real loop, the counterspell's target is not always
directly beneath it (e.g. A casts spell1, holds priority, casts spell2; B
counters spell1). The design counters **by stack-item id** (matching XMage's
`getStack().counter(targetId, ...)`), never by position. This is the single
behavioral bug the redesign must not reintroduce.

---

## 7. Scope boundary (what this design deliberately omits)

To stay minimal and deterministic, out of scope for the first cut:
- Triggered-ability ordering by APNAP among simultaneous triggers (put them
  on the stack active-player-first; do not model player-choice ordering yet).
- Mana abilities don't use the stack (correct already -- tapping for mana in
  our engine is not a stack object; keep it that way).
- Split-second, can't-be-countered nuances beyond the existing name checks
  (Voice of Victory lock stays as a pre-check, game_state.py:1334-1338).
- Replacing the goldfish `interaction.py` probabilistic model -- untouched.
- The mana-accumulation approximation (lands not untapping for the reactive
  player) is a *separate* known limitation; this design does not depend on
  fixing it, but per-land tap reserve (already TODO at match_engine.py:220)
  would make the priority loop's mana checks exact.

---

## 8. Cited files

Our engine (read directly, line numbers exact):
- `mtg-sim/engine/stack.py` (Stack, StackItem, counter_top:86-89,
  resolve_one:91-98, resolve_interaction:227-323, classify_card:181-207)
- `mtg-sim/engine/counter_resolver.py` (try_counter_spell:122-183,
  COUNTER_VALIDITY:42-65, tap hack:100-119)
- `mtg-sim/engine/match_engine.py` (turn loop:148-415, reactive windows:
  267-272/286-289/340-346/392-394, _try_reactive_interaction:79-146,
  _tap_for_response:67-77)
- `mtg-sim/engine/game_state.py` (cast_spell:1308-1377, counter window:
  1348-1369, Voice/High Noon locks:1317-1338)
- `mtg-sim/engine/interaction.py` (legacy probabilistic model -- context only)

XMage (magefree/mage, MIT; pattern reference, paths cited; names via
summarizer not verbatim):
- `Mage/src/main/java/mage/game/GameImpl.java` (playPriority, allPassed,
  resolve loop)
- `Mage/src/main/java/mage/players/PlayerImpl.java` (passed flag, pass(),
  resetPassed on action)
- `Mage/src/main/java/mage/game/stack/SpellStack.java` (resolve via
  peek()/top.resolve(game); counter(targetId)/remove() by id)
- `Mage/src/main/java/mage/abilities/effects/common/CounterTargetEffect.java`
  (apply -> getStack().counter(targetId, source, game))
- `Mage.Sets/src/mage/cards/c/Counterspell.java` ({U}{U} instant, TargetSpell
  + CounterTargetEffect)

open-mtg (hlynurd/open-mtg, MIT; lighter Python pass-loop reference):
- `game.py` (player_with_priority, per-player passed_priority, both-passed +
  stack-empty -> next phase; sorcery-speed, stack resolution stubbed)
