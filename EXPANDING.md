# Expanding to Other States

The data pipeline is designed to work for any US state. Here's how to add one.

## Step 1: Get the Species List

Each state maintains its own endangered/threatened species list. Common sources:

- **State wildlife agency** (e.g., CT DEEP, MA NHESP, NY DEC)
- **NatureServe Explorer** -- search by state, filter for S1/S2/S3/SH ranks
- **State Natural Heritage programs** -- affiliated with NatureServe

You need at minimum: scientific name and state conservation status for each species.

## Step 2: Format the Species List

Add species to `fetch_data.py` in the same format as the CT species. The script extracts species from the embedded data in `index.html`, but you can also modify it to read from a CSV:

```csv
status,common_name,scientific_name,extirpated,federal_status,note
E,Balsam fir,Abies balsamea,false,,"native populations only"
SC,Virginia copperleaf,Acalypha virginica,false,,
```

## Step 3: Run the Data Fetch

```bash
python3 fetch_data.py
```

The script queries four APIs for each species:

1. **Wikipedia** -- description text and images (no auth, no rate limit)
2. **GBIF** -- taxonomy backbone (no auth, generous limits)
3. **iNaturalist** -- photos and observation counts (~1 req/sec)
4. **NatureServe** -- conservation ranks for ALL states (1 req per species)

At ~1.5 seconds per species, a 300-species list takes ~8 minutes.

## Step 4: Build the Compact JS

```bash
python3 build_compact.py
```

This converts `species_data.json` into the browser-ready `species_data_compact.js`.

## Step 5: Update the App

In `index.html`, update:
- The location header (state, hardiness zone, ecoregion)
- The footer data source attribution
- The default sort if desired

## Using NatureServe for Automated State Lists

Instead of manually sourcing each state's list, you can query NatureServe programmatically:

```python
import urllib.request, json

url = "https://explorer.natureserve.org/api/data/speciesSearch"
payload = {
    "criteriaType": "species",
    "textCriteria": [{"paramType": "quickSearch", "searchToken": "Quercus"}],
    "statusCriteria": [{
        "paramType": "subnationConservationStatus",
        "subnation": "MA",
        "rank": ["S1", "S2", "S3", "SH"]
    }]
}
# POST this to get all imperiled Quercus species in Massachusetts
```

This approach lets you generate equivalent endangered species lists for any state without manually finding each state's official list.

## Multi-State Architecture

For a national version, consider:

1. **One JSON file per state** (e.g., `data/CT.json`, `data/MA.json`)
2. **Zip code to state mapping** at the app level
3. **Shared species data** -- many species appear in multiple states
4. **FloraAPI** ($19/month) provides county-level native species lists via API, which is the cleanest path to national coverage

## Data Volume Estimates

| Scope | Species Count | Data Size | Fetch Time |
|---|---|---|---|
| Connecticut | 331 | 610 KB | ~8 min |
| New England (6 states) | ~1,200 | ~2 MB | ~30 min |
| All 50 states (T&E only) | ~5,000 | ~10 MB | ~2 hours |
| All US native plants | ~18,000 | ~35 MB | ~7.5 hours |
