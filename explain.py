"""
explain.py — Interactive turn-by-turn game walkthrough

Runs a single goldfish game and narrates every decision the APL makes:
what options were available, what was chosen, and why.

Usage:
    python explain.py                        # random game
    python explain.py --seed 42             # reproducible game
    python explain.py --mulligan 0          # force keep opener
    python explain.py --deck decks/humans_legacy.txt
    python explain.py --interactive         # pause at each turn for input
"""

import sys
import os
import argparse
import copy
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mtg-meta-analyzer"))

from data.card import Card, Tag
from data.deck import load_deck_from_file, load_deck_from_text
from engine.game_state import GameState, Phase
from engine.keywords import KWTag
from apl.mulligan import take_opening_hand


# ---------------------------------------------------------------------------
# ANSI colors for terminal output
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

def hdr(text):    print(f"\n{C.BOLD}{C.CYAN}{text}{C.RESET}")
def good(text):   print(f"  {C.GREEN}✓{C.RESET} {text}")
def info(text):   print(f"  {C.BLUE}→{C.RESET} {text}")
def warn(text):   print(f"  {C.YELLOW}!{C.RESET} {text}")
def dim(text):    print(f"  {C.GRAY}{text}{C.RESET}")
def label(k, v):  print(f"  {C.WHITE}{k:<18}{C.RESET} {v}")

def card_str(card: Card) -> str:
    kw = []
    for t in (KWTag.FLYING, KWTag.HASTE, KWTag.VIGILANCE, KWTag.FIRST_STRIKE,
              KWTag.DEATHTOUCH, KWTag.LIFELINK, KWTag.HEXPROOF, KWTag.TRAMPLE,
              KWTag.HATE_BEAR, KWTag.ETB_BOUNCE, KWTag.ETB_REMOVAL):
        if t in card.tags:
            kw.append(t.replace("_", " "))
    ep = card.effective_power() if card.has(Tag.CREATURE) else None
    et = card.effective_toughness() if card.has(Tag.CREATURE) else None
    pt = f" {ep}/{et}" if ep is not None else ""
    kw_str = f" [{', '.join(kw)}]" if kw else ""
    ctr = f" +{card.counters}" if card.counters > 0 else ""
    copy_str = f" (copy of {card.copying})" if getattr(card, "copying", None) else ""
    sick_str = f" {C.RED}[sick]{C.RESET}" if getattr(card, "summoning_sickness", False) else ""
    return f"{C.WHITE}{card.name}{C.RESET}{C.DIM}({card.cmc:.0f}){pt}{ctr}{copy_str}{kw_str}{C.RESET}{sick_str}"

def print_hand(hand):
    lands   = [c for c in hand if c.is_land()]
    spells  = sorted([c for c in hand if not c.is_land()], key=lambda c: c.cmc)
    parts = []
    for c in lands:
        parts.append(f"{C.GRAY}{c.name}{C.RESET}")
    for c in spells:
        parts.append(card_str(c))
    print(f"  Hand ({len(hand)}): {', '.join(parts) or 'empty'}")

def print_battlefield(bf):
    lands    = [c for c in bf if c.is_land()]
    creatures = [c for c in bf if not c.is_land()]
    land_str = f"{C.GRAY}{', '.join(c.name for c in lands)}{C.RESET}" if lands else ""
    cre_parts = [card_str(c) for c in creatures]
    print(f"  Battlefield: {', '.join(cre_parts) or 'empty'}", end="")
    if land_str:
        print(f"  |  Lands: {land_str}", end="")
    print()


# ---------------------------------------------------------------------------
# Decision explainer — wraps HumansAPL and intercepts decisions
# ---------------------------------------------------------------------------

