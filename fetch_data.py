#!/usr/bin/env python3
"""Fetch plant data from free APIs for all CT native plant species.

Sources:
  - Wikipedia REST API: summary text + images (no auth, no rate limit issues)
  - iNaturalist API: photos + observation counts (~1 req/sec)
  - NatureServe API: conservation G/S ranks (no auth needed)
  - GBIF: taxonomy backbone (no auth needed)
  - phzmapi.org: hardiness zone (already confirmed 7a for 06824)

Outputs JSON to native/species_data.json
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import sys
import os

SPECIES_FILE = os.path.join(os.path.dirname(__file__), "index.html")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "species_data.json")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "species_data_partial.json")

def extract_species_from_html(html_path):
    """Extract species list from the embedded JS in index.html."""
    with open(html_path) as f:
        content = f.read()

    import re
    species = []
    # Match each object in the PLANTS array
    pattern = r'\{s:"([^"]+)",c:"([^"]+)"(?:,n:"([^"]*)")?(?:,sci:"([^"]+)")(?:,ext:true)?(?:,fed:"([^"]*)")?\}'
    for m in re.finditer(pattern, content):
        status, common, note, sci, fed = m.groups()
        entry = {
            "status": status,
            "common_name": common,
            "scientific_name": sci or "",
            "note": note or "",
            "extirpated": "ext:true" in m.group(0),
            "federal_status": fed or ""
        }
        species.append(entry)
    return species


def fetch_json(url, method="GET", data=None, headers=None, timeout=15):
    """Fetch JSON from a URL."""
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", "NativePlantFinder/0.1 (research; contact@example.com)")

    if data and method == "POST":
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method="POST")
        headers["Content-Type"] = "application/json"
        req.add_header("Content-Type", "application/json")
    else:
        req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as e:
        return {"_error": str(e)}


def fetch_wikipedia(sci_name):
    """Get Wikipedia summary and image for a species."""
    url_name = sci_name.replace(" ", "_")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(url_name)}"
    data = fetch_json(url)
    if "_error" in data or data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None
    return {
        "title": data.get("title"),
        "description": data.get("description", ""),
        "extract": data.get("extract", ""),
        "image": data.get("originalimage", {}).get("source"),
        "thumbnail": data.get("thumbnail", {}).get("source"),
        "page_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


def fetch_inaturalist(sci_name):
    """Get iNaturalist taxon info, photo, and observation count."""
    url = f"https://api.inaturalist.org/v1/taxa?q={urllib.parse.quote(sci_name)}&rank=species&per_page=1"
    data = fetch_json(url)
    if "_error" in data or not data.get("results"):
        return None
    t = data["results"][0]
    # Verify exact match
    if t.get("name", "").lower() != sci_name.lower():
        return None
    photo = t.get("default_photo") or {}
    return {
        "inat_id": t["id"],
        "observations_count": t.get("observations_count", 0),
        "photo_url": photo.get("medium_url"),
        "photo_attribution": photo.get("attribution"),
        "photo_license": photo.get("license_code"),
        "preferred_common_name": t.get("preferred_common_name"),
        "wikipedia_url": t.get("wikipedia_url"),
        "iconic_taxon_name": t.get("iconic_taxon_name"),
        "conservation_status": t.get("conservation_status"),
    }


def fetch_natureserve(sci_name):
    """Get NatureServe conservation ranks."""
    url = "https://explorer.natureserve.org/api/data/speciesSearch"
    payload = {
        "criteriaType": "species",
        "textCriteria": [{"paramType": "quickSearch", "searchToken": sci_name}]
    }
    data = fetch_json(url, method="POST", data=payload, timeout=20)
    if "_error" in data or not data.get("results"):
        return None
    r = data["results"][0]
    # Verify name match
    if sci_name.split()[0].lower() not in r.get("scientificName", "").lower():
        return None

    result = {
        "element_global_id": r.get("uniqueId"),
        "g_rank": r.get("roundedGRank"),
        "scientific_name_full": r.get("scientificName"),
    }

    for nation in r.get("nations", []):
        if nation["nationCode"] == "US":
            result["us_n_rank"] = nation.get("roundedNRank")
            for sub in nation.get("subnations", []):
                if sub["subnationCode"] == "CT":
                    result["ct_s_rank"] = sub.get("roundedSRank")
                    result["ct_native"] = sub.get("native")

    return result


def fetch_gbif(sci_name):
    """Get GBIF taxonomy match."""
    url = f"https://api.gbif.org/v1/species/match?name={urllib.parse.quote(sci_name)}&kingdom=Plantae"
    data = fetch_json(url)
    if "_error" in data or data.get("matchType") == "NONE":
        return None
    return {
        "gbif_key": data.get("usageKey"),
        "scientific_name_full": data.get("scientificName"),
        "family": data.get("family"),
        "order": data.get("order"),
        "class": data.get("class"),
        "phylum": data.get("phylum"),
        "confidence": data.get("confidence"),
    }


def main():
    species_list = extract_species_from_html(SPECIES_FILE)
    print(f"Found {len(species_list)} species to process")

    # Load existing progress if any
    results = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            results = json.load(f)
        print(f"Resuming from {len(results)} previously fetched species")

    total = len(species_list)
    sources_stats = {"wikipedia": 0, "inaturalist": 0, "natureserve": 0, "gbif": 0}

    for i, sp in enumerate(species_list):
        sci = sp["scientific_name"]
        # Use base species name for lookups (strip variety/subspecies for some APIs)
        sci_base = " ".join(sci.split()[:2])

        if sci in results:
            # Already fetched
            for src in ["wikipedia", "inaturalist", "natureserve", "gbif"]:
                if results[sci].get(src):
                    sources_stats[src] += 1
            continue

        print(f"[{i+1}/{total}] {sp['common_name']} ({sci})")

        entry = {
            "common_name": sp["common_name"],
            "scientific_name": sci,
            "ct_status": sp["status"],
            "extirpated": sp["extirpated"],
            "federal_status": sp["federal_status"],
            "note": sp["note"],
        }

        # Wikipedia (fast, no rate limit)
        wiki = fetch_wikipedia(sci_base)
        if not wiki and sci != sci_base:
            wiki = fetch_wikipedia(sci)
        entry["wikipedia"] = wiki
        if wiki:
            sources_stats["wikipedia"] += 1

        # GBIF (fast, generous limits)
        gbif = fetch_gbif(sci)
        if not gbif:
            gbif = fetch_gbif(sci_base)
        entry["gbif"] = gbif
        if gbif:
            sources_stats["gbif"] += 1

        # iNaturalist (1 req/sec limit)
        inat = fetch_inaturalist(sci)
        if not inat and sci != sci_base:
            inat = fetch_inaturalist(sci_base)
        entry["inaturalist"] = inat
        if inat:
            sources_stats["inaturalist"] += 1

        # NatureServe (be gentle, ~1 req/2sec)
        ns = fetch_natureserve(sci_base)
        entry["natureserve"] = ns
        if ns:
            sources_stats["natureserve"] += 1

        results[sci] = entry

        # Save progress every 10 species
        if (i + 1) % 10 == 0:
            with open(PROGRESS_FILE, "w") as f:
                json.dump(results, f, indent=2)
            done = i + 1
            print(f"  -- Progress saved ({done}/{total}) | Wiki:{sources_stats['wikipedia']} iNat:{sources_stats['inaturalist']} NS:{sources_stats['natureserve']} GBIF:{sources_stats['gbif']}")

        # Rate limiting: iNat wants 1/sec, NatureServe be gentle
        time.sleep(1.5)

    # Final save
    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    # Clean up partial
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print(f"\nDone! Saved {len(results)} species to {OUTPUT_FILE}")
    print(f"Coverage:")
    print(f"  Wikipedia:    {sources_stats['wikipedia']}/{total}")
    print(f"  iNaturalist:  {sources_stats['inaturalist']}/{total}")
    print(f"  NatureServe:  {sources_stats['natureserve']}/{total}")
    print(f"  GBIF:         {sources_stats['gbif']}/{total}")


if __name__ == "__main__":
    main()
