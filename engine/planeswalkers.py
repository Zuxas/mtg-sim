"""engine/planeswalkers.py -- Planeswalker loyalty + ability dispatch.

Stage 3 of the T1.3+T1.4 transform infrastructure arc (2026-04-26).

Planeswalkers in mtg-sim are represented as Card objects with a
loyalty: int field (added Stage 1, defaults from card_db). Their
activated abilities are dispatched via the PLANESWALKER_ABILITIES
registry below: card_name -> {loyalty_change: handler}. Each
handler is (card, gs) -> None and applies the ability's *effect*;
the loyalty change itself (the cost) is applied by
activate_planeswalker_ability before calling the handler.

Per-turn budget per CR 606.3 (one loyalty ability per planeswalker
per turn) is tracked on the GameState via gs._pw_activated_this_turn:
set[str] of card names. Lazy reset on first activation each turn
detects gs.turn change and clears the set -- this avoids the need
to wire a hook into engine/game_state.py's next_turn() method, which
matters for keeping module-extension changes (this file) decoupled
from the load-bearing engine state machine.

Stage 3 deliverable: dispatch infrastructure only. PLANESWALKER_ABILITIES
is empty in this commit; Stage 5 fills it with Ajani Avenger handlers
when the front-face Cat-die transform consumer lands.

Death by 0 loyalty: state-based action per CR 704.5i. Implemented as
inline check after handler fires (the handler may itself reduce
loyalty, e.g. via the conditional-bolt 0-ability that pings face for
N damage but doesn't change loyalty further -- here we only check the
ability's own loyalty cost, which is the change parameter).
"""
from typing import Callable


# ── R5 instrumentation (test-only, zero-RNG, no game-state mutation) ──
#
# Pure integer bookkeeping. The legacy gate-OFF gauntlet path never runs
# the orchestrator, so any nonzero value here is direct evidence the R5
# loyalty layer fired in real play. PW_COMBAT_DEATHS is bumped by the
# combat path (note_pw_combat_death) and is the immortal-PW guard.
PW_ACTIVATIONS = 0
PW_ULTIMATES = 0
PW_COMBAT_DEATHS = 0

# Fixed-cost approximation of Ugin's variable -X minus (v1). Card-accurate
# -X magnitude is intentionally deferred (see R5 design 5.2).
UGIN_X_APPROX = 4


def reset_fire_count() -> None:
    """Zero the R5 instrumentation counters (call before a measured run)."""
    global PW_ACTIVATIONS, PW_ULTIMATES, PW_COMBAT_DEATHS
    PW_ACTIVATIONS = 0
    PW_ULTIMATES = 0
    PW_COMBAT_DEATHS = 0


def note_pw_combat_death() -> None:
    """Bump the combat-death counter. Called by the combat-damage path when a
    planeswalker dies to combat. Kept here so all PW instrumentation lives in
    one module (the combat wiring is a separate task; this is its hook)."""
    global PW_COMBAT_DEATHS
    PW_COMBAT_DEATHS += 1


# ── Registry ────────────────────────────────────────────────────────
#
# Keyed by the planeswalker's actual card name (post-transform name
# for DFC PWs like Ajani Avenger). Inner dict is keyed by loyalty
# change (positive for +N, 0 for the 0 ability, negative for -N).
# Handlers receive (card, gs) and apply the ability's effect; loyalty
# adjustment is handled by activate_planeswalker_ability around the
# handler call.

def _ajani_avenger_plus_2(card, gs):
    """Ajani, Nacatl Avenger +2: Put a +1/+1 counter on each Cat
    you control. Cats include front-face Ajani Pariah (if not yet
    transformed), Cat tokens (Ocelot Pride end-step Cat, Ajani Pariah
    ETB Cat Warrior), and any other Cat-subtype creatures."""
    cats = [
        c for c in gs.zones.battlefield
        if "cat" in (c.type_line or "").lower()
        and "creature" in (c.type_line or "").lower()
    ]
    for cat in cats:
        cat.counters += 1
    gs._log(f"  Ajani Avenger +2: +1/+1 on {len(cats)} Cats")


