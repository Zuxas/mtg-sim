"""
sim_bridge.py — Wire mtg-sim kill distributions into the Team Resolve Gauntlet

Replaces hardcoded ARC_TILT values in run_pipeline_v3.py with actual
simulated G1 race win probabilities from goldfish kill turn distributions.

Usage:
    python sim_bridge.py --list-archetypes
    python sim_bridge.py --field "Humans,Lands,Delver,Elves,Painter,Stoneforge,Golgari Hogaak"
    python sim_bridge.py --sheet gauntlet_input.csv --out tilts.csv
    python sim_bridge.py --sheet gauntlet_input.csv --patch
"""

import argparse
import csv
import os
import sys
import re
import random
import statistics
import shutil
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ARCHETYPE_CLOCKS = {
    "humans":           {4: 0.5, 5: 21.9, 6: 38.5, 7: 28.2, 8: 7.8, 9: 2.1, 10: 0.5, 11: 0.4, 12: 0.1},
    "elves":            {2: 15.0, 3: 40.0, 4: 25.0, 5: 12.0, 6: 5.0, 7: 3.0},
    "delver":           {3: 8.0, 4: 30.0, 5: 32.0, 6: 18.0, 7: 8.0, 8: 4.0},
    "izzet delver":     {3: 8.0, 4: 30.0, 5: 32.0, 6: 18.0, 7: 8.0, 8: 4.0},
    "dimir tempo":      {3: 6.0, 4: 30.0, 5: 32.0, 6: 18.0, 7: 9.0, 8: 5.0},
    "lands":            {2: 5.0, 3: 25.0, 4: 30.0, 5: 20.0, 6: 12.0, 7: 5.0, 8: 3.0},
    "painter":          {2: 8.0, 3: 28.0, 4: 30.0, 5: 20.0, 6: 10.0, 7: 4.0},
    "mono red painter": {2: 8.0, 3: 28.0, 4: 30.0, 5: 20.0, 6: 10.0, 7: 4.0},
    "stoneforge":       {3: 5.0, 4: 20.0, 5: 35.0, 6: 25.0, 7: 10.0, 8: 5.0},
    "hogaak":           {2: 10.0, 3: 35.0, 4: 30.0, 5: 15.0, 6: 7.0, 7: 3.0},
    "golgari hogaak":   {2: 10.0, 3: 35.0, 4: 30.0, 5: 15.0, 6: 7.0, 7: 3.0},
    # Legacy combo — fast, disruptable
    "dimir reanimator": {1: 5.0, 2: 35.0, 3: 35.0, 4: 15.0, 5: 7.0, 6: 3.0},
    "reanimator":       {1: 5.0, 2: 35.0, 3: 35.0, 4: 15.0, 5: 7.0, 6: 3.0},
    "lotus combo":      {1: 8.0, 2: 42.0, 3: 30.0, 4: 12.0, 5: 6.0, 6: 2.0},
    "cephalid breakfast":{2: 20.0, 3: 40.0, 4: 25.0, 5: 10.0, 6: 5.0},
    "sneak and show":   {3: 25.0, 4: 35.0, 5: 25.0, 6: 10.0, 7: 5.0},
    "doomsday":         {2: 15.0, 3: 40.0, 4: 30.0, 5: 10.0, 6: 5.0},
    "bant nadu":        {3: 20.0, 4: 40.0, 5: 25.0, 6: 10.0, 7: 5.0},
    "eldrazi stompy":   {2: 5.0, 3: 20.0, 4: 35.0, 5: 25.0, 6: 12.0, 7: 3.0},
    "death and taxes":  {3: 5.0, 4: 20.0, 5: 35.0, 6: 25.0, 7: 10.0, 8: 5.0},
    "four-color":       {3: 5.0, 4: 20.0, 5: 35.0, 6: 25.0, 7: 10.0, 8: 5.0},
    "jeskai control":   {5: 10.0, 6: 20.0, 7: 30.0, 8: 25.0, 9: 10.0, 10: 5.0},
    "mono red aggro":   {2: 10.0, 3: 30.0, 4: 30.0, 5: 20.0, 6: 8.0, 7: 2.0},
    "mono red prison":  {3: 10.0, 4: 25.0, 5: 30.0, 6: 20.0, 7: 10.0, 8: 5.0},
    # Modern
    "burn":             {3: 25.0, 4: 45.0, 5: 20.0, 6: 7.0, 7: 3.0},
    "affinity":         {3: 15.0, 4: 40.0, 5: 30.0, 6: 12.0, 7: 3.0},
    "tron":             {4: 10.0, 5: 30.0, 6: 35.0, 7: 15.0, 8: 7.0, 9: 3.0},
    "murktide":         {3: 10.0, 4: 30.0, 5: 35.0, 6: 18.0, 7: 5.0, 8: 2.0},
    "yawgmoth":         {4: 2.4, 5: 19.0, 6: 19.8, 7: 20.6, 8: 11.2, 9: 8.6, 10: 5.6, 11: 4.8},  # measured
    "living end":       {4: 3.4, 5: 37.4, 6: 24.0, 7: 11.0, 8: 9.8, 9: 4.4, 10: 3.0, 11: 2.0},  # measured
    "amulet":           {5: 6.0, 6: 8.6, 7: 21.8, 8: 5.6, 9: 4.8, 10: 3.6, 11: 4.8, 12: 3.6, 13: 2.4},  # measured
    "borosenergy":      {4: 6.2, 5: 17.6, 6: 23.2, 7: 22.4, 8: 12.4, 9: 6.0, 10: 3.4, 11: 3.4, 12: 1.6},  # measured
    "boros energy":     {4: 6.2, 5: 17.6, 6: 23.2, 7: 22.4, 8: 12.4, 9: 6.0, 10: 3.4},
    "control":          {5: 5.0, 6: 15.0, 7: 30.0, 8: 30.0, 9: 15.0, 10: 5.0},
    "aggro":            {3: 10.0, 4: 30.0, 5: 35.0, 6: 18.0, 7: 5.0, 8: 2.0},
    "combo":            {2: 5.0, 3: 25.0, 4: 35.0, 5: 25.0, 6: 10.0},
    "midrange":         {4: 10.0, 5: 25.0, 6: 35.0, 7: 20.0, 8: 8.0, 9: 2.0},
    "tempo":            {3: 8.0, 4: 28.0, 5: 35.0, 6: 20.0, 7: 7.0, 8: 2.0},
    "ramp":             {4: 5.0, 5: 20.0, 6: 35.0, 7: 25.0, 8: 10.0, 9: 5.0},
    # Measured from GenericAPL simulation of real playbook decklists
    "5colorhumans":       {3: 23.8, 4: 49.6, 5: 17.2, 6: 6.0, 7: 1.6, 8: 0.8, 9: 0.8},
    "amulettitan":        {5: 6.0, 6: 8.6, 7: 21.8, 8: 5.6, 9: 4.8, 10: 3.6, 11: 4.8, 12: 3.6, 13: 2.4, 14: 4.2, 15: 3.4},
    "borosaggro":         {4: 4.8, 5: 26.4, 6: 23.8, 7: 16.4, 8: 11.4, 9: 9.0, 10: 3.6, 11: 2.2, 12: 1.4},
    "borosenergy":        {4: 6.2, 5: 17.6, 6: 23.2, 7: 22.4, 8: 12.4, 9: 6.0, 10: 3.4, 11: 3.4, 12: 1.6},
    "dimirmidrange":      {4: 10.4, 5: 21.6, 6: 21.6, 7: 15.4, 8: 10.8, 9: 6.6, 10: 6.0, 11: 3.0, 12: 0.8},
    "dimiroculus":        {4: 3.0, 5: 13.6, 6: 16.6, 7: 10.2, 8: 11.4, 9: 9.0, 10: 11.2, 11: 5.8, 12: 5.8},
    "domainzoo":          {5: 4.4, 6: 8.8, 7: 15.0, 8: 17.0, 9: 12.6, 10: 13.4, 11: 8.6, 12: 5.0, 13: 5.0},
    "eldrazitron":        {4: 4.2, 5: 32.8, 6: 15.8, 7: 21.0, 8: 6.2, 9: 7.0, 10: 4.4, 11: 3.8, 12: 0.8},
    "glockulous":         {5: 20.6, 6: 27.2, 7: 17.4, 8: 11.6, 9: 8.0, 10: 5.4, 11: 4.6, 12: 2.0},
    "golgariyawgmoth":    {4: 2.4, 5: 19.0, 6: 19.8, 7: 20.6, 8: 11.2, 9: 8.6, 10: 5.6, 11: 4.8},
    "goryosvengeance":    {5: 0.8, 6: 7.4, 7: 13.8, 8: 13.6, 9: 12.4, 10: 11.8, 11: 8.6, 12: 8.0},
    "izzetaffinity":      {5: 5.2, 6: 9.0, 7: 12.6, 8: 11.4, 9: 9.4, 10: 7.6, 11: 7.8, 12: 5.6},
    "izzetprowess":       {6: 1.0, 7: 6.2, 8: 10.4, 9: 12.8, 10: 9.2, 11: 11.0, 12: 11.8, 13: 6.0},
    "jeskaiblink":        {4: 1.6, 5: 14.8, 6: 16.8, 7: 21.8, 8: 9.4, 9: 7.6, 10: 7.8, 11: 6.2},
    "livingend":          {4: 3.4, 5: 37.4, 6: 24.0, 7: 11.0, 8: 9.8, 9: 4.4, 10: 3.0, 11: 2.0},
    "monogreenlandfall":  {4: 2.2, 5: 10.4, 6: 12.2, 7: 15.2, 8: 8.6, 9: 11.0, 10: 7.6, 11: 6.6},
    "simicneoform":       {5: 4.4, 6: 10.0, 7: 13.8, 8: 11.2, 9: 11.8, 10: 9.8, 11: 7.0, 12: 6.4},
    "uwblink":            {4: 8.4, 5: 36.2, 6: 24.4, 7: 14.8, 8: 7.6, 9: 3.4, 10: 2.4, 11: 1.2},
    # Hand-tuned for Modern archetypes not in playbooks
    # ("grinding breach" / "grindingbreach" removed 2026-05-14 -- the deck file
    # was actually a Temur storm-ritual list, no real Grinding Breach modeled.)
    "temur breach":       {3: 8.0, 4: 30.0, 5: 32.0, 6: 18.0, 7: 8.0, 8: 4.0},    # Underworld Breach cascade T4-5
    "temurbreach":        {3: 8.0, 4: 30.0, 5: 32.0, 6: 18.0, 7: 8.0, 8: 4.0},
    "mono blue belcher":  {1: 15.0, 2: 40.0, 3: 30.0, 4: 10.0, 5: 5.0},            # Glass cannon T1-2
    "monobluebelcher":    {1: 15.0, 2: 40.0, 3: 30.0, 4: 10.0, 5: 5.0},
    "orzhov blink":       {4: 5.0, 5: 20.0, 6: 30.0, 7: 25.0, 8: 12.0, 9: 5.0, 10: 3.0},  # Midrange T6 avg
    "orzhovblink":        {4: 5.0, 5: 20.0, 6: 30.0, 7: 25.0, 8: 12.0, 9: 5.0, 10: 3.0},
    "esper blink":        {4: 3.0, 5: 15.0, 6: 28.0, 7: 28.0, 8: 15.0, 9: 7.0, 10: 4.0},
    "esperblink":         {4: 3.0, 5: 15.0, 6: 28.0, 7: 28.0, 8: 15.0, 9: 7.0, 10: 4.0},
    "dimir murktide":     {3: 8.0, 4: 28.0, 5: 32.0, 6: 20.0, 7: 8.0, 8: 4.0},    # Tempo T4-5
    "dimirmurktide":      {3: 8.0, 4: 28.0, 5: 32.0, 6: 20.0, 7: 8.0, 8: 4.0},
    "eldrazi ramp":       {3: 5.0, 4: 20.0, 5: 35.0, 6: 25.0, 7: 10.0, 8: 5.0},   # Tron variant T5-6
    "eldraziramp":        {3: 5.0, 4: 20.0, 5: 35.0, 6: 25.0, 7: 10.0, 8: 5.0},
    "unknown":            {4: 5.0, 5: 20.0, 6: 35.0, 7: 25.0, 8: 10.0, 9: 5.0},
    # ── Standard field clocks (PT SOS 2026 — measured 2026-05-04, 500 games on play) ─
    # These override the Modern/generic entries above for Standard gauntlet accuracy.
    "izzetprowess":        {4: 0.2, 5: 12.6, 6: 29.6, 7: 20.0, 8: 16.4, 9: 9.8, 10: 6.4},   # avg T7.00
    "izzetprowessstandard":{4: 0.2, 5: 12.6, 6: 29.6, 7: 20.0, 8: 16.4, 9: 9.8, 10: 6.4},   # alias
    "monogreenlandfall":   {4: 4.2, 5: 42.2, 6: 32.8, 7: 16.6, 8: 2.6,  9: 1.2, 10: 0.4},   # avg T5.76
    "izzetspellementals":  {4: 0.2, 5: 3.2,  6: 9.8,  7: 18.0, 8: 16.8, 9: 20.0, 10: 14.2}, # avg T8.00
    "golgarimidrange":     {5: 15.2, 6: 35.2, 7: 24.4, 8: 11.2, 9: 7.8, 10: 3.0, 11: 1.8},  # avg T6.83
    "golgari":             {5: 15.2, 6: 35.2, 7: 24.4, 8: 11.2, 9: 7.8, 10: 3.0, 11: 1.8},  # alias
    "izzetlessons":        {5: 0.2, 6: 1.8, 7: 5.6, 8: 13.0, 9: 17.0, 10: 16.0, 11: 12.6},  # avg T9.92
    "izzetlesson":         {5: 0.2, 6: 1.8, 7: 5.6, 8: 13.0, 9: 17.0, 10: 16.0, 11: 12.6},  # alias
    "azoriusmomo":         {3: 0.2, 4: 8.0, 5: 26.6, 6: 31.4, 7: 22.0, 8: 6.8, 9: 2.4},     # avg T6.11
    "momo":                {3: 0.2, 4: 8.0, 5: 26.6, 6: 31.4, 7: 22.0, 8: 6.8, 9: 2.4},     # alias
    "azoriusblink":        {4: 0.6, 5: 15.2, 6: 50.6, 7: 23.6, 8: 8.0, 9: 1.4, 10: 0.4},    # avg T6.30
    "azoriustempo":        {4: 3.8, 5: 25.8, 6: 43.8, 7: 16.4, 8: 6.6, 9: 3.0, 10: 0.6},    # avg T6.08
    "izzetmaestro":        {4: 9.6, 5: 48.2, 6: 21.8, 7: 9.2,  8: 3.6, 9: 3.8, 10: 1.0},    # avg T5.80
    "selesnyalandfall":    {4: 1.8, 5: 32.2, 6: 34.0, 7: 20.2, 8: 6.6, 9: 3.0, 10: 1.4},    # avg T6.16
    "selesnyaouroboroid":  {4: 3.0, 5: 47.0, 6: 37.0, 7: 8.2,  8: 3.2, 9: 1.0, 10: 0.4},    # avg T5.66
    "azoriusomniscience":  {4: 1.2, 5: 22.2, 6: 42.4, 7: 19.6, 8: 8.6, 9: 3.8, 10: 0.8},   # avg T6.34
    "dimirexcruciator":    {7: 7.6, 8: 28.4, 9: 25.4, 10: 14.2, 11: 8.6, 12: 6.6, 13: 3.4}, # avg T9.45
    # Sultai Reanimator: goldfish APL can't model the reanimate-Atraxa combo;
    # hand-tune to reanimator profile (T2-4 kills when the combo assembles).
    "sultaireanimator":    {2: 8.0, 3: 30.0, 4: 35.0, 5: 18.0, 6: 7.0, 7: 2.0},             # hand-tuned
    # Jeskai Control: ManaPool.available error skips sim; use slow control proxy.
    "jeskaicontrol":       {5: 8.0, 6: 18.0, 7: 28.0, 8: 25.0, 9: 14.0, 10: 7.0},           # hand-tuned
    "mardudiscard":        {5: 15.0, 6: 44.0, 7: 22.7, 8: 11.3, 9: 3.7, 10: 1.7},            # measured T6.49
    "rakdosdiscard":       {5: 6.0, 6: 28.3, 7: 36.3, 8: 12.7, 9: 8.3, 10: 4.3},             # measured T7.02
    "borosdiscard":        {5: 8.7, 6: 36.7, 7: 35.3, 8: 10.7, 9: 6.0, 10: 1.0},             # measured T6.71
    "sultaicontrol":       {7: 2.7, 8: 17.3, 9: 17.3, 10: 18.0, 11: 16.7, 12: 9.3},          # measured T10.19
    # Dimir Excruciator: slow midrange/control (GenericAPL stub)
    "dimirmidrangestd":    {7: 7.6, 8: 28.4, 9: 25.4, 10: 14.2, 11: 8.6, 12: 6.6, 13: 3.4}, # alias
}

