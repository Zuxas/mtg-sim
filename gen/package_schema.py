"""
gen/package_schema.py -- Synergy "package" notation schema.

A Package is a reusable bundle of cards that work together (a combo core, a card
engine, a payoff suite, an interaction package, or a mana base fragment). The
generator assembles a decklist by selecting a core package and following its
`conjoins_with` edges to compatible support packages.

Packages live as JSON in gen/packages/*.json (git-tracked, human/LLM authored).
Discovered packages (from gen/discovery.py) are written with a machine
provenance tag and flagged for human review before becoming seeds.

Validation is split so most checks need no card data:
  structural_issues()      -> schema/slot/role sanity (no pool needed)
  pool_issues(pool)        -> legality + simulatability + color-identity (needs CardPool)

Usage:
    from gen.package_schema import Package, load_all_packages
    pkgs = load_all_packages()                  # dict id -> Package
    issues = pkgs["amulet_titan_core"].pool_issues(pool)
"""

import os
import glob
import json
from dataclasses import dataclass, field, asdict

ROLES = {"combo-core", "aggro-core", "engine", "payoff", "interaction", "mana"}
CORE_ROLES = {"combo-core", "aggro-core"}

PACKAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packages")


@dataclass
class Package:
    id: str
    name: str
    role: str                       # one of ROLES
    cards: dict                     # {card_name: qty}
    color_identity: list            # e.g. ["R", "W"]; [] for colorless
    conjoins_with: list = field(default_factory=list)   # package ids OR tag strings
    tags: list = field(default_factory=list)            # capability tags for conjoin matching
    synergy_notes: str = ""
    provenance: str = "seed:human"
    min_slots: int = 0
    max_slots: int = 0
    requires_simulatable: bool = True
    # optional authored hints; recomputed from a pool when available
    pip_demand: dict = field(default_factory=dict)
    avg_cmc: float = 0.0

    # --- derived ---------------------------------------------------------
    def slot_count(self) -> int:
        return sum(self.cards.values())

    def card_names(self):
        return list(self.cards.keys())

    # --- validation ------------------------------------------------------
    def structural_issues(self) -> list:
        """Schema-level checks that need no card data."""
        issues = []
        if not self.id:
            issues.append("missing id")
        if self.role not in ROLES:
            issues.append(f"invalid role '{self.role}' (expected one of {sorted(ROLES)})")
        if not self.cards:
            issues.append("no cards")
        if any(q <= 0 for q in self.cards.values()):
            issues.append("non-positive card quantity")
        n = self.slot_count()
        lo = self.min_slots or n
        hi = self.max_slots or n
        if lo > hi:
            issues.append(f"min_slots {lo} > max_slots {hi}")
        if not (lo <= n <= hi):
            issues.append(f"slot_count {n} outside [{lo},{hi}]")
        # colored packages should declare a color identity
        return issues

    def pool_issues(self, pool) -> list:
        """Legality / simulatability / color-identity checks against a CardPool."""
        issues = []
        union_ci = set()
        for name in self.cards:
            pc = pool.get(name)
            if pc is None:
                issues.append(f"'{name}' not in {pool.fmt} pool (illegal/banned/unknown)")
                continue
            union_ci |= set(pc.color_identity)
            if self.requires_simulatable and not pc.simulatable:
                issues.append(f"'{name}' not simulatable (bucket {pc.sim_bucket})")
        if not union_ci.issubset(set(self.color_identity)):
            issues.append(f"declared color_identity {self.color_identity} does not cover "
                          f"card identities {sorted(union_ci)}")
        return issues

    def compute_metrics(self, pool):
        """Fill pip_demand + avg_cmc from real card data (mutates self)."""
        demand, total_cmc, total_qty = {}, 0.0, 0
        for name, qty in self.cards.items():
            pc = pool.get(name)
            if pc is None:
                continue
            for color, n in pc.colored_pips.items():
                demand[color] = demand.get(color, 0) + n * qty
            total_cmc += pc.cmc * qty
            total_qty += qty
        self.pip_demand = demand
        self.avg_cmc = round(total_cmc / total_qty, 2) if total_qty else 0.0
        return self

    # --- serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Package":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def save(self, directory: str = None):
        directory = directory or PACKAGES_DIR
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{self.id}.json")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp, path)
        return path


def load_all_packages(directory: str = None) -> dict:
    """Load every gen/packages/*.json into {id: Package}. Raises on duplicate id."""
    directory = directory or PACKAGES_DIR
    out = {}
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        with open(path, encoding="utf-8") as f:
            pkg = Package.from_dict(json.load(f))
        if pkg.id in out:
            raise ValueError(f"duplicate package id '{pkg.id}' in {path}")
        out[pkg.id] = pkg
    return out


def conjoin_graph(packages: dict) -> dict:
    """
    Resolve conjoins_with (which may name package ids OR tag strings) into a
    directed adjacency map {pkg_id: set(reachable pkg_ids)}.
    """
    by_tag = {}
    for pid, pkg in packages.items():
        for t in pkg.tags:
            by_tag.setdefault(t, set()).add(pid)
    graph = {}
    for pid, pkg in packages.items():
        nbrs = set()
        for ref in pkg.conjoins_with:
            if ref in packages:
                nbrs.add(ref)
            elif ref in by_tag:
                nbrs |= by_tag[ref]
        nbrs.discard(pid)
        graph[pid] = nbrs
    return graph