def _ajani_avenger_zero(card, gs):
    """Ajani, Nacatl Avenger 0: Create a 2/1 white Cat Warrior token.
    When you do, if you control a red permanent other than Ajani,
    he deals damage equal to the number of creatures you control to
    any target.

    Goldfish modeling: damage goes to face. The "red permanent other
    than Ajani" check matches Mountain (basic), Ragavan (red creature),
    Phlage (R/W), Goblin Bombardment (red enchantment), Bolt/Galvanic
    (red instants -- but instants aren't permanents). For BE the
    condition is essentially always true post-T1 (Ragavan or Mountain
    almost always present)."""
    gs._make_token("Cat Warrior Token", "2", "1", "Creature — Cat Warrior")
    has_red_other = any(
        ("R" in (c.colors or []))
        or "Mountain" in (c.type_line or "")
        for c in gs.zones.battlefield
        if c is not card
    )
    if has_red_other:
        creatures = sum(
            1 for c in gs.zones.battlefield
            if "creature" in (c.type_line or "").lower()
        )
        gs.damage_dealt += creatures
        gs._log(f"  Ajani Avenger 0: Cat Warrior token + {creatures} dmg "
                f"({gs.damage_dealt} total)")
    else:
        gs._log(f"  Ajani Avenger 0: Cat Warrior token only "
                f"(no red permanent)")


def _ajani_avenger_minus_4(card, gs):
    """Ajani, Nacatl Avenger -4: Each opponent chooses an artifact,
    a creature, an enchantment, and a planeswalker from among the
    nonland permanents they control, then sacrifices the rest.

    Goldfish modeling: no opponent -> no-op. (Loyalty cost is still
    paid by the dispatch wrapper before this fires.)"""
    gs._log(f"  Ajani Avenger -4: no-op in goldfish (no opponent)")


# ── Shared handler utilities (defensive; goldfish + match-view safe) ──
#
# Handlers receive (card, gs) only. In the match path the orchestrator
# stashes the opponent view on gs._pw_opp so opponent-zone effects are
# reachable best-effort; when absent (goldfish), those effects are no-ops
# -- exactly like the existing Ajani -4 handler. No handler raises on a
# missing attribute; effects degrade to a log line.

def _pwlog(gs, msg):
    fn = getattr(gs, "_log", None)
    if callable(fn):
        fn(msg)


def _pw_opp(gs):
    return getattr(gs, "_pw_opp", None)


def _opp_battlefield(gs):
    opp = _pw_opp(gs)
    z = getattr(opp, "zones", None) if opp is not None else None
    bf = getattr(z, "battlefield", None) if z is not None else None
    return bf if isinstance(bf, list) else None


def _opp_hand(gs):
    opp = _pw_opp(gs)
    z = getattr(opp, "zones", None) if opp is not None else None
    h = getattr(z, "hand", None) if z is not None else None
    return h if isinstance(h, list) else None


def _is_nonland(c):
    return "land" not in (getattr(c, "type_line", "") or "").lower()


def _is_creature(c):
    return "creature" in (getattr(c, "type_line", "") or "").lower()


def _remove_best_opp_nonland(gs):
    """Deterministically remove the opponent's highest-mana-value nonland
    permanent (models exile/bounce/tuck of 'their best threat'). No-op when
    no opponent view is present."""
    bf = _opp_battlefield(gs)
    if not bf:
        return None
    cands = [c for c in bf if _is_nonland(c)]
    if not cands:
        return None
    tgt = max(cands, key=lambda c: getattr(c, "cmc", 0) or 0)
    bf.remove(tgt)
    return tgt


def _remove_best_opp_creature(gs):
    bf = _opp_battlefield(gs)
    if not bf:
        return None
    cands = [c for c in bf if _is_creature(c)]
    if not cands:
        return None
    tgt = max(cands, key=lambda c: getattr(c, "cmc", 0) or 0)
    bf.remove(tgt)
    return tgt


def _gain_life(gs, n):
    if hasattr(gs, "life"):
        gs.life += n


def _ping_opp_face(gs, n):
    opp = _pw_opp(gs)
    if opp is not None and hasattr(opp, "life"):
        opp.life -= n
    elif hasattr(gs, "damage_dealt"):
        gs.damage_dealt += n


def _draw_self(gs, n):
    fn = getattr(gs, "_draw", None)
    if callable(fn):
        for _ in range(n):
            fn()


# ── Eldrazi Tron payoffs (anchor deck) ───────────────────────────────

def _karn_liberated_plus_4(card, gs):
    """Karn Liberated +4: Target player exiles a card from their hand."""
    h = _opp_hand(gs)
    if h:
        h.pop(0)
    _pwlog(gs, "  Karn Liberated +4: opp exiles a card from hand")