class ExplainHumansAPL:
    """Humans APL that narrates every decision with reasoning."""

    PRIORITY_NAMES = {
        "Aether Vial":           "Always T1 — generates ongoing card advantage, bypasses future Thalia tax on your own creatures",
        "Champion of the Parish":"Snowball threat — gets +1/+1 every Human you cast. Play ASAP to maximize counters",
        "Thalia's Lieutenant":   "Lord + anthem on ETB — pumps everything immediately and grows with each Human after",
        "Thalia, Guardian of Thraben": "Taxing hate bear — slows opponent's non-creature spells by 1 mana",
        "Kitesail Freebooter":   "ETB disruption — strips opponent's best spell from hand, must be answered",
        "Meddling Mage":         "Combo stopper — names the opponent's key spell to shut off their plan",
        "Phantasmal Image":      "Flex copy — copies your best creature for 2 mana",
        "Mantis Rider":          "Flying haste clock — attacks immediately, hard to block",
        "Reflector Mage":        "Tempo play — bounces a blocker and blanks it for a turn",
        "Militia Bugler":        "Card advantage — finds any 2-power human from top 4",
        "Imperial Recruiter":    "Tutor — finds Champion, Bugler, or any small human",
    }

    def __init__(self, interactive=False):
        self.interactive = interactive

    def _pause(self):
        if self.interactive:
            input(f"  {C.DIM}[Press Enter for next decision]{C.RESET}")

    def explain_keep(self, hand, mulligans, on_play):
        lands  = [c for c in hand if c.is_land()]
        ones   = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        vialed = [c for c in hand if c.name == "Aether Vial"]
        lords  = [c for c in hand if c.name in ("Champion of the Parish", "Thalia's Lieutenant")]
        twos   = [c for c in hand if c.has(Tag.TWO_DROP) and not c.is_land()]

        lc = len(lands)
        print(f"\n  {C.BOLD}Hand analysis:{C.RESET}")
        label("Lands:", f"{lc} ({', '.join(c.name for c in lands)})")
        label("1-drops:", f"{len(ones)} ({', '.join(c.name for c in ones) or 'none'})")
        label("Aether Vial:", "YES" if vialed else "NO")
        label("Lords:", f"{', '.join(c.name for c in lords) or 'none'}")

        # Evaluate
        if lc == 0:
            warn("0 lands — automatic mulligan. Cannot function.")
            return False
        if lc == 1 and len(hand) >= 6:
            warn("1 land in 6+ card hand — too risky. Need T2 land drop to stay functional.")
            return False
        if lc >= 5 and len(hand) == 7:
            warn(f"{lc} lands in opener — flood risk. Mulligan for better ratio.")
            return False
        if lc >= 4 and len(hand) == 6:
            warn(f"{lc} lands in 6-card hand — still flooded. Mulligan.")
            return False

        has_action = bool(ones or vialed or lords)
        if lc == 2 and not has_action and on_play and len(hand) >= 6:
            warn("2 lands but no T1/T2 action on the play — too slow. Mulligan.")
            return False
        if lc == 2 and not has_action and not on_play and not twos and len(hand) >= 6:
            warn("2 lands but no early action on the draw either — marginal, mulligan.")
            return False

        good(f"{'Keep' if mulligans == 0 else f'Keep {len(hand)}-card hand'}!")
        if vialed: info("Aether Vial in hand — strong keep regardless of curve.")
        if lords:  info(f"{lords[0].name} — lord payoff, prioritize playing T1-2 humans around it.")
        if ones:   info(f"T1 plays: {', '.join(c.name for c in ones)}")
        return True

    def explain_bottom(self, hand, n):
        """Explain which n cards to put on the bottom."""
        if n == 0:
            return []
        print(f"\n  {C.BOLD}Bottoming {n} card(s):{C.RESET}")
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)

        to_bottom = []

        # Bottom excess lands over 3
        if len(lands) > 3:
            excess = lands[3:]
            info(f"Bottom excess lands (keeping 3): {', '.join(c.name for c in excess[:n])}")
            to_bottom.extend(excess[:n])

        # Bottom high CMC spells
        for card in spells:
            if len(to_bottom) >= n: break
            if card.cmc >= 3 and card.name not in ("Champion of the Parish", "Thalia's Lieutenant"):
                info(f"Bottom {card.name} (CMC {card.cmc:.0f}, not a lord — deprioritized on {7-n}-card hand)")
                to_bottom.append(card)

        # Fill remainder
        for card in spells:
            if len(to_bottom) >= n: break
            if card not in to_bottom:
                info(f"Bottom {card.name} (lowest priority remaining)")
                to_bottom.append(card)

        return to_bottom[:n]

    def explain_land(self, gs):
        """Explain land selection."""
        lands_in_hand = [c for c in gs.hand() if c.is_land()]
        if not lands_in_hand:
            dim("No land to play.")
            return None

        # Humans just plays first land — all lands produce mana for humans
        chosen = lands_in_hand[0]
        if len(lands_in_hand) > 1:
            others = [c.name for c in lands_in_hand[1:]]
            info(f"Land options: {', '.join(c.name for c in lands_in_hand)}")
            info(f"Playing {chosen.name} — all Humans lands tap for colorless/any-color for creatures; order doesn't matter here.")
        else:
            info(f"Only land available: {chosen.name}")
        return chosen

    def explain_spells(self, gs):
        """Explain full casting sequence for the main phase."""
        castable = [c for c in gs.hand()
                    if not c.is_land() and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
        if not castable:
            dim(f"No castable spells ({gs.mana_pool.total()} mana available).")
            return []

        print(f"\n  {C.BOLD}Casting decisions ({gs.mana_pool.total()} mana):{C.RESET}")
        info(f"Castable: {', '.join(card_str(c) for c in sorted(castable, key=lambda c: c.cmc))}")

        cast_order = []

        # Vial first
        for c in castable:
            if c.name == "Aether Vial" and c not in cast_order:
                vials_in_play = sum(1 for p in gs.battlefield() if p.name == "Aether Vial")
                if vials_in_play == 0:
                    good(f"Cast {c.name} — {self.PRIORITY_NAMES.get(c.name, 'high priority')}")
                    cast_order.append(c)

        # Lords
        for name in ("Champion of the Parish", "Thalia's Lieutenant", "Thalia, Guardian of Thraben"):
            for c in castable:
                if c.name == name and c not in cast_order and gs.mana_pool.total() >= c.cmc:
                    good(f"Cast {c.name} — {self.PRIORITY_NAMES.get(c.name, '')}")
                    cast_order.append(c)

        # Remaining creatures by CMC
        remaining = sorted([c for c in castable
                           if c.has(Tag.CREATURE) and c not in cast_order],
                          key=lambda c: (c.cmc, c.name))
        for c in remaining:
            total_spent = sum(int(x.cmc) for x in cast_order)
            mana_left = gs.mana_pool.total() - total_spent
            if mana_left >= c.cmc:
                reason = self.PRIORITY_NAMES.get(c.name, f"CMC {c.cmc:.0f} creature, fills curve")
                good(f"Cast {card_str(c)} — {reason}")
                cast_order.append(c)

        # Non-creature spells last
        others = sorted([c for c in castable
                        if not c.is_land() and not c.has(Tag.CREATURE)
                        and c.name != "Aether Vial" and c not in cast_order],
                       key=lambda c: c.cmc)
        for c in others:
            total_spent = sum(int(x.cmc) for x in cast_order)
            if gs.mana_pool.total() - total_spent >= c.cmc:
                good(f"Cast {c.name} — non-creature, fills remaining mana")
                cast_order.append(c)

        # What we couldn't cast
        couldnt = [c for c in gs.hand()
                   if not c.is_land() and not gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
        # Note Image only if it wasn't cast
        image_in_hand = [c for c in gs.hand() if c.name == "Phantasmal Image"]
        if image_in_hand:
            creatures_on_bf = [c for c in gs.battlefield() if c.has(Tag.CREATURE)]
            best = max(creatures_on_bf, key=lambda c: c.effective_power(), default=None)
            if not best or best.effective_power() < 2:
                dim(f"Holding Phantasmal Image — "
                    + (f"best target is {best.name} {best.effective_power()}/{best.effective_toughness()} (too small)"
                       if best else "no creatures to copy yet"))
        if couldnt:
            dim(f"Held: {', '.join(f'{c.name}({c.cmc:.0f})' for c in couldnt)} — not enough mana")

        return cast_order


# ---------------------------------------------------------------------------
# Full game runner with narration
# ---------------------------------------------------------------------------

def run_explained_game(mainboard, seed=None, on_play=True, interactive=False, max_turns=12):
    explainer = ExplainHumansAPL(interactive=interactive)
    rng_seed = seed if seed is not None else random.randint(0, 99999)
    random.seed(rng_seed)

    fresh_deck = copy.deepcopy(mainboard)

    print(f"\n{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  LEGACY HUMANS — Explained Game  (seed={rng_seed}){C.RESET}")
    print(f"  {'On the PLAY' if on_play else 'On the DRAW'}")
    print(f"{C.BOLD}{C.CYAN}{'='*60}{C.RESET}")

    # --- Mulligan ---
    hdr("OPENING HAND")
    mulligans = 0
    hand = library = None

    for attempt in range(5):
        random.shuffle(fresh_deck)
        hand    = fresh_deck[:7]
        library = fresh_deck[7:]
        size    = 7 - attempt

        print(f"\n  {'Opener' if attempt == 0 else f'Mulligan {attempt}'} ({len(hand)} cards drawn, keeping {size}):")
        print_hand(hand)

        keep = explainer.explain_keep(hand, attempt, on_play)

        if keep:
            if attempt > 0:
                to_bottom = explainer.explain_bottom(list(hand), attempt)
                for c in to_bottom:
                    hand.remove(c)
                    library.append(c)
            mulligans = attempt
            break
        else:
            fresh_deck = list(hand) + library
            mulligans = attempt + 1
    else:
        info("Forced keep on 3-card hand.")
        mulligans = 4

    print(f"\n  {C.GREEN}Kept {len(hand)}-card hand after {mulligans} mulligan(s){C.RESET}")
    if interactive:
        explainer._pause()

    # --- Game State ---
    gs = GameState(mainboard=mainboard, on_play=on_play)
    gs.new_game()
    gs.zones.hand    = list(hand)
    gs.zones.library = list(library)

    # --- Turn loop ---
    for turn_num in range(1, max_turns + 1):
        hdr(f"TURN {turn_num} {'(Play)' if on_play else '(Draw)'}")

        # Untap
        gs.turn          = turn_num
        gs.phase         = Phase.UNTAP
        gs.land_played   = False
        gs.mana_pool.empty()
        # Clear summoning sickness
        for card in gs.zones.battlefield:
            card.summoning_sickness = False

        # Upkeep — tick Vial, narrate
        gs.phase = Phase.UPKEEP
        vial = gs.vial_in_play()
        if vial:
            vial.counters += 1
            info(f"Upkeep: Aether Vial ticks to {vial.counters} counter(s)"
                 f" — can deploy CMC {vial.counters} creatures for free")

        # Draw
        gs.phase = Phase.DRAW
        if not (turn_num == 1 and on_play):
            drawn = gs.zones.draw(1)
            if drawn:
                info(f"Draw: {card_str(drawn[0])}")
        else:
            dim("No draw (on the play, turn 1)")

        print_hand(gs.zones.hand)

        # Main phase 1
        gs.phase = Phase.MAIN1
        gs.tap_lands()

        info(f"Mana available: {gs.mana_pool.total()} ({gs.zones.count_lands_in_play()} lands in play)")

        # Land
        print(f"\n  {C.BOLD}Land drop:{C.RESET}")
        chosen_land = explainer.explain_land(gs)
        if chosen_land:
            gs.play_land(chosen_land)
            # Retap after playing
            gs.mana_pool.empty()
            gs.tap_lands()
            info(f"Mana after land: {gs.mana_pool.total()}")

        # Spells
        bf_before = set(id(c) for c in gs.zones.battlefield)
        cast_order = explainer.explain_spells(gs)
        for card in cast_order:
            if gs.mana_pool.can_cast(card.mana_cost, card.cmc) and card in gs.zones.hand:
                gs.cast_spell(card)

        # Show Vial deploys (creatures that appeared on battlefield not via cast)
        vial_deployed = [c for c in gs.zones.battlefield
                         if id(c) not in bf_before
                         and c not in cast_order
                         and c.has(Tag.CREATURE)]
        if vial_deployed:
            for c in vial_deployed:
                info(f"Vial deploy: {card_str(c)} enters free")

        # Combat
        gs.phase = Phase.COMBAT
        attackers = gs.zones.creatures_on_battlefield()
        if attackers:
            damage_this_turn = sum(c.effective_power() for c in attackers)
            gs.damage_dealt += damage_this_turn
            atk_str = ", ".join(f"{card_str(c)} ({c.effective_power()} dmg)" for c in attackers)
            print(f"\n  {C.BOLD}Combat:{C.RESET}")
            info(f"Attacking with: {atk_str}")
            good(f"Deal {damage_this_turn} damage  →  Total: {C.YELLOW}{gs.damage_dealt}/20{C.RESET}")
        else:
            dim("No attackers yet.")

        # State summary
        print(f"\n  {C.BOLD}Board after turn {turn_num}:{C.RESET}")
        print_battlefield(gs.zones.battlefield)
        label("Total damage:", f"{C.YELLOW}{gs.damage_dealt}/20{C.RESET}")
        label("Cards in hand:", str(gs.zones.hand_size()))
        label("Cards in library:", str(gs.zones.library_size()))

        # End step
        gs.phase = Phase.END
        gs.mana_pool.empty()

        if gs.damage_dealt >= 20:
            print(f"\n{C.BOLD}{C.GREEN}  *** WON ON TURN {turn_num} ***{C.RESET}")
            break

        if interactive:
            explainer._pause()

    else:
        print(f"\n{C.YELLOW}  Game went to turn {max_turns} without a goldfish kill.{C.RESET}")
        print(f"  Damage dealt: {gs.damage_dealt}/20")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SAMPLE_LIST = """
4 Champion of the Parish
4 Thalia's Lieutenant
4 Mantis Rider
4 Reflector Mage
4 Militia Bugler
3 Thalia, Guardian of Thraben
3 Aether Vial
2 Kitesail Freebooter
2 Meddling Mage
2 Phantasmal Image
2 Imperial Recruiter
4 Cavern of Souls
4 Unclaimed Territory
4 Ancient Ziggurat
4 Horizon Canopy
3 Seachrome Coast
2 Plains
1 Island
""".strip()


def main():
    ap = argparse.ArgumentParser(description="Walk through a Humans game decision by decision")
    ap.add_argument("--seed",        type=int, default=None)
    ap.add_argument("--deck",        default="")
    ap.add_argument("--draw",        action="store_true")
    ap.add_argument("--interactive", action="store_true", help="Pause at each turn")
    ap.add_argument("--turns",       type=int, default=12)
    args = ap.parse_args()

    if args.deck:
        main_deck, _ = load_deck_from_file(args.deck)
    else:
        main_deck, _ = load_deck_from_text(SAMPLE_LIST)

    run_explained_game(
        mainboard=main_deck,
        seed=args.seed,
        on_play=not args.draw,
        interactive=args.interactive,
        max_turns=args.turns,
    )


if __name__ == "__main__":
    main()
