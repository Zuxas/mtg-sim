"""test_card_resolution.py -- issue #27.

Three silent failures in card lookup, tested without network or card data:
1. Scryfall fallback keyed results by canonical name, so double-faced cards
   ("Front // Back") and differently-cased names came back as blank Cards.
2. CardDB.get matched any substring in either direction, so an unknown name
   resolved to an unrelated card.
3. A name with no data silently became a blank Card.
"""
import sys, os, io, contextlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import scryfall_client, deck
from engine.card_db import CardDB

AJANI = {"name": "Ajani, Nacatl Pariah // Ajani, Nacatl Avenger", "cmc": 2.0,
         "type_line": "Legendary Creature - Cat Warrior // Legendary Planeswalker - Ajani",
         "color_identity": ["R", "W"], "id": "x1",
         "card_faces": [
             {"name": "Ajani, Nacatl Pariah", "mana_cost": "{1}{W}", "power": "1",
              "toughness": "2", "oracle_text": "front", "colors": ["W"],
              "type_line": "Legendary Creature - Cat Warrior"},
             {"name": "Ajani, Nacatl Avenger", "mana_cost": "", "loyalty": "3",
              "oracle_text": "back", "type_line": "Legendary Planeswalker - Ajani"}]}
BOLT = {"name": "Lightning Bolt", "mana_cost": "{R}", "cmc": 1.0, "type_line": "Instant",
        "oracle_text": "3 damage", "colors": ["R"], "color_identity": ["R"], "id": "x2"}
WEAR = {"name": "Wear // Tear", "mana_cost": "{1}{R} // {W}", "cmc": 3.0,
        "type_line": "Instant // Instant", "colors": ["R", "W"], "id": "x3",
        "card_faces": [{"name": "Wear", "mana_cost": "{1}{R}", "type_line": "Instant"},
                       {"name": "Tear", "mana_cost": "{W}", "type_line": "Instant"}]}


class _FakeResponse:
    def __init__(self, cards): self._cards = cards
    def raise_for_status(self): pass
    def json(self): return {"data": self._cards}


def _with_fake_scryfall(cards, fn):
    sent = []

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.extend(i["name"] for i in json["identifiers"])
        return _FakeResponse(cards)
    real = scryfall_client.requests.post
    scryfall_client.requests.post = fake_post
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(), sent
    finally:
        scryfall_client.requests.post = real


def test_dfc_is_found_by_front_face_and_fully_populated():
    data, _ = _with_fake_scryfall([AJANI], lambda: scryfall_client.get_cards_data(
        ["Ajani, Nacatl Pariah"]))
    c = data["Ajani, Nacatl Pariah"]
    assert (c["mana_cost"], c["power"], c["toughness"]) == ("{1}{W}", "1", "2"), c
    assert c["type_line"] == "Legendary Creature - Cat Warrior", c["type_line"]
    assert len(c["card_faces"]) == 2


def test_back_face_name_does_not_resolve_to_the_front_face():
    data, _ = _with_fake_scryfall([AJANI], lambda: scryfall_client.get_cards_data(
        ["Ajani, Nacatl Avenger"]))
    assert "Ajani, Nacatl Avenger" not in data, data.keys()


def test_lookup_is_case_insensitive_and_accepts_slash_spellings():
    data, sent = _with_fake_scryfall([BOLT, WEAR], lambda: scryfall_client.get_cards_data(
        ["lightning bolt", "Wear / Tear"]))
    assert data["lightning bolt"]["type_line"] == "Instant"
    assert data["Wear / Tear"]["mana_cost"] == "{1}{R} // {W}"
    assert "Wear" in sent and "Wear / Tear" not in sent, sent


def test_unknown_name_raises_and_names_the_card():
    os.environ.pop("MTG_SIM_ALLOW_UNRESOLVED", None)
    known = {"Lightning Bolt": {"name": "Lightning Bolt", "type_line": "Instant", "cmc": 1}}
    try:
        deck._build_cards([(4, "Lightning Bolt"), (1, "Lightnign Bolt")], known)
        raise AssertionError("expected UnresolvedCardError")
    except deck.UnresolvedCardError as e:
        assert "Lightnign Bolt" in str(e) and "'Lightning Bolt'" not in str(e), str(e)


