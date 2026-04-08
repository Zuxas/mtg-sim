"""
data/stub_decks.py — Minimal playable decks for archetypes without playbooks

Used by the both-sides sim when no real decklist exists.
These are simplified proxies that play correctly enough to generate
directionally accurate win rates. Not perfect, but far better than skipping.
"""

from data.card import Card
from engine.card_db import CardDB

_db = None


def _card(name: str) -> Card:
    global _db
    if _db is None:
        _db = CardDB()
    data = _db.get(name)
    if data:
        return Card(
            name=data.get("name", name),
            mana_cost=data.get("mana_cost", ""),
            cmc=float(data.get("cmc", 2)),
            type_line=data.get("type_line", "Creature"),
            oracle_text=data.get("oracle_text", ""),
            power=data.get("power"),
            toughness=data.get("toughness"),
            colors=data.get("colors", []),
        )
    # Fallback minimal card
    return Card(name=name, mana_cost="{1}", cmc=1,
                type_line="Creature", oracle_text="",
                power="1", toughness="1", colors=[])


def _land(name: str, color: str = "W") -> Card:
    return Card(name=name, mana_cost="", cmc=0,
                type_line="Land", oracle_text="",
                power=None, toughness=None, colors=[])


def _make_deck(creatures: list, lands: list) -> list:
    """Build a 60-card deck from creature and land lists."""
    deck = []
    for qty, name in creatures:
        for _ in range(qty):
            deck.append(_card(name))
    for qty, name in lands:
        for _ in range(qty):
            deck.append(_land(name))
    return deck


# ---------------------------------------------------------------------------
# Stub decklists — minimal proxies for archetype behavior
# ---------------------------------------------------------------------------

