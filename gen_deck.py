"""
gen_deck.py -- Generate one Modern deck from synergy packages.

Mirrors sim.py conventions (argparse, repo-root sys.path, ASCII output).

Examples:
  python gen_deck.py --core boros_energy_core --auto
  python gen_deck.py --core amulet_titan_core --supports green_ramp_engine,amulet_bounce_lands
  python gen_deck.py --core yawgmoth_sac_core --auto --register
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen.card_pool import CardPool
from gen.package_schema import load_all_packages
from gen.generator import assemble, auto_supports
from gen.deck_writer import write_candidate


def main():
    ap = argparse.ArgumentParser(description="Generate a Modern deck from packages")
    ap.add_argument("--core", required=True, help="core package id")
    ap.add_argument("--supports", default="", help="comma-separated support package ids")
    ap.add_argument("--auto", action="store_true", help="auto-select supports via conjoin graph")
    ap.add_argument("--format", default="modern")
    ap.add_argument("--rebuild-pool", action="store_true")
    ap.add_argument("--register", action="store_true",
                    help="also generate+cache the APL and register the deck by name")
    args = ap.parse_args()

    packages = load_all_packages()
    if args.core not in packages:
        print(f"Unknown core package '{args.core}'. Known: {', '.join(sorted(packages))}")
        sys.exit(2)

    pool = CardPool.load_or_build(args.format, rebuild=args.rebuild_pool)

    if args.auto:
        supports = auto_supports(args.core, packages)
    else:
        supports = [s for s in args.supports.split(",") if s]
    missing = [s for s in supports if s not in packages]
    if missing:
        print(f"Unknown support package(s): {', '.join(missing)}")
        sys.exit(2)

    cand = assemble(args.core, supports, pool, packages)
    out = write_candidate(cand, fmt=args.format, pool=pool)

    print(f"Generated: {cand.name}")
    print(f"  Packages    : {', '.join(cand.packages)}")
    print(f"  Color id    : {''.join(cand.color_identity) or 'C'}")
    print(f"  Mainboard   : {cand.main_count()} ({cand.spell_count(pool)} spells, "
          f"{cand.land_count(pool)} lands)")
    print(f"  Fidelity    : {cand.metadata.get('fidelity')}")
    print(f"  Castability : {cand.metadata.get('castability')}")
    print(f"  Deck file   : {out['deck_file']}")
    print(f"  Candidate   : {out['meta_file']}")

    if args.register:
        from gen.apl_cache import get_apl_for_candidate
        from gen.registry_integration import register_generated_deck
        apl, info = get_apl_for_candidate(cand, packages=packages, fmt=args.format)
        apl_file = os.path.join("apl", "auto_apls", f"gen_{info['hash']}.py")
        if os.path.exists(apl_file):
            row = register_generated_deck(out["deck_id"], out["deck_file"], apl_file,
                                          type(apl).__name__)
            print(f"  Registered  : key '{list(row)[0]}' -> {list(row.values())[0]['module']}")
            print(f"  APL source  : {info['source']}")
        else:
            print(f"  APL         : {info['source']} (no cached module to register)")


if __name__ == "__main__":
    main()
