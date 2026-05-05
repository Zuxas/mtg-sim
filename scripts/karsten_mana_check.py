"""
scripts/karsten_mana_check.py — Frank Karsten mana source validator

Ports the core simulation from frankkarsten/MTG-Math/HowManySources2022Update.py
into a reusable function. Given a deck's colored pip requirements and source count,
returns the on-curve casting probability with London mulligan.

Usage:
    python scripts/karsten_mana_check.py --deck decks/boros_energy_modern.txt
    python scripts/karsten_mana_check.py --sources 18 --pips 2 --turn 3 --decksize 60
    python scripts/karsten_mana_check.py --format modern --all  # check all Modern decks

Reference: https://github.com/frankkarsten/MTG-Math
"""
import random
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Core simulation (ported from Karsten, London mulligan) ────────────────────

def prob_cast_on_curve(good_sources, total_lands, pips_needed, turn,
                       deck_size=60, simulations=200_000):
    """Monte Carlo: probability of casting a spell requiring `pips_needed` colored
    mana on turn `turn` in a `deck_size`-card deck with `total_lands` lands
    (of which `good_sources` produce the required color).

    London mulligan: keep hands with 2-5 lands (7-card), bottom worst on 6/5.
    Always-on-play assumption (matches Karsten's methodology).

    Returns:
        float — conditional probability (given you hit land drops) of casting on curve
    """
    assert pips_needed <= turn, "Need at most turn's worth of colored pips"

    decklist = {
        'Spell':     deck_size - total_lands,
        'Good Land': good_sources,
        'Other Land': total_lands - good_sources,
    }

    def total_l(hand):
        return hand['Good Land'] + hand['Other Land']

    def bottom_land(hand, n):
        bot_other = min(hand['Other Land'], n)
        hand['Other Land'] -= bot_other
        bot_good  = min(hand['Good Land'], n - bot_other)
        hand['Good Land']  -= bot_good

    successes = relevant = 0

    for _ in range(simulations):
        # Build and shuffle library
        library = []
        for card, qty in decklist.items():
            library += [card] * qty
        random.shuffle(library)

        # Mulligan
        kept = False
        hand = None
        for handsize in ['free', 7, 6, 5, 4]:
            hand = {'Spell': 0, 'Good Land': 0, 'Other Land': 0}
            for _ in range(7):
                hand[library.pop(0)] += 1

            if handsize == 4 or (handsize == 7 and 2 <= total_l(hand) <= 5):
                kept = True
            elif handsize == 6:
                if hand['Spell'] > 3:
                    hand['Spell'] -= 1
                else:
                    bottom_land(hand, 1)
                if 2 <= total_l(hand) <= 4:
                    kept = True
            elif handsize == 5:
                if hand['Spell'] > 3:
                    hand['Spell'] -= 2
                elif hand['Spell'] == 3:
                    bottom_land(hand, 1); hand['Spell'] -= 1
                else:
                    bottom_land(hand, 2)
                if 2 <= total_l(hand) <= 3:
                    kept = True

            if kept:
                break
            # Reshuffle for next mull attempt
            for card, qty in decklist.items():
                library += [card] * qty
            random.shuffle(library)

        # Draw to turn (skip T1 draw = on-play)
        for _ in range(2, turn + 1):
            hand[library.pop(0)] += 1

        if total_l(hand) >= turn:
            relevant += 1
            if hand['Good Land'] >= pips_needed:
                successes += 1

    return successes / relevant if relevant else 0.0


# ── Deck file parsing ──────────────────────────────────────────────────────────

