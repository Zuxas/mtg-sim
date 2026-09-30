"""M0: the pinned rules baseline is intact and every citation is verbatim within its own entry."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.v2 import cr_index
from tests.v2.cr_citations import CITATIONS


def test_pinned_file_hash_and_date():
    meta = cr_index.rules_meta()
    text = cr_index.rules_text()                        # raises if the hash or size changed
    assert meta["effective_date"] == "2026-09-25"
    assert "These rules are effective as of September 25, 2026." in text


def test_entries_parsed():
    e = cr_index.entries()
    assert len(e) > 3000
    assert e["608.3a"].startswith("608.3a ")
    assert "Multiplayer Rules" not in e["733.2"]      # chapter headings end an entry


def test_every_citation_is_verbatim_in_its_own_entry():
    missing = []
    for rule_id, quotes in CITATIONS.items():
        body = cr_index.entry(rule_id)
        for q in quotes:
            if q not in body:
                missing.append((rule_id, q))
    assert not missing, missing


def test_engine_v2_cites_only_known_rules():
    """Every 'CR nnn.n' mentioned in engine/v2 AND tests/v2 source is in CITATIONS."""
    base = os.path.normpath(os.path.join(os.path.dirname(cr_index.RR), ".."))
    cited = set()
    for root in (os.path.join(base, "engine", "v2"), os.path.join(base, "tests", "v2")):
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                if f.endswith(".py") and f != "cr_citations.py":
                    cited |= set(re.findall(r"CR (\d{3}\.\d+[a-z]?)", open(os.path.join(dirpath, f), encoding="utf-8").read()))
    assert cited, "engine/v2 cites no rules"
    assert cited <= set(CITATIONS), sorted(cited - set(CITATIONS))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("M0 CITATION TESTS PASS")
