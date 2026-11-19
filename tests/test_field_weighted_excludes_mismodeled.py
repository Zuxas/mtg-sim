"""The field-weighted win rate leaves out combo cells that are Legacy Humans'
number standing in for our deck (#25), renormalizes over the rest, and
reports the excluded share.

Run: python tests/test_field_weighted_excludes_mismodeled.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parallel_sim import cell_flag, field_weighted

good = {"opp": "A", "field_pct": 30.0, "match": 60.0}
good2 = {"opp": "B", "field_pct": 10.0, "match": 40.0}
bad = {"opp": "Neobrand", "field_pct": 20.0, "match": 99.0, "our_side_modeled": False}
err = {"opp": "C", "field_pct": 5.0, "match": 0, "error": "boom"}

# the stand-in cell does not move the headline; its share is reported
assert field_weighted([good, good2, bad, err]) == (55.0, 20.0)
assert field_weighted([good, good2]) == (55.0, 0.0)
# nothing valid left: unavailable, not 0% and not the stand-in number
assert field_weighted([bad]) == (None, 20.0)
assert field_weighted([]) == (None, 0.0)
assert cell_flag(bad).strip() == "[!COMBO MODEL]" and cell_flag(good) == ""
print("test_field_weighted_excludes_mismodeled: OK")