APL_REGISTRY = {}

def _try_register_apls():
    try:
        from apl import APL_REGISTRY as REG
        APL_REGISTRY.update(REG)
    except ImportError:
        pass

_try_register_apls()

def _infer_archetype_key(deck_name: str, explicit: str = "") -> str:
    s       = (explicit or deck_name).lower()
    s_clean = s.replace(" ", "").replace("-", "").replace("'", "")

    # Exact explicit match
    if explicit.lower().strip() in ARCHETYPE_CLOCKS:
        return explicit.lower().strip()

    # Try full name match — both spaced and cleaned versions (longest key wins)
    for key in sorted(ARCHETYPE_CLOCKS, key=len, reverse=True):
        key_clean = key.replace(" ", "").replace("-", "").replace("'", "")
        if key in s or key_clean in s_clean:
            return key

    # Strip format prefixes and retry
    for prefix in ["legacy ", "modern ", "pioneer ", "standard "]:
        s = s.replace(prefix, "")
    s_clean = s.replace(" ", "").replace("-", "").replace("'", "")
    for key in sorted(ARCHETYPE_CLOCKS, key=len, reverse=True):
        key_clean = key.replace(" ", "").replace("-", "").replace("'", "")
        if key in s or key_clean in s_clean:
            return key

    # Fuzzy fallbacks
    if any(k in s for k in ["burn","goblin","zoo","hammer","scales"]): return "aggro"
    if any(k in s for k in ["control","azorius","jeskai","esper"]):    return "control"
    if any(k in s for k in ["mid","rakdos","golgari","jund"]):         return "midrange"
    if any(k in s for k in ["tempo","murktide","blink"]):              return "tempo"
    if any(k in s for k in ["tron","titan","amulet"]):                 return "ramp"
    if any(k in s for k in ["combo","storm","creativity"]):            return "combo"
    return "unknown"

