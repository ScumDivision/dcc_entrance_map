# DCC Entrance Map

*Where did the stairwells open, and what was the weather like when the world ended?*

An unofficial fan map for **Dungeon Crawler Carl**. It places the 150,000 dungeon entrances from the books on the real
Earth, based on real population data, and shows the weather at the exact moment of the collapse. Explore it as a globe
or a flat map, switch between two ways of distributing the entrances, and click any entrance to see where it is, how
many people lived around it, what time it was there and what the sky looked like.

**Open the map: <https://scumdivision.github.io/dcc_entrance_map/>** · available in English and German ·
[Deutsche Fassung dieser Anleitung](README.de.md)

![The map over northern Europe: temperature, wind flow, isobars and the popup of an entrance in Svolvær, Lofoten](docs/screenshot.jpg)

## Features

- **150,000 entrances** worldwide, as in the books, placed on the GHSL 2025 population grid.
- **Two distributions** to choose from:
  - **Hybrid (H):** follows the population closely. Megacities get hundreds of entrances.
  - **Diversity (D):** spreads the entrances wider, so crawlers can just as well come from Greenland, Alaska, the
    Lofoten islands or a Pacific atoll.
- **Weather at the collapse** (3 January 2023, 10:23 UTC) from the ERA5 reanalysis: temperature, cloud cover,
  precipitation by type (rain, snow, freezing rain, sleet), wind with an animated flow layer, snow cover, isobars with
  highs and lows, the 0 °C line, and day and night with the twilight zone.
- **Entrance details:** region and country, population of the settlement and its surroundings, number of entrances
  there and people per entrance, population within 5 km, settlement type, distance to the nearest entrance, local
  time, when the stairwell was open, and a short weather summary.
- **Search** by place name (German names such as *München* work too), a **country filter** with statistics (share of
  entrances in daylight, frost, precipitation, snow cover, coldest and warmest entrance), and a weather readout under
  the mouse cursor anywhere on the map.
- Dark, light and satellite base maps.

## Canon and assumptions

- **When:** Book 1 places the collapse on *Tuesday, 3 January, at about 2:23 AM Pacific Standard Time*, which is
  10:23 UTC. The books never name the year. 3 January fell on a Tuesday in both 2017 and 2023, and later hints point to
  2023, so the map uses **3 January 2023**.
- **How many:** 150,000 stairwells, appearing in populated areas, more often where survivors gather, and rarely evenly
  spread. They open a few minutes after the collapse and stay open for about an hour (roughly 2:30 to 3:30 AM PST);
  the popup converts that into local time.
- **Where exactly** is not in the books. This map is one plausible answer built on real population data, not canon.

## The two distributions

Both start from the same data: settlements are connected clusters of populated 1 km cells (GHSL settlement model),
plus the population living up to 25 km around them. Within a settlement, each entrance first picks a 1 km cell by its
population and then one of its hundred 100 m cells, again by population, so entrances land between the houses.

**Hybrid (H)** uses settlements from small-town size upwards. Each one gets a small base share plus a share
proportional to population<sup>0.85</sup>, so the number of entrances grows almost in step with the population.

**Diversity (D)** works in two steps. First, the world is divided into equal-area squares of 100 × 100 km, and each
square gets a share proportional to its population<sup>0.45</sup>. Then that share is split among the settlements in
the square, which now count from village size (1,000 people). Dense regions still get the most entrances, but far
fewer than their population alone would give them, and remote places get a real chance.

| | Hybrid (H) | Diversity (D) |
|---|---:|---:|
| Shanghai, within 50 km | 267 | 110 |
| Delhi, within 50 km | 306 | 103 |
| Tokyo, within 50 km | 246 | 96 |
| Berlin, within 50 km | 59 | 48 |
| Greenland | 1 | 19 |
| Iceland | 6 | 41 |
| Alaska | 14 | 84 |
| Lofoten and Vesterålen | 1 | 10 |
| Pacific islands | 47 | 364 |
| Share of China and India | 37 % | 21 % |

![Entrances per 50 × 50 km: Hybrid (H) on the left, Diversity (D) on the right](zugaenge/dungeon_vergleich.png)

## Run it locally

The easiest way is the hosted version linked above. To run it yourself, any static web server will do, because all
generated data is included:

```bash
git clone https://github.com/ScumDivision/dcc_entrance_map.git
cd dcc_entrance_map
python3 -m http.server 8790 --directory web
```

