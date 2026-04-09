"""Verify CardDB fix — should now return real game card data."""
from engine.card_db import CardDB
db = CardDB()

test_cards = ["Emberheart Challenger", "Hired Claw", "Razorkin Needlehead",
              "Soulstone Sanctuary", "Copperline Gorge", "Heartfire Hero",
              "Manifold Mouse", "Innkeeper's Talent", "Questing Druid",
              "Monstrous Rage"]

for name in test_cards:
    card = db.get(name)
    if card:
        mc = card.get("mana_cost", "")
        tl = card.get("type_line", "")
        st = card.get("set_type", "")
        pw = card.get("power", "")
        th = card.get("toughness", "")
        ok = "OK" if mc or tl != "Card" else "BAD"
        print(f"  {ok}  {name:<30} {mc:<10} {tl:<35} P/T={pw}/{th}  set_type={st}")
    else:
        print(f"  MISS {name}")