def avg_kill_turn(dist: dict) -> float:
    total = sum(dist.values())
    if not total: return 99.0
    return sum(t * (p / total) for t, p in dist.items())

def _try_load_deck(deck_name: str) -> list:
    """Try to load a deck from the decks/ folder by name matching."""
    import glob, os
    deck_dir = os.path.join(os.path.dirname(__file__), "decks")
    name_clean = deck_name.lower().replace(" ", "_").replace("-", "_")

    for f in glob.glob(os.path.join(deck_dir, "*.txt")):
        fname = os.path.basename(f).lower().replace("-", "_").replace(" ", "_")
        # Match if deck name words appear in filename
        words = [w for w in name_clean.split("_") if len(w) > 2]
        if any(w in fname for w in words):
            try:
                from data.deck import load_deck_from_file
                main, _ = load_deck_from_file(f)
                if len(main) >= 40:
                    return main
            except Exception:
                pass
    return []


def get_kill_distribution(deck_name, archetype="", mainboard=None, n_sim=5000):
    arch_key = _infer_archetype_key(deck_name, archetype)

    # Auto-load deck from decks/ folder if not provided
    if not mainboard:
        mainboard = _try_load_deck(deck_name)

    # 1. Hand-tuned APL
    if mainboard and arch_key in APL_REGISTRY:
        try:
            from engine.runner import run_simulation
            results = run_simulation(APL_REGISTRY[arch_key](), mainboard, n=n_sim, on_play=True)
            dist = results.kill_turn_distribution()
            if dist:
                print(f"  [{deck_name}] APL sim (avg T{avg_kill_turn(dist):.1f})")
                return dist
        except Exception as e:
            print(f"  [{deck_name}] APL sim failed ({e})")

    # 2. Playbook + GenericAPL
    if mainboard:
        try:
            from apl.playbook_parser import load_all_playbooks, find_playbook
            from apl.generic_apl import generic_from_playbook
            from engine.runner import run_simulation
            pbs = load_all_playbooks()
            pb  = find_playbook(deck_name, pbs)
            if pb and pb.mainboard:
                from data.deck import load_deck_from_text
                dl  = "\n".join(f"{q} {n}" for n, q in pb.mainboard.items())
                main2, _ = load_deck_from_text(dl)
                if len(main2) >= 40:
                    apl = generic_from_playbook(pb)
                    results = run_simulation(apl, main2, n=n_sim, on_play=True)
                    dist = results.kill_turn_distribution()
                    if dist:
                        print(f"  [{deck_name}] Playbook GenericAPL: {pb.deck_name} "
                              f"(avg T{avg_kill_turn(dist):.1f})")
                        return dist
        except Exception as e:
            print(f"  [{deck_name}] Playbook APL failed ({e})")

    # 3. Clock fallback
    dist = ARCHETYPE_CLOCKS.get(arch_key, ARCHETYPE_CLOCKS["unknown"])
    print(f"  [{deck_name}] Clock fallback: '{arch_key}' (avg T{avg_kill_turn(dist):.1f})")
    return dist

