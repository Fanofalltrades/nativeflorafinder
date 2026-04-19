# Native Flora Finder

A location-aware tool for discovering native plants with conservation status, ecological data, and full-resolution photos. Currently features 331 endangered, threatened, and special concern species for Connecticut.

## Features

- **331 CT native species** with conservation status from CT DEEP
- **Full-resolution photos** from iNaturalist and Wikimedia Commons
- **NatureServe conservation ranks** (state and global) with human-readable labels
- **Wikipedia descriptions** for every species
- **GBIF taxonomy** (family, order, class)
- **Search** by common name, scientific name, or family
- **Filter** by Endangered, Threatened, Special Concern, Extirpated, Federal status
- **Sort** by most observed, name, status, family, or rarity
- **Lightbox** for full-size image viewing
- **Detail modal** with conservation status, taxonomy, care data, and links to external databases
- **Fully static** -- runs in any browser, no server required

## Data Sources

| Source | Data Provided | License |
|---|---|---|
| [CT DEEP](https://portal.ct.gov/deep) | State endangered/threatened/special concern species list | Public |
| [iNaturalist](https://www.inaturalist.org) | Photos, observation counts | CC BY-NC (photos) |
| [Wikipedia](https://www.wikipedia.org) | Species descriptions, images | CC BY-SA |
| [NatureServe](https://explorer.natureserve.org) | Conservation ranks (G-rank, S-rank) | Citation required |
| [GBIF](https://www.gbif.org) | Taxonomy (family, order, class, phylum) | CC0 / CC BY |
| [Go Botany](https://gobotany.nativeplanttrust.org) | Photos for rare species | Native Plant Trust |

## Quick Start

Just open `index.html` in a browser. No build step, no dependencies, no server.

```bash
git clone https://github.com/Fanofalltrades/nativeflorafinder.git
cd nativeflorafinder
open index.html
```

## Refreshing Data

The data fetch script pulls from four free APIs (no keys required):

```bash
python3 fetch_data.py
```

This takes ~8 minutes (rate-limited to respect API terms). It produces `species_data.json` with Wikipedia, iNaturalist, NatureServe, and GBIF data for all 331 species.

To rebuild the compact JS file from the JSON:

```bash
python3 build_compact.py
```

## Expanding to Other States

The data pipeline is species-agnostic. To add another state:

1. Obtain the state's endangered/threatened species list
2. Format species as entries in the fetch script
3. Run `fetch_data.py` -- it queries national/global APIs
4. NatureServe returns S-ranks for all 50 states in a single call

See [EXPANDING.md](EXPANDING.md) for detailed instructions.

## Project Structure

```
nativeflorafinder/
  index.html                  # Main app (single-file, self-contained)
  species_data_compact.js     # Compact species data for the browser (234 KB)
  species_data.json           # Full enriched species data (618 KB)
  fetch_data.py               # Data collection script (Wikipedia, iNat, NatureServe, GBIF)
  build_compact.py            # Converts species_data.json to compact JS
```

## API Architecture

The app itself is 100% static -- no API calls at runtime. All data is pre-fetched and bundled. This means:

- Zero hosting cost (GitHub Pages, Netlify, etc.)
- No API keys needed for end users
- Works offline after initial load
- No rate limiting concerns

For a dynamic version with live data, these APIs are available:

| API | Auth Required | Cost | Use Case |
|---|---|---|---|
| [FloraAPI](https://floraapi.com) | API key | Free-$79/mo | County-level native species, conservation status |
| [Etsy API](https://developers.etsy.com) | API key | Free | Search native plant sellers |
| [Perenual](https://perenual.com) | API key | Free-$50/mo | Plant care guides |
| [phzmapi.org](https://phzmapi.org) | None | Free | USDA hardiness zone by zip code |

## Contributing

Contributions welcome. Priority areas:

- [ ] Additional state species lists
- [ ] Improved photo selection (prefer color field photos over B/W illustrations)
- [ ] Plant care data from open sources
- [ ] Nursery/supplier finder integration
- [ ] Mobile-responsive improvements

## License

MIT License. See [LICENSE](LICENSE).

Species data is sourced from public databases and used under their respective licenses. Photo attributions are embedded in the data and displayed in the app.
