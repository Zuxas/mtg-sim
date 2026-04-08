"""
engine/rules_engine.py — MTG Comprehensive Rules parser + auto-trigger generator

Three capabilities:
  1. RulesIndex  — parses comp_rules.txt into a searchable dict of rule sections
  2. lookup()    — find rules relevant to a keyword or phrase
  3. auto_trigger() — given card oracle text, use Claude API to generate
                      Python trigger code for the sim engine

Usage:
    from engine.rules_engine import RulesIndex, auto_trigger

    idx = RulesIndex()
    idx.lookup("flying")          # returns relevant rule sections
    idx.lookup("token")
    idx.section("508")            # exact section lookup

    code = auto_trigger(card_name, oracle_text, idx)
    # Returns Python code snippet ready to drop into game_state.py
"""

import os
import re
import json
from pathlib import Path

RULES_PATH = Path(__file__).parent.parent / "data" / "comp_rules.txt"


# ---------------------------------------------------------------------------
# Rule index — parses the comp rules into {rule_number: text} dict
# ---------------------------------------------------------------------------

class RulesIndex:
    """
    Parsed MTG Comprehensive Rules, indexed by rule number.

    rules["702.9"]  → full text of Flying rule
    rules["508"]    → full text of Declare Attackers Step
    glossary["flying"] → glossary definition
    """

    def __init__(self, path: str = None):
        self.path     = path or str(RULES_PATH)
        self.rules    = {}   # {rule_num: text}
        self.glossary = {}   # {term: definition}
        self.sections = {}   # {section_num: title}
        self._raw_lines = []
        self._parse()

    def _parse(self):
        try:
            raw = open(self.path, encoding="utf-8", errors="replace").read()
        except FileNotFoundError:
            print(f"[RulesIndex] Rules file not found: {self.path}")
            return

        lines = raw.splitlines()
        self._raw_lines = lines

        rule_re    = re.compile(r"^(\d+\.\d+[a-z]?)\.?\s+(.*)")
        section_re = re.compile(r"^(\d+)\.\s+([A-Za-z].+)")

        buf_key  = None
        buf_text = []
        in_gloss = False

        for line in lines:
            s = line.strip()
            if not s:
                continue

            # Switch to glossary mode — only after actual rules have been parsed
            # (the word "Glossary" also appears in the Contents section at the top)
            if s == "Glossary" and len(self.rules) > 100:
                if buf_key and buf_text:
                    self.rules[buf_key] = " ".join(buf_text).strip()
                buf_key, buf_text = None, []
                in_gloss = True
                continue

            if in_gloss:
                # Glossary: un-numbered term starts each entry
                if not s[0].isdigit():
                    if buf_key and buf_text:
                        self.glossary[buf_key.lower()] = " ".join(buf_text).strip()
                    buf_key  = s
                    buf_text = []
                else:
                    buf_text.append(s)
                continue

            # Try rule match FIRST (e.g. "702.9. Flying" or "702.9a A creature...")
            m = rule_re.match(s)
            if m:
                if buf_key and buf_text:
                    self.rules[buf_key] = " ".join(buf_text).strip()
                buf_key  = m.group(1)
                buf_text = [m.group(2)] if m.group(2) else []
                continue

            # Section header (e.g. "702. Keyword Abilities")
            m2 = section_re.match(s)
            if m2:
                self.sections[m2.group(1)] = m2.group(2)
                continue

            # Continuation
            if buf_key:
                buf_text.append(s)

        # Flush final entry
        if buf_key and buf_text:
            if in_gloss:
                self.glossary[buf_key.lower()] = " ".join(buf_text).strip()
            else:
                self.rules[buf_key] = " ".join(buf_text).strip()

    def section(self, num: str) -> dict:
        """Return all rules starting with num (e.g. '508' returns 508, 508.1, 508.1a ...)"""
        return {k: v for k, v in self.rules.items() if k.startswith(num)}

    def lookup(self, query: str, max_results: int = 10) -> dict:
        """
        Find rules containing the query string (case-insensitive).
        Returns {rule_num: text} dict, most specific matches first.
        """
        q = query.lower()
        exact, partial = {}, {}

        for num, text in self.rules.items():
            tl = text.lower()
            if q in tl[:50]:   # query near start of rule = more specific
                exact[num] = text
            elif q in tl:
                partial[num] = text

        combined = {**exact, **partial}
        # Sort: glossary match → shorter rule numbers → alphabetical
        sorted_keys = sorted(combined, key=lambda k: (len(k), k))
        return {k: combined[k] for k in sorted_keys[:max_results]}

    def keyword_rules(self, keyword: str) -> dict:
        """Look up a specific keyword ability (Flying, Haste, Vigilance, etc.)"""
        kw = keyword.lower()
        # Keyword abilities are in section 702
        candidates = {k: v for k, v in self.rules.items()
                      if k.startswith("702") and kw in v.lower()[:30]}
        # Also check glossary
        gloss = {k: v for k, v in self.glossary.items() if kw in k}
        return {**candidates, **gloss}

    def triggered_ability_rules(self) -> dict:
        """Return rules about triggered abilities (section 603)"""
        return self.section("603")

    def etb_rules(self) -> dict:
        """Rules about enters the battlefield effects (relevant subset of 603)"""
        return {k: v for k, v in self.rules.items()
                if "enters the battlefield" in v.lower() or k.startswith("603")}

    def combat_rules(self) -> dict:
        """Return all combat rules (sections 506-511)"""
        result = {}
        for sec in ("506", "507", "508", "509", "510", "511"):
            result.update(self.section(sec))
        return result

    def token_rules(self) -> dict:
        """Rules about tokens (section 111)"""
        return self.section("111")

    def energy_rules(self) -> dict:
        """Rules about energy counters"""
        return self.lookup("energy counter")

    def summary(self) -> str:
        return (f"RulesIndex: {len(self.rules)} rules, "
                f"{len(self.glossary)} glossary entries, "
                f"{len(self.sections)} sections")