def _karn_liberated_minus_3(card, gs):
    """Karn Liberated -3: Exile target permanent."""
    _remove_best_opp_nonland(gs)
    _pwlog(gs, "  Karn Liberated -3: exile target permanent")


def _karn_liberated_minus_14(card, gs):
    """Karn Liberated -14 (ultimate): Restart the game leaving Karn-exiled
    cards in play. v1 board-defining approximation: exile every nonland
    permanent the opponent controls (board reset in the controller's favor)."""
    bf = _opp_battlefield(gs)
    n = 0
    if bf is not None:
        survivors = [c for c in bf if not _is_nonland(c)]
        n = len(bf) - len(survivors)
        bf[:] = survivors
    _pwlog(gs, f"  Karn Liberated -14 ULTIMATE: restart approx, "
               f"exiled {n} opp nonland permanents")


def _karn_great_creator_plus_1(card, gs):
    """Karn, the Great Creator +1: animate up to one noncreature artifact
    (the artifact-ability lock is a static, modeled passively). Board no-op."""
    _pwlog(gs, "  Karn, the Great Creator +1: animate artifact / artifact lock")


def _karn_great_creator_minus_2(card, gs):
    """Karn, the Great Creator -2: wish an artifact from outside the game.
    Modeled as a flagged fetch (no SB zone in this scope)."""
    setattr(gs, "_pw_karn_wish_pending", True)
    _pwlog(gs, "  Karn, the Great Creator -2: SB-wish an artifact")


def _ugin_spirit_dragon_plus_2(card, gs):
    """Ugin, the Spirit Dragon +2: deals 3 damage to any target (face)."""
    _ping_opp_face(gs, 3)
    _pwlog(gs, "  Ugin, the Spirit Dragon +2: 3 damage")


def _ugin_spirit_dragon_minus_x(card, gs):
    """Ugin, the Spirit Dragon -X: Exile each colored permanent with mana
    value X or less. v1 fixed-cost (X = UGIN_X_APPROX) approximation: exile
    the opponent's nonland permanents with mana value <= UGIN_X_APPROX."""
    bf = _opp_battlefield(gs)
    n = 0
    if bf is not None:
        survivors = []
        for c in bf:
            if _is_nonland(c) and (getattr(c, "cmc", 0) or 0) <= UGIN_X_APPROX:
                n += 1
            else:
                survivors.append(c)
        bf[:] = survivors
    _pwlog(gs, f"  Ugin, the Spirit Dragon -X: exiled {n} opp permanents "
               f"(mv<={UGIN_X_APPROX})")


def _ugin_spirit_dragon_minus_10(card, gs):
    """Ugin, the Spirit Dragon -10 (ultimate): gain 7 life, draw 7, put up to
    7 permanents from hand. v1: +7 life + draw approx."""
    _gain_life(gs, 7)
    _draw_self(gs, 7)
    _pwlog(gs, "  Ugin, the Spirit Dragon -10 ULTIMATE: gain 7 life, draw 7")


def _ugin_eye_plus_2(card, gs):
    """Ugin, Eye of the Storms +2: gain 3 life and draw a card."""
    _gain_life(gs, 3)
    _draw_self(gs, 1)
    _pwlog(gs, "  Ugin, Eye of the Storms +2: gain 3 life, draw a card")


def _ugin_eye_zero(card, gs):
    """Ugin, Eye of the Storms 0: Add {C}{C}{C}."""
    pool = getattr(gs, "mana_pool", None)
    if isinstance(pool, dict):
        pool["C"] = pool.get("C", 0) + 3
    _pwlog(gs, "  Ugin, Eye of the Storms 0: add CCC")


def _ugin_eye_minus_11(card, gs):
    """Ugin, Eye of the Storms -11 (ultimate): free-cast colorless cards from
    library. v1: large card-advantage burst (draw approx)."""
    _draw_self(gs, 3)
    _pwlog(gs, "  Ugin, Eye of the Storms -11 ULTIMATE: free-cast colorless burst")


# ── Other canonical planeswalkers in the live decklists ──────────────

def _teferi_time_raveler_plus_1(card, gs):
    """Teferi, Time Raveler +1: cast sorceries as though they had flash."""
    setattr(gs, "_pw_sorcery_flash", True)
    _pwlog(gs, "  Teferi, Time Raveler +1: cast sorceries at flash")


