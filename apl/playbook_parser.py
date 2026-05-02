"""
apl/playbook_parser.py — Parse Team Resolve HTML playbooks into structured data

Extracts from the 46 playbooks in My-Website/:
  - Deck identity (name, format, role, kill turn)
  - Full 75 (mainboard + sideboard as {card: qty})
  - Engine descriptions (key card packages)
  - Mulligan criteria
  - Matchup table (opponent, sb_in, sb_out, notes)
  - Strengths / weaknesses

Output is a PlaybookData dataclass, also serializable to JSON for caching.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

PLAYBOOK_DIR = Path(__file__).parent.parent.parent / "My-Website"


@dataclass
class MatchupEntry:
    opponent:  str
    sb_in:     list[str] = field(default_factory=list)
    sb_out:    list[str] = field(default_factory=list)
    notes:     str = ""
    win_pct:   Optional[float] = None   # filled in from real DB data

@dataclass
class PlaybookData:
    # Identity
    deck_name:   str = ""
    format_name: str = ""
    role:        str = ""          # "Aggressive Midrange", "Combo-Control", etc.
    kill_turn:   str = ""          # e.g. "3-5"
    complexity:  str = ""
    colors:      str = ""

    # 75
    mainboard:   dict = field(default_factory=dict)   # {card_name: qty}
    sideboard:   dict = field(default_factory=dict)

    # Strategy
    game_plan:   str = ""
    strengths:   str = ""
    weaknesses:  str = ""
    mulligan:    str = ""
    engines:     list[dict] = field(default_factory=list)  # [{title, body}]

    # Matchups
    matchups:    list[MatchupEntry] = field(default_factory=list)

    # Source
    source_file: str = ""

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "PlaybookData":
        d = json.loads(s)
        d["matchups"] = [MatchupEntry(**m) for m in d.get("matchups", [])]
        return cls(**{k: v for k, v in d.items() if k != "matchups"},
                   matchups=d["matchups"])

    def kill_turn_range(self) -> tuple[float, float]:
        """Parse '3-5' → (3.0, 5.0). Returns (4.0, 6.0) as fallback."""
        m = re.search(r"(\d+)[^\d]+(\d+)", self.kill_turn or "")
        if m:
            return float(m.group(1)), float(m.group(2))
        m2 = re.search(r"(\d+)", self.kill_turn or "")
        if m2:
            v = float(m2.group(1))
            return v, v + 1
        return 4.0, 6.0

    def avg_kill_turn(self) -> float:
        lo, hi = self.kill_turn_range()
        return (lo + hi) / 2


# ---------------------------------------------------------------------------
# HTML Parser
# ---------------------------------------------------------------------------

def parse_playbook(html_path: str) -> PlaybookData:
    """Parse a single Team Resolve HTML playbook file."""
    if not BS4_AVAILABLE:
        raise ImportError("pip install beautifulsoup4")

    text = Path(html_path).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    pb   = PlaybookData(source_file=str(html_path))

    # ── Identity block ────────────────────────────────────────────────────
    title_el = soup.select_one(".header-title")
    if title_el:
        pb.deck_name = title_el.get_text(strip=True).replace("\n", " ").strip()

    label_el = soup.select_one(".header-label")
    if label_el:
        label_text = label_el.get_text(" ", strip=True)
        for fmt in ("Modern", "Pioneer", "Standard", "Legacy", "Pauper"):
            if fmt in label_text:
                pb.format_name = fmt
                break

    for stat in soup.select(".header-stat"):
        lbl = (stat.select_one(".hs-label") or stat).get_text(strip=True)
        val = (stat.select_one(".hs-val") or stat).get_text(strip=True)
        lbl_clean = lbl.replace(val, "").strip().lower()
        if "identity" in lbl_clean or "role" in lbl_clean:
            pb.role = val
        elif "kill" in lbl_clean:
            pb.kill_turn = val
        elif "complex" in lbl_clean:
            pb.complexity = val
        elif "color" in lbl_clean:
            pb.colors = val

    # Fallback: grab kill turn from any element mentioning it
    if not pb.kill_turn:
        for el in soup.find_all(string=re.compile(r"Kill Turn", re.I)):
            parent = el.parent
            if parent:
                sibling_text = parent.find_next_sibling()
                if sibling_text:
                    pb.kill_turn = sibling_text.get_text(strip=True)
                    break
        if not pb.kill_turn:
            m = re.search(r"Kill Turn[:\s]+([0-9]+[–\-][0-9]+|[0-9]+)", text, re.I)
            if m:
                pb.kill_turn = m.group(1)

    # ── Decklist ──────────────────────────────────────────────────────────
    in_side = False
    for row in soup.select(".dl-card-row"):
        txt = row.get_text(strip=True)
        m = re.match(r"(.+?)(\d+)$|^(\d+)\s+(.+)$", txt)
        if m:
            if m.group(1) and m.group(2):
                name, qty = m.group(1).strip(), int(m.group(2))
            else:
                qty, name = int(m.group(3)), m.group(4).strip()
        else:
            continue

        # Check parent section label
        section_el = row.find_parent(class_="dl-section")
        if section_el:
            label_el2 = section_el.select_one(".dl-section-label")
            if label_el2 and "side" in label_el2.get_text(strip=True).lower():
                in_side = True
            elif label_el2:
                in_side = False

        if in_side:
            pb.sideboard[name] = pb.sideboard.get(name, 0) + qty
        else:
            pb.mainboard[name] = pb.mainboard.get(name, 0) + qty

    # ── Engines ───────────────────────────────────────────────────────────
    for card_el in soup.select(".card"):
        title = card_el.select_one(".card-title")
        body  = card_el.select_one(".card-body")
        if title and body:
            pb.engines.append({
                "title": title.get_text(strip=True),
                "body":  body.get_text(" ", strip=True)[:400],
            })

    # ── Strengths / Weaknesses ────────────────────────────────────────────
    for card_el in soup.select(".card"):
        title_txt = (card_el.select_one(".card-title") or card_el).get_text(strip=True).lower()
        body_el   = card_el.select_one(".card-body")
        if not body_el:
            continue
        body_txt = body_el.get_text(" ", strip=True)[:500]
        if "strength" in title_txt or "do well" in title_txt:
            pb.strengths = body_txt
        elif "weakness" in title_txt or "beats you" in title_txt:
            pb.weaknesses = body_txt

    # ── Mulligan ──────────────────────────────────────────────────────────
    for section in soup.select(".section, [class*='mull']"):
        txt = section.get_text(" ", strip=True)
        if "mulligan" in txt.lower()[:50]:
            pb.mulligan = txt[:600]
            break
    if not pb.mulligan:
        m = re.search(r"(mulligan[^.]{0,400}\.)", text, re.I | re.S)
        if m:
            pb.mulligan = m.group(1)[:400]

    # ── Matchups table ────────────────────────────────────────────────────
    for row in soup.select("tr"):
        cells = [td.get_text(" ", strip=True) for td in row.select("td,th")]
        if len(cells) >= 2:
            opp = cells[0].strip()
            # Skip header rows
            if opp.lower() in ("matchup", "opponent", "deck", ""):
                continue
            if len(opp) < 3 or opp.lower().startswith("matchup"):
                continue
            me = MatchupEntry(opponent=opp)
            if len(cells) >= 3:
                me.sb_in  = [s.strip() for s in re.split(r"[,+]+", cells[1]) if s.strip()]
                me.sb_out = [s.strip() for s in re.split(r"[,\-]+", cells[2]) if s.strip()]
            if len(cells) >= 4:
                me.notes = cells[3][:200]
            if me.opponent:
                pb.matchups.append(me)

    # ── Game plan (from first section body) ──────────────────────────────
    first_section = soup.select_one(".section.active, .section")
    if first_section:
        pb.game_plan = first_section.get_text(" ", strip=True)[:600]

    return pb


# ---------------------------------------------------------------------------
# Bulk loader — parse all 46 playbooks into a cache
# ---------------------------------------------------------------------------

CACHE_PATH = Path(__file__).parent.parent / "data" / "playbook_cache.json"


def load_all_playbooks(
    playbook_dir: str = None,
    use_cache:    bool = True,
    force_rebuild: bool = False,
) -> dict[str, PlaybookData]:
    """
    Load all HTML playbooks from My-Website/.
    Returns {deck_name: PlaybookData}.

    Results are cached in data/playbook_cache.json for fast reuse.
    """
    cache_path = CACHE_PATH
    pb_dir     = Path(playbook_dir) if playbook_dir else PLAYBOOK_DIR

    if use_cache and cache_path.exists() and not force_rebuild:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        results = {}
        for k, v in raw.items():
            v["matchups"] = [MatchupEntry(**m) for m in v.get("matchups", [])]
            results[k] = PlaybookData(**{kk: vv for kk, vv in v.items()
                                         if kk != "matchups"},
                                      matchups=v["matchups"])
        return results

    if not BS4_AVAILABLE:
        print("[PlaybookParser] beautifulsoup4 not installed — pip install beautifulsoup4")
        return {}

    results    = {}
    html_files = sorted(pb_dir.glob("*playbook*.html"))
    print(f"[PlaybookParser] Parsing {len(html_files)} playbooks…")

    for f in html_files:
        try:
            pb = parse_playbook(str(f))
            if pb.deck_name:
                results[pb.deck_name] = pb
                mb_count = sum(pb.mainboard.values())
                print(f"  OK {pb.deck_name:<35} {pb.format_name:<10} "
                      f"T{pb.kill_turn:<6} {mb_count}main")
            else:
                print(f"  ?  {f.name} -- no deck name found")
        except Exception as e:
            print(f"  ERR {f.name}: {e}")

    # Cache results
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    raw = {}
    for k, pb in results.items():
        d = asdict(pb)
        raw[k] = d
    cache_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"[PlaybookParser] Cached {len(results)} playbooks → {cache_path}")

    return results


def find_playbook(
    deck_name:  str,
    playbooks:  dict[str, "PlaybookData"] = None,
    threshold:  float = 0.5,
) -> Optional["PlaybookData"]:
    """
    Fuzzy-find a playbook by deck name.
    'Boros Energy' matches 'BorosEnergy', 'Boros Energy Modern', etc.
    """
    if playbooks is None:
        playbooks = load_all_playbooks()

    name_clean = re.sub(r"[^a-z0-9]", "", deck_name.lower())

    # Exact match first
    for k, pb in playbooks.items():
        if re.sub(r"[^a-z0-9]", "", k.lower()) == name_clean:
            return pb

    # Fuzzy: deck name words appear in playbook name
    words = [w for w in re.split(r"[^a-z]+", name_clean) if len(w) > 2]
    best_score, best_pb = 0.0, None
    for k, pb in playbooks.items():
        k_clean = re.sub(r"[^a-z0-9]", "", k.lower())
        hits = sum(1 for w in words if w in k_clean)
        score = hits / max(len(words), 1)
        if score > best_score:
            best_score, best_pb = score, pb

    return best_pb if best_score >= threshold else None


# ---------------------------------------------------------------------------
# Also parse tac team TXT guides
# ---------------------------------------------------------------------------

TAC_TEAM_DIR = Path(__file__).parent.parent.parent / "Team Resolve" / "guides"


def parse_tac_guide(txt_path: str) -> PlaybookData:
    """Parse a tac team txt guide into PlaybookData."""
    text = Path(txt_path).read_text(encoding="utf-8", errors="replace")
    pb   = PlaybookData(source_file=str(txt_path))

    # Deck name from first line
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if lines:
        pb.deck_name = lines[0].replace("tac team", "").strip().title()

    # Format
    for fmt in ("Modern", "Pioneer", "Standard", "Legacy"):
        if fmt.lower() in text.lower():
            pb.format_name = fmt
            break

    # Sideboard table — tab-separated: MATCHUP\tSB_IN\tSB_OUT
    for line in lines:
        parts = line.split("\t")
        if len(parts) >= 3:
            opp = parts[0].strip()
            if opp and opp.lower() not in ("matchup", "deck", ""):
                pb.matchups.append(MatchupEntry(
                    opponent=opp,
                    sb_in=[s.strip() for s in parts[1].split(",") if s.strip()],
                    sb_out=[s.strip() for s in parts[2].split(",") if s.strip()],
                    notes=parts[3].strip() if len(parts) > 3 else "",
                ))

    # Game plan from intro section
    m = re.search(r"Intro\s*\n+([\s\S]{100,600}?)(?:\n\n|\Z)", text, re.I)
    if m:
        pb.game_plan = m.group(1).strip()

    return pb


def load_all_tac_guides(tac_dir: str = None) -> dict[str, PlaybookData]:
    d = Path(tac_dir) if tac_dir else TAC_TEAM_DIR
    results = {}
    for f in d.glob("tac team*.txt"):
        try:
            pb = parse_tac_guide(str(f))
            if pb.deck_name:
                results[pb.deck_name] = pb
                print(f"  OK Tac guide: {pb.deck_name}")
        except Exception as e:
            print(f"  ERR {f.name}: {e}")
    return results



# ---------------------------------------------------------------------------
# SB Plan extraction from HTML playbooks (used by sideboard.py)
# ---------------------------------------------------------------------------

def extract_sb_plans_from_html(html_path: str) -> list:
    """
    Extract real SB plans from HTML playbooks.
    Returns list of MatchupEntry with proper sb_in / sb_out card lists.
    
    Handles two HTML formats:
      1. Newer (div-based): .sb-table > .sb-col > .sb-item with .c and .sb-qty
      2. Older (table-based): table.sb-table > tr > td.sb-in / td.sb-out
    """
    if not BS4_AVAILABLE:
        return []
    
    text = Path(html_path).read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(text, "html.parser")
    
    results = []
    sb_tables = soup.select('.sb-table')
    
    for table in sb_tables:
        # ── Find opponent name ──
        opp_name = _find_matchup_opponent(table)
        if not opp_name:
            continue
        
        # ── Detect format and extract cards ──
        if table.name == 'table':
            # Older table-based format: <tr><td class="sb-out">-2 Card</td><td class="sb-in">+2 Card</td></tr>
            in_cards, out_cards = _extract_sb_table_format(table)
        else:
            # Newer div-based format: .sb-col > .sb-item
            in_cards, out_cards = _extract_sb_div_format(table)
        
        if in_cards or out_cards:
            results.append(MatchupEntry(
                opponent=opp_name,
                sb_in=in_cards,
                sb_out=out_cards,
            ))
    
    return results


def _find_matchup_opponent(table) -> str:
    """Find the opponent name for a given sb-table element."""
    import re
    
    # Strategy 1: .matchup-writeup parent (newer format)
    mu_div = table.find_parent(class_='matchup-writeup')
    if mu_div:
        first_text = mu_div.get_text(strip=True)[:120]
        m = re.match(r'^(.+?)\s*[\u2014\u2013\-]\s', first_text)
        if m:
            return m.group(1).strip()
    
    # Strategy 2: .matchup-detail parent div with preceding h2 (older format)
    md_div = table.find_parent(class_='matchup-detail')
    if md_div:
        prev = md_div.find_previous_sibling('h2')
        if prev:
            h2_text = prev.get_text(strip=True)
            opp = h2_text.split('\u2014')[0].split('\u2013')[0].strip()
            opp = re.sub(r'\s*[\-]\s*[\d.]+%.*$', '', opp).strip()
            if opp:
                return opp
    
    # Strategy 3: td.matchup-detail parent in a matchup-table (Amulet Titan format)
    td_parent = table.find_parent('td', class_='matchup-detail')
    if td_parent:
        row = td_parent.find_parent('tr')
        if row:
            # Opponent name is in the PREVIOUS row's first cell
            prev_row = row.find_previous_sibling('tr')
            if prev_row:
                first_td = prev_row.select_one('td')
                if first_td:
                    opp = first_td.get_text(strip=True).strip()
                    if opp and len(opp) > 2:
                        return opp
        # Fallback: parse from the td's id attribute (e.g. mu-boros -> Boros)
        td_id = td_parent.get('id', '')
        if td_id.startswith('mu-'):
            return td_id[3:].replace('-', ' ').title()
    
    return ""


def _extract_sb_div_format(table) -> tuple:
    """Extract IN/OUT from div-based .sb-col > .sb-item format."""
    in_cards = []
    out_cards = []
    
    for col in table.select('.sb-col'):
        label = col.select_one('.sb-col-label')
        if not label:
            continue
        label_txt = label.get_text(strip=True).lower()
        
        card_list = []
        for item in col.select('.sb-item'):
            name_el = item.select_one('.c')
            if not name_el:
                spans = item.select('span > span')
                if not spans:
                    spans = item.select('span')
                name_el = spans[0] if spans else None
            
            qty_el = item.select_one('.sb-qty')
            if name_el and qty_el:
                name = name_el.get_text(strip=True)
                qty_raw = qty_el.get_text(strip=True)
                qty_raw = qty_raw.replace('\u2212', '').replace('+', '').replace('-', '').strip()
                try:
                    qty = int(qty_raw)
                except ValueError:
                    qty = 1
                card_list.append(f"{qty} {name}")
            elif not qty_el:
                # Fallback: parse inline text like "+2 Dismember (kills Ragavan)"
                raw = item.get_text(strip=True)
                m = re.match(r'[\+\-\u2212]?\s*(\d+)\s*(.+?)(?:\s*\(.*\))?$', raw)
                if m:
                    card_list.append(f"{int(m.group(1))} {m.group(2).strip()}")
        
        if 'in' in label_txt:
            in_cards = card_list
        elif 'out' in label_txt:
            out_cards = card_list
    
    return in_cards, out_cards


def _extract_sb_table_format(table) -> tuple:
    """
    Extract IN/OUT from table-based <tr><td class="sb-in/sb-out"> format.
    
    Cell text patterns:
      "+2 Pyroclasm (sweeps tokens)" -> "2 Pyroclasm"
      "\u22122 Psychic Frog" -> "2 Psychic Frog"
      "+4 Consign to Memory(counters FoN)" -> "4 Consign to Memory"
    """
    import re
    in_cards = []
    out_cards = []
    
    for row in table.select('tr'):
        for td in row.select('td'):
            classes = td.get('class', [])
            is_in  = 'sb-in' in classes
            is_out = 'sb-out' in classes
            if not (is_in or is_out):
                continue
            
            # Try to get card name from .c span first
            c_el = td.select_one('.c')
            if c_el:
                card_name = c_el.get_text(strip=True)
            else:
                # Parse from raw text: "+2 Card Name (notes)" or "\u22122 Card Name"
                raw = td.get_text(strip=True)
                card_name = raw
            
            # Extract quantity and clean card name from the full cell text
            raw_text = td.get_text(strip=True)
            # Pattern: optional +/- or \u2212, then digits, then card name, optional (notes)
            m = re.match(r'[\+\-\u2212]?\s*(\d+)\s*(.+?)(?:\s*\(.*\))?$', raw_text)
            if m:
                qty = int(m.group(1))
                # Prefer .c element name if available, else use regex capture
                if c_el:
                    name = card_name
                else:
                    name = m.group(2).strip()
                entry = f"{qty} {name}"
                if is_in:
                    in_cards.append(entry)
                else:
                    out_cards.append(entry)
    
    return in_cards, out_cards



# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    force = "--rebuild" in sys.argv

    print("=== Parsing HTML Playbooks ===")
    pbs = load_all_playbooks(force_rebuild=force)
    print(f"\nLoaded {len(pbs)} playbooks")

    print("\n=== Parsing Tac Team Guides ===")
    tacs = load_all_tac_guides()
    print(f"Loaded {len(tacs)} tac guides")

    if len(sys.argv) > 1 and sys.argv[1] not in ("--rebuild",):
        query = " ".join(a for a in sys.argv[1:] if a != "--rebuild")
        all_pbs = {**pbs, **tacs}
        pb = find_playbook(query, all_pbs)
        if pb:
            print(f"\n=== {pb.deck_name} ===")
            print(f"Format:    {pb.format_name}")
            print(f"Role:      {pb.role}")
            print(f"Kill Turn: {pb.kill_turn}")
            print(f"Mainboard: {sum(pb.mainboard.values())} cards")
            print(f"Sideboard: {sum(pb.sideboard.values())} cards")
            print(f"Matchups:  {len(pb.matchups)}")
            print(f"\nTop cards:")
            for name, qty in sorted(pb.mainboard.items(), key=lambda x: -x[1])[:10]:
                print(f"  {qty}x {name}")
        else:
            print(f"No playbook found for '{query}'")
