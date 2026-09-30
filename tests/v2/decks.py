"""Pinned synthetic decks for engine v2 milestone one (spec section 9)."""


def _expand(spec):
    return [name for name, n in spec for _ in range(n)]


RG = _expand([("Mountain", 12), ("Forest", 8), ("Raging Goblin", 4), ("Grizzly Bears", 4), ("Hill Giant", 4),
              ("Lightning Bolt", 4), ("Giant Growth", 4)])
WU = _expand([("Plains", 10), ("Island", 10), ("Youthful Knight", 4), ("Wind Drake", 4), ("Serra Angel", 4),
              ("Counterspell", 4), ("Divination", 4)])
DECKOUT = _expand([("Island", 6), ("Divination", 4)])

assert len(RG) == 40 and len(WU) == 40 and len(DECKOUT) == 10
