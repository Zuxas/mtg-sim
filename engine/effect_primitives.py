"""engine/effect_primitives.py — atomic effect primitives.

Every complex card effect can be decomposed into a sequence of these
primitives. The oracle parser (`oracle_parser.py`) reads oracle text
and emits a list of (primitive_name, kwargs) pairs. The dispatcher
calls each primitive with the current GameState + context.

Design goals:
  - Every primitive takes (gs, ctx, **kwargs) and returns nothing.
  - `ctx` carries: source_card, trigger_event, opp_gs (if match),
    chosen_target (for targeted effects).
  - Primitives never read oracle text — that's the parser's job.
  - Failure to resolve is silent (pass) — the engine keeps moving.

Catalog groups:
  - Card flow:    draw, mill, scry, discard, tutor, look
  - Life:         gain_life, lose_life, damage_player
  - Damage:       damage_creature, damage_any
  - Removal:      destroy, exile, bounce, shrink
  - Tokens:       create_token (w/ PT, types, keywords)
  - Counters:     add_counter, remove_counter
  - Mana:         add_mana, treasure, add_mana_any
  - Ramp:         search_land_to_battlefield
  - Reanimate:    return_from_gy_to_bf, return_from_gy_to_hand
  - Bounce:       return_to_hand
  - Counterspell: counter_spell (match-only)
  - Pump:         pump_target (P/T adjust, until EOT)
  - Tutor:        tutor_library_to_hand, tutor_to_gy
"""

from __future__ import annotations
from typing import Optional


# ─── Card-flow primitives ─────────────────────────────────────────

def draw(gs, ctx, n: int = 1):
    """Draw N cards. If library empties, remaining draws are no-ops
    (no deck-out loss modeled yet)."""
    gs.zones.draw(n)
    gs._log(f"    primitive: draw({n})")


def mill(gs, ctx, n: int = 1, target: str = "self"):
    """Move top N of target's library to their graveyard."""
    g = _resolve_player(gs, ctx, target)
    if g is None:
        return
    for _ in range(n):
        if g.zones.library:
            card = g.zones.library.pop(0)
            g.zones.graveyard.append(card)
    gs._log(f"    primitive: mill({n}, {target})")


def scry(gs, ctx, n: int = 1):
    """Scry N. Goldfish: we don't actually reorder — flag it so future
    draws benefit (no-op for now)."""
    gs._log(f"    primitive: scry({n}) — goldfish no-op")


def discard(gs, ctx, n: int = 1, target: str = "opp", who_chooses: str = "controller"):
    """Make a player discard N cards. who_chooses='controller' means
    the caster picks; 'player' means random (here: highest-cmc)."""
    g = _resolve_player(gs, ctx, target)
    if g is None:
        return
    for _ in range(n):
        if not g.zones.hand:
            break
        victim = max(g.zones.hand, key=lambda c: getattr(c, 'cmc', 0))
        g.zones.hand.remove(victim)
        g.zones.graveyard.append(victim)
    gs._log(f"    primitive: discard({n}, {target})")


def look_top(gs, ctx, n: int = 1):
    """Look at top N of library — pure information; goldfish no-op."""
    gs._log(f"    primitive: look_top({n})")


# ─── Life primitives ──────────────────────────────────────────────

def gain_life(gs, ctx, n: int = 1):
    gs.life += n
    gs._log(f"    primitive: +{n} life (now {gs.life})")


def lose_life(gs, ctx, n: int = 1, target: str = "opp"):
    g = _resolve_player(gs, ctx, target)
    if g is None:
        return
    g.life -= n
    gs._log(f"    primitive: -{n} life to {target} (now {g.life})")


def damage_player(gs, ctx, n: int = 1, target: str = "opp"):
    """Deal N damage to target player (or self if target='self')."""
    if target == "opp":
        opp = getattr(gs, "_match_opp", None)
        if opp is not None:
            opp.life -= n
        gs.damage_dealt += n
    else:
        gs.life -= n
    gs._log(f"    primitive: damage_player({n}, {target})")


# ─── Damage primitives ───────────────────────────────────────────

def damage_creature(gs, ctx, n: int = 1, target: str = "opp_biggest"):
    """Deal N damage to a creature. Selection:
      - opp_biggest: opp's biggest creature
      - each_opp:    each opp creature (mini-wipe)
      - target:      ctx.chosen_target if set
    """
    from data.card import Tag
    from engine.match_state import safe_power, safe_toughness
    opp = getattr(gs, "_match_opp", None)
    if opp is None:
        return
    creatures = [c for c in opp.zones.battlefield
                  if not c.is_land() and c.has(Tag.CREATURE)]
    if not creatures:
        return
    if target == "each_opp":
        deaths = []
        for c in creatures:
            if n >= safe_toughness(c):
                deaths.append(c)
        for c in deaths:
            opp.zones.battlefield.remove(c)
            opp.zones.graveyard.append(c)
        gs._log(f"    primitive: {n} to each opp creature ({len(deaths)} die)")
        return
    # Single target — biggest
    tgt = ctx.get("chosen_target") or max(creatures, key=lambda c: safe_power(c))
    if n >= safe_toughness(tgt) and tgt in opp.zones.battlefield:
        opp.zones.battlefield.remove(tgt)
        opp.zones.graveyard.append(tgt)
        gs._log(f"    primitive: {n} dmg kills {tgt.name}")