def _teferi_time_raveler_minus_3(card, gs):
    """Teferi, Time Raveler -3: bounce an artifact/creature/enchantment; draw."""
    bf = _opp_battlefield(gs)
    if bf:
        cands = [c for c in bf if any(
            t in (getattr(c, "type_line", "") or "").lower()
            for t in ("artifact", "creature", "enchantment"))]
        if cands:
            bf.remove(max(cands, key=lambda c: getattr(c, "cmc", 0) or 0))
    _draw_self(gs, 1)
    _pwlog(gs, "  Teferi, Time Raveler -3: bounce permanent, draw a card")


def _teferi_hero_plus_1(card, gs):
    """Teferi, Hero of Dominaria +1: Draw a card."""
    _draw_self(gs, 1)
    _pwlog(gs, "  Teferi, Hero of Dominaria +1: draw a card")


def _teferi_hero_minus_3(card, gs):
    """Teferi, Hero of Dominaria -3: tuck target nonland permanent."""
    _remove_best_opp_nonland(gs)
    _pwlog(gs, "  Teferi, Hero of Dominaria -3: tuck nonland permanent")


def _teferi_hero_minus_8(card, gs):
    """Teferi, Hero of Dominaria -8 (ultimate): draw-exile emblem."""
    setattr(gs, "_pw_teferi_emblem", True)
    _pwlog(gs, "  Teferi, Hero of Dominaria -8 ULTIMATE: emblem (draw-exile)")


def _jace_mind_sculptor_plus_2(card, gs):
    """Jace, the Mind Sculptor +2: fateseal the opponent."""
    _pwlog(gs, "  Jace, the Mind Sculptor +2: fateseal opp")


def _jace_mind_sculptor_zero(card, gs):
    """Jace, the Mind Sculptor 0: Brainstorm (draw 3, put back 2)."""
    _draw_self(gs, 3)
    _pwlog(gs, "  Jace, the Mind Sculptor 0: brainstorm (draw 3, put 2 back)")


def _jace_mind_sculptor_minus_1(card, gs):
    """Jace, the Mind Sculptor -1: return target creature to hand."""
    _remove_best_opp_creature(gs)
    _pwlog(gs, "  Jace, the Mind Sculptor -1: bounce target creature")


def _jace_mind_sculptor_minus_12(card, gs):
    """Jace, the Mind Sculptor -12 (ultimate): exile opponent's library."""
    opp = _pw_opp(gs)
    z = getattr(opp, "zones", None) if opp is not None else None
    lib = getattr(z, "library", None) if z is not None else None
    if isinstance(lib, list):
        lib.clear()
    _pwlog(gs, "  Jace, the Mind Sculptor -12 ULTIMATE: exile opp library")


def _chandra_spark_hunter_plus_2(card, gs):
    """Chandra, Spark Hunter +2: loot (sacrifice artifact or discard; draw)."""
    _draw_self(gs, 1)
    _pwlog(gs, "  Chandra, Spark Hunter +2: loot (sac/discard, draw)")


def _chandra_spark_hunter_zero(card, gs):
    """Chandra, Spark Hunter 0: create a 3/2 colorless Vehicle (crew 1)."""
    fn = getattr(gs, "_make_token", None)
    if callable(fn):
        fn("Vehicle Token", "3", "2", "Artifact - Vehicle")
    _pwlog(gs, "  Chandra, Spark Hunter 0: create 3/2 Vehicle (crew 1)")


def _chandra_spark_hunter_minus_7(card, gs):
    """Chandra, Spark Hunter -7 (ultimate): artifact-damage emblem."""
    setattr(gs, "_pw_chandra_emblem", True)
    _pwlog(gs, "  Chandra, Spark Hunter -7 ULTIMATE: artifact-damage emblem")


def _dellian_fel_plus_2(card, gs):
    """Professor Dellian Fel +2: You gain 3 life."""
    _gain_life(gs, 3)
    _pwlog(gs, "  Professor Dellian Fel +2: gain 3 life")


def _dellian_fel_zero(card, gs):
    """Professor Dellian Fel 0: Draw a card and lose 1 life."""
    _draw_self(gs, 1)
    _gain_life(gs, -1)
    _pwlog(gs, "  Professor Dellian Fel 0: draw a card, lose 1 life")


def _dellian_fel_minus_3(card, gs):
    """Professor Dellian Fel -3: Destroy target creature."""
    _remove_best_opp_creature(gs)
    _pwlog(gs, "  Professor Dellian Fel -3: destroy target creature")