def race_win_pct(dist_a, dist_b, n=50_000):
    def make_cdf(d):
        cdf, running = [], 0.0
        for t in sorted(d):
            running += d[t]
            cdf.append((t, running))
        return cdf
    def sample(cdf):
        r = random.random() * 100
        for t, cum in cdf:
            if r <= cum: return t
        return 99
    cdf_a, cdf_b = make_cdf(dist_a), make_cdf(dist_b)
    wins = sum(1 for _ in range(n) if sample(cdf_a) <= sample(cdf_b))
    return round(wins / n * 100, 1)

def get_real_win_pct(arch_a: str, arch_b: str, format_name: str,
                     min_matches: int = 10) -> float | None:
    """
    Look up a real matchup win% from the meta-analyzer DB.
    Returns None if insufficient data.
    """
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=format_name, min_matches=min_matches)
        matrix = bridge.real_matchup_matrix()
        # Try exact match first, then normalized
        key = (arch_a, arch_b)
        if key in matrix:
            return matrix[key]
        # Try case-insensitive fuzzy search
        for (a, b), wp in matrix.items():
            if arch_a.lower() in a.lower() and arch_b.lower() in b.lower():
                return wp
    except Exception:
        pass
    return None

def dist_to_tilt(win_pct): return round(win_pct - 50.0, 1)

