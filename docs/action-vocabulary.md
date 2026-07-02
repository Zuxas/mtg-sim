# Action Vocabulary — B1 Step 1 deliverable

Spec: `harness/specs/2026-07-01-b1-legal-action-api.md` (Step 1).
Purpose: the complete decision surface the APL layer exposes today, verified against
source, so `legal_actions()` can cover the SAME vocabulary — search must never be
weaker than APLs merely because a decision kind was missed.

Proposed dataclass: `Action(kind, seat, card_uid=None, targets=(), payload=None)`.

## 1. Per-turn decision hooks (engine -> APL call sites, verified)

| # | Decision site | Hook signature (base) | Engine call site | Returns | Action kind(s) |
|---|---|---|---|---|---|
| 1 | Mulligan keep | `keep(hand, mulligans, on_play) -> bool` (match_apl.py:553) | match_engine.py:45; routed crude/london_crude/keep via `_mull_mode` (match_runner.py:1590-1652) | bool | `MULL_KEEP` / `MULL_TAKE` |
| 2 | London bottom | `bottom(hand, n) -> list` (match_apl.py:556) | match_engine.py:48 | list[Card] to bottom | `MULL_BOTTOM(card_uids)` |
| 3 | Opp-aware keep | `keep_vs_opp(hand, mulligans, on_play, ...)` (aware_match_apl.py:864) | keep-mode routing only | bool | same as 1 (context param) |
| 4 | Main phase 1 | `main_phase_match(gs, opponent)` (match_apl.py:297) | match_runner.py:251; match_engine.py:415 | mutates state via engine calls | decomposes into 8-12 below |
| 5 | Mana reservation | `reserve_mana(gs, opponent)` (aware_match_apl.py:627) | match_engine.py:403 (pre-main) | marks lands held | `RESERVE_MANA(land_uids)` |
| 6 | Declare attackers | `declare_attackers(gs, opponent) -> list[Card]` (match_apl.py:366; aware:474) | match_engine.py:461 | list[Card] | `ATTACK(set_of_uids)` |
| 7 | Declare blockers | `declare_blockers(gs, opponent, attackers)` (match_apl.py:467; aware:587) | match_engine.py:518 | dict[id(attacker) -> list[blockers]] | `BLOCK(assignment_map)` |
| 8 | Main phase 2 | `main_phase2_match(gs, opponent)` (match_apl.py:563 area) | match_runner.py:567-569 | mutates state | same kinds as 4 |
| 9 | Priority window (R1) | `priority_action(my_gs, opp_gs, stack)` (match_apl.py:55; aware:648) | via `run_priority_pass` (match_engine.py:222 path) | counter/removal choice or pass | `RESPOND_COUNTER(card_uid, target_stack_uid)` / `RESPOND_REMOVAL(card_uid, target_uid)` / `PASS_PRIORITY` |
| 10 | Combat priority (R2) | `combat_priority_action(my_gs, their_gs, stack, window)` (match_apl.py:117) | R2-gated combat windows | trick/removal or pass | `RESPOND_*` + `PASS_PRIORITY` (window param) |
| 11 | PW activation | `choose_pw_ability(pw, gs, opp_gs) -> int` (match_apl.py:109) | R5 loyalty path | ability index | `ACTIVATE_PW(pw_uid, ability_idx)` |
| 12 | Opp-end-step flash | `end_step_actions(gs, opponent)` (match_apl.py:518; aware:832) | match_runner.py:1557; match_engine.py:575 | flash casts | `CAST` at instant speed (window=OPP_END) |
| 13 | Spell response (legacy) | `respond_to_spell(gs, opponent, spell)` (match_apl.py:485) | match_engine.py:105 | shallow; predates R1 | fold into 9 (do not model separately) |
| 14 | Combo answer | `answer_combo(event, ...)` via `offer_interaction` (engine/combo_interaction.py; gated `WANTS_COMBO_INTERACTION`) | combo APL decisive steps | InteractionResult | `RESPOND_COMBO(kind, card_uid)` |

## 2. Inside main-phase hooks: primitive mutators APLs invoke (the `step()` targets)

| Primitive | Canonical path | Action kind |
|---|---|---|
| Play a land | land-drop helpers -> zone move | `PLAY_LAND(card_uid)` |
| Cast a spell | `gs.cast_spell(...)` (game_state.py:~1098; fires ETB :1142; earns counter window via priority pass) | `CAST(card_uid, targets)` |
| Cheat into play | `GameState.put_into_play(card, from_zone)` (sanctioned bypass helper) | `PUT_INTO_PLAY(card_uid, from_zone)` |
| Activate ability | ability helpers incl. `activate_planeswalker_ability` (engine/planeswalkers.py) | `ACTIVATE(card_uid, ability_idx, targets)` |
| Direct damage routing | `gs.damage_dealt` accumulation (WANTS_BURN/WANTS_STORM sync) | consequence of CAST/ACTIVATE, not its own kind |
| Discard / GY setup | zone-move helpers (loot/discard lines) | `DISCARD(card_uids)` |

`step()` MUST route through these same paths (spec Step 3); `battlefield.append` bypass
sites are known-and-tracked (2026-04-22 audit) and are NOT part of the vocabulary.

## 3. Completeness argument

Every engine->APL invocation in match_runner.py / match_engine.py was enumerated by
grep of call sites (verified list above); boros_energy_match.py and murktide_match.py
override only hooks in this table. Trigger-ordering infrastructure exists but has no
engine call site yet (excluded until wired). Sideboarding is a between-games decision
(bo3_match.py), out of B1 scope by spec.

**Vocabulary: 13 action kinds** — MULL_KEEP, MULL_TAKE, MULL_BOTTOM, RESERVE_MANA,
PLAY_LAND, CAST, PUT_INTO_PLAY, ACTIVATE, ACTIVATE_PW, ATTACK, BLOCK,
RESPOND_COUNTER / RESPOND_REMOVAL / RESPOND_COMBO (one RESPOND family), PASS_PRIORITY.

Spec Step-1 stop-condition armed: if implementation surfaces >2 kinds missing from
this table, STOP and amend here first.

*Authored 2026-07-01 (Cowork). Verified against source greps same day; agent survey
cross-checked. This file is UNCOMMITTED in mtg-sim (sandbox is pre-history-rewrite);
commit it workstation-side.*
