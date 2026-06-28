"""test_r3_storm_lifecycle.py -- R3 storm spell-damage MATCH-PATH lifecycle.

The discriminating proof for the R3 storm spike (spec 4.1). It demonstrates the
full storm lifecycle ON THE MATCH PATH (match_runner._simple_play_turn) with an
in-file RED(gate-OFF)/GREEN(gate-ON) differential. Because the harness forbids
`git checkout`, the gate-OFF RED phase is the pre-R3 stand-in: with the active
player's WANTS_STORM False the new main-phase-1 spell-damage sync is a pure
no-op (byte-identical to the trilogy+R4 baseline), so the storm payoff's damage
is computed on the throwaway view and then DROPPED -- the opponent's match life
total never moves. The gate-ON GREEN phase is the post-R3 behavior: the same
view damage is propagated back onto gs.life_b / gs.damage_to_b. RED and GREEN
are mutual negations, which is what proves the gate is load-bearing.

The card under test is Grapeshot ({1}{R} sorcery, "Grapeshot deals 1 damage to
any target. Storm." -- handler _grapeshot_spell in card_handlers_verified.py).
Storm count + copy-on-resolve ALREADY existed in the goldfish engine
(_grapeshot_spell reads gs.spells_cast_this_turn); R3 only makes that reachable,
correct, and CREDITED on the two-player MATCH path. The discriminator is that
the damage SCALES with the storm count: casting K cheap spells first, then
Grapeshot as the (K+1)th spell, must deal K+1 (NOT 1) -- and that scaled total
must land on the TwoPlayerGameState opponent (gs.damage_to_b / gs.life_b), not
merely on the view's throwaway damage_dealt.

We construct a TwoPlayerGameState DIRECTLY and HAND-PLACE cards (no full match
-> no mulligan fragility). We drive the REAL engine surface
match_runner._simple_play_turn(gs, "a", apl) -- which builds the per-player
view, wires _match_opp, runs apl.main_phase_match, and then runs the GATED
active-player main1 spell-damage sync. We ASSERT ON gs.life_b / gs.damage_to_b
(the shared TwoPlayerGameState) right after that call -- NEVER on
view.damage_dealt.

Discriminators (design 4.1):
  (i)   propagation: the storm damage lands on gs.damage_to_b / gs.life_b (the
        match state), not just the throwaway view -- asserted on gs.* only.
  (ii)  scaling: damage_to_b == K+1 (NOT 1) -- one copy would give 1; K+1 proves
        the storm count was applied.
  (iii) gate is load-bearing: the GREEN expectation FAILS on the RED state
        (gate OFF -> damage dropped) -- the GATE-THE-TEST clause below.

ASCII-only output. Prints "ALL R3 PROOF TESTS PASS". Exit 0 on pass, 1 on fail.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Make any APL exception inside _simple_play_turn raise instead of becoming a
# silent WARN (match_runner L252), so a wiring bug fails loud here.
os.environ["SIM_DEBUG"] = "1"

from data.card import Card
from apl.match_apl import MatchAPL
from engine.match_runner import (
    TwoPlayerGameState, _simple_play_turn, _storm_match_gate,
)

# K cheap spells precede the payoff; Grapeshot is the (K+1)th spell.
K = 4
GRAPESHOT = "Grapeshot"


class _StormProofAPL(MatchAPL):
    """Minimal MatchAPL carrying only the R3 opt-in flag. Subclasses MatchAPL
    (not a bare object) so _simple_play_turn's isinstance(apl, MatchAPL) check
    passes and the apl is used DIRECTLY -- not wrapped in
    RemovalAwareGoldfishAdapter (which would ignore our sequencing). Its
    main_phase_match casts every cheap spell first, then Grapeshot LAST, all via
    gs.cast_spell so spells_cast_this_turn accrues and _grapeshot_spell reads a
    storm count of K."""

    def __init__(self, wants_storm: bool):
        self.WANTS_STORM = wants_storm
        self.name = "StormProof"

    def keep(self, hand, mulligans, on_play) -> bool:
        return True

    def bottom(self, hand, n) -> list:
        return []

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # Do NOT touch gs.mana_pool: _build_view already filled it from the
        # hand-placed Mountains (match_runner L227-232). Cast cheap spells
        # first so the payoff sees the maximal storm count.
        for c in list(gs.zones.hand):
            if c.name != GRAPESHOT and not c.is_land():
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
        # Payoff LAST -> storm count == number of prior spells (K).
        for c in list(gs.zones.hand):
            if c.name == GRAPESHOT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)


def _grapeshot() -> Card:
    return Card(
        name=GRAPESHOT, mana_cost="{1}{R}", cmc=2,
        type_line="Sorcery",
        oracle_text="Grapeshot deals 1 damage to any target. Storm",
        colors=["R"],
    )


def _cheap_spell(i: int) -> Card:
    # Vanilla {R} sorcery with a name no handler matches -> casting it only
    # bumps spells_cast_this_turn (the storm count) and resolves to graveyard.
    return Card(
        name=f"Storm Filler {i}", mana_cost="{R}", cmc=1,
        type_line="Sorcery", oracle_text="", colors=["R"],
    )


def _mountain(i: int) -> Card:
    return Card(name=f"Mountain {i}", mana_cost="", cmc=0,
                type_line="Basic Land - Mountain", oracle_text="")


def _fresh_state(wants_storm: bool) -> TwoPlayerGameState:
    """Hand-place K cheap spells + Grapeshot in A's hand, and enough Mountains
    on A's battlefield for _build_view to bankroll all K+1 casts. Opponent B is
    untouched: 20 life, no creatures -> every Grapeshot copy hits face."""
    gs = TwoPlayerGameState(deck_a=[], deck_b=[], on_play=True, seed=0)
    gs.turn = 3
    apl = _StormProofAPL(wants_storm)
    gs.apl_a = apl
    gs.apl_b = None            # no opp APL -> cast_spell skips the counter window
    gs.spells_cast_a = 0       # storm count starts at 0 on the view
    gs.hand_a = [_cheap_spell(i) for i in range(K)] + [_grapeshot()]
    # K cheap {R} = K mana, Grapeshot {1}{R} = 2 mana -> K+2 needed; place extra.
    gs.bf_a = [_mountain(i) for i in range(K + 4)]
    gs.land_played_a = True    # already have lands down; APL plays none
    return apl, gs


def _green_assert(life_b: int, damage_to_b: int) -> None:
    """The GREEN expectation, factored out so the GATE-THE-TEST clause can prove
    it FAILS on the RED (gate-off) state."""
    assert damage_to_b == K + 1, \
        f"GREEN: storm-scaled damage must be K+1={K + 1} (got {damage_to_b})"
    assert life_b == 20 - (K + 1), \
        f"GREEN: opp life must be 20-(K+1)={20 - (K + 1)} (got {life_b})"


def run_red():
    """Gate OFF (WANTS_STORM False) == pre-R3 / legacy match path: the storm
    payoff's damage is computed on the throwaway view and then DROPPED. The
    opponent's match life total never moves."""
    apl, gs = _fresh_state(wants_storm=False)
    assert apl.WANTS_STORM is False, "RED: active-player gate must be OFF"
    assert _storm_match_gate(gs) is False, \
        "RED: no seat wants storm -> _storm_match_gate OFF"

    _simple_play_turn(gs, "a", apl)

    assert gs.life_b == 20, f"RED: opp life must stay 20 (got {gs.life_b})"
    assert gs.damage_to_b == 0, \
        f"RED: storm damage must be DROPPED (got {gs.damage_to_b})"
    return {"life_b": gs.life_b, "damage_to_b": gs.damage_to_b}


