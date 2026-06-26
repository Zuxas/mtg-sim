"""
gen/lineage.py -- Lineage + leaderboard persistence for optimizer runs.

Every evaluated candidate is recorded as a node with a parent pointer, so an
optimization run is a reconstructable tree (which mutation of which parent
produced which fitness). A leaderboard keeps the top-N by fitness with fidelity
flags so search results survive the ephemeral container.

Layout:
  data/auto_pipeline/lineage/<run_id>/<node_id>.json   -- per-candidate record
  data/auto_pipeline/leaderboard.json                  -- global top-N
"""

import os
import json

from gen import PIPELINE_DATA

LINEAGE_DIR = os.path.join(PIPELINE_DATA, "lineage")
LEADERBOARD = os.path.join(PIPELINE_DATA, "leaderboard.json")


class Lineage:
    def __init__(self, run_id, base_dir=None):
        self.run_id = run_id
        self.dir = os.path.join(base_dir or LINEAGE_DIR, run_id)
        os.makedirs(self.dir, exist_ok=True)
        self._counter = 0

    def record(self, cand, report=None, parent_id=None, mutation=None):
        """Persist a candidate + its fitness report; return the node id."""
        self._counter += 1
        node_id = f"{self.run_id}_n{self._counter:04d}"
        node = {
            "node_id": node_id,
            "parent_id": parent_id,
            "mutation": mutation,
            "name": cand.name,
            "packages": list(cand.packages),
            "mainboard": dict(cand.mainboard),
            "color_identity": list(cand.color_identity),
            "metadata": dict(cand.metadata),
            "fitness": getattr(report, "fitness", None),
            "verdict": getattr(report, "verdict", None),
            "fidelity": getattr(report, "fidelity", cand.metadata.get("fidelity")),
            "field_wr": getattr(report, "field_wr", None),
        }
        path = os.path.join(self.dir, f"{node_id}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(node, f, indent=2)
        os.replace(tmp, path)
        cand.lineage = list(cand.lineage) + [node_id]
        return node_id


def update_leaderboard(entries, top_n=25, path=None):
    """
    Merge (deck_id, fitness, verdict, fidelity, meta) entries into the global
    leaderboard, keep the top-N by fitness. Returns the merged list.
    """
    path = path or LEADERBOARD
    existing = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = json.load(f).get("entries", [])
        except Exception:
            existing = []

    by_id = {e["deck_id"]: e for e in existing}
    for e in entries:
        cur = by_id.get(e["deck_id"])
        if cur is None or e.get("fitness", 0) > cur.get("fitness", 0):
            by_id[e["deck_id"]] = e

    merged = sorted(by_id.values(), key=lambda e: -(e.get("fitness") or 0))[:top_n]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"entries": merged}, f, indent=2)
    os.replace(tmp, path)
    return merged
