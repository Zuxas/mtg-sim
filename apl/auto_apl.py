"""
apl/auto_apl.py — Generate deck-specific APLs using Claude API + playbook data

Workflow:
  1. Load PlaybookData for the target deck
  2. Pull relevant rules from RulesIndex for key card mechanics
  3. Send oracle text + playbook strategy to Claude API
  4. Get back a Python APL class
  5. Cache to disk — never regenerate unless forced

Usage:
    from apl.auto_apl import AutoAPLFactory
    factory = AutoAPLFactory()
    apl = factory.get_apl("Boros Energy")      # loads from cache or generates
    apl = factory.get_apl("Boros Energy", force_rebuild=True)  # regenerate
"""

import json
import urllib.request
import re
import importlib.util
import sys
import traceback
from pathlib import Path
from typing import Optional

from apl.base_apl import BaseAPL

APL_CACHE_DIR = Path(__file__).parent.parent / "data" / "auto_apls"


SYSTEM_PROMPT = """You are an expert Magic: The Gathering simulator engineer.

Your job is to generate Python APL (Action Priority List) classes for the mtg-sim engine.
The sim is a goldfish simulator — no opponent interaction, no blocking.
Focus only on effects that advance the clock: damage, tokens, pumping creatures, card draw.

SIMULATOR API:
- GameState (gs):
  gs.hand()                    → list[Card] in hand
  gs.battlefield()             → list[Card] on battlefield
  gs.zones.draw(n)             → draw n cards
  gs.zones.lands_on_battlefield()  → list[Card] (lands)
  gs.zones.creatures_on_battlefield() → list[Card]
  gs.mana_pool.can_cast(mana_cost, cmc) → bool
  gs.mana_pool.total()         → int (floating mana)
  gs.cast_spell(card)          → bool
  gs.play_land(card)           → bool
  gs.tap_lands()               → taps all lands for mana
  gs.damage_dealt              → int (cumulative damage to opponent)
  gs.energy                    → int (energy counters)
  gs.life                      → int (our life total)
  gs._make_token(name, power, toughness, type_line) → Card
  gs._log(msg)                 → log a message

- Card:
  card.name                    → str
  card.cmc                     → float
  card.mana_cost               → str (e.g. "{1}{W}")
  card.type_line               → str
  card.oracle_text             → str
  card.power / card.toughness  → str
  card.counters                → int (+1/+1 counters)
  card.effective_power()       → int
  card.is_land()               → bool
  card.has(Tag.CREATURE)       → bool
  card.tags                    → set (KWTag.FLYING, HASTE, etc.)
  card.summoning_sickness      → bool

- Tag enum: Tag.CREATURE, Tag.INSTANT, Tag.SORCERY, Tag.ARTIFACT, Tag.ENCHANTMENT, Tag.LAND
- KWTag enum: KWTag.FLYING, KWTag.HASTE, KWTag.VIGILANCE, KWTag.LIFELINK

CONSTANTS TO USE:
Define string constants at the top of the class for all key card names.
Example: CHAMPION = "Champion of the Parish"

OUTPUT FORMAT:
Return ONLY valid Python code. No markdown, no explanation, no backticks.
Start with the imports, then the class definition.
The class MUST:
  1. Extend BaseAPL
  2. Set class attribute: name = "DeckName"
  3. Implement keep(hand, mulligans, on_play) → bool
  4. Implement bottom(hand, n) → list[Card]  
  5. Implement main_phase(gs) — make all decisions for the turn
  6. Optionally implement main_phase2(gs) for post-combat plays

The generated APL will be loaded dynamically and run 5000 times.
Make it efficient — no expensive operations inside the hot loop.
"""


def _build_prompt(pb, rules_idx=None) -> str:
    """Build the Claude API prompt for a given PlaybookData."""
    # Card list
    mainboard_txt = "\n".join(f"{qty}x {name}"
                              for name, qty in sorted(pb.mainboard.items(),
                                                       key=lambda x: -x[1]))
    sideboard_txt = "\n".join(f"{qty}x {name}"
                              for name, qty in sorted(pb.sideboard.items(),
                                                       key=lambda x: -x[1]))

    # Key card rules from rules engine
    rules_section = ""
    if rules_idx and pb.mainboard:
        from engine.rules_engine import RulesIndex
        relevant = {}
        # Get oracle text for key cards
        top_cards = [name for name, qty in sorted(pb.mainboard.items(),
                                                    key=lambda x: -x[1])[:12]]
        for card_name in top_cards:
            card_name_lower = card_name.lower()
            for kw in ("flying", "haste", "enters", "attack", "token", "energy",
                       "counter", "+1/+1", "mobilize", "vigilance", "first strike"):
                if kw in card_name_lower:
                    relevant.update(rules_idx.lookup(kw, max_results=3))
        if relevant:
            rules_section = "\nRELEVANT RULES:\n"
            for num, text in list(relevant.items())[:10]:
                rules_section += f"  {num}. {text[:100]}\n"

    # Engines (key card descriptions)
    engines_txt = ""
    if pb.engines:
        engines_txt = "\nKEY ENGINES:\n"
        for eng in pb.engines[:5]:
            engines_txt += f"  [{eng['title']}] {eng['body'][:200]}\n"

    prompt = f"""Generate a Python APL class for this MTG deck:

DECK: {pb.deck_name}
FORMAT: {pb.format_name}
ROLE: {pb.role}
KILL TURN: {pb.kill_turn}
AVG KILL TURN: {pb.avg_kill_turn():.1f}

MAINBOARD:
{mainboard_txt}

SIDEBOARD:
{sideboard_txt}

GAME PLAN: {pb.game_plan[:400] if pb.game_plan else 'Unknown'}

STRENGTHS: {pb.strengths[:200] if pb.strengths else 'Unknown'}
WEAKNESSES: {pb.weaknesses[:200] if pb.weaknesses else 'Unknown'}
MULLIGAN: {pb.mulligan[:300] if pb.mulligan else 'Unknown'}
{engines_txt}{rules_section}

Generate the APL class now. Class name: {_safe_class_name(pb.deck_name)}APL
"""
    return prompt