def _dellian_fel_minus_6(card, gs):
    """Professor Dellian Fel -6 (ultimate): lifegain-drain emblem."""
    setattr(gs, "_pw_dellian_emblem", True)
    _pwlog(gs, "  Professor Dellian Fel -6 ULTIMATE: lifegain-drain emblem")


def _ajani_chaperone_plus_1(card, gs):
    """Ajani, Outland Chaperone +1: create a 1/1 G/W Kithkin token."""
    fn = getattr(gs, "_make_token", None)
    if callable(fn):
        fn("Kithkin Token", "1", "1", "Creature - Kithkin")
    _pwlog(gs, "  Ajani, Outland Chaperone +1: create 1/1 Kithkin")


def _ajani_chaperone_minus_2(card, gs):
    """Ajani, Outland Chaperone -2: deal 4 damage to a tapped creature."""
    _remove_best_opp_creature(gs)
    _pwlog(gs, "  Ajani, Outland Chaperone -2: 4 damage to tapped creature")


def _ajani_chaperone_minus_8(card, gs):
    """Ajani, Outland Chaperone -8 (ultimate): cheat permanents into play."""
    setattr(gs, "_pw_ajani_chaperone_ult", True)
    _pwlog(gs, "  Ajani, Outland Chaperone -8 ULTIMATE: cheat permanents into play")


def _liliana_veil_plus_1(card, gs):
    """Liliana of the Veil +1: Each player discards a card."""
    h = _opp_hand(gs)
    if h:
        h.pop(0)
    _pwlog(gs, "  Liliana of the Veil +1: each player discards")


def _liliana_veil_minus_2(card, gs):
    """Liliana of the Veil -2: Target player sacrifices a creature."""
    _remove_best_opp_creature(gs)
    _pwlog(gs, "  Liliana of the Veil -2: opp sacrifices a creature")


