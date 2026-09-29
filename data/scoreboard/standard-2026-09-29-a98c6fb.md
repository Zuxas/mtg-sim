# Sim vs real -- standard since 2026-05-15 (commit a98c6fb)

Covers **45%** of 24,659 real match rows. 19 cells, 4,880 decisive real matches, sim n=400/cell.

| Slice | Cells | Weighted mean abs delta | Median abs delta | Outside real CI | Same favourite | r (sim vs real) | Spread sim / real |
|---|---|---|---|---|---|---|---|
| all | 19 | 35.85pp | 37.31pp | 18 | 57% of 7 | 0.301 | 36.7pp / 6.5pp |
| not_flagged | 16 | 34.33pp | 34.65pp | 15 | 67% of 6 | 0.432 | 34.96pp / 6.71pp |
| trusted | 3 | 38.01pp | 37.31pp | 3 | 100% of 2 | 0.999 | 42.3pp / 7.46pp |

## Worst cells (|delta| weighted by real sample)

| Matchup | Sim G1 | Sim match | Real | Real 95% CI | n | Delta | Trust | Flag |
|---|---|---|---|---|---|---|---|---|
| Izzet Prowess vs Izzet Spellementals | 94.0% | 99.0% | 51.2% | 48-55 | 843 | +47.7 | trusted |  |
| Four-Color Control vs Izzet Spellementals | 11.0% | 3.4% | 56.5% | 51-61 | 370 | -53.1 | directional |  |
| Four-Color Control vs Izzet Prowess | 4.0% | 0.5% | 37.8% | 34-42 | 548 | -37.3 | trusted |  |
| Izzet Lessons vs Izzet Prowess | 80.2% | 89.8% | 44.9% | 39-51 | 247 | +44.9 | directional | Izzet Lessons: MILDLY OFF / STUB (real PT list, 14-card sideboard) |
| Izzet Lessons vs Izzet Spellementals | 91.8% | 98.1% | 41.6% | 34-50 | 149 | +56.5 | directional | Izzet Lessons: MILDLY OFF / STUB (real PT list, 14-card sideboard) |
| Azorius Momo vs Four-Color Control | 92.5% | 98.4% | 39.5% | 31-49 | 109 | +59.0 | directional |  |
| Azorius Momo vs Izzet Spellementals | 87.0% | 95.4% | 45.1% | 37-54 | 133 | +50.3 | directional |  |
| Dimir Excruciator vs Four-Color Control | 89.2% | 96.8% | 56.2% | 49-63 | 192 | +40.5 | directional |  |
| Izzet Spellementals vs Mardu Discard | 15.8% | 6.7% | 44.0% | 37-51 | 193 | -37.4 | directional |  |
| Four-Color Control vs Izzet Lessons | 0.0% | 0.0% | 47.4% | 38-56 | 114 | -47.4 | directional | Izzet Lessons: MILDLY OFF / STUB (real PT list, 14-card sideboard) |
| Izzet Prowess vs Mardu Discard | 73.2% | 82.4% | 55.4% | 50-61 | 318 | +27.0 | directional |  |
| Dimir Excruciator vs Izzet Spellementals | 77.0% | 86.6% | 56.6% | 50-63 | 233 | +29.9 | directional |  |
| Four-Color Control vs Mardu Discard | 10.2% | 2.9% | 37.6% | 30-46 | 141 | -34.6 | directional |  |
| Dimir Excruciator vs Izzet Prowess | 30.0% | 21.6% | 41.1% | 36-46 | 421 | -19.5 | trusted |  |
| Izzet Prowess vs Jeskai Control | 79.0% | 88.6% | 57.4% | 50-65 | 162 | +31.2 | directional |  |

## Field: modeled share vs real share

| Deck | Modeled % | Real % |
|---|---|---|
| Izzet Prowess | 9.5 | 15.73 |
| Izzet Spellementals | 4.9 | 10.88 |
| Four-Color Control | - | 7.46 |
| Dimir Excruciator | 2.0 | 4.85 |
| Mardu Discard | - | 3.33 |
| Izzet Lessons | 3.5 | 2.85 |
| Azorius Momo | 1.5 | 2.68 |
| Jeskai Control | 2.3 | 2.42 |
| Selesnya Ouroboroid | 1.8 | 1.61 |
| Izzet Control | - | 1.42 |
| Dimir Midrange | - | 1.33 |
| Temur Omniscience | - | 1.22 |
| Azorius Control | - | 1.19 |
| Temur Prowess | - | 1.19 |
| Azorius Prison | - | 1.01 |
| Sultai Control | - | 0.9 |
| Azorius Aggro | - | 0.89 |
| Golgari Midrange | - | 0.8 |
| Bant Rhythm | 15.0 | 0.69 |
| Azorius Blink | - | 0.55 |
| Sultai Reanimator | 10.1 | 0.55 |
| Boros Aggro | - | 0.51 |
| Selesnya Rhythm | - | 0.51 |
| Boros Dragons | - | 0.4 |
| Bant Airbending | 6.5 | 0.39 |
| Mono Green Aggro | - | 0.38 |
| Simic Rhythm | 15.7 | 0.13 |
| Boros Discard | - | 0.01 |
| Rakdos Discard | - | 0.01 |
| Izzet Looting | - | 0.0 |
| Five-Color Rhythm | 2.9 | 0 |
| Grixis Elementals | 2.5 | 0 |
| Selesnya Landfall | 4.8 | 0 |
| Mono Green Landfall | 4.5 | 0 |
| (real decks not modeled) | - | 34.11 |