def run_green():
    """Gate ON (WANTS_STORM True) == post-R3 match path: the same view damage is
    propagated back onto gs.life_b / gs.damage_to_b, SCALED by the storm count."""
    apl, gs = _fresh_state(wants_storm=True)
    assert apl.WANTS_STORM is True, "GREEN: active-player gate must be ON"
    assert _storm_match_gate(gs) is True, \
        "GREEN: a seat wants storm -> _storm_match_gate ON"

    _simple_play_turn(gs, "a", apl)

    # Assert on the SHARED TwoPlayerGameState -- never on view.damage_dealt.
    _green_assert(gs.life_b, gs.damage_to_b)
    return {"life_b": gs.life_b, "damage_to_b": gs.damage_to_b}


def run():
    red = run_red()
    green = run_green()

    # GATE-THE-TEST: the GREEN expectation MUST fail on the RED (gate-off)
    # state. If it didn't, the gate would not be the discriminator.
    gate_is_discriminator = False
    try:
        _green_assert(red["life_b"], red["damage_to_b"])
    except AssertionError:
        gate_is_discriminator = True
    assert gate_is_discriminator, \
        "GATE-THE-TEST: GREEN expectation unexpectedly held on the gate-OFF state"

    # The differential: RED shows the storm damage ABSENT, GREEN shows it
    # PRESENT and SCALED.
    assert red["life_b"] == 20 and red["damage_to_b"] == 0, \
        "RED phase did not reproduce the storm-dropped baseline"
    assert (green["damage_to_b"] == K + 1
            and green["life_b"] == 20 - (K + 1)), \
        "GREEN phase did not reproduce the scaled+propagated storm line"

    import json
    print("R3_LIFECYCLE_RED   " + json.dumps(red, sort_keys=True))
    print("R3_LIFECYCLE_GREEN " + json.dumps(green, sort_keys=True))
    print(f"R3_STORM_COUNT K={K} copies={K + 1}")
    print("ALL R3 PROOF TESTS PASS")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    sys.exit(0)