def parse_deck_colors(filepath):
    """Read a deck file and infer pip requirements from mana costs of spells."""
    from data.card import Card
    import json

    with open(os.path.join(os.path.dirname(__file__), '..',
                           'data', 'rules_reference', 'scryfall_oracle_cards.json'),
              encoding='utf-8') as f:
        oracle = {c['name']: c for c in json.load(f)}

    cards = {}
    with open(filepath, encoding='utf-8', errors='ignore') as f:
        in_side = False
        for line in f:
            l = line.strip()
            if 'sideboard' in l.lower():
                in_side = True
            if not in_side:
                m = re.match(r'(\d+)\s+(.+)', l)
                if m:
                    cards[m.group(2).strip()] = int(m.group(1))

    color_counts = {'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0}
    land_count = 0
    for name, qty in cards.items():
        if name.lower() in ('plains', 'island', 'swamp', 'mountain', 'forest'):
            land_count += qty
            continue
        c = oracle.get(name)
        if not c:
            continue
        if c.get('type_line', '').lower().startswith('land') or 'Land' in (c.get('type_line') or ''):
            land_count += qty
        else:
            mc = c.get('mana_cost', '') or ''
            for pip in ('W', 'U', 'B', 'R', 'G'):
                count = mc.count(f'{{{pip}}}')
                color_counts[pip] += count * qty

    return color_counts, land_count, sum(cards.values()) - land_count


# ── Main ───────────────────────────────────────────────────────────────────────

def check_sources_for_spell(pips, turn, good_sources, total_lands, deck_size=60,
                             target_pct=90.0, sims=200_000):
    """Report on whether a deck has enough sources for a spell."""
    prob = prob_cast_on_curve(good_sources, total_lands, pips, turn,
                               deck_size, simulations=sims)
    ok = prob * 100 >= target_pct
    status = 'OK' if ok else 'LOW'
    return prob, status


def main():
    ap = argparse.ArgumentParser(description='Karsten mana source checker')
    ap.add_argument('--sources', type=int, help='Number of colored sources')
    ap.add_argument('--pips',    type=int, help='Colored pips needed (e.g. 2 for WW)')
    ap.add_argument('--turn',    type=int, help='Turn to cast the spell')
    ap.add_argument('--decksize',type=int, default=60)
    ap.add_argument('--sims',    type=int, default=200_000)
    ap.add_argument('--deck',    type=str, help='Path to deck file')
    ap.add_argument('--target',  type=float, default=90.0,
                    help='Target cast probability % (default 90)')
    args = ap.parse_args()

    if args.sources and args.pips and args.turn:
        # Direct calculation mode
        # Need total_lands estimate — assume ~24 for 60-card
        total_lands = args.sources + max(0, 24 - args.sources)
        prob, status = check_sources_for_spell(
            args.pips, args.turn, args.sources, total_lands,
            args.decksize, args.target, args.sims)
        cost = 'C' * args.pips
        print(f"Cast {''.join(['C']*args.pips)} on T{args.turn} with {args.sources} sources: "
              f"{prob*100:.1f}%  [{status}]")

    elif args.deck:
        if not os.path.exists(args.deck):
            print(f"Deck file not found: {args.deck}")
            return
        print(f"Checking mana base: {args.deck}")
        try:
            color_pips, land_count, spell_count = parse_deck_colors(args.deck)
        except Exception as e:
            print(f"  Error parsing deck: {e}")
            return

        deck_size = land_count + spell_count
        colors = [(c, pips) for c, pips in color_pips.items() if pips > 0]
        if not colors:
            print("  No colored pips found.")
            return

        print(f"  Deck size: {deck_size}  Lands: {land_count}  Spells: {spell_count}")
        print(f"  Pip counts: {dict(color_pips)}")
        print()

        for color, total_pips in sorted(colors, key=lambda x: -x[1]):
            # The "hardest" cast: most pips in this color / earliest turn needed
            # Use 1-pip requirement (most common) and 2-pip (double-pip spells)
            max_pips_per_spell = min(3, (total_pips + spell_count - 1) // spell_count + 1)
            for pips in range(1, max_pips_per_spell + 1):
                turn = pips + 1  # roughly T2 for 1-pip, T3 for 2-pip, etc.
                # Estimate colored sources (rough: count lands with that color in name)
                # Use 1/3 of lands as colored proxy for now
                good_src_estimate = max(4, land_count // 3)
                prob, status = check_sources_for_spell(
                    pips, turn, good_src_estimate, land_count,
                    deck_size, args.target, args.sims)
                marker = '' if status == 'OK' else '  <-- ADD SOURCES'
                print(f"  {color}x{pips} on T{turn} with ~{good_src_estimate} sources: "
                      f"{prob*100:.1f}%  [{status}]{marker}")
    else:
        print("Use --sources --pips --turn for single check, or --deck for full analysis.")
        print("Example: python scripts/karsten_mana_check.py --sources 14 --pips 2 --turn 3")


if __name__ == "__main__":
    main()
