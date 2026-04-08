"""
engine/combo_model.py — Accurate combo matchup modeling

The real Reanimator matchup isn't "who kills first" — it's:
  - Do we have T1/T2 disruption (Thalia, Meddling Mage, Thoughtseize)?
  - Do we have hate (Cage, Macabre, Priest, Silence)?
  - Does our clock beat theirs once hate lands?

This models the actual game tree:
  1. Both players draw opening hands
  2. Our hand is evaluated for disruption + hate
  3. Their combo kill is adjusted based on what we have
  4. Race is run with adjusted distributions

Kill distribution adjustments per disruption piece:
  Thalia T1/T2:        +1.0 turn to their kill dist (taxes Dark Ritual)
  Meddling Mage:       +INF turns (hard stop if we name the right card)
  Grafdigger's Cage:   +INF turns (combo stops entirely)
  Containment Priest:  +INF turns (creatures can't ETB from GY)
  Faerie Macabre:      -1 from their probability (50% exile key card)
  Thoughtseize:        +0.5 turns (stripped a key piece)
  Cavern of Souls:     +0 (doesn't interact, just protects our threats)
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Per-archetype: which of our cards interact meaningfully
# ---------------------------------------------------------------------------

HARD_STOPS = {
    # Cards that completely shut down the combo if we can resolve them
    "dimir reanimator":   {"Grafdigger's Cage", "Containment Priest",
                           "Faerie Macabre", "Meddling Mage"},
    "lotus combo":        {"Deafening Silence", "Meddling Mage",
                           "Thalia, Guardian of Thraben"},
    "cephalid breakfast": {"Grafdigger's Cage", "Containment Priest",
                           "Faerie Macabre"},
    "sneak and show":     {"Containment Priest", "Meddling Mage"},
    "mono red painter":   {"Stony Silence", "Meddling Mage"},
    "doomsday":           {"Meddling Mage", "Deafening Silence",
                           "Thalia, Guardian of Thraben"},
    "bant nadu":          {"Grafdigger's Cage", "Containment Priest",
                           "Meddling Mage"},
}

SOFT_DISRUPT = {
    # Cards that delay but don't stop — shift kill dist by N turns
    "dimir reanimator":   {"Thalia, Guardian of Thraben": 1.0,
                           "Thoughtseize": 0.5,
                           "Esper Sentinel": 0.3},
    "lotus combo":        {"Thalia, Guardian of Thraben": 1.5,
                           "Esper Sentinel": 0.5},
    "cephalid breakfast": {"Thalia, Guardian of Thraben": 0.5},
    "sneak and show":     {"Thalia, Guardian of Thraben": 0.5},
    "doomsday":           {"Thalia, Guardian of Thraben": 1.5,
                           "Esper Sentinel": 0.5},
    "mono red painter":   {},
    "bant nadu":          {"Thalia, Guardian of Thraben": 0.5},
}

# Our full maindeck card distribution (simplified for evaluation)
HUMANS_MAINDECK = {
    "Champion of the Parish": 4,
    "Thalia's Lieutenant": 4,
    "Thalia, Guardian of Thraben": 4,
    "Guide of Souls": 4,
    "Esper Sentinel": 4,
    "Coppercoat Vanguard": 4,
    "Voice of Victory": 4,
    "Adeline, Resplendent Cathar": 2,
    "Kytheon, Hero of Akros": 2,
    "Urdnan, Dromoka Warrior": 2,
    "Witch Enchanter": 1,
    "Zack Fair": 2,
    "Swords to Plowshares": 4,
    "Cavern of Souls": 4,
    "Valley of Gorgoroth": 4,
    "Karakas": 2,
    "Mutavault": 2,
    "Eiganjo, Seat of the Empire": 1,
    "Plains": 6,
}

HUMANS_SIDEBOARD_G2 = {
    "Grafdigger's Cage": 2,
    "Faerie Macabre": 2,
    "Containment Priest": 2,
    "Deafening Silence": 2,
    "Stony Silence": 2,
    "Meddling Mage": 0,     # not in current list but key card
    "Sanctifier en-Vec": 1,
    "Path to Exile": 1,
    "Wrath of the Skies": 1,
    "Sheltered by Ghosts": 1,
    "Clarion Conqueror": 1,
}


@dataclass
class HandEval:
    has_hard_stop: bool = False
    soft_delay: float   = 0.0
    has_t1_play: bool   = False
    has_t2_play: bool   = False
    hand_size: int      = 7
    hard_stop_card: str = ""


def build_library() -> list:
    """Build a 75-card library from maindeck counts."""
    lib = []
    for card, qty in HUMANS_MAINDECK.items():
        lib.extend([card] * qty)
    return lib


def build_library_g2(archetype: str) -> list:
    """Post-sideboard library: swap in relevant hate, swap out dead cards."""
    lib = list(build_library())
    arch = archetype.lower()

    # Swap out: Swords to Plowshares (often worse vs combo) and filler
    dead_cards = {
        "dimir reanimator":   ["Swords to Plowshares", "Swords to Plowshares",
                               "Voice of Victory", "Voice of Victory"],
        "lotus combo":        ["Swords to Plowshares", "Swords to Plowshares",
                               "Voice of Victory", "Voice of Victory"],
        "cephalid breakfast": ["Swords to Plowshares", "Swords to Plowshares",
                               "Voice of Victory", "Voice of Victory"],
        "sneak and show":     ["Swords to Plowshares", "Voice of Victory"],
        "mono red painter":   ["Swords to Plowshares", "Voice of Victory",
                               "Witch Enchanter"],
        "doomsday":           ["Swords to Plowshares", "Swords to Plowshares",
                               "Voice of Victory", "Voice of Victory"],
        "bant nadu":          ["Swords to Plowshares", "Voice of Victory"],
    }

    # Swap in: hate cards
    hate_in = {
        "dimir reanimator":   ["Grafdigger's Cage", "Grafdigger's Cage",
                               "Faerie Macabre", "Faerie Macabre",
                               "Containment Priest", "Containment Priest"],
        "lotus combo":        ["Deafening Silence", "Deafening Silence",
                               "Grafdigger's Cage", "Containment Priest"],
        "cephalid breakfast": ["Grafdigger's Cage", "Grafdigger's Cage",
                               "Faerie Macabre", "Faerie Macabre",
                               "Containment Priest", "Containment Priest"],
        "sneak and show":     ["Containment Priest", "Containment Priest",
                               "Clarion Conqueror"],
        "mono red painter":   ["Stony Silence", "Stony Silence",
                               "Sanctifier en-Vec"],
        "doomsday":           ["Deafening Silence", "Deafening Silence",
                               "Grafdigger's Cage", "Containment Priest"],
        "bant nadu":          ["Grafdigger's Cage", "Grafdigger's Cage",
                               "Containment Priest", "Containment Priest"],
    }

    for card in dead_cards.get(arch, []):
        if card in lib:
            lib.remove(card)

    lib.extend(hate_in.get(arch, []))
    return lib


def evaluate_hand(hand: list, archetype: str, on_play: bool) -> HandEval:
    """Evaluate an opening hand for its interaction against a specific archetype."""
    arch  = archetype.lower()
    stops = HARD_STOPS.get(arch, set())
    soft  = SOFT_DISRUPT.get(arch, {})

    hard_stop      = any(c in stops for c in hand)
    hard_stop_card = next((c for c in hand if c in stops), "")
    delay          = sum(soft.get(c, 0.0) for c in hand)
    lands          = sum(1 for c in hand if c in {
        "Plains", "Cavern of Souls", "Valley of Gorgoroth",
        "Karakas", "Mutavault", "Eiganjo, Seat of the Empire"
    })

    # T1/T2 play ability
    one_drops = {"Champion of the Parish", "Guide of Souls",
                 "Esper Sentinel", "Kytheon, Hero of Akros"}
    two_drops = {"Thalia, Guardian of Thraben", "Thalia's Lieutenant",
                 "Coppercoat Vanguard"}
    has_t1 = any(c in one_drops for c in hand) and lands >= 1
    has_t2 = (any(c in two_drops for c in hand) or has_t1) and lands >= 2

    return HandEval(
        has_hard_stop=hard_stop,
        soft_delay=min(delay, 3.0),   # cap at 3 turns
        has_t1_play=has_t1,
        has_t2_play=has_t2,
        hand_size=len(hand),
        hard_stop_card=hard_stop_card,
    )


def adjusted_kill_dist(base_dist: dict, delay: float) -> dict:
    """Shift a kill distribution by `delay` turns."""
    result = {}
    for t, prob in base_dist.items():
        new_t = min(int(t + round(delay)), 15)
        result[new_t] = result.get(new_t, 0) + prob
    return result


def run_combo_matchup(
    archetype:   str,
    n:           int   = 10000,
    game:        int   = 1,       # 1=G1 (no SB), 2=G2 (we SB'd), 3=G3 (both SB'd, opp on play)
    on_play:     bool  = True,
    seed:        int   = 42,
) -> dict:
    """
    Simulate N games of Humans vs a combo archetype.
    Returns win%, avg game length, and breakdown by outcome type.

    Outcome types:
      "hard_stop_wins":  we had hate, they couldn't combo, we won
      "hard_stop_lost":  we had hate but they outran it or we died
      "race_win":        no hate, we killed them before they comboed
      "race_loss":       no hate, they comboed before we killed them
    """
    from engine.match_runner import ComboKillSampler

    arch  = archetype.lower()
    rng   = random.Random(seed)

    # Our library
    if game == 1:
        lib_template = build_library()
        opp_on_play  = False   # G1: we're on play (default for sims)
    elif game == 2:
        lib_template = build_library_g2(arch)
        opp_on_play  = True    # G2: model worst case — they're on play
    else:
        # G3: both fully boarded, opponent on play
        lib_template = build_library_g2(arch)
        opp_on_play  = True

    # Our kill distribution (goldfish, from sim data)
    OUR_KILL_DIST = {3: 5, 4: 38, 5: 32, 6: 15, 7: 7, 8: 3}

    wins = 0
    outcomes = {"hard_stop_wins": 0, "hard_stop_lost": 0,
                "race_win": 0, "race_loss": 0}
    game_lengths = []

    for _ in range(n):
        # Shuffle and draw 7
        lib = list(lib_template)
        rng.shuffle(lib)

        # Mulligan: mull if 0-1 lands or no action
        hand = lib[:7]; lib = lib[7:]
        for mull_i in range(3):
            lands = sum(1 for c in hand if c in {
                "Plains", "Cavern of Souls", "Valley of Gorgoroth",
                "Karakas", "Mutavault", "Eiganjo, Seat of the Empire"})
            creatures = sum(1 for c in hand if c in {
                "Champion of the Parish", "Thalia, Guardian of Thraben",
                "Guide of Souls", "Esper Sentinel", "Thalia's Lieutenant",
                "Grafdigger's Cage", "Faerie Macabre", "Containment Priest",
                "Deafening Silence", "Stony Silence"})
            if lands < 2 or (lands == 0):
                rng.shuffle(lib + hand)
                new_size = max(4, 7 - mull_i - 1)
                hand = lib[:new_size]; lib = lib[new_size:]
            else:
                break

        eval_h = evaluate_hand(hand, arch, on_play)

        # Sample their kill turn
        sampler = ComboKillSampler(archetype, rng)
        their_kill = sampler._kill_t

        # Adjust their kill turn based on our interaction
        if eval_h.has_hard_stop:
            # Hard stop: they effectively never combo (model as kill turn 20)
            # BUT: they still have a clock if we don't kill them
            # We win if we kill them before they switch to beatdown (~T8-10)
            their_effective_kill = 20
        else:
            their_effective_kill = max(
                their_kill,
                int(their_kill + eval_h.soft_delay)
            )

        # Sample our kill turn
        our_turns = sorted(OUR_KILL_DIST.keys())
        our_weights = [OUR_KILL_DIST[t] for t in our_turns]
        our_total = sum(our_weights)
        r = rng.random() * our_total
        cumul, our_kill = 0, our_turns[-1]
        for t, w in zip(our_turns, our_weights):
            cumul += w
            if r <= cumul:
                our_kill = t
                break

        # Adjust our kill for on_play/on_draw (opponent on play = we're on draw)
        if opp_on_play:
            our_kill += 1   # one extra turn before we can kill

        # Determine winner
        if our_kill <= their_effective_kill:
            wins += 1
            game_lengths.append(our_kill)
            if eval_h.has_hard_stop:
                outcomes["hard_stop_wins"] += 1
            else:
                outcomes["race_win"] += 1
        else:
            game_lengths.append(their_kill)
            if eval_h.has_hard_stop:
                outcomes["hard_stop_lost"] += 1
            else:
                outcomes["race_loss"] += 1

    win_pct = round(wins / n * 100, 1)
    avg_t   = round(sum(game_lengths) / n, 1)

    return {
        "archetype":  archetype,
        "game":       game,
        "n":          n,
        "win_pct":    win_pct,
        "avg_turns":  avg_t,
        "outcomes":   outcomes,
        "hard_stop_rate": round(
            (outcomes["hard_stop_wins"] + outcomes["hard_stop_lost"]) / n * 100, 1),
    }
