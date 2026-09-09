#!/usr/bin/env python3

from pathlib import Path
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict

import requests


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "metadata"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "verified_page_ids.json"
AUDIT_JSON = OUTPUT_DIR / "page_id_selection_audit.json"

API_VERSION = "v23.0"
COUNTRY = "DE"
AD_ACTIVE_STATUS = "ALL"
PAGE_LIMIT = 500
MAX_PAGES_PER_QUERY = 5
REQUEST_TIMEOUT = 60
PAGE_DELAY_SECONDS = 0.4

MIN_ACCEPT_SCORE = 100


BRANDS = {
    "Aldi Nord": {
        "queries": ["Aldi Nord", "ALDI Nord"],
        "accepted_names": ["ALDI Nord"],
    },
    "Aldi Süd": {
        "queries": ["Aldi Süd", "ALDI SÜD"],
        "accepted_names": ["ALDI SÜD", "ALDI Süd"],
    },
    "Penny": {
        "queries": ["Penny Markt", "PENNY"],
        "accepted_names": ["PENNY"],
    },
    "Lidl": {
        "queries": ["Lidl", "Lidl Deutschland"],
        "accepted_names": ["Lidl in Deutschland", "Lidl Deutschland"],
    },
    "Kaufland": {
        "queries": ["Kaufland", "Kaufland Deutschland"],
        "accepted_names": ["Kaufland"],
    },
    "Edeka Südwest": {
        "queries": ["Edeka Südwest", "EDEKA Südwest"],
        "accepted_names": ["EDEKA Südwest"],
    },
    "Bonprix": {
        "queries": ["bonprix"],
        "accepted_names": ["bonprix"],
    },
    "Zalando": {
        "queries": ["Zalando"],
        "accepted_names": ["Zalando"],
    },
    "New Yorker": {
        "queries": ["NEW YORKER", "New Yorker Fashion"],
        "accepted_names": ["NEW YORKER"],
    },
    "Zara": {
        "queries": ["Zara", "ZARA"],
        "accepted_names": ["ZARA", "Zara"],
    },
    "About You": {
        "queries": [
            "ABOUT YOU fashion",
            "ABOUT YOU Deutschland",
            "aboutyou.de",
            "ABOUT YOU Online Shop",
        ],
        "accepted_names": [
            "ABOUT YOU",
            "ABOUT YOU Deutschland",
        ],
    },
    "dm": {
        "queries": ["dm drogerie markt", "dm-drogerie markt Deutschland"],
        "accepted_names": [
            "dm-drogerie markt Deutschland",
            "dm drogerie markt Deutschland",
        ],
    },
    "Rossmann": {
        "queries": ["Rossmann", "ROSSMANN"],
        "accepted_names": ["Rossmann", "ROSSMANN"],
    },
    "Douglas": {
        "queries": ["Douglas Cosmetics", "Douglas"],
        "accepted_names": ["Douglas Cosmetics"],
    },
    "Müller": {
        "queries": ["Müller Drogerie", "Müller Deutschland"],
        "accepted_names": [
            "Müller",
            "Müller Deutschland",
            "Müller Drogerie",
        ],
    },
    "Flaconi": {
        "queries": ["flaconi"],
        "accepted_names": ["flaconi"],
    },
    "Bauhaus": {
        "queries": ["BAUHAUS Deutschland", "BAUHAUS"],
        "accepted_names": ["BAUHAUS Deutschland"],
    },
    "OBI": {
        "queries": ["OBI Deutschland", "OBI"],
        "accepted_names": ["OBI"],
    },
    "IKEA": {
        "queries": [
            "IKEA Deutschland",
            "IKEA Germany",
            "IKEA Möbel",
            "IKEA Einrichtung",
            "IKEA Family Deutschland",
            "ikea.de",
        ],
        "accepted_names": ["IKEA"],
    },
    "Hornbach": {
        "queries": ["HORNBACH", "HORNBACH Deutschland"],
        "accepted_names": ["HORNBACH"],
    },
}


REJECT_TERMS = {
    "karriere",
    "career",
    "jobs",
    "job",
    "stellen",
    "stellenangebote",
    "ausbildung",
    "azubi",
    "recruit",
    "recruiting",
    "arbeiten bei",
    "werken bij",
    "polska",
    "österreich",
    "austria",
    "schweiz",
    "suisse",
    "svizzera",
    "italia",
    "france",
    "hungary",
    "romania",
    "românia",
}