Then open <http://127.0.0.1:8790>. Base maps and fonts are loaded from the internet, so you need a connection.

## Rebuild the data

You only need this to change the distribution or the weather time. The scripts declare their own dependencies and run
with [uv](https://docs.astral.sh/uv/):

```bash
uv run dungeon_zugaenge.py   # entrances: downloads about 5.7 GB of source data to cache/, writes zugaenge/*.csv
uv run bauen.py              # map data: downloads ERA5 fields (about 40 MB), writes web/daten/
```

Useful options of `dungeon_zugaenge.py` (see `--help` for all):

| Option | Meaning |
|---|---|
| `--vielfalt 0.45` | exponent per region in Diversity (D); 1 = proportional to population, smaller = spread wider |
| `--d-zelle 100` | size of the regions in km |
| `--d-schwelle 1000` | smallest settlement (people, including surroundings) that can get an entrance in D |
| `--seed 42` | random seed |
| `--grob` | skip the 100 m population grid (5.3 GB) and place entrances at random inside their 1 km cell |

The code is commented in German; the README and the map are bilingual.

## The entrance data

The two CSV files in [`zugaenge/`](zugaenge/) contain one row per entrance:

| Column | Meaning |
|---|---|
| `lat`, `lon` | position (WGS 84) |
| `name` | largest named place of the settlement; `bei X` = near X; `(namenlos)` = no named place within 30 km |
| `cc` | country code (ISO 3166-1 alpha-2) |
| `region`, `region_en` | state or province (Natural Earth admin-1), German and English name |
| `siedlung_pop` | population of the settlement including its surroundings up to 25 km |
| `zugaenge_siedlung` | number of entrances in that settlement |
| `umkreis_pop` | population in the 9 × 9 km square around the entrance |
| `dichte` | population of the 1 km cell the entrance lies in |
| `klasse` | GHSL settlement class: 30 urban centre, 23 dense town, 22 small town, 21 suburb, 13 village, 12/11 rural |
| `abstand_km` | distance to the nearest other entrance |

Feel free to use them for your own games, stories or maps; please keep the source credits below.

## Known limitations

- Entrances sit in the most populated 100 m cells, but the population grid models where people live, not streets or
  squares. In very small or very scattered places an entrance can still end up next to a farm track.
- Settlements without a named place nearby are called `(namenlos)` (unnamed). The popup still shows region and country.
- ERA5 has a resolution of about 28 km, so valleys, coasts and city climates are smoothed out.
- Population data is from 2025, not 2023. The difference does not matter at this scale.

## Feedback

Found an entrance in a strange spot, or have an idea for the map? Open an
[issue](https://github.com/ScumDivision/dcc_entrance_map/issues).

## Sources and licences

| Data | Source | Licence |
|---|---|---|
| Population, settlement classes | [GHSL](https://human-settlement.emergency.copernicus.eu/) GHS-POP (1 km and 100 m) and GHS-SMOD 2025, European Commission, Joint Research Centre | CC BY 4.0 |
| Place names | [GeoNames](https://www.geonames.org/) cities500 | CC BY 4.0 |
| Regions | [Natural Earth](https://www.naturalearthdata.com/) admin-1 states and provinces | public domain |
| Weather | [ERA5](https://cds.climate.copernicus.eu/) through [ARCO-ERA5](https://github.com/google-research/arco-era5) (Google Research) | Copernicus licence; contains modified Copernicus Climate Change Service information (2023) |
| Base maps | [OpenFreeMap](https://openfreemap.org/), [OpenMapTiles](https://openmaptiles.org/), © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors | ODbL, see providers |
| Satellite imagery | Esri, Maxar, Earthstar Geographics | Esri terms of use |
| Map library | [MapLibre GL JS](https://maplibre.org/) | BSD-3-Clause |

The canon details (date, time, number of stairwells, opening hour) come from *Dungeon Crawler Carl*, book 1.

## Licence

The code (`dungeon_zugaenge.py`, `bauen.py`, `web/*.html|js|css`) is released under the [MIT licence](LICENSE).
The generated data in `zugaenge/` and `web/daten/` is derived from the sources above and keeps their terms, in
particular attribution for GHSL, GeoNames and Copernicus (CC BY 4.0 / Copernicus licence).

## Disclaimer

This is an unofficial fan project. It is not affiliated with or endorsed by Matt Dinniman or the publishers of
*Dungeon Crawler Carl*. All rights to *Dungeon Crawler Carl* belong to their respective owners.