def test_override_loads_blank_cards_with_a_warning():
    os.environ["MTG_SIM_ALLOW_UNRESOLVED"] = "1"
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cards = deck._build_cards([(2, "Lightnign Bolt")], {})
        assert len(cards) == 2 and "UNRESOLVED" in out.getvalue()
    finally:
        del os.environ["MTG_SIM_ALLOW_UNRESOLVED"]


def test_carddb_does_not_match_on_substrings():
    db = CardDB.__new__(CardDB)
    db._loaded = True
    ow = {"name": "Ow"}
    fable = {"name": "Fable of the Mirror-Breaker // Reflection of Kiki-Jiki"}
    stomp_a, stomp_b = {"name": "Stomping Ground"}, {"name": "Stomping Slabs"}
    db._by_name = {CardDB._norm(c["name"]): c for c in (ow, fable, stomp_a, stomp_b)}
    assert db.get("Shadow of the Goblin") is None          # 'ow' is a substring
    assert db.get("ow") is ow                              # exact still works
    assert db.get("Fable of the Mirror") is fable          # unique prefix, long enough
    assert db.get("Stomping") is None                      # ambiguous prefix
    assert db.get("Fable") is None                         # too short to trust


def test_scryfall_client_works_without_requests():
    """`requests` is only for the network fallback. Without it installed the
    module must still import (sim.py could not start on the CI runner) and a
    lookup just finds nothing."""
    import data.scryfall_client as client
    real = client.requests
    client.requests = None
    try:
        assert client.get_cards_data(["Lightning Bolt"]) == {}
    finally:
        client.requests = real


def test_arena_names_load_as_the_paper_card():
    main, side = deck._parse_decklist("4 Kavaero, Mind-Bitten\n1 Lightning Bolt\nSideboard\n2 Detect Intrusion\n")
    assert main == [(4, "Superior Spider-Man"), (1, "Lightning Bolt")], main
    assert side == [(2, "Spider-Sense")], side


class _EmptyDB:
    _loaded = False
    def get(self, name): return None


class _BoltDB:
    _loaded = True
    def get(self, name): return BOLT if name == "Lightning Bolt" else None


def _with_db(db, fn):
    import engine.card_db as card_db
    real = card_db.CardDB
    card_db.CardDB = lambda *a, **k: db
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return fn()
    finally:
        card_db.CardDB = real


def test_missing_local_data_is_an_error_not_an_api_call():
    os.environ.pop("MTG_SIM_ALLOW_NETWORK", None)
    calls = []
    real = deck.get_cards_data
    deck.get_cards_data = lambda names: calls.append(names) or {}
    try:
        try:
            _with_db(_EmptyDB(), lambda: deck._get_cards_local(["Lightning Bolt"]))
            raise AssertionError("expected FileNotFoundError")
        except FileNotFoundError as e:
            assert "fetch_scryfall_bulk.sh" in str(e)
        # a name the local file lacks is left out, not looked up online
        got = _with_db(_BoltDB(), lambda: deck._get_cards_local(["Lightning Bolt", "Nope"]))
        assert list(got) == ["Lightning Bolt"] and calls == [], (got, calls)
        # opting in restores the API fallback for missing names
        os.environ["MTG_SIM_ALLOW_NETWORK"] = "1"
        _with_db(_BoltDB(), lambda: deck._get_cards_local(["Lightning Bolt", "Nope"]))
        assert calls == [["Nope"]], calls
    finally:
        deck.get_cards_data = real
        os.environ.pop("MTG_SIM_ALLOW_NETWORK", None)


if __name__ == "__main__":
    test_dfc_is_found_by_front_face_and_fully_populated()
    test_back_face_name_does_not_resolve_to_the_front_face()
    test_lookup_is_case_insensitive_and_accepts_slash_spellings()
    test_unknown_name_raises_and_names_the_card()
    test_override_loads_blank_cards_with_a_warning()
    test_carddb_does_not_match_on_substrings()
    test_scryfall_client_works_without_requests()
    test_arena_names_load_as_the_paper_card()
    test_missing_local_data_is_an_error_not_an_api_call()
    print("test_card_resolution: OK")
