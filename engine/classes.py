"""engine/classes.py -- Class enchantment mechanic.

Classes are enchantments with level-up activated abilities. They
enter at level 1; the controller can pay a level-up cost (sorcery
speed) to advance to the next level, each unlocking a new ability
until max level.

API:

  is_class(card) -> bool
      True when the card is a Class enchantment.

  class_etb(card, gs)
      Fire the Class's ETB effect (Level 1's triggered/static).

  level_up(card, gs) -> bool
      Pay the level-up cost and advance the Class by 1 level.
      Returns True on successful level-up. Called from main phase
      logic when the controller's APL wants to advance a Class.

  class_on_noncreature_spell(card, gs)
  class_on_instant_or_sorcery(card, gs)
      Triggered ability hooks fired by cast_spell when the relevant
      spell type resolves.

Registry shape per card:
  CLASS_DEFS = {
      'Card Name': {
          'etb':       (card, gs) -> None,     # Level 1 auto-ability
          'level_2_cost':  int,                 # mana to advance to 2
          'level_2_etb':   (card, gs) -> None,  # Level 2 trigger on advance
          'level_3_cost':  int,
          'level_3_etb':   (card, gs) -> None,
          'on_noncreature_spell': (card, gs) -> None,   # at any level
          'on_instant_or_sorcery_spell': (card, gs) -> None,  # gated by level
      },
  }

Levels are tracked via card.counters so the existing serialization
works without schema changes.
"""


def is_class(card) -> bool:
    tl = (getattr(card, "type_line", "") or "").lower()
    return "class" in tl and "enchantment" in tl


def _make_otter_token(gs):
    """Create a 1/1 U/R Otter creature token with prowess."""
    from engine.keywords import KWTag
    token = gs._make_token("Otter Token", "1", "1",
                           "Token Creature — Otter")
    token.tags.add(KWTag.PROWESS)
    # Tokens summoning-sick by default; Otter tokens don't have haste
    # intrinsically, so this matches the real rules.
    return token


# ── Class handlers ─────────────────────────────────────────────────

def _stormchaser_etb(card, gs):
    """Stormchaser's Talent ETB (Level 1): create a 1/1 Otter token
    with prowess."""
    _make_otter_token(gs)
    gs._log("  Stormchaser's Talent: created 1/1 Otter with prowess")


def _stormchaser_level_2(card, gs):
    """Level 2: return target instant/sorcery from graveyard to hand.
    Goldfish: grab the highest-cmc cheap damage/lesson spell from
    graveyard if any."""
    from data.card import Tag
    candidates = [
        c for c in gs.zones.graveyard
        if c.has(Tag.INSTANT) or c.has(Tag.SORCERY)
    ]
    if not candidates:
        return
    # Prefer Lesson cards (keep them in play for Gran-Gran synergy)
    lessons = [c for c in candidates
               if "lesson" in (c.type_line or "").lower()]
    pool = lessons or candidates
    pool.sort(key=lambda c: -(c.cmc or 0))
    target = pool[0]
    gs.zones.graveyard.remove(target)
    gs.zones.hand.append(target)
    gs._log(f"  Stormchaser's Talent Lv2: return {target.name}")


def _stormchaser_on_instant_or_sorcery(card, gs):
    """Level 3: whenever you cast an instant/sorcery, create a 1/1
    Otter with prowess."""
    if (card.counters or 0) < 3:
        return
    _make_otter_token(gs)
    gs._log("  Stormchaser's Talent Lv3: +1 Otter token")


def _artist_on_noncreature_spell(card, gs):
    """Artist's Talent Lv1 trigger: when you cast a noncreature spell,
    you may discard a card. If you do, draw a card. Goldfish always
    chooses to do it — cycles the deck."""
    if not gs.zones.hand:
        return
    # Discard the least-valuable card (highest-cmc land, or a dupe)
    discards = [c for c in gs.zones.hand if c.is_land()]
    victim = discards[-1] if discards else gs.zones.hand[-1]
    gs.zones.hand.remove(victim)
    gs.zones.graveyard.append(victim)
    gs.zones.draw(1)
    gs._log(f"  Artist's Talent: discard {victim.name}, draw 1")
    # Monument to Endurance triggers on this discard — fire via the
    # card-effect hook.
    from engine.card_effects import on_discard_event
    on_discard_event(gs, victim)


def _artist_level_3_bonus(card, gs):
    """Artist's Talent Lv3 static: noncombat damage to opp/perm +2.
    Set a flag on gs that damage helpers read."""
    gs._artist_noncombat_damage_bonus = 2


CLASS_DEFS = {
    "Stormchaser's Talent": {
        "etb":            _stormchaser_etb,
        "level_2_cost":   4,   # {3}{U}
        "level_3_cost":   6,   # {5}{U}
        "on_instant_or_sorcery_spell": _stormchaser_on_instant_or_sorcery,
    },
    "Artist's Talent": {
        "level_2_cost":   3,   # {2}{R}
        "level_3_cost":   3,   # {2}{R}
        "level_3_etb":    _artist_level_3_bonus,
        "on_noncreature_spell": _artist_on_noncreature_spell,
    },
}


def class_etb(card, gs):
    """Fire a Class's Level 1 ETB effect and mark the counter at 1."""
    if card.name not in CLASS_DEFS:
        return
    card.counters = 1   # level 1
    defn = CLASS_DEFS[card.name]
    fn = defn.get("etb")
    if fn:
        try:
            fn(card, gs)
        except Exception as e:
            gs._log(f"  Class {card.name} ETB error: {e}")


def level_up(card, gs) -> bool:
    """Try to advance `card` one level. Returns True on success.
    Called from APL main-phase logic when wanting to level up a Class."""
    if card.name not in CLASS_DEFS:
        return False
    current = card.counters or 1
    defn = CLASS_DEFS[card.name]
    next_level = current + 1
    cost_key = f"level_{next_level}_cost"
    etb_key = f"level_{next_level}_etb"
    if cost_key not in defn:
        return False   # already at max level
    cost = defn[cost_key]
    if gs.mana_pool.total() < cost:
        return False
    gs.mana_pool.flex = max(0, gs.mana_pool.flex - cost)
    card.counters = next_level
    gs._log(f"  {card.name}: level up to {next_level} (paid {cost})")
    fn = defn.get(etb_key)
    if fn:
        try:
            fn(card, gs)
        except Exception as e:
            gs._log(f"  Class {card.name} level {next_level} error: {e}")
    return True


def class_on_spell_cast(card_cast, gs):
    """Fire all Class on-cast triggers appropriate to the card type.
    Called from GameState.cast_spell after a spell resolves.

    card_cast is the spell that was just cast, not the Class itself.
    We iterate every Class on the battlefield and dispatch."""
    from data.card import Tag
    is_noncreature = not card_cast.has(Tag.CREATURE)
    is_instant_or_sorcery = card_cast.has(Tag.INSTANT) or card_cast.has(Tag.SORCERY)
    for perm in list(gs.zones.battlefield):
        if not is_class(perm):
            continue
        defn = CLASS_DEFS.get(perm.name)
        if not defn:
            continue
        if is_noncreature:
            fn = defn.get("on_noncreature_spell")
            if fn:
                try:
                    fn(perm, gs)
                except Exception as e:
                    gs._log(f"  Class {perm.name} on-noncreature error: {e}")
        if is_instant_or_sorcery:
            fn = defn.get("on_instant_or_sorcery_spell")
            if fn:
                try:
                    fn(perm, gs)
                except Exception as e:
                    gs._log(f"  Class {perm.name} on-i/s error: {e}")
