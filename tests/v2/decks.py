"""Pinned synthetic decks for engine v2 milestone one (spec section 9)."""


def _expand(spec):
    return [name for name, n in spec for _ in range(n)]


RG = _expand([("Mountain", 12), ("Forest", 8), ("Raging Goblin", 4), ("Grizzly Bears", 4), ("Hill Giant", 4),
              ("Lightning Bolt", 4), ("Giant Growth", 4)])
WU = _expand([("Plains", 10), ("Island", 10), ("Youthful Knight", 4), ("Wind Drake", 4), ("Serra Angel", 4),
              ("Counterspell", 4), ("Divination", 4)])
DECKOUT = _expand([("Island", 6), ("Divination", 4)])

# Test-only synthetic deck exercising the burn primitives (Lava Spike, Lightning Helix). Not a real list.
BURN_TEST = _expand([("Mountain", 12), ("Plains", 6), ("Lightning Bolt", 4), ("Lava Spike", 4),
                     ("Lightning Helix", 4), ("Raging Goblin", 4), ("Youthful Knight", 4), ("Hill Giant", 2)])

# Test-only synthetic deck for triggered abilities (S1). Not a real list.
TRIGGER_TEST = _expand([("Mountain", 14), ("Plains", 4), ("Monastery Swiftspear", 4), ("Goblin Guide", 4),
                        ("Lightning Bolt", 4), ("Lava Spike", 4), ("Lightning Helix", 4), ("Raging Goblin", 2)])

assert len(RG) == 40 and len(WU) == 40 and len(DECKOUT) == 10 and len(BURN_TEST) == 40
# Test-only synthetic deck for activated abilities / pain lands (S2). Not a real list.
ACTIVATED_TEST = _expand([("Mountain", 10), ("Plains", 4), ("Sunbaked Canyon", 4), ("Fiery Islet", 2),
                          ("Monastery Swiftspear", 4), ("Goblin Guide", 4), ("Lightning Bolt", 4),
                          ("Lava Spike", 4), ("Lightning Helix", 4)])

assert len(TRIGGER_TEST) == 40 and len(ACTIVATED_TEST) == 40