def read_gauntlet_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_tilt_csv(path, tilt_matrix, deck_ids, id_to_name):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Deck_A_ID","Deck_A_Name","Deck_B_ID","Deck_B_Name","G1_WinPct_A","Tilt","Avg_Kill_A","Avg_Kill_B"])
        for a in deck_ids:
            for b in deck_ids:
                if a == b: continue
                wp = tilt_matrix.get((a, b), 50.0)
                w.writerow([a, id_to_name.get(a,a), b, id_to_name.get(b,b),
                            wp, dist_to_tilt(wp),
                            round(tilt_matrix.get(f"avg_{a}", 6.0), 2),
                            round(tilt_matrix.get(f"avg_{b}", 6.0), 2)])
    print(f"\n  Tilt CSV written: {path}")

def print_matrix(tilt_matrix, deck_ids, id_to_name):
    print(f"\n  {'':22}", end="")
    for b in deck_ids: print(f"  {b:>7}", end="")
    print("  AvgKill")
    print(f"  {'-'*80}")
    for a in deck_ids:
        avg = tilt_matrix.get(f"avg_{a}", 6.0)
        print(f"  {id_to_name.get(a,a)[:20]:22}", end="")
        for b in deck_ids:
            if a == b: print(f"  {'--':>7}", end="")
            else: print(f"  {tilt_matrix.get((a,b),50.0):>6.1f}%", end="")
        print(f"  T{avg:.1f}")