STUB_DECKS = {
    # Legacy combo — modeled as fast goldfish with cheap spells
    "dimir reanimator": lambda: _make_deck([
        (4, "Faithless Looting"), (4, "Entomb"), (4, "Animate Dead"),
        (4, "Reanimate"), (4, "Griselbrand"), (4, "Force of Will"),
        (4, "Thoughtseize"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Dark Ritual"), (4, "Lotus Petal"),
    ], [(11, "Swamp"), (7, "Island")]),

    "lotus combo": lambda: _make_deck([
        (4, "Brainstorm"), (4, "Ponder"), (4, "Hidden Strings"),
        (4, "Vizier of Tumbling Sands"), (4, "Crop Rotation"),
        (4, "Explore"), (4, "Cultivate"), (4, "Bala Ged Recovery"),
        (4, "Sylvan Scrying"),
    ], [(12, "Forest"), (7, "Island"), (4, "Lotus Field"), (3, "Thespian's Stage")]),

    "dimir tempo": lambda: _make_deck([
        (4, "Delver of Secrets"), (4, "Dragon's Rage Channeler"),
        (4, "Murktide Regent"), (4, "Force of Will"), (4, "Daze"),
        (4, "Lightning Bolt"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Thoughtseize"),
    ], [(7, "Island"), (7, "Swamp"), (4, "Wasteland"), (6, "Volcanic Island")]),

    "cephalid breakfast": lambda: _make_deck([
        (4, "Cephalid Illusionist"), (4, "Narcomoeba"),
        (4, "Cabal Therapy"), (4, "Force of Will"), (4, "Brainstorm"),
        (4, "Ponder"), (4, "Lotus Petal"), (4, "Hapless Researcher"),
        (4, "Dread Return"),
    ], [(11, "Island"), (7, "Swamp"), (4, "Plains")]),

    "eldrazi stompy": lambda: _make_deck([
        (4, "Chalice of the Void"), (4, "Thought-Knot Seer"),
        (4, "Reality Smasher"), (4, "Eldrazi Mimic"),
        (4, "Matter Reshaper"), (4, "Warping Wail"),
        (4, "Dismember"), (4, "Trinisphere"),
    ], [(4, "Ancient Tomb"), (4, "City of Traitors"), (4, "Eye of Ugin"),
        (8, "Wastes"), (4, "Eldrazi Temple")]),

    "sneak and show": lambda: _make_deck([
        (4, "Emrakul, the Aeons Torn"), (4, "Griselbrand"),
        (4, "Show and Tell"), (4, "Sneak Attack"),
        (4, "Force of Will"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Lotus Petal"), (4, "Ancient Tomb"),
    ], [(8, "Island"), (4, "Mountain"), (4, "Volcanic Island"), (4, "City of Traitors")]),

    "mono red painter": lambda: _make_deck([
        (4, "Painter's Servant"), (4, "Grindstone"),
        (4, "Goblin Engineer"), (4, "Imperial Recruiter"),
        (4, "Pyroblast"), (4, "Red Elemental Blast"),
        (4, "Blood Moon"), (4, "Chalice of the Void"),
    ], [(4, "Ancient Tomb"), (4, "City of Traitors"), (4, "Great Furnace"),
        (12, "Mountain")]),

    "doomsday": lambda: _make_deck([
        (4, "Doomsday"), (4, "Thassa's Oracle"), (4, "Dark Ritual"),
        (4, "Force of Will"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Gitaxian Probe"), (4, "Lotus Petal"),
        (4, "Counterspell"),
    ], [(10, "Island"), (6, "Swamp"), (4, "Underground Sea")]),

    "izzet delver": lambda: _make_deck([
        (4, "Delver of Secrets"), (4, "Dragon's Rage Channeler"),
        (4, "Murktide Regent"), (4, "Force of Will"), (4, "Daze"),
        (4, "Lightning Bolt"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Pyroblast"),
    ], [(8, "Island"), (4, "Mountain"), (4, "Volcanic Island"), (4, "Wasteland")]),

    "death and taxes": lambda: _make_deck([
        (4, "Thalia, Guardian of Thraben"), (4, "Flickerwisp"),
        (4, "Recruiter of the Guard"), (4, "Mother of Runes"),
        (4, "Phyrexian Revoker"), (4, "Swords to Plowshares"),
        (4, "Solitude"), (4, "Aether Vial"),
    ], [(4, "Karakas"), (4, "Wasteland"), (4, "Rishadan Port"), (12, "Plains")]),

    "bant nadu": lambda: _make_deck([
        (4, "Nadu, Winged Wisdom"), (4, "Arboreal Grazer"),
        (4, "Noble Hierarch"), (4, "Birds of Paradise"),
        (4, "Force of Will"), (4, "Brainstorm"), (4, "Crop Rotation"),
        (4, "Shuko"), (4, "Dryad Arbor"),
    ], [(6, "Forest"), (4, "Island"), (4, "Plains"),
        (4, "Tropical Island"), (4, "Savannah")]),

    "four-color": lambda: _make_deck([
        (4, "Ragavan, Nimble Pilferer"), (4, "Dragon's Rage Channeler"),
        (4, "Force of Will"), (4, "Swords to Plowshares"),
        (4, "Brainstorm"), (4, "Ponder"), (4, "Expressive Iteration"),
        (4, "Prismatic Ending"), (4, "Murktide Regent"),
    ], [(4, "Island"), (4, "Plains"), (4, "Volcanic Island"),
        (4, "Tundra"), (4, "Wasteland"), (4, "Flooded Strand")]),

    "jeskai control": lambda: _make_deck([
        (4, "Force of Will"), (4, "Counterspell"), (4, "Swords to Plowshares"),
        (4, "Terminus"), (4, "Brainstorm"), (4, "Ponder"),
        (4, "Snapcaster Mage"), (4, "Monastery Mentor"),
        (4, "Jace, the Mind Sculptor"),
    ], [(6, "Island"), (4, "Plains"), (4, "Mountain"),
        (4, "Tundra"), (4, "Volcanic Island"), (2, "Plateau")]),

    "mono red aggro": lambda: _make_deck([
        (4, "Goblin Guide"), (4, "Eidolon of the Great Revel"),
        (4, "Chain Lightning"), (4, "Lightning Bolt"),
        (4, "Monastery Swiftspear"), (4, "Price of Progress"),
        (4, "Fireblast"), (4, "Rift Bolt"), (4, "Searing Blaze"),
    ], [(12, "Mountain"), (4, "Bloodstained Mire")]),

    "mono red prison": lambda: _make_deck([
        (4, "Blood Moon"), (4, "Magus of the Moon"),
        (4, "Goblin Rabblemaster"), (4, "Seasoned Pyromancer"),
        (4, "Pyroblast"), (4, "Chalice of the Void"),
        (4, "Trinisphere"), (4, "Ensnaring Bridge"),
    ], [(4, "Ancient Tomb"), (4, "City of Traitors"), (12, "Mountain")]),
}


def get_stub_deck(archetype_name: str) -> list:
    """Get a stub deck for an archetype. Returns None if not found."""
    key = archetype_name.lower().replace(" ", "").replace("-", "").replace("'", "")
    for stub_key, builder in STUB_DECKS.items():
        if stub_key.replace(" ", "").replace("-", "") == key:
            return builder()
    # Partial match
    for stub_key, builder in STUB_DECKS.items():
        sk = stub_key.replace(" ", "")
        if sk in key or key in sk:
            return builder()
    return None