def damage_any(gs, ctx, n: int = 1):
    """Deal N 'to any target'. Pick biggest opp creature if killable,
    else face."""
    from data.card import Tag
    from engine.match_state import safe_toughness
    opp = getattr(gs, "_match_opp", None)
    if opp is not None:
        creatures = [c for c in opp.zones.battlefield
                      if not c.is_land() and c.has(Tag.CREATURE)
                      and safe_toughness(c) <= n]
        if creatures:
            damage_creature(gs, ctx, n=n, target="opp_biggest")
            return
    # Fall through to face
    damage_player(gs, ctx, n=n, target="opp")


# ─── Removal primitives ──────────────────────────────────────────

def destroy(gs, ctx, target: str = "opp_biggest_creature"):
    """Destroy (to GY) a permanent."""
    from data.card import Tag
    from engine.match_state import safe_power
    opp = getattr(gs, "_match_opp", None)
    if opp is None:
        return
    pool = [c for c in opp.zones.battlefield
            if not c.is_land() and c.has(Tag.CREATURE)]
    if not pool:
        return
    tgt = ctx.get("chosen_target") or max(pool, key=lambda c: safe_power(c))
    if tgt in opp.zones.battlefield:
        opp.zones.battlefield.remove(tgt)
        opp.zones.graveyard.append(tgt)
        gs._log(f"    primitive: destroy {tgt.name}")


def exile(gs, ctx, target: str = "opp_biggest_creature"):
    """Exile a permanent."""
    from data.card import Tag
    from engine.match_state import safe_power
    opp = getattr(gs, "_match_opp", None)
    if opp is None:
        return
    pool = [c for c in opp.zones.battlefield
            if not c.is_land()]
    if not pool:
        return
    tgt = ctx.get("chosen_target") or max(pool, key=lambda c: safe_power(c)
                                           if c.has(Tag.CREATURE) else 3)
    if tgt in opp.zones.battlefield:
        opp.zones.battlefield.remove(tgt)
        opp.zones.exile.append(tgt)
        gs._log(f"    primitive: exile {tgt.name}")


def destroy_all_creatures(gs, ctx, max_toughness: Optional[int] = None):
    """Wrath. If max_toughness set, only kills creatures with
    effective_toughness <= max_toughness."""
    from data.card import Tag
    from engine.match_state import safe_toughness

    def _wipe(g):
        deaths = [c for c in list(g.zones.battlefield)
                  if c.has(Tag.CREATURE) and not c.is_land()
                  and (max_toughness is None
                       or safe_toughness(c) <= max_toughness)]
        for c in deaths:
            g.zones.battlefield.remove(c)
            g.zones.graveyard.append(c)
        return len(deaths)

    my = _wipe(gs)
    opp = getattr(gs, "_match_opp", None)
    opp_count = _wipe(opp) if opp else 0
    gs._log(f"    primitive: wrath (me {my}, opp {opp_count})")


def bounce_to_hand(gs, ctx, target: str = "opp_creature"):
    from data.card import Tag
    from engine.match_state import safe_power
    opp = getattr(gs, "_match_opp", None)
    if opp is None:
        return
    pool = [c for c in opp.zones.battlefield
            if not c.is_land() and c.has(Tag.CREATURE)]
    if not pool:
        return
    tgt = max(pool, key=lambda c: safe_power(c))
    opp.zones.battlefield.remove(tgt)
    opp.zones.hand.append(tgt)
    gs._log(f"    primitive: bounce {tgt.name} to hand")


# ─── Token primitives ────────────────────────────────────────────

def create_token(gs, ctx, name: str = "Token", power: str = "1",
                 toughness: str = "1",
                 type_line: str = "Token Creature",
                 count: int = 1, keywords: Optional[list] = None):
    from engine.keywords import KWTag
    kw_map = {
        "flying": KWTag.FLYING, "haste": KWTag.HASTE,
        "trample": KWTag.TRAMPLE, "menace": KWTag.MENACE,
        "deathtouch": KWTag.DEATHTOUCH, "lifelink": KWTag.LIFELINK,
        "first strike": KWTag.FIRST_STRIKE,
        "double strike": KWTag.DOUBLE_STRIKE,
        "vigilance": KWTag.VIGILANCE, "reach": KWTag.REACH,
        "prowess": KWTag.PROWESS,
    }
    for _ in range(count):
        tok = gs._make_token(name, power, toughness, type_line)
        for k in (keywords or []):
            tag = kw_map.get(k.lower())
            if tag:
                tok.tags.add(tag)
    gs._log(f"    primitive: +{count} {name} ({power}/{toughness})")