def patch_pipeline(pipeline_path, arch_tilts):
    backup = pipeline_path + ".sim_bridge.bak"
    shutil.copy2(pipeline_path, backup)
    print(f"  Backup: {backup}")
    with open(pipeline_path, encoding="utf-8") as f:
        content = f.read()
    lines = ["ARC_TILT = {",
             "    # Auto-generated by sim_bridge.py — do not edit manually"]
    for (a, b), tilt in sorted(arch_tilts.items()):
        lines.append(f"    ({a!r},{b!r}):{tilt:+.1f},")
    lines.append("}")
    new_block = "\n".join(lines)
    pattern = r"ARC_TILT\s*=\s*\{[^}]+\}"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_block, content, flags=re.DOTALL)
        with open(pipeline_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Patched ARC_TILT in: {pipeline_path}")
    else:
        print(f"  WARNING: Could not find ARC_TILT block — manual patch needed")

def main():
    ap = argparse.ArgumentParser(description="Bridge mtg-sim kill distributions into gauntlet tilts")
    ap.add_argument("--sheet",        default="", help="Gauntlet input CSV")
    ap.add_argument("--field",        default="", help="Comma-separated deck names")
    ap.add_argument("--auto-field",   action="store_true",
                    help="Auto-populate field from meta-analyzer DB standings")
    ap.add_argument("--format",       default="legacy",
                    help="Format for real matchup data + auto-field (default: legacy)")
    ap.add_argument("--top-n",        type=int, default=10,
                    help="Number of archetypes for --auto-field (default: 10)")
    ap.add_argument("--out",          default="reports/sim_tilt_overrides.csv")
    ap.add_argument("--patch",        action="store_true")
    ap.add_argument("--pipeline",     default="")
    ap.add_argument("--n-sim",        type=int, default=5000)
    ap.add_argument("--n-race",       type=int, default=50000)
    ap.add_argument("--list-archetypes", action="store_true")
    ap.add_argument("--show-field",   action="store_true",
                    help="Show real meta field composition from DB and exit")
    args = ap.parse_args()

    if args.list_archetypes:
        print("\nAvailable archetype clocks:")
        for k, dist in ARCHETYPE_CLOCKS.items():
            apl = "  [APL]" if k in APL_REGISTRY else ""
            print(f"  {k:<22} avg T{avg_kill_turn(dist):.1f}{apl}")
        return

    if args.show_field:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=args.format, min_matches=10)
        rows = bridge.field_summary(top_n=args.top_n)
        print(f"\nReal {args.format.upper()} field (top {args.top_n}):")
        print(f"  {'#':>3}  {'Archetype':<35} {'Share':>6}  {'Matches':>8}")
        print(f"  {'-'*60}")
        for r in rows:
            print(f"  {r['rank']:>3}. {r['archetype']:<35} {r['share']:>5.1f}%  {r['matches']:>8,}")
        cov = bridge.matchup_coverage()
        print(f"\n  Matchup coverage: {cov['pairs_with_data']} pairs "
              f"across {cov['archetypes']} archetypes "
              f"({cov['coverage_pct']}% of possible)")
        return

    if args.auto_field:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=args.format, min_matches=10)
        rows = bridge.field_summary(top_n=args.top_n)
        if not rows:
            print(f"  No field data for {args.format} — check DB")
            return
        print(f"\nAuto-field from {args.format.upper()} meta ({len(rows)} archetypes):")
        decks = []
        for i, r in enumerate(rows):
            deck_id = chr(65 + i)
            print(f"  {deck_id}. {r['archetype']:<35} {r['share']:.1f}%")
            decks.append({
                "Deck_ID (A-L)":        deck_id,
                "Deck_Name":            r["archetype"],
                "Archetype (optional)": _infer_archetype_key(r["archetype"]),
            })
    elif args.field and not args.sheet:
        names = [d.strip() for d in args.field.split(",")]
        decks = [{"Deck_ID (A-L)": chr(65+i), "Deck_Name": n, "Archetype (optional)": ""}
                 for i, n in enumerate(names)]
    elif args.sheet:
        decks = read_gauntlet_csv(args.sheet)
    else:
        ap.print_help(); return

    # Propagate format_name for real matchup lookup
    format_name = args.format

    id_col, name_col, arch_col = "Deck_ID (A-L)", "Deck_Name", "Archetype (optional)"
    deck_ids   = [d[id_col]   for d in decks]
    id_to_name = {d[id_col]: d[name_col] for d in decks}

    print(f"\nGetting kill distributions for {len(decks)} decks...")
    distributions = {}
    for d in decks:
        distributions[d[id_col]] = get_kill_distribution(
            d[name_col], d.get(arch_col, ""), n_sim=args.n_sim)

    n_pairs = len(deck_ids) * (len(deck_ids) - 1)
    print(f"\nComputing {n_pairs} race matchups ({args.n_race:,} samples each)...")
    tilt_matrix = {}

    # Try to load real matchup data from meta-analyzer DB
    format_name = "legacy"  # default; override via --format arg
    real_matrix: dict = {}
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=format_name, min_matches=10)
        real_matrix = bridge.real_matchup_matrix()
        cov = bridge.matchup_coverage()
        if real_matrix:
            print(f"  [MetaBridge] Loaded {len(real_matrix)} real matchup pairs "
                  f"({cov['coverage_pct']}% coverage, "
                  f"{cov['archetypes']} archetypes)")
    except Exception as e:
        print(f"  [MetaBridge] Not available ({e}) — using goldfish races only")

    for a_id in deck_ids:
        tilt_matrix[f"avg_{a_id}"] = avg_kill_turn(distributions[a_id])
        a_name = id_to_name.get(a_id, a_id)
        a_arch = _infer_archetype_key(a_name)
        for b_id in deck_ids:
            if a_id == b_id:
                continue
            b_name = id_to_name.get(b_id, b_id)
            b_arch = _infer_archetype_key(b_name)

            # 1. Try real match data first
            real_wp = get_real_win_pct(a_arch, b_arch, format_name)
            if real_wp is not None:
                tilt_matrix[(a_id, b_id)] = real_wp
                continue

            # 2. Fallback: goldfish race simulation
            tilt_matrix[(a_id, b_id)] = race_win_pct(
                distributions[a_id], distributions[b_id], args.n_race)

    print_matrix(tilt_matrix, deck_ids, id_to_name)
    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else ".", exist_ok=True)
    write_tilt_csv(args.out, tilt_matrix, deck_ids, id_to_name)

    if args.patch:
        pipeline = args.pipeline or os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "Team Resolve", "gauntlet",
            "Gauntlet_AutoRunner_20251003_085226", "run_pipeline_v3.py"))
        arch_tilts = {}
        for a in decks:
            for b in decks:
                if a[id_col] == b[id_col]: continue
                ak = _infer_archetype_key(a[name_col], a.get(arch_col,""))
                bk = _infer_archetype_key(b[name_col], b.get(arch_col,""))
                key = (ak, bk)
                arch_tilts.setdefault(key, []).append(
                    dist_to_tilt(tilt_matrix.get((a[id_col],b[id_col]),50.0)))
        arch_tilts = {k: round(statistics.mean(v),1) for k,v in arch_tilts.items()}
        patch_pipeline(pipeline, arch_tilts)

    print("\nDone.")

if __name__ == "__main__":
    main()
