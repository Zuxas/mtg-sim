"""test_response_capability.py -- Stages 1-2 of the oracle-driven-responses
spec (harness/specs/2026-07-02-oracle-driven-responses.md; golden-test
discipline BY REFERENCE from the 2026-07-01 parent spec, its G1/G3).

GOLDEN CONTRACT (Gate 4): every currently-whitelisted card
(engine/counter_resolver.py::COUNTER_VALIDITY, apl/match_apl.py::
MATCH_REMOVAL incl. per-APL extensions) is pinned into exactly one bucket:

  EXACT            -- classifier reproduces the table's predicate + cost
                      from oracle text alone (predicate equality proven
                      BEHAVIORALLY over probe spells, not by name).
  DOCUMENTED_*     -- classifier derives the printed-oracle truth; the
                      table deliberately encodes a POLICY value (its own
                      source comments say so) or an approximation/error.
                      Both sides are pinned so any drift screams.
  NOT_DERIVED      -- v1 grammar declines (alt/pitch cost, {X},
                      cost-reduction statics, Spree/Tiered, unknown
                      riders, variable damage, non-removal table entries);
                      the card KEEPS its whitelist entry (spec fallback).
  OUT_OF_SCOPE     -- not castable at instant speed (sorcery-speed
                      removal / wipes stay table-driven in v1).

The partition is asserted EXHAUSTIVELY: adding a whitelist entry without
classifying it here fails the suite. Grammar-attributable mismatches are
ZERO; the >2-mismatch stop condition (07-01) is not triggered -- the four
non-exact derived entries below are table-side deviations proven against
oracle text quoted inline.

Also covers: classification cache (spec design 2), negative fixtures
(Risk 4), and the Stages-0-2 structural guarantee that NO live engine
path imports this module (gate-OFF byte-identity by construction).
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from engine import response_capability as rc
from engine.counter_resolver import COUNTER_VALIDITY
from apl.match_apl import MatchAPL
from data.card import Tag


# ---------------------------------------------------------------------------
# Probe spells: behavioral predicate comparison (table lambda vs derived
# condition) -- equality is proven by evaluation, never by card name.
# ---------------------------------------------------------------------------

class _FakeSpell:
    def __init__(self, name, cmc, tags):
        self.name = name
        self.cmc = cmc
        self._tags = set(tags)

    def has(self, tag):
        return tag in self._tags


PROBE_SPELLS = [
    _FakeSpell("bear",          2, {Tag.CREATURE}),
    _FakeSpell("big-creature",  4, {Tag.CREATURE}),
    _FakeSpell("cantrip",       1, {Tag.INSTANT}),
    _FakeSpell("big-sorcery",   4, {Tag.SORCERY}),
    _FakeSpell("artifact",      2, {Tag.ARTIFACT}),
    _FakeSpell("enchantment",   3, {Tag.ENCHANTMENT}),
    _FakeSpell("planeswalker",  4, {Tag.PLANESWALKER}),
    _FakeSpell("artifact-creature", 3, {Tag.ARTIFACT, Tag.CREATURE}),
    _FakeSpell("two-drop-instant",  2, {Tag.INSTANT}),
]


# ---------------------------------------------------------------------------
# Golden pinning: COUNTER_VALIDITY (18 entries)
# ---------------------------------------------------------------------------

# name -> (expected kind, expected derived cost == table base_cmc)
EXACT_COUNTERS = {
    "Spell Snare":       (rc.COUNTER_CMC_COND,     1),
    "Spell Pierce":      (rc.COUNTER_NONCREATURE,  1),
    "Negate":            (rc.COUNTER_NONCREATURE,  2),
    "Disdainful Stroke": (rc.COUNTER_CMC_COND,     2),
    "Essence Scatter":   (rc.COUNTER_CREATURE,     2),
    "Annul":             (rc.COUNTER_NONCREATURE,  1),
    "Counterspell":      (rc.COUNTER_ANY,          2),
}

# name -> (derived printed cost, table policy cost, table's own justification)
DOCUMENTED_POLICY_COST_COUNTERS = {
    # counter_resolver.py comment: "Effective cmc=3 in the value gate --
    # it's {U}{U} actual cost but bouncing own for tempo is usually higher
    # value" -- POLICY, stays table-owned (spec design 4).
    "Get Out":         (rc.COUNTER_CREATURE, 2, 3),
    # counter_resolver.py comment: "base_cmc=1 value-gate lets it answer
    # cheap spells; _pay_for_counter still charges the full printed cmc (3)".
    "Metallic Rebuke": (rc.COUNTER_UNLESS_PAY_N, 3, 1),
}

# name -> v1 reason the whitelist entry is kept (spec "NOT DERIVED in v1")
NOT_DERIVED_COUNTERS = {
    "Force of Will":        "alt-pitch-cost",
    "Force of Negation":    "alt-pitch-cost",
    "Daze":                 "alt-pitch-cost",
    "Disrupting Shoal":     "x-cost + alt-pitch-cost",
    "Mystical Dispute":     "cost-reduction-static",
    "Phantom Interference": "spree additional-cost modes",
    # 'Counter target instant spell, sorcery spell, or triggered ability'
    # -- outside the closed filter vocabulary; table's noncreature predicate
    # is itself an approximation (broader than the card).
    "Spider-Sense":         "unknown counter filter",
    # 'Counter target triggered ability or colorless spell'
    "Consign to Memory":    "unknown counter filter",
    # ETB pseudo-counter on an evoke elemental; no 'counter target' text.
    "Subtlety":             "counter-ability on permanent",
}


def test_counter_golden_partition_exhaustive():
    """Every COUNTER_VALIDITY entry is pinned in exactly one bucket."""
    pinned = (set(EXACT_COUNTERS) | set(DOCUMENTED_POLICY_COST_COUNTERS)
              | set(NOT_DERIVED_COUNTERS))
    table = set(COUNTER_VALIDITY)
    assert pinned == table, (
        f"golden partition drift: unpinned={sorted(table - pinned)} "
        f"stale={sorted(pinned - table)}")
    overlap = (set(EXACT_COUNTERS) & set(DOCUMENTED_POLICY_COST_COUNTERS)
               | set(EXACT_COUNTERS) & set(NOT_DERIVED_COUNTERS)
               | set(DOCUMENTED_POLICY_COST_COUNTERS) & set(NOT_DERIVED_COUNTERS))
    assert not overlap, f"cards pinned twice: {overlap}"


def _single_counter_cap(name):
    caps = [c for c in rc.capabilities(name) if c.kind in rc.COUNTER_KINDS]
    assert len(caps) == 1, f"{name}: expected 1 counter capability, got {caps}"
    return caps[0]


def test_counter_golden_exact():
    """Gate 4 core: derived predicate+cost == table predicate+cost, with
    predicate equality proven behaviorally over the probe spells."""
    for name, (kind, cost) in EXACT_COUNTERS.items():
        cap = _single_counter_cap(name)
        table_pred, table_cost = COUNTER_VALIDITY[name]
        assert cap.kind == kind, f"{name}: kind {cap.kind} != {kind}"
        assert cap.cost == cost == table_cost, (
            f"{name}: cost derived={cap.cost} pinned={cost} table={table_cost}")
        for spell in PROBE_SPELLS:
            assert rc.counter_matches(cap, spell) == bool(table_pred(spell)), (
                f"{name}: predicate mismatch on probe {spell.name} "
                f"(cmc={spell.cmc})")


def test_counter_golden_documented_policy_costs():
    """Predicate parity holds; cost differs exactly as the table's own
    comments document. Pin BOTH sides so any drift fails loudly."""
    for name, (kind, derived_cost, policy_cost) in \
            DOCUMENTED_POLICY_COST_COUNTERS.items():
        cap = _single_counter_cap(name)
        table_pred, table_cost = COUNTER_VALIDITY[name]
        assert cap.kind == kind
        assert cap.cost == derived_cost, (
            f"{name}: derived cost {cap.cost} != printed {derived_cost}")
        assert table_cost == policy_cost, (
            f"{name}: table cost changed ({table_cost} != {policy_cost}) -- "
            f"re-adjudicate this pin")
        for spell in PROBE_SPELLS:
            assert rc.counter_matches(cap, spell) == bool(table_pred(spell)), (
                f"{name}: predicate mismatch on probe {spell.name}")


def test_counter_golden_not_derived_keep_whitelist():
    """v1-excluded cards derive NO counter capability (so Stage 3's
    either/or consultation falls back to the table entry they keep)."""
    for name in NOT_DERIVED_COUNTERS:
        caps = [c for c in rc.capabilities(name) if c.kind in rc.COUNTER_KINDS]
        assert not caps, (
            f"{name}: unexpectedly derived {caps}; it was pinned as v1 "
            f"whitelist-fallback ({NOT_DERIVED_COUNTERS[name]})")
        assert name in COUNTER_VALIDITY   # the fallback entry must exist


# ---------------------------------------------------------------------------
# Golden pinning: base MatchAPL.MATCH_REMOVAL (36 entries)
# projection semantics: REMOVAL_DMG_N -> (cmc, N); DESTROY/EXILE -> (cmc, None)
# ---------------------------------------------------------------------------

EXACT_REMOVAL = {
    # name: (cost, max_tgh) -- must equal the table entry
    "Lightning Helix":   (2, 3),
    "Bitter Triumph":    (2, None),
    "Go for the Throat": (2, None),   # + ('nonartifact',) rider, see below
    "Long Goodbye":      (2, None),   # + ('mv_le', 3) rider, see below
    "Get Lost":          (2, None),
    "Archenemy's Charm": (3, None),
    "Lightning Strike":  (2, 3),
    "Burst Lightning":   (1, 2),
    "Shock":             (1, 2),
    "Torch the Tower":   (1, 2),
    "Abrade":            (2, 3),
    "Stab":              (1, 2),
}

# Riders the classifier derives that the table cannot encode in its
# (cmc, max_tgh) slots. Each is TRUE per oracle text and acknowledged in the
# table's own comments -- the classifier is STRICTER, never looser.
EXPECTED_RIDERS = {
    "Go for the Throat": (("nonartifact",),),
    "Long Goodbye":      (("mv_le", 3),),
}

# Table-side deviations: classifier output pinned to ORACLE truth, table
# value pinned to its CURRENT (approximate/erroneous) encoding.
DOCUMENTED_TABLE_DEVIATIONS = {
    # oracle: 'Destroy target creature with mana value 2 or less.'
    # table (1, 2) jams the MV condition into the max-toughness slot
    # (its comment: 'destroy creature CMC <= 2').
    "Requiting Hex": {"derived": (1, None), "rider": (("mv_le", 2),),
                      "table": (1, 2)},
    # oracle: 'Sear deals 4 damage to target creature or planeswalker.'
    # table (2, 3) under-models (its comment says '3 dmg bolt' -- stale).
    "Sear":          {"derived": (2, 4), "rider": (("dmg", 4),),
                      "table": (2, 3)},
}

NOT_DERIVED_REMOVAL = {
    "Fire Magic":           "tiered additional-cost modes",
    "Shoot the Sheriff":    "unknown rider: non-outlaw",
    "Witchstalker Frenzy":  "cost-reduction-static",
    "Combustion Technique": "variable damage (equal to ...)",
    "Destroy Evil":         "unknown rider: toughness 4 or greater",
    "Faebloom Trick":       "not removal (token maker + tap); table entry "
                            "is itself a mismodel",
    "Annul":                "derives as COUNTER, not removal; table entry "
                            "is category reuse",
}

OUT_OF_SCOPE_REMOVAL = {
    # sorcery-speed / non-instant frames: stay MATCH_REMOVAL-table-driven
    "Deadly Cover-Up", "Day of Judgment", "Depopulate", "Sunfall",
    "Farewell", "Temporary Lockdown", "Obliterating Bolt", "Exorcise",
    "Iroh's Demonstration", "Pyroclasm", "Slagstorm", "Scorching Shot",
    "Path of Peril", "The Cruelty of Gix", "Strategic Betrayal",
}


def test_removal_golden_partition_exhaustive():
    pinned = (set(EXACT_REMOVAL) | set(DOCUMENTED_TABLE_DEVIATIONS)
              | set(NOT_DERIVED_REMOVAL) | OUT_OF_SCOPE_REMOVAL)
    table = set(MatchAPL.MATCH_REMOVAL)
    assert pinned == table, (
        f"removal golden drift: unpinned={sorted(table - pinned)} "
        f"stale={sorted(pinned - table)}")


def test_removal_golden_exact():
    for name, expected in EXACT_REMOVAL.items():
        spec = rc.removal_spec_from(rc.capabilities(name))
        assert spec is not None, f"{name}: derived no removal"
        cost, tgh, cond = spec
        assert (cost, tgh) == expected == MatchAPL.MATCH_REMOVAL[name], (
            f"{name}: derived ({cost},{tgh}) pinned {expected} "
            f"table {MatchAPL.MATCH_REMOVAL[name]}")
        if name in EXPECTED_RIDERS:
            for rider in EXPECTED_RIDERS[name]:
                assert rider in cond, f"{name}: missing rider {rider}"


def test_removal_golden_documented_deviations():
    for name, pin in DOCUMENTED_TABLE_DEVIATIONS.items():
        spec = rc.removal_spec_from(rc.capabilities(name))
        assert spec is not None, f"{name}: derived no removal"
        cost, tgh, cond = spec
        assert (cost, tgh) == pin["derived"], (
            f"{name}: derived ({cost},{tgh}) != oracle-pinned {pin['derived']}")
        for rider in pin["rider"]:
            assert rider in cond, f"{name}: missing rider {rider}"
        assert MatchAPL.MATCH_REMOVAL[name] == pin["table"], (
            f"{name}: table entry changed -- re-adjudicate this deviation pin")


def test_removal_golden_not_derived_keep_whitelist():
    for name in NOT_DERIVED_REMOVAL:
        spec = rc.removal_spec_from(rc.capabilities(name))
        assert spec is None, (
            f"{name}: unexpectedly derived {spec}; pinned as fallback "
            f"({NOT_DERIVED_REMOVAL[name]})")
        assert name in MatchAPL.MATCH_REMOVAL


def test_removal_golden_out_of_scope_timing():
    for name in OUT_OF_SCOPE_REMOVAL:
        r = rc.classify(name)
        assert r.timing == "", (
            f"{name}: pinned out-of-scope (sorcery-speed) but classifier "
            f"sees timing={r.timing!r}")
        assert not r.caps


# ---------------------------------------------------------------------------
# Golden pinning: per-APL MATCH_REMOVAL extensions (~60-card whitelist total).
# Extension entries use pip-string costs ('1R', 4) and often CONTEXT-adjusted
# values (Unholy Heat 6 = delirium, Torch the Tower 3 = bargained) -- those
# are policy encodings, pinned as such.
# ---------------------------------------------------------------------------

def _pip_cmc(cost_spec):
    """cmc of a pip string like '1R' / '2WW' / 'B' (extension format)."""
    if isinstance(cost_spec, (int, float)):
        return int(cost_spec)
    m = re.match(r"^(\d*)([WUBRGC]*)$", str(cost_spec))
    assert m, f"unparseable extension cost {cost_spec!r}"
    return int(m.group(1) or 0) + len(m.group(2))


# (name, table_spec) -> bucket; values verified against oracle text.
EXTENSION_MATCH = {
    ("Burst Lightning", ("R", 2)),      # derived (1,2)
    ("Lightning Bolt",  ("R", 3)),      # derived (1,3)
    ("Get Lost",        ("1W", None)),  # derived (2,None)
}
EXTENSION_CONTEXT_VALUES = {
    # oracle 'deals 3 damage' vs table tgh 4: APL-local policy stretch
    ("Abrade",          ("1R", 4)): (2, 3),
    # oracle base 2 dmg; table 3 = bargained value (policy)
    ("Torch the Tower", ("R", 3)): (1, 2),
    # oracle base 2 dmg; table 6 = delirium value (policy)
    ("Unholy Heat",     ("R", 6)): (1, 2),
}
EXTENSION_NOT_DERIVED = {
    ("Fatal Push",       ("B", 4)):  "conditional-mv phrasing outside v1 grammar",
    ("Flare of Malice",  ("2BB", None)): "alt-pitch-cost",
    ("Fire Magic",       ("R", 2)):  "tiered additional-cost modes",
    ("Nowhere to Run",   ("1B", 3)): "flash enchantment static; v1-inert",
    ("Pyrrhic Strike",   ("2W", 4)): "outside v1 grammar",
}
EXTENSION_OUT_OF_SCOPE = {
    ("Avatar's Wrath",   ("2WW", None)),
    ("Pyroclasm",        ("1R", 2)),
    ("Seam Rip",         ("W", 2)),
    ("Tragic Trajectory", ("B", 2)),
}


def _extension_entries():
    """Union of per-APL MATCH_REMOVAL entries that differ from base."""
    import importlib
    from apl import APL_REGISTRY
    base = dict(MatchAPL.MATCH_REMOVAL)
    seen = set()
    for key, (mod_path, cls_name, _stub) in sorted(APL_REGISTRY.items()):
        try:
            cls = getattr(importlib.import_module(mod_path), cls_name)
        except Exception:
            continue   # registry rot is test_apls' territory, not golden's
        mr = getattr(cls, "MATCH_REMOVAL", None)
        if isinstance(mr, dict):
            for name, spec in mr.items():
                if base.get(name) != spec:
                    seen.add((name, tuple(spec) if isinstance(spec, tuple)
                              else spec))
    return seen


def test_removal_golden_apl_extensions():
    entries = _extension_entries()
    pinned = (set(EXTENSION_MATCH) | set(EXTENSION_CONTEXT_VALUES)
              | set(EXTENSION_NOT_DERIVED) | EXTENSION_OUT_OF_SCOPE)
    assert entries == pinned, (
        f"extension whitelist drift: unpinned={sorted(entries - pinned)} "
        f"stale={sorted(pinned - entries)}")
    for name, spec in EXTENSION_MATCH:
        d = rc.removal_spec_from(rc.capabilities(name))
        assert d is not None, f"{name}: derived no removal"
        assert (d[0], d[1]) == (_pip_cmc(spec[0]), spec[1]), (
            f"{name}: derived ({d[0]},{d[1]}) != extension table "
            f"({_pip_cmc(spec[0])},{spec[1]})")
    for (name, spec), derived in EXTENSION_CONTEXT_VALUES.items():
        d = rc.removal_spec_from(rc.capabilities(name))
        assert d is not None and (d[0], d[1]) == derived, (
            f"{name}: derived {d} != oracle-pinned {derived} "
            f"(table {spec} is a policy encoding)")
    for name, spec in EXTENSION_NOT_DERIVED:
        d = rc.removal_spec_from(rc.capabilities(name))
        assert d is None, f"{name}: unexpectedly derived {d}"
    for name, spec in EXTENSION_OUT_OF_SCOPE:
        assert rc.classify(name).timing == "", f"{name}: expected non-instant"


# ---------------------------------------------------------------------------
# Classification cache (spec design 2): classify once per unique card,
# process lifetime -- classification can never enter the inner loop.
# ---------------------------------------------------------------------------

def test_cache_hit_on_second_lookup():
    rc._reset_cache()
    r1 = rc.classify("Counterspell")
    stats1 = rc.cache_stats()
    r2 = rc.classify("Counterspell")
    stats2 = rc.cache_stats()
    assert stats1["misses"] == 1 and stats1["hits"] == 0
    assert stats2["misses"] == 1 and stats2["hits"] == 1, (
        f"second lookup did not hit the cache: {stats2}")
    assert r1 is r2, "cache must return the same immutable object"


def test_cache_key_is_oracle_id_not_call_arg():
    """Card-object and name-string lookups share one cache entry."""
    rc._reset_cache()

    class _CardStub:
        name = "Negate"

    r1 = rc.classify(_CardStub())
    r2 = rc.classify("Negate")
    assert r1 is r2
    assert rc.cache_stats()["size"] == 1


# ---------------------------------------------------------------------------
# Negative fixtures (Risk 4: grammar false positives; Gate 4 extension).
# classify_fields lets us pin synthetic oracle text without CardDB entries.
# ---------------------------------------------------------------------------

def _fields(text, type_line="Instant", cmc=1, cost="{U}", kw=()):
    return rc.classify_fields("Fixture", text, type_line, cmc, cost, kw)


def test_negative_counter_own_spell():
    r = _fields("Counter target spell you control.")
    assert not r.caps, f"false positive: {r.caps}"
    assert any("counter-own-spell" in u for u in r.unhandled)


def test_negative_player_only_burn_is_not_removal():
    r = _fields("Fixture deals 3 damage to target player or planeswalker.")
    assert not r.caps, f"false positive: {r.caps}"


def test_negative_wipe_is_not_spot_removal():
    r = _fields("Destroy all creatures.")
    assert not r.caps


def test_negative_own_bounce_is_not_removal():
    r = _fields("Return target creature you control to its owner's hand.")
    assert not r.caps


def test_negative_ability_counter_unhandled():
    r = _fields("Counter target activated ability.")
    assert not r.caps


def test_negative_variable_damage_unhandled_not_wrong():
    r = _fields("Fixture deals damage equal to the number of Zombies you "
                "control to target creature.")
    assert not r.caps
    assert any(u.startswith("damage-unparsed") for u in r.unhandled)


def test_negative_sorcery_timing_excluded():
    r = _fields("Destroy target creature.", type_line="Sorcery")
    assert r.timing == "" and not r.caps


def test_negative_inert_cantrip():
    r = _fields("Draw a card.")
    assert not r.caps and not r.unhandled and not r.guarded


def test_positive_unless_pay_and_flash_frames():
    r = _fields("Counter target spell unless its controller pays {3}.",
                cmc=2, cost="{1}{U}")
    assert len(r.caps) == 1 and r.caps[0].kind == rc.COUNTER_UNLESS_PAY_N
    assert ("unless_pay", 3) in r.caps[0].condition
    # flash keyword grants timing
    r = _fields("Destroy target creature.", type_line="Enchantment",
                cmc=2, cost="{1}{B}", kw=("Flash",))
    assert r.timing == rc.TIMING_FLASH
    assert rc.removal_spec_from(r.caps) == (2, None, ())


def test_first_mode_only_for_modal_spells():
    r = _fields("Choose one —\n• Counter target creature or "
                "enchantment spell.\n• Return one or two target "
                "creatures you own to your hand.", cmc=2, cost="{U}{U}")
    kinds = [c.kind for c in r.caps]
    assert kinds == [rc.COUNTER_CREATURE], (
        f"modal handling must derive FIRST mode only, got {kinds}")


# ---------------------------------------------------------------------------
# Determinism + purity: same fields -> equal result; no RNG anywhere.
# ---------------------------------------------------------------------------

def test_classification_is_deterministic_and_hashable():
    a = _fields("Counter target noncreature spell.")
    b = _fields("Counter target noncreature spell.")
    assert a == b
    assert hash(a.caps) == hash(b.caps)


def test_module_draws_no_randomness():
    src = open(os.path.join(REPO_ROOT, "engine", "response_capability.py"),
               encoding="utf-8").read()
    assert "import random" not in src and "random." not in src, (
        "response_capability must stay RNG-free (spec Risk 1: zero new "
        "global-random sites)")


# ---------------------------------------------------------------------------
# Stages 0-2 structural contract: gate OFF = the live engine cannot even
# SEE this module. Byte-identity holds by construction until Stage 3.
# ---------------------------------------------------------------------------

_LIVE_PATH_FILES = [
    "engine/game_state.py",
    "engine/counter_resolver.py",
    "engine/priority_stack.py",
    "engine/match_engine.py",
    "engine/match_runner.py",
    "apl/match_apl.py",
    "apl/aware_match_apl.py",
]


def test_no_live_engine_path_imports_the_classifier():
    for rel in _LIVE_PATH_FILES:
        src = open(os.path.join(REPO_ROOT, rel), encoding="utf-8").read()
        assert "response_capability" not in src, (
            f"{rel} references response_capability -- that is Stage 3 work "
            f"and must arrive WITH the WANTS_ORACLE_RESPONSES gate checks")


def test_gate_defaults_off():
    class _Plain:
        pass
    assert rc.GATE_ATTR == "WANTS_ORACLE_RESPONSES"
    assert rc.oracle_responses_enabled(_Plain(), _Plain()) is False
    on = _Plain(); setattr(on, rc.GATE_ATTR, True)
    assert rc.oracle_responses_enabled(_Plain(), on) is True


if __name__ == "__main__":
    for fn_name in sorted(k for k in dir() if k.startswith("test_")):
        globals()[fn_name]()
        print(f"PASS {fn_name}")
    print("ALL RESPONSE-CAPABILITY TESTS PASS")
