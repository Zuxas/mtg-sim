"""Systematic audit of all Hybrid (mainboard + sideboard) card handlers.

For each unique card:
  1. Look up Scryfall oracle text (truth)
  2. Locate handler in card_handlers_verified.py / standard_auto_handlers.py
  3. Print side-by-side for human review
  4. Flag obvious mismatches (length, missing keywords, missing draw/scry/lifegain)
"""
import sys, os, json, re, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from data.deck import load_deck_from_file


HYBRID_DECK = "decks/dimir_bounce_jermey_hybrid_standard.txt"


def main():
    mb, sb = load_deck_from_file(HYBRID_DECK)
    unique = sorted(set(c.name for c in mb + sb if not c.is_land()))
    print(f"Unique non-land cards: {len(unique)}\n")

    # Load oracle data
    with open('data/rules_reference/scryfall_oracle_cards.json', encoding='utf-8') as f:
        cards = json.load(f)
    oracle = {c['name']: c for c in cards}

    # Load handler source
    with open('engine/card_handlers_verified.py', 'r', encoding='utf-8') as f:
        verified_src = f.read()
    try:
        with open('engine/standard_auto_handlers.py', 'r', encoding='utf-8') as f:
            auto_src = f.read()
    except FileNotFoundError:
        auto_src = ""

    for name in unique:
        od = oracle.get(name, {})
        oracle_text = od.get('oracle_text', '').strip()
        cost = od.get('mana_cost', '?')
        type_line = od.get('type_line', '?')

        # Find handler in verified
        handler_in_verified = name in verified_src
        handler_in_auto = name in auto_src
        location = "verified" if handler_in_verified else ("auto" if handler_in_auto else "MISSING")

        # Extract handler body if present
        body = ""
        if handler_in_verified:
            # Find the registration line then trace back to the function
            reg_match = re.search(rf'"{re.escape(name)}"\s*:\s*(\w+),', verified_src)
            if reg_match:
                fn_name = reg_match.group(1)
                fn_match = re.search(rf'def {fn_name}\(.*?(?=\ndef |\Z)', verified_src, re.DOTALL)
                if fn_match:
                    body = fn_match.group(0)

        # Side-by-side: oracle text + handler body
        print(f"\n{'='*80}")
        print(f"  {name}    {cost}    ({type_line})    [{location}]")
        print(f"{'='*80}")
        print("ORACLE:")
        for line in oracle_text.split('\n'):
            print(f"  {line}")
        print("HANDLER (body length: {} chars):".format(len(body)))
        if body:
            # Strip the def line and docstring, show actual code
            lines = body.split('\n')
            in_docstring = False
            shown = 0
            for L in lines[1:]:
                if '"""' in L:
                    in_docstring = not in_docstring
                    continue
                if in_docstring:
                    continue
                stripped = L.rstrip()
                if stripped.strip().startswith('#'):
                    continue
                if not stripped.strip():
                    continue
                print(f"  {stripped}")
                shown += 1
                if shown >= 25:
                    print("  ... (truncated)")
                    break
        else:
            print("  <no handler body found>")


if __name__ == '__main__':
    main()
