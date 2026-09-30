"""Rules engine v2 (milestone one).

Spec: harness/specs/2026-09-30-rules-engine-v2-design.md (revision 4, approved 2026-09-30).
One canonical two-player state machine. The engine owns every rule and every state
change (only engine.v2.reducer mutates GameState); players are policies that choose
among typed legal actions from immutable observations. Isolated from the legacy
engine: the only legacy import is engine.card_db (printed card data, exact lookup).
"""
ENGINE_VERSION = "v2-m1.0"
