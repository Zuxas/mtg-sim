"""Team Resolve sideboard plans parsed from playbook HTML files.
Format: {(our_deck, opponent): ([sb_in], [sb_out])}
"""

SB_PLANS = {
    ("Boros Energy", "Amulet Titan"): (['1 Blood Moon', '1 Meltdown', '2 Obsidian Charmaw'], ['2 Voice of Victory', '2 Thraben Charm']),
    ("Boros Energy", "Boros Energy Mirror"): (['2 Celestial Purge', '1 Blood Moon', '2 Wear // Tear'], ['2 Voice of Victory', '2 Thraben Charm', '1 Ranger-Captain of Eos']),
    ("Boros Energy", "Domain Zoo"): (['1 Surgical Extraction', '2 Celestial Purge'], ['2 Voice of Victory', '1 Thraben Charm']),
    ("Boros Energy", "Eldrazi Tron"): (['2 Wear // Tear', '1 Meltdown'], ['2 Voice of Victory', '1 Thraben Charm']),
    ("Boros Energy", "Esper Reanimator"): (['2 Celestial Purge', '1 Surgical Extraction'], ['2 Voice of Victory', '1 Thraben Charm']),
    ("Boros Energy", "Grixis Reanimator"): (['1 Surgical Extraction', '2 Celestial Purge'], ['2 Thraben Charm', '1 Voice of Victory']),
    ("Boros Energy", "Izzet Affinity"): (['2 Meltdown', '2 Wear // Tear'], ['2 Voice of Victory', '2 Thraben Charm']),
    ("Boros Energy", "Izzet Prowess"): (['1 High Noon', "1 Orim's Chant", '1 Wrath of the Skies', '2 Celestial Purge'], ['4 Ragavan, Nimble Pilferer', '1 Voice of Victory']),
    ("Boros Energy", "Ruby Storm"): (['1 High Noon', "1 Orim's Chant", '2 Celestial Purge'], ['2 Voice of Victory', '2 Thraben Charm']),
    ("Boros Energy", "UW / Jeskai Blink"): (['1 Wrath of the Skies', '2 Celestial Purge'], ['1 Thraben Charm', '2 Voice of Victory']),
    ("Boros Energy", "UW Control"): (['2 Wear // Tear', '2 The Legend of Roku'], ['2 Voice of Victory', '2 Thraben Charm']),
    ("Glockulous", "Amulet Titan"): (['2 Harbinger of the Seas', '2 Surgical Extraction', '1 Blood Moon'], ['2 Thought Scour', '1 Troll of Khazad-dûm−2\n        Unearth']),
    ("Glockulous", "Azorius Control"): (['3 Mystical Dispute', '2 Spell Pierce', '2 Drown in the Loch'], ['3 Thought Scour', '2 Troll of Khazad-dûm', '2 Fatal Push']),
    ("Glockulous", "Boros Energy"): (['3 Nihil Spellbomb', '2 Mystical Dispute', '2 Harbinger of the Seas'], ['3 Thought Scour', '2 Unearth', '2 Troll of Khazad-dûm']),
    ("Glockulous", "Domain Zoo"): (['3 Harbinger of the Seas', '2 Pyroclasm'], ['2 Persist', '2 Unearth', '1 Emperor of Bones']),
    ("Glockulous", "Eldrazi Tron"): (['2 Nihil Spellbomb', '2 Harvester of Misery'], ['2 Thought Scour', '2 Unearth']),
    ("Glockulous", "Esper Reanimator"): (['2 Nihil Spellbomb', '2 Surgical Extraction'], ['2 Unearth', '2 Thought Scour']),
    ("Glockulous", "Grixis Reanimator"): (['3 Nihil Spellbomb', '2 Surgical Extraction'], ['2 Troll of Khazad-dûm', '2 Faithless Looting', '1 Thought Scour']),
    ("Glockulous", "Izzet Affinity"): (['2 Harvester of Misery', '2 Pyroclasm'], ['2 Unearth', '2 Thought Scour']),
    ("Glockulous", "Izzet Prowess"): (['2 Drown in the Loch', '2 Nihil Spellbomb'], ['2 Unearth', '2 Troll of Khazad-dûm']),
    ("Glockulous", "Jeskai Blink"): (['3 Mystical Dispute', '2 Spell Pierce', '2 Harbinger of the Seas', '2 Drown in the Loch'], ['4 Thought Scour', '2 Troll of Khazad-dûm', '2 Unearth', '1 Faithless Looting']),
    ("Glockulous", "Ruby Storm"): (['2 Nihil Spellbomb', '2 Harvester of Misery'], ['2 Unearth', '2 Emperor of Bones']),
    ("Izzet Affinity", "Amulet Titan"): (['2 Consign to Memory', '1 Damping Sphere'], ["2 Tormod's Crypt", '1 Welding Jar']),
    ("Izzet Affinity", "Azorius Control"): (['2 Mystical Dispute', '1 Force of Negation', '2 Blood Moon'], ["3 Tormod's Crypt", '2 Damping Sphere']),
    ("Izzet Affinity", "Boros Energy"): (['2 Whipflare'], ["2 Tormod's Crypt"]),
    ("Izzet Affinity", "Domain Aggro"): (['2 Whipflare', '2 Galvanic Blast'], ["2 Tormod's Crypt", '2 Damping Sphere']),
    ("Izzet Affinity", "Eldrazi Tron"): (['3 Blood Moon', '2 Damping Sphere'], ["3 Tormod's Crypt", '2 Claws of Gix']),
    ("Izzet Affinity", "Esper Reanimator"): (["1 Grafdigger's Cage", '2 Consign to Memory'], ['2 Claws of Gix', '1 Welding Jar']),
    ("Izzet Affinity", "Grixis Reanimator"): (['2 Galvanic Blast', "1 Grafdigger's Cage"], ['2 Claws of Gix', '1 Welding Jar']),
    ("Izzet Affinity", "Izzet Affinity Mirror"): (['2 Galvanic Blast', '2 Mystical Dispute'], ["2 Tormod's Crypt", '2 Damping Sphere']),
    ("Izzet Affinity", "Izzet Prowess"): (['2 Galvanic Blast', '2 Whipflare'], ["2 Tormod's Crypt", '2 Claws of Gix']),
    ("Izzet Affinity", "Jeskai Blink"): (['3 Blood Moon', '2 Mystical Dispute'], ["3 Tormod's Crypt", '2 Claws of Gix']),
    ("Izzet Affinity", "Ruby Storm"): (['3 Damping Sphere', '1 Force of Negation', '2 Consign to Memory'], ["3 Tormod's Crypt", '2 Claws of Gix', '1 Welding Jar']),
    ("Izzet Prowess", "Amulet Titan"): (['4 Consign to Memory', '2 Blood Moon'], ['2 Violent Urge', '2 Preordain', '2 Murktide Regent']),
    ("Izzet Prowess", "Azorius Control"): (['4 Consign to Memory', '1 Spell Pierce', '2 Spell Snare'], ['2 Violent Urge', '3 Lava Dart', '2 Mutagenic Growth']),
    ("Izzet Prowess", "Boros Energy"): (['4 Unholy Heat', '1 Surgical Extraction'], ['2 Preordain', '2 Murktide Regent', '1 Violent Urge']),
    ("Izzet Prowess", "Domain Zoo"): (['2 Dress Down', '1 Surgical Extraction'], ['2 Gut Shot', '1 Sleight of Hand']),
    ("Izzet Prowess", "Eldrazi Tron"): (['2 Surgical Extraction', '2 Blood Moon'], ['2 Gut Shot', '2 Sleight of Hand']),
    ("Izzet Prowess", "Esper Reanimator"): (['2 Surgical Extraction'], ['2 Gut Shot']),
    ("Izzet Prowess", "Grixis Reanimator"): (['1 Surgical Extraction', '2 Blood Moon'], ['2 Preordain', '1 Violent Urge']),
    ("Izzet Prowess", "Izzet Affinity"): (['2 Blood Moon'], ['2 Gut Shot']),
    ("Izzet Prowess", "Jeskai Blink"): (['4 Consign to Memory', '2 Spell Snare', '2 Unholy Heat'], ['2 Violent Urge', '2 Lava Dart', '2 Preordain', '2 Murktide Regent']),
    ("Izzet Prowess", "Prowess Mirror"): (['4 Unholy Heat', '2 Spell Snare'], ['2 Violent Urge', '2 Mutagenic Growth', '2 Preordain']),
    ("Izzet Prowess", "Ruby Storm"): (['2 Blood Moon'], ['2 Gut Shot']),
    ("Jeskai Blink", "Amulet Titan"): (['1 Consign to Memory', '2 Teferi, Time Raveler', '1 Pithing Needle', '1 Stony Silence'], ['2 Rest in Peace', '1 Sanctifier en-Vec (main)', '2 Ocelot Pride']),
    ("Jeskai Blink", "Azorius Control"): (['2 Teferi, Time Raveler', '1 Vexing Bauble', '1 Pithing Needle'], ['2 Rest in Peace', '1 Sanctifier en-Vec (main)', '1 Witch Enchanter']),
    ("Jeskai Blink", "Blink Mirror"): (['2 Teferi, Time Raveler', '1 Consign to Memory', '1 Pithing Needle', '1 Mockingbird'], ['2 Rest in Peace', '1 Sanctifier en-Vec (main)', '1 Witch Enchanter', '1 Ocelot Pride']),
    ("Jeskai Blink", "Boros Energy"): (['2 Sanctifier en-Vec', '2 Wrath of the Skies', '1 Teferi, Time Raveler'], ['2 Consign to Memory', '2 Quantum Riddler', '1 Witch Enchanter']),
    ("Jeskai Blink", "Domain Zoo"): (['2 Consign to Memory', '1 Stony Silence'], ['2 Quantum Riddler', '1 Mockingbird']),
    ("Jeskai Blink", "Eldrazi Tron"): (['2 Consign to Memory', '1 Pithing Needle'], ['2 Quantum Riddler', '1 Mockingbird']),
    ("Jeskai Blink", "Esper Reanimator"): (['2 Rest in Peace', '2 Consign to Memory'], ['2 Quantum Riddler', '2 Mockingbird']),
    ("Jeskai Blink", "Grixis Reanimator"): (['1 Consign to Memory', '2 Rest in Peace', '2 Sanctifier en-Vec', '2 Teferi, Time Raveler', '1 Mistcaller'], ['2 Witch Enchanter', '2 Quantum Riddler', '2 Starfield Shepherd', '2 Ocelot Pride']),
    ("Jeskai Blink", "Izzet Affinity"): (['2 Stony Silence', '2 Consign to Memory'], ['2 Quantum Riddler', '2 Mockingbird']),
    ("Jeskai Blink", "Izzet Prowess"): (['2 Sanctifier en-Vec', '2 Wrath of the Skies', "1 Orim's Chant", '1 Teferi, Time Raveler'], ['2 Consign to Memory', '2 Quantum Riddler', '1 Witch Enchanter', '1 Starfield Shepherd']),
    ("Jeskai Blink", "Ruby Storm"): (['3 Consign to Memory', '1 Rest in Peace'], ['2 Quantum Riddler', '2 Mockingbird']),
    ("UW Control", "Amulet Titan"): (['3 Consign to Memory', '1 Rest in Peace'], ['2 Wrath of the Skies (main x2)', '1 Spell Snare', '1 Tune the Narrative']),
    ("UW Control", "Boros Energy"): (['2 Wrath of the Skies (SB x2)', '1 Celestial Purge'], ['1 Force of Negation', "1 Day's Undoing", '1 Lórien Revealed']),
    ("UW Control", "Domain Zoo"): (['2 Wrath of the Skies (SB)', '2 Wrath of the Skies'], ['2 Force of Negation', '2 Spell Snare']),
    ("UW Control", "Eldrazi Tron"): (['3 Consign to Memory'], ['2 Spell Snare', '1 Tune the Narrative']),
    ("UW Control", "Esper Reanimator"): (['2 Rest in Peace', '3 Consign to Memory'], ['2 Supreme Verdict', '2 Spell Snare', '1 Wrath of the Skies']),
    ("UW Control", "Glockulous"): (['2 Rest in Peace', '3 Consign to Memory'], ['2 Supreme Verdict', '2 Spell Snare', '1 Wrath of the Skies (main)']),
    ("UW Control", "Izzet Affinity"): (['3 Consign to Memory', '2 Wrath of the Skies (SB x2)'], ['2 Spell Snare', '2 Supreme Verdict', "1 Day's Undoing"]),
    ("UW Control", "Izzet Prowess"): (['2 Wrath of the Skies (SB x2)', '1 Celestial Purge'], ['1 Force of Negation', "1 Day's Undoing", '1 Lórien Revealed']),
    ("UW Control", "Jeskai Blink"): (['2 Mystical Dispute', '2 Wrath of the Skies (SB)', '1 Vendilion Clique'], ["1 Day's Undoing", '1 Lórien Revealed', '2 Tune the Narrative', '1 Force of Negation']),
    ("UW Control", "Ruby Storm"): (['2 Consign to Memory', '2 Consign to Memory', '1 Tamiyo, Inquisitive Student'], ['2 Supreme Verdict', '2 Tune the Narrative', '1 Solitude']),
    ("UW Control", "UW Control Mirror"): (['2 Mystical Dispute', '1 Vendilion Clique'], ['2 Wrath of the Skies (main x2)', '1 Tune the Narrative']),
}


def get_tr_sb_plan(our_deck: str, opponent: str):
    """Look up a Team Resolve SB plan. Returns (sb_in_list, sb_out_list) or ([], [])."""
    import re
    our_clean = re.sub(r'[^a-z0-9]', '', our_deck.lower())
    opp_clean = re.sub(r'[^a-z0-9]', '', opponent.lower())
    for (deck, opp), plan in SB_PLANS.items():
        dk = re.sub(r'[^a-z0-9]', '', deck.lower())
        op = re.sub(r'[^a-z0-9]', '', opp.lower())
        if our_clean in dk or dk in our_clean:
            if opp_clean in op or op in opp_clean:
                return plan
    return ([], [])
