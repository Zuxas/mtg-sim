# Keyword tag audit (issue #17), 2026-11-18

Cards in `decks/` whose keyword-ability tags change when a keyword is tagged only
if it is the card's own ability (a keyword line, or "this creature has ..."), not
when the card grants it to something else or only mentions it.

1,052 distinct card names checked against the live Scryfall API. 119 change: 40 creatures and 79 non-creatures. Every change is a tag removed; no card gains a tag.

## Creatures

| Card | Tags removed |
|---|---|
| Absolute Virtue | protection |
| Agonasaur Rex | indestructible |
| Ardyn, the Usurper | haste, lifelink, menace |
| Badgermole Cub | haste |
| Coppercoat Vanguard | ward |
| Craterhoof Behemoth | trample |
| Dark Leo & Shredder | deathtouch |
| Drake Hatcher | flying |
| Emperor of Bones | haste |
| Expressive Firedancer | double_strike |
| Fleeting Spirit | first_strike |
| Greasefang, Okiba Boss | haste |
| Guardian of New Benalia | indestructible |
| Guide of Souls | flying |
| Hardened Academic | lifelink |
| Inti, Seneschal of the Sun | trample |
| Iron-Shield Elf | indestructible |
| Jirina, Dauntless General | hexproof, indestructible |
| Kellan, Planar Trailblazer | double_strike |
| Leatherhead, Swamp Stalker | hexproof |
| Nev, the Practical Dean | trample |
| Overlord of the Mistmoors | flying |
| Pinnacle Emissary | flying |
| Preacher of the Schism | lifelink |
| Psychic Frog | flying |
| Ragavan, Nimble Pilferer | haste |
| Regal Caracal | lifelink |
| Rootha, Mastering the Moment | flying, haste |
| Sarkhan, Dragon Ascendant | flying |
| Scion of Draco | first_strike, hexproof, lifelink, trample, vigilance |
| Seasoned Hallowblade | indestructible |
| Skrelv, Defector Mite | hexproof |
| Summon: Brynhildr | haste |
| Sylvan Safekeeper | shroud |
| The Swarmweaver | deathtouch, flying |
| Urdnan, Dromoka Warrior | double_strike, first_strike |
| Xenagos, God of Revels | haste |
| Yuna, Hope of Spira | lifelink, trample, ward |
| Zack Fair | indestructible |
| Zur, Eternal Schemer | deathtouch, hexproof, lifelink |

## Non-creatures

Spells, auras, equipment and planeswalkers that grant or mention a keyword. They
were tagged as if they had it themselves.

| Card | Tags removed |
|---|---|
| Academic Dispute | reach |
| Archenemy's Charm | lifelink |
| Arena of Glory | haste |
| Ba Sing Se | haste |
| Boros Charm | double_strike, indestructible |
| Break Out | haste |
| Celestial Colonnade | flying, vigilance |
| Chandra, Spark Hunter | haste |
| Chase Inspiration | hexproof |
| Choreographed Sparks | haste |
| Cori-Steel Cutter | haste, prowess, trample |
| Deafening Clarion | lifelink |
| Dreadmaw's Ire | trample |
| Earthbender Ascension | trample |
| Elspeth, Storm Slayer | flying |
| Experimental Synthesizer | vigilance |
| Extinguisher Battleship | flying, trample |
| Faebloom Trick | flying |
| Frostcliff Siege | haste, trample |
| Full Bore | haste, trample |
| Ghost Vacuum | flying |
| Goryo's Vengeance | haste |
| Hall of Storm Giants | ward |
| Hanweir Battlements | haste |
| Heroes' Hangout | first_strike |
| Hollowmurk Siege | menace |
| Impolite Entrance | haste, trample |
| Innkeeper's Talent | ward |
| Jeskai Revelation | prowess |
| Kavaron, Memorial World | haste |
| Leyline of Sanctity | hexproof |
| Long Goodbye | ward |
| Might of the Meek | trample |
| Monstrous Rage | trample |
| Nowhere to Run | hexproof, ward |
| Octopus Form | hexproof |
| Origin of Metalbending | indestructible |
| Overprotect | hexproof, indestructible, trample |
| Pawpatch Formation | flying |
| Phantom Interference | flying |
| Pick Your Poison | flying |
| Practiced Offense | double_strike, lifelink |
| Ral, Crackling Wit | prowess |
| Reasonable Doubt | menace |
| Restless Anchorage | flying |
| Restless Reef | deathtouch |
| Restless Vents | menace |
| Restless Vinestalk | trample |
| Restoration Magic | hexproof, indestructible |
| Rockface Village | haste |
| Royal Treatment | hexproof, ward |
| Sapling Nursery | indestructible, reach |
| Shadowspear | hexproof, indestructible, lifelink, trample |
| Shardmage's Rescue | hexproof |
| Sheltered by Ghosts | lifelink, ward |
| Shore Up | hexproof |
| Skateboard | haste |
| Skrelv's Hive | lifelink |
| Smuggler's Surprise | hexproof, indestructible |
| Snakeskin Veil | hexproof |
| Sokenzan, Crucible of Defiance | haste |
| Soul Search | flying |
| Soulstone Sanctuary | vigilance |
| Spectacular Tactics | hexproof |
| Stormchaser's Talent | prowess |
| Strix Serenade | flying |
| Surge of Salvation | hexproof |
| Swan Song | flying |
| Sword of Once and Future | protection |
| Sygg's Command | lifelink |
| Teferi, Time Raveler | flash |
| The Wandering Emperor | first_strike, vigilance |
| Twisted Fealty | haste |
| Tyvar's Stand | hexproof, indestructible |
| Veil of Summer | hexproof |
| Vengeful Possession | haste |
| Violent Urge | double_strike, first_strike |
| Vivien Reid | flying, indestructible, trample, vigilance |
| Wild Ride | haste |

## Conditional abilities (your call)

These eight cards have a keyword only while a condition holds ("has flying as long as ...").
The tagger cannot evaluate the condition, so the keyword is always on or always off.
`engine.keywords.TAG_CONDITIONAL_SELF_GRANTS` is `True`, which keeps what the old tagger did:
always on. Set it to `False` and these lose the tags below.

| Card | Conditional tags |
|---|---|
| Aven Heartstabber | deathtouch |
| Bloodghast | haste |
| Dragon's Rage Channeler | flying |
| Kaito, Bane of Nightmares | hexproof |
| Keen-Eyed Curator | trample |
| Stoic Sphinx | hexproof |
| Warden of the Inner Sky | flying, vigilance |
| Wildfire Wickerfolk | trample |

## Known miss

- Leatherhead, Swamp Stalker enters with a hexproof counter. A keyword counter is not
  read as the card's own ability, so it is no longer tagged hexproof.