def _safe_class_name(name: str) -> str:
    """'Boros Energy' → 'BorosEnergy'"""
    return re.sub(r"[^A-Za-z0-9]", "", name.title().replace(" ", ""))


def _get_api_token() -> str:
    """
    Get Anthropic API token from Claude Code credentials (persisted).
    Falls back to ANTHROPIC_API_KEY env var or .env file.
    Never requires manual setup.
    """
    import os, json, time
    from pathlib import Path

    # 1. Environment variable
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key

    # 2. Claude Code OAuth credentials (~/.claude/.credentials.json)
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = json.loads(creds_path.read_text(encoding="utf-8"))
            oauth = creds.get("claudeAiOauth", {})
            token     = oauth.get("accessToken", "")
            expires   = oauth.get("expiresAt", 0)
            refresh   = oauth.get("refreshToken", "")

            # Token still valid (with 5-min buffer)
            if token and expires > (time.time() * 1000 + 300_000):
                return token

            # Token expired — refresh it
            if refresh:
                refreshed = _refresh_oauth_token(refresh)
                if refreshed:
                    # Persist refreshed token
                    oauth["accessToken"]  = refreshed["access_token"]
                    oauth["expiresAt"]    = int(time.time() * 1000) + refreshed.get("expires_in", 3600) * 1000
                    if "refresh_token" in refreshed:
                        oauth["refreshToken"] = refreshed["refresh_token"]
                    creds["claudeAiOauth"] = oauth
                    creds_path.write_text(json.dumps(creds), encoding="utf-8")
                    return refreshed["access_token"]
        except Exception as e:
            print(f"[AutoAPL] Claude Code creds error: {e}")

    # 3. .env file in project root
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")

    raise RuntimeError(
        "No Anthropic API token found.\n"
        "Options:\n"
        "  1. Set ANTHROPIC_API_KEY env var\n"
        "  2. Create .env with ANTHROPIC_API_KEY=sk-ant-...\n"
        "  3. Make sure Claude Code is installed and logged in"
    )