def normalize(text):
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.casefold()
    text = re.sub(r"[^\w\s]+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_token():
    token = os.environ.get("META_ACCESS_TOKEN")
    if not token:
        sys.exit("ERROR: META_ACCESS_TOKEN is not set.")
    return token


def is_rate_limited(response):
    try:
        error = response.json().get("error", {})
        return (
            response.status_code == 429
            or error.get("code") in (4, 17, 32, 613)
            or error.get("is_transient", False)
        )
    except Exception:
        return response.status_code == 429


def collect_candidates(search_term, token):
    url = f"https://graph.facebook.com/{API_VERSION}/ads_archive"

    params = {
        "search_terms": search_term,
        "ad_reached_countries": json.dumps([COUNTRY]),
        "ad_active_status": AD_ACTIVE_STATUS,
        "fields": "page_id,page_name",
        "limit": PAGE_LIMIT,
        "access_token": token,
    }

    tally = defaultdict(lambda: {"page_name": "", "ad_count": 0})
    pages = 0
    backoff = 5

    while pages < MAX_PAGES_PER_QUERY:
        try:
            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            print(f"    network error: {exc}; retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue

        if is_rate_limited(response):
            print(f"    rate limited; retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue

        if response.status_code >= 400:
            raise RuntimeError(
                f"HTTP {response.status_code}: {response.text[:250]}"
            )

        payload = response.json()

        for ad in payload.get("data", []):
            page_id = str(ad.get("page_id", "")).strip()
            page_name = str(ad.get("page_name", "") or "").strip()

            if not page_id:
                continue

            tally[page_id]["page_name"] = page_name
            tally[page_id]["ad_count"] += 1

        pages += 1

        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break

        url = next_url
        params = None
        time.sleep(PAGE_DELAY_SECONDS)

    return tally


def rejected_name(page_name):
    normalized = normalize(page_name)

    return any(
        normalize(term) in normalized
        for term in REJECT_TERMS
    )


def score_candidate(page_name, ad_count, accepted_names):
    if rejected_name(page_name):
        return -10000

    name_norm = normalize(page_name)
    accepted_norms = [normalize(name) for name in accepted_names]

    score = 0

    if name_norm in accepted_norms:
        score += 1000

    for accepted in accepted_norms:
        if accepted and accepted in name_norm:
            score += 250

        accepted_tokens = set(accepted.split())
        name_tokens = set(name_norm.split())

        if accepted_tokens and accepted_tokens.issubset(name_tokens):
            score += 150

    score += min(int(ad_count), 500) / 1000

    return score


def find_brand_page(brand, config, token):
    combined = defaultdict(lambda: {"page_name": "", "ad_count": 0})

    for query in config["queries"]:
        query_results = collect_candidates(query, token)

        for page_id, row in query_results.items():
            combined[page_id]["page_name"] = row["page_name"]
            combined[page_id]["ad_count"] += row["ad_count"]

    scored = []

    for page_id, row in combined.items():
        score = score_candidate(
            row["page_name"],
            row["ad_count"],
            config["accepted_names"],
        )

        scored.append(
            {
                "page_id": page_id,
                "page_name": row["page_name"],
                "ad_count": row["ad_count"],
                "score": score,
            }
        )

    scored.sort(
        key=lambda row: (
            -row["score"],
            -row["ad_count"],
            row["page_name"].casefold(),
            row["page_id"],
        )
    )

    if not scored:
        raise RuntimeError(f"{brand}: no Page IDs returned.")

    best = scored[0]

    if best["score"] < MIN_ACCEPT_SCORE:
        top = scored[:8]

        details = "\n".join(
            f"    {row['page_id']} | {row['page_name']} | "
            f"{row['ad_count']} ads | score={row['score']:.3f}"
            for row in top
        )

        raise RuntimeError(
            f"{brand}: no sufficiently strong official-page match.\n"
            f"Top candidates:\n{details}"
        )

    if len(scored) > 1 and scored[1]["score"] == best["score"]:
        raise RuntimeError(
            f"{brand}: ambiguous Page-ID match. "
            f"Top two candidates have the same score."
        )

    return best, scored[:10]


def main():
    token = get_token()

    verified = {}
    audit = {}

    for brand, config in BRANDS.items():
        print(f"\n{brand}")

        best, top_candidates = find_brand_page(
            brand,
            config,
            token,
        )

        verified[brand] = best["page_id"]

        audit[brand] = {
            "queries": config["queries"],
            "accepted_names": config["accepted_names"],
            "selected": best,
            "top_candidates": top_candidates,
        }

        print(
            f"    selected: {best['page_id']}   "
            f"{best['page_name']}   "
            f"{best['ad_count']} ads"
        )

    if len(verified) != len(BRANDS):
        raise RuntimeError(
            "Not all retailers received a verified Page ID."
        )

    if len(set(verified.values())) != len(verified):
        raise RuntimeError(
            "Duplicate Page IDs were selected for different retailers."
        )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            verified,
            file,
            indent=2,
            ensure_ascii=False,
        )

    with open(
        AUDIT_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            audit,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\nCompleted.")
    print(f"Verified IDs: {OUTPUT_JSON}")
    print(f"Selection audit: {AUDIT_JSON}")


if __name__ == "__main__":
    main()