# ---------------------------------------------------------------------------
# Auto-trigger generator — Claude API + oracle text + rules
# ---------------------------------------------------------------------------

def auto_trigger(
    card_name: str,
    oracle_text: str = None,     # optional — auto-fetched from CardDB if not provided
    rules_index: RulesIndex = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1500,
) -> str:
    """
    Given a card name, use Claude API to generate Python trigger code.

    Oracle text is auto-fetched from the local CardDB (no network calls).
    Official judge rulings are also included for accuracy.
    """
    import urllib.request

    # Auto-fetch oracle text and rulings from local DB
    rulings_text = ""
    try:
        from engine.card_db import CardDB
        db = CardDB()
        if not oracle_text:
            oracle_text = db.oracle_text(card_name)
        rulings = db.rulings(card_name)
        if rulings:
            rulings_text = "\n\nOFFICIAL JUDGE RULINGS:\n"
            for r in rulings[:5]:
                rulings_text += f"- {r[:200]}\n"
    except Exception:
        pass

    if not oracle_text:
        return f"# Could not find oracle text for {card_name}"

    if rules_index is None:
        rules_index = RulesIndex()

    # Extract relevant rules for context
    relevant_rules = {}

    # Parse oracle text for keywords and trigger patterns
    oracle_lower = oracle_text.lower()

    # Keyword abilities
    for kw in ("flying", "haste", "vigilance", "trample", "first strike",
               "double strike", "lifelink", "deathtouch", "indestructible",
               "reach", "menace", "ward", "flash"):
        if kw in oracle_lower:
            relevant_rules.update(rules_index.keyword_rules(kw))

    # Triggered ability types
    if "enters" in oracle_lower or "etb" in oracle_lower:
        relevant_rules.update(rules_index.etb_rules())
    if "attack" in oracle_lower:
        relevant_rules.update(rules_index.section("508"))
    if "token" in oracle_lower:
        relevant_rules.update(rules_index.token_rules())
    if "energy" in oracle_lower or "{e}" in oracle_lower:
        relevant_rules.update(rules_index.energy_rules())
    if "counter" in oracle_lower and "+1/+1" in oracle_lower:
        relevant_rules.update(rules_index.lookup("+1/+1 counter"))

    # Trim rules to avoid bloating the prompt
    rules_text = ""
    for num, text in list(relevant_rules.items())[:20]:
        rules_text += f"{num}. {text}\n"

    prompt = f"""You are generating Python code for an MTG simulator engine.

CARD: {card_name}
ORACLE TEXT:
{oracle_text}
{rulings_text}
RELEVANT RULES:
{rules_text or "(use general MTG rules knowledge)"}

SIMULATOR API:
- gs.zones.battlefield, gs.zones.hand, gs.zones.graveyard
- gs.zones.draw(n), gs.damage_dealt, gs.energy, gs.life
- gs._make_token(name, power, toughness, type_line) → Card
- gs._fire_etb_triggers(card), gs._log(msg)
- card.counters, card.effective_power(), card.effective_toughness()
- card.name, card.type_line, card.tags, card.summoning_sickness
- Tag.CREATURE, KWTag.FLYING, KWTag.HASTE, KWTag.INDESTRUCTIBLE

Goldfish sim — no opponent interaction, no blocking.
Return ONLY Python code, no markdown."""

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except Exception as e:
        return f"# Error calling Claude API: {e}\n# Implement manually."


def download_rules(out_path: str = None):
    """Download the latest Comprehensive Rules TXT from Wizards."""
    import urllib.request
    url = "https://media.wizards.com/2026/downloads/MagicCompRules%2020260227.txt"
    out = out_path or str(RULES_PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"Downloading Comprehensive Rules → {out}")
    urllib.request.urlretrieve(url, out)
    size = os.path.getsize(out)
    print(f"Done: {size/1024:.0f} KB")


# ---------------------------------------------------------------------------
# CLI — quick lookup tool
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    idx = RulesIndex()
    print(idx.summary())
    print()

    if len(sys.argv) < 2:
        print("Usage: python -m engine.rules_engine <query>")
        print("       python -m engine.rules_engine flying")
        print("       python -m engine.rules_engine 508")
        print("       python -m engine.rules_engine 'enters the battlefield'")
        sys.exit(0)

    query = " ".join(sys.argv[1:])

    # If it looks like a rule number, do section lookup
    if re.match(r"^\d+", query):
        results = idx.section(query)
        label = f"Section {query}"
    else:
        results = idx.lookup(query, max_results=15)
        label = f'"{query}"'

    print(f"Results for {label}: {len(results)} rules\n")
    for num, text in list(results.items())[:15]:
        print(f"  {num}. {text[:120]}")