def create_treasure(gs, ctx, n: int = 1):
    for _ in range(n):
        gs.make_treasure_token()


# ─── Counter primitives ──────────────────────────────────────────

def add_counters(gs, ctx, n: int = 1, target: str = "self"):
    """Add +1/+1 counters."""
    if target == "self":
        tgt = ctx.get("source_card")
    elif target == "my_biggest":
        from data.card import Tag
        creatures = [c for c in gs.zones.battlefield
                      if not c.is_land() and c.has(Tag.CREATURE)]
        tgt = max(creatures, key=lambda c: c.effective_power()) if creatures else None
    else:
        tgt = ctx.get("chosen_target")
    if tgt is not None:
        tgt.counters = (tgt.counters or 0) + n
        gs._log(f"    primitive: +{n} counter on {tgt.name}")


# ─── Mana / ramp ─────────────────────────────────────────────────

def add_mana(gs, ctx, n: int = 1):
    gs.mana_pool.flex += n
    gs._log(f"    primitive: +{n} mana")


def search_basic_land(gs, ctx, n: int = 1, tapped: bool = True):
    """Ramp N basic lands. Simplified: +N flex mana (proxies land
    drop value without tracking the actual land card)."""
    gs.mana_pool.flex += n
    gs._log(f"    primitive: search {n} basic(s) (+{n} mana)")


# ─── Reanimator ──────────────────────────────────────────────────

def return_gy_to_bf(gs, ctx, filter_type: str = "creature",
                    pick: str = "biggest"):
    """Return a card from graveyard to battlefield."""
    from data.card import Tag
    pool = _filter_gy(gs, filter_type)
    if not pool:
        return
    if pick == "biggest":
        tgt = max(pool, key=lambda c: getattr(c, 'cmc', 0))
    else:
        tgt = pool[0]
    gs.zones.graveyard.remove(tgt)
    gs.zones.battlefield.append(tgt)
    tgt.turn_entered = gs.turn
    tgt.summoning_sickness = True
    tgt.tapped = False
    gs._log(f"    primitive: reanimate {tgt.name}")


def return_gy_to_hand(gs, ctx, filter_type: str = "creature",
                      pick: str = "biggest"):
    pool = _filter_gy(gs, filter_type)
    if not pool:
        return
    if pick == "biggest":
        tgt = max(pool, key=lambda c: getattr(c, 'cmc', 0))
    else:
        tgt = pool[0]
    gs.zones.graveyard.remove(tgt)
    gs.zones.hand.append(tgt)
    gs._log(f"    primitive: return {tgt.name} to hand")


# ─── Internal helpers ────────────────────────────────────────────

def _resolve_player(gs, ctx, target: str):
    if target == "self":
        return gs
    if target == "opp":
        return getattr(gs, "_match_opp", None)
    return None


def _filter_gy(gs, filter_type: str):
    from data.card import Tag
    gy = gs.zones.graveyard
    if filter_type == "creature":
        return [c for c in gy if c.has(Tag.CREATURE)]
    if filter_type == "instant_or_sorcery":
        return [c for c in gy if c.has(Tag.INSTANT) or c.has(Tag.SORCERY)]
    if filter_type == "enchantment":
        return [c for c in gy if "Enchantment" in (c.type_line or "")]
    if filter_type == "any":
        return list(gy)
    return list(gy)


# ─── Registry — string name → callable ───────────────────────────
# Exposed for the oracle parser, which emits effect-lists like
#   [("draw", {"n": 2}), ("damage_player", {"n": 3, "target": "opp"})]

PRIMITIVES = {
    "draw": draw,
    "mill": mill,
    "scry": scry,
    "discard": discard,
    "look_top": look_top,
    "gain_life": gain_life,
    "lose_life": lose_life,
    "damage_player": damage_player,
    "damage_creature": damage_creature,
    "damage_any": damage_any,
    "destroy": destroy,
    "exile": exile,
    "destroy_all_creatures": destroy_all_creatures,
    "bounce_to_hand": bounce_to_hand,
    "create_token": create_token,
    "create_treasure": create_treasure,
    "add_counters": add_counters,
    "add_mana": add_mana,
    "search_basic_land": search_basic_land,
    "return_gy_to_bf": return_gy_to_bf,
    "return_gy_to_hand": return_gy_to_hand,
}


def run_effects(gs, ctx, effects: list):
    """Execute a list of (primitive_name, kwargs) pairs sequentially."""
    for name, kwargs in effects:
        fn = PRIMITIVES.get(name)
        if fn is None:
            gs._log(f"    [WARN] unknown primitive: {name}")
            continue
        try:
            fn(gs, ctx, **(kwargs or {}))
        except Exception as e:
            gs._log(f"    [ERR] {name}({kwargs}): {e}")