Top unmapped real labels: 5C Landfall (5914), Izzet Aggro (811), Jeskai Lessons (781), 5C Aggro (748), Mardu Aggro (585), Four-Color (402), 5C Combo (353), Azorius Fliers (310), Azorius Flash (258), Selesnya Bogles (241), Mono Red Aggro (233), 5C Control (210), Temur Aggro (199), Dimir Deceit (183), Dimir Reanimator (178)

## Lists: sim decklist vs real lists

| Deck | Real lists | Cosine | Missing staples (>=60% of real lists) | Sim cards rare in real (<10%) |
|---|---|---|---|---|
| Azorius Control | 84 | 0.191 | Floodfarm Verge, Hallowed Fountain, Island, Meticulous Archive, Day of Judgment, Petrified Hamlet | Cavern of Souls, Cosmogrand Zenith, Enduring Innocence, Novice Inspector, Nurturing Pixie, Shardmage's Rescue |
| Sultai Reanimator | 1 | 0.285 | Ardyn, the Usurper, Awaken the Honored Dead, Bedeck / Bedazzle, Bitter Triumph, Breeding Pool, Cavern of Souls | Duress, Esper Origins, Faerie Dreamthief, Fatal Push, Feed the Cycle, Forest |
| Azorius Aggro | 77 | 0.395 | Aang, Swift Savior, Starting Town, Skycoach Conductor, Restless Anchorage, Aven Interrupter, Voice of Victory | Cavern of Souls, Deepchannel Duelist, Deepway Navigator, Disruptor of Currents, Mindspring Merfolk, Silvergill Mentor |
| Boros Aggro | 82 | 0.453 | Plains | Burnout Bashtronaut, Cheeky House-Mouse, Full Bore, Honor, Leyline of Resonance, Might of the Meek |
| Jeskai Control | 94 | 0.534 | Great Hall of the Biblioplex, Tablet of Discovery, Sundown Pass, Firebending Lesson, Flashback | Lightning Helix, North Wind Avatar, Restless Anchorage, Seam Rip, Shiko, Paragon of the Way, Ultima |
| Dimir Midrange | 47 | 0.583 | Duress, Deceit, Undercity Sewers, Strategic Betrayal, Day of Black Sun, Emeritus of Ideation | Deep-Cavern Bat, Phantom Interference, Preacher of the Schism, Starting Town |
| Izzet Control | 52 | 0.592 | Prismari Charm, Mountain, Stormcarved Coast, Tablet of Discovery | Slickshot Show-Off, Stormchaser's Talent |
| Azorius Momo | 108 | 0.628 | Daydream, Floodfarm Verge, Hallowed Fountain, Quantum Riddler, Practiced Offense, Erode | Curious Farm Animals, Soulstone Sanctuary, Voice of Victory |
| Selesnya Ouroboroid | 1 | 0.651 | Ba Sing Se, Bedeck / Bedazzle, Leatherhead, Swamp Stalker, Multiversal Passage, Practiced Offense, Spider Manifestation | Erode, Keen-Eyed Curator, Nurturing Pixie, Sage of the Skies, Starting Town |
| Sultai Control | 59 | 0.669 | Deadly Cover-Up, Professor Dellian Fel, Bitter Triumph, Great Hall of the Biblioplex | Black Cat, Cunning Thief |
| Izzet Lessons | 10 | 0.72 | Great Hall of the Biblioplex, Flashback, Hallowed Fountain, Improvisation Capstone, Jeskai Revelation, Mistrise Village | Spell Pierce |
| Simic Rhythm | 13 | 0.739 | Mockingbird | Frostcliff Siege, Great Divide Guide, Spider-Sense, Stomping Ground |
| Four-Color Control | 331 | 0.769 | Tablet of Discovery, Sacred Foundry, Sear | Resonating Lute, Spell Snare |
| Golgari Midrange | 4 | 0.77 | Deathcap Glade, Ral Zarek, Guest Lecturer, Sentinel of the Nameless City | Firdoch Core, Intimidation Tactics, Soulstone Sanctuary, Tragedy Feaster, Unholy Annex // Ritual Chamber |
| Mono Green Aggro | 114 | 0.819 | Sapling Nursery | Archdruid's Charm |
| Azorius Prison | 2 | 0.832 | Abandoned Air Temple, Enduring Curiosity, Erode, Restless Anchorage |  |
| Mardu Discard | 8 | 0.844 | Carnage, Crimson Chaos, Requiting Hex, Inti, Seneschal of the Sun, Swamp | Cecil, Dark Knight, Shardmage's Rescue |
| Izzet Prowess | 621 | 0.861 | Spell Pierce, Vibrant Outburst | Three Steps Ahead |
| Boros Dragons | 30 | 0.865 | Smaug the Magnificent, Plains | Lorehold, the Historian, Spectacular Tactics |
| Mono Green Landfall | 323 | 0.893 | Demolition Field, Surrak, Elusive Hunter |  |
| Izzet Spellementals | 417 | 0.905 | Get Out, Impractical Joke |  |
| Bant Airbending | 21 | 0.919 | Michelangelo's Technique |  |
| Selesnya Landfall | 102 | 0.925 | Dyadrine, Synthesis Amalgam, Mossborn Hydra |  |
| Dimir Excruciator | 9 | 0.95 | Multiversal Passage |  |
| Temur Omniscience | 0 | None |  |  |
| Temur Prowess | 0 | None |  |  |
| Bant Rhythm | 0 | None |  |  |
| Azorius Blink | 0 | None |  |  |
| Selesnya Rhythm | 0 | None |  |  |
| Izzet Looting | 0 | None |  |  |
| Rakdos Discard | 0 | None |  |  |
| Boros Discard | 0 | None |  |  |