def _refresh_oauth_token(refresh_token: str) -> dict:
    """Refresh an expired Claude Code OAuth token."""
    import urllib.request, json
    try:
        payload = json.dumps({
            "grant_type":    "refresh_token",
            "refresh_token": refresh_token,
        }).encode()
        req = urllib.request.Request(
            "https://claude.ai/api/oauth/token",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[AutoAPL] Token refresh failed: {e}")
        return {}


def _call_claude(prompt: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Call Claude API using persisted Claude Code credentials."""
    token = _get_api_token()

    # OAuth tokens use Bearer auth; API keys use x-api-key
    if token.startswith("sk-ant-oat") or token.startswith("Bearer "):
        auth_headers = {"Authorization": f"Bearer {token.lstrip('Bearer ')}"}
    else:
        auth_headers = {"x-api-key": token}

    payload = json.dumps({
        "model":      model,
        "max_tokens": 2000,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "anthropic-version": "2023-06-01",
            **auth_headers,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
        return data["content"][0]["text"]


def _clean_code(raw: str) -> str:
    """Strip markdown fences if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        start = 1 if lines[0].startswith("```") else 0
        end   = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        raw   = "\n".join(lines[start:end])
    return raw.strip()


# ---------------------------------------------------------------------------
# AutoAPLFactory — load from cache or generate via Claude API
# ---------------------------------------------------------------------------

class AutoAPLFactory:
    """
    Generates and caches deck-specific APL classes.

    Usage:
        factory = AutoAPLFactory()
        apl_instance = factory.get_apl("Boros Energy")
        results = run_simulation(apl_instance, mainboard, n=5000)
    """

    def __init__(self, cache_dir: str = None, rules_index=None):
        self.cache_dir   = Path(cache_dir) if cache_dir else APL_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rules_index = rules_index
        self._playbooks  = None
        self._loaded     = {}

    def _get_playbooks(self):
        if self._playbooks is None:
            from apl.playbook_parser import load_all_playbooks, load_all_tac_guides
            self._playbooks = {
                **load_all_playbooks(),
                **load_all_tac_guides(),
            }
        return self._playbooks

    def _cache_path(self, deck_name: str) -> Path:
        safe = re.sub(r"[^a-z0-9_]", "_", deck_name.lower())
        return self.cache_dir / f"{safe}.py"

    def get_apl(
        self,
        deck_name:     str,
        force_rebuild: bool = False,
    ) -> BaseAPL:
        """
        Get an APL instance for the given deck name.
        Loads from cache if available, otherwise generates via Claude API.
        Falls back to GenericAPL if generation fails.
        """
        from apl.generic_apl import GenericAPL

        # Check in-memory cache
        if deck_name in self._loaded and not force_rebuild:
            return self._loaded[deck_name]

        # Check disk cache
        cache_file = self._cache_path(deck_name)
        if cache_file.exists() and not force_rebuild:
            apl = self._load_from_file(cache_file, deck_name)
            if apl:
                self._loaded[deck_name] = apl
                return apl

        # Find playbook
        pbs = self._get_playbooks()
        from apl.playbook_parser import find_playbook
        pb = find_playbook(deck_name, pbs)

        if not pb:
            print(f"[AutoAPL] No playbook for '{deck_name}' — using GenericAPL")
            return GenericAPL(deck_name=deck_name)

        # Generate via Claude API
        print(f"[AutoAPL] Generating APL for {pb.deck_name}…")
        try:
            prompt    = _build_prompt(pb, self.rules_index)
            raw_code  = _call_claude(prompt)
            clean     = _clean_code(raw_code)

            # Save to cache
            header = (f"# Auto-generated APL for {pb.deck_name}\n"
                      f"# Format: {pb.format_name}  |  Kill Turn: {pb.kill_turn}\n"
                      f"# Generated by AutoAPLFactory\n\n")
            cache_file.write_text(header + clean, encoding="utf-8")
            print(f"[AutoAPL] Saved → {cache_file}")

            # Load and return
            apl = self._load_from_file(cache_file, deck_name)
            if apl:
                self._loaded[deck_name] = apl
                return apl

        except Exception as e:
            print(f"[AutoAPL] Generation failed: {e}")
            traceback.print_exc()

        # Fallback
        print(f"[AutoAPL] Falling back to GenericAPL for {deck_name}")
        pb_role = pb.role if pb else "unknown"
        return GenericAPL(deck_name=deck_name, role=pb_role)

    def _load_from_file(self, path: Path, deck_name: str) -> Optional["BaseAPL"]:
        """Dynamically load a Python APL file and return an instance."""
        try:
            spec   = importlib.util.spec_from_file_location(
                f"auto_apl_{deck_name}", str(path))
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Find BaseAPL subclass in module
            from apl.base_apl import BaseAPL
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, BaseAPL)
                        and attr is not BaseAPL):
                    instance = attr()
                    print(f"[AutoAPL] Loaded {attr.__name__} from cache")
                    return instance

            print(f"[AutoAPL] No BaseAPL subclass found in {path.name}")
        except Exception as e:
            print(f"[AutoAPL] Failed to load {path.name}: {e}")
        return None

    def list_cached(self) -> list[str]:
        return [f.stem for f in self.cache_dir.glob("*.py")]

    def clear_cache(self, deck_name: str = None):
        if deck_name:
            p = self._cache_path(deck_name)
            if p.exists():
                p.unlink()
        else:
            for p in self.cache_dir.glob("*.py"):
                p.unlink()
        self._loaded.clear()


# ---------------------------------------------------------------------------
# Convenience: simulate any deck by name
# ---------------------------------------------------------------------------

def simulate_any_deck(
    deck_name:     str,
    mainboard:     list,
    n:             int = 5000,
    force_rebuild: bool = False,
) -> "SimulationResults":
    """One-liner: simulate any deck by name using playbook + AutoAPL."""
    from engine.runner import run_simulation

    factory = AutoAPLFactory()
    apl     = factory.get_apl(deck_name, force_rebuild=force_rebuild)
    return run_simulation(apl, mainboard, n=n, on_play=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from apl.playbook_parser import load_all_playbooks
    from data.deck import load_deck_from_file

    pbs = load_all_playbooks()
    print(f"Available playbooks: {len(pbs)}")

    if len(sys.argv) > 1:
        deck_name = " ".join(sys.argv[1:])
        factory   = AutoAPLFactory()
        apl       = factory.get_apl(deck_name, force_rebuild="--rebuild" in sys.argv)
        print(f"APL: {apl.name}")
        print(f"Type: {type(apl).__name__}")
