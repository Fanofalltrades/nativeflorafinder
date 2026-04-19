#!/usr/bin/env python3
"""Build species_data_compact.js from species_data.json.

Converts the full enriched JSON into a compact JS file for the browser.
Prefers iNaturalist photos (color field photos) over Wikipedia (may be B/W).
Uses original/full-resolution image URLs.
"""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(SCRIPT_DIR, "species_data.json")
OUTPUT = os.path.join(SCRIPT_DIR, "species_data_compact.js")


def build():
    with open(INPUT) as f:
        data = json.load(f)

    plants = []
    for sci, v in data.items():
        wiki = v.get("wikipedia") or {}
        inat = v.get("inaturalist") or {}
        ns = v.get("natureserve") or {}
        gbif = v.get("gbif") or {}
        gb = v.get("gobotany") or {}
        per = v.get("perenual") or {}

        # Prefer iNaturalist (color field photos) over Wikipedia (may be B/W)
        # Use original resolution
        inat_url = inat.get("photo_url", "")
        inat_orig = inat_url.replace("/medium.", "/original.") if inat_url else ""
        wiki_img = wiki.get("image", "")

        if inat_orig:
            photo = inat_orig
            photo_attr = inat.get("photo_attribution", "")
        elif wiki_img:
            photo = wiki_img
            photo_attr = "Wikimedia Commons (CC BY-SA)"
        elif gb.get("photos"):
            photo = gb["photos"][0]["url"]
            photo_attr = gb["photos"][0].get("credit", "") + " / Native Plant Trust"
        else:
            photo = ""
            photo_attr = ""

        p = {
            "s": v["ct_status"],
            "c": v["common_name"],
            "sci": v["scientific_name"],
            "n": v.get("note", ""),
            "ext": v.get("extirpated", False),
            "fed": v.get("federal_status", ""),
            "img": photo,
            "attr": photo_attr,
            "desc": wiki.get("extract", "") or (gb.get("description", "") if gb else ""),
            "fam": gbif.get("family", ""),
            "ord": gbif.get("order", ""),
            "cls": gbif.get("class", ""),
            "gr": ns.get("g_rank", ""),
            "sr": ns.get("ct_s_rank", ""),
            "obs": inat.get("observations_count", 0),
            "wiki": wiki.get("page_url", ""),
            "inat": inat.get("inat_id", ""),
        }

        # Care data from Perenual
        if per:
            care = {}
            for key, field in [
                ("water", "watering"), ("sun", "sunlight"), ("soil", "soil"),
                ("cycle", "cycle"), ("growth", "growth_rate"),
                ("zone", "hardiness"), ("attracts", "attracts"),
                ("prop", "propagation"),
            ]:
                val = per.get(field)
                if val and val != "Upgrade Plans To Premium/Supreme":
                    care[key] = val
            if care:
                p["care"] = care

        plants.append(p)

    js = json.dumps(plants, separators=(",", ":"))
    with open(OUTPUT, "w") as f:
        f.write("const PLANTS=" + js + ";")

    # Stats
    inat_count = sum(1 for p in plants if "inaturalist" in p["img"])
    wiki_count = sum(1 for p in plants if "wikipedia" in p["img"])
    other_count = sum(1 for p in plants if p["img"] and "inaturalist" not in p["img"] and "wikipedia" not in p["img"])

    print(f"Built {OUTPUT}")
    print(f"  {len(plants)} species, {len(js) // 1024} KB")
    print(f"  Images: {inat_count} iNaturalist, {wiki_count} Wikipedia, {other_count} other")


if __name__ == "__main__":
    build()