def _liliana_veil_minus_6(card, gs):
    """Liliana of the Veil -6 (ultimate): opp splits permanents into two piles
    and sacrifices one. v1 approximation: opp loses ~half its nonland
    permanents."""
    bf = _opp_battlefield(gs)
    n = 0
    if bf is not None:
        nonland = [c for c in bf if _is_nonland(c)]
        half = nonland[: max(1, len(nonland) // 2)] if nonland else []
        for c in half:
            bf.remove(c)
        n = len(half)
    _pwlog(gs, f"  Liliana of the Veil -6 ULTIMATE: opp sacrifices {n} permanents")


# Printed starting loyalty (used by the gated ETB-set-loyalty wiring; additive
# data only). Grounded in data/rules_reference/scryfall_oracle_cards.json.
PLANESWALKER_START_LOYALTY: dict[str, int] = {
    "Karn Liberated":             6,
    "Karn, the Great Creator":    5,
    "Ugin, the Spirit Dragon":    7,
    "Ugin, Eye of the Storms":    7,
    "Teferi, Time Raveler":       4,
    "Teferi, Hero of Dominaria":  4,
    "Jace, the Mind Sculptor":    3,
    "Chandra, Spark Hunter":      4,
    "Professor Dellian Fel":      5,
    "Ajani, Outland Chaperone":   3,
    "Liliana of the Veil":        3,
}

# The loyalty change that counts as a card's ULTIMATE (most card-defining
# minus). Used to increment PW_ULTIMATES and by the default chooser. Cards
# with no true ultimate (Karn the Great Creator, Teferi Time Raveler, the
# Ajani Avenger -4) are intentionally omitted.
PLANESWALKER_ULTIMATES: dict[str, int] = {
    "Karn Liberated":             -14,
    "Ugin, the Spirit Dragon":    -10,
    "Ugin, Eye of the Storms":    -11,
    "Teferi, Hero of Dominaria":  -8,
    "Jace, the Mind Sculptor":    -12,
    "Chandra, Spark Hunter":      -7,
    "Professor Dellian Fel":      -6,
    "Ajani, Outland Chaperone":   -8,
    "Liliana of the Veil":        -6,
}


PLANESWALKER_ABILITIES: dict[str, dict[int, Callable]] = {
    "Ajani, Nacatl Avenger": {
        2:  _ajani_avenger_plus_2,
        0:  _ajani_avenger_zero,
        -4: _ajani_avenger_minus_4,
    },
    "Karn Liberated": {
        4:   _karn_liberated_plus_4,
        -3:  _karn_liberated_minus_3,
        -14: _karn_liberated_minus_14,
    },
    "Karn, the Great Creator": {
        1:  _karn_great_creator_plus_1,
        -2: _karn_great_creator_minus_2,
    },
    "Ugin, the Spirit Dragon": {
        2:   _ugin_spirit_dragon_plus_2,
        -4:  _ugin_spirit_dragon_minus_x,   # the -X minus (fixed approx)
        -10: _ugin_spirit_dragon_minus_10,
    },
    "Ugin, Eye of the Storms": {
        2:   _ugin_eye_plus_2,
        0:   _ugin_eye_zero,
        -11: _ugin_eye_minus_11,
    },
    "Teferi, Time Raveler": {
        1:  _teferi_time_raveler_plus_1,
        -3: _teferi_time_raveler_minus_3,
    },
    "Teferi, Hero of Dominaria": {
        1:  _teferi_hero_plus_1,
        -3: _teferi_hero_minus_3,
        -8: _teferi_hero_minus_8,
    },
    "Jace, the Mind Sculptor": {
        2:   _jace_mind_sculptor_plus_2,
        0:   _jace_mind_sculptor_zero,
        -1:  _jace_mind_sculptor_minus_1,
        -12: _jace_mind_sculptor_minus_12,
    },
    "Chandra, Spark Hunter": {
        2:  _chandra_spark_hunter_plus_2,
        0:  _chandra_spark_hunter_zero,
        -7: _chandra_spark_hunter_minus_7,
    },
    "Professor Dellian Fel": {
        2:  _dellian_fel_plus_2,
        0:  _dellian_fel_zero,
        -3: _dellian_fel_minus_3,
        -6: _dellian_fel_minus_6,
    },
    "Ajani, Outland Chaperone": {
        1:  _ajani_chaperone_plus_1,
        -2: _ajani_chaperone_minus_2,
        -8: _ajani_chaperone_minus_8,
    },
    "Liliana of the Veil": {
        1:  _liliana_veil_plus_1,
        -2: _liliana_veil_minus_2,
        -6: _liliana_veil_minus_6,
    },
}


def _pw_zero_loyalty_sba(card, gs) -> bool:
    """Shared CR 704.5i state-based action: a planeswalker at 0 loyalty is put
    into its owner's graveyard. Reused by activate_planeswalker_ability AND by
    the combat-damage path, so a walker dropped to 0 by combat dies the same
    way as one dropped to 0 by its own minus ability (no divergent death code).
    Behavior is byte-identical to the prior inline block (gate-OFF safe)."""
    if card.loyalty <= 0 and card in gs.zones.battlefield:
        gs.zones.battlefield.remove(card)
        gs.zones.graveyard.append(card)
        gs._log(f"  {card.name} loyalty 0, sent to graveyard")
        return True
    return False


def activate_planeswalker_ability(card, gs, change: int) -> bool:
    """Activate a +N / 0 / -N loyalty ability on a planeswalker.

    Per CR 606.3: a player may activate a loyalty ability of a
    planeswalker they control as a sorcery, only if no loyalty ability
    of that planeswalker has been activated this turn. Per CR 704.5i:
    if a planeswalker has 0 or less loyalty, it's put into its owner's
    graveyard as a state-based action.

    Args:
      card: the planeswalker (must be on battlefield)
      gs: GameState
      change: loyalty cost as a signed integer
                +N adds N counters
                0  no change
                -N removes N counters

    Returns:
      True if the ability fired (loyalty changed, handler called).
      False if rejected (no handler registered, already activated this
      turn, or card not in PLANESWALKER_ABILITIES at all).

    Side effects on success:
      - card.loyalty += change
      - gs._pw_activated_this_turn.add(card.name)
      - handler(card, gs) called
      - If card.loyalty <= 0 after the change, the card moves to
        graveyard.
    """
    global PW_ACTIVATIONS, PW_ULTIMATES
    # Lazy per-turn reset: detect turn-number change since last call.
    # This avoids wiring a hook into engine/game_state.py.
    last_turn = getattr(gs, "_pw_activation_turn", -1)
    if gs.turn != last_turn:
        gs._pw_activation_turn = gs.turn
        gs._pw_activated_this_turn = set()

    # Per-turn budget: one loyalty ability per PW per turn.
    if card.name in gs._pw_activated_this_turn:
        return False

    # Look up handler by card name + loyalty change.
    abilities = PLANESWALKER_ABILITIES.get(card.name, {})
    handler = abilities.get(change)
    if handler is None:
        return False

    # Apply loyalty change (the "cost") BEFORE handler resolution
    # per CR 606.3 -- the cost is paid as the ability is announced;
    # the effect resolves afterward.
    card.loyalty += change
    gs._pw_activated_this_turn.add(card.name)
    PW_ACTIVATIONS += 1

    # Fire the effect.
    try:
        handler(card, gs)
    except Exception as e:
        gs._log(f"  PW {card.name} ability {change:+d} error: {e}")

    # Instrumentation: a negative ultimate resolved.
    if change == PLANESWALKER_ULTIMATES.get(card.name):
        PW_ULTIMATES += 1

    # State-based action: loyalty <= 0 -> graveyard (shared helper).
    _pw_zero_loyalty_sba(card, gs)

    return True


# ── R5 gate + activate-for-turn orchestrator (zero-RNG) ──────────────

def _pw_loyalty_enabled(gs, opp_gs) -> bool:
    """R5 capability gate. Fires if EITHER seat's APL opts in via the
    WANTS_PW_LOYALTY flag. The gate is checked at the CALL SITE (the runner);
    this orchestrator itself stays gate-agnostic so it remains composable and
    unit-testable. Gate OFF -> the runner never calls the orchestrator, so the
    legacy path is byte-identical."""
    self_apl = getattr(gs, "_self_apl", None) or getattr(gs, "_match_self_apl", None)
    opp_apl = getattr(gs, "_match_opp_apl", None) or getattr(opp_gs, "_self_apl", None)
    return bool(getattr(self_apl, "WANTS_PW_LOYALTY", False)
                or getattr(opp_apl, "WANTS_PW_LOYALTY", False))


def _default_choose_pw_ability(card) -> int:
    """Zero-RNG default loyalty policy: fire the ultimate once it is affordable
    (loyalty + ult_change >= 0), otherwise tick UP with the largest + ability.
    If the walker has no + ability, take the cheapest affordable change.
    Deterministic: no random(), no board inspection beyond loyalty."""
    abilities = PLANESWALKER_ABILITIES.get(card.name, {})
    if not abilities:
        return 0
    loyalty = getattr(card, "loyalty", 0) or 0
    ult = PLANESWALKER_ULTIMATES.get(card.name)
    if ult is not None and loyalty + ult >= 0:
        return ult
    plus = [c for c in abilities if c > 0]
    if plus:
        return max(plus)
    affordable = [c for c in abilities if loyalty + c >= 0]
    return max(affordable) if affordable else 0


def activate_pw_for_turn(card, gs, opp_gs=None, apl=None) -> bool:
    """Choose and apply ONE loyalty ability for a single planeswalker this
    turn, delegating the loyalty change + per-turn budget (CR 606.3) + 0-loyalty
    SBA (CR 704.5i) to activate_planeswalker_ability. Zero-RNG.

    The choice comes from apl.choose_pw_ability(card, gs, opp_gs) when the APL
    provides one, else the deterministic _default_choose_pw_ability policy.
    opp_gs is stashed transiently on gs._pw_opp so ability handlers can reach
    the opponent's zones best-effort (no-op when absent), then restored.

    Returns True iff an ability fired."""
    chooser = getattr(apl, "choose_pw_ability", None)
    if callable(chooser):
        change = chooser(card, gs, opp_gs)
    else:
        change = _default_choose_pw_ability(card)
    prev = getattr(gs, "_pw_opp", None)
    gs._pw_opp = opp_gs
    try:
        return activate_planeswalker_ability(card, gs, change)
    finally:
        gs._pw_opp = prev


def activate_pws_for_turn(gs, opp_gs=None, apl=None) -> int:
    """Iterate the active player's battlefield and activate ONE ability per
    planeswalker (each subject to the once-per-turn budget). Returns the count
    that fired. The CALLER gates this on _pw_loyalty_enabled; the orchestrator
    is gate-agnostic by design."""
    fired = 0
    zones = getattr(gs, "zones", None)
    battlefield = getattr(zones, "battlefield", None) if zones is not None else None
    for card in list(battlefield or []):
        if "planeswalker" in (getattr(card, "type_line", "") or "").lower():
            if activate_pw_for_turn(card, gs, opp_gs, apl):
                fired += 1
    return fired
