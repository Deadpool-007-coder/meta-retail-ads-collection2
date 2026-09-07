#!/usr/bin/env python3
"""
Collect Meta Marketing API estimated monthly audience sizes for Germany.

Platform scopes:
- Facebook + Instagram
- Facebook only
- Instagram only

Required environment variables:
    META_ACCESS_TOKEN
    META_AD_ACCOUNT_ID

Optional environment variable:
    META_API_VERSION
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_VERSION = os.getenv("META_API_VERSION", "v25.0")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "").strip()
AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "").strip()

COUNTRY = "DE"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

AGE_BANDS = [
    ("18-24", 18, 24),
    ("25-34", 25, 34),
    ("35-44", 35, 44),
    ("45-54", 45, 54),
    ("55-64", 55, 64),
    ("65+", 65, 65),
]

GENDERS = [
    ("all", None),
    ("male", [1]),
    ("female", [2]),
]

PLATFORM_SCOPES = [
    ("facebook_instagram", ["facebook", "instagram"]),
    ("facebook_only", ["facebook"]),
    ("instagram_only", ["instagram"]),
]

OUTPUT_DIR = Path("benchmark")
CSV_PATH = OUTPUT_DIR / "meta_audience_estimates_germany.csv"
RAW_JSON_PATH = OUTPUT_DIR / "meta_audience_estimates_germany_raw.json"

REQUEST_DELAY_SECONDS = 0.75
MAX_RETRIES = 5


def normalize_account_id(value):
    return value if value.startswith("act_") else f"act_{value}"


def build_targeting(platforms, gender_values=None, age_min=18, age_max=65):
    spec = {
        "geo_locations": {"countries": [COUNTRY]},
        "age_min": age_min,
        "age_max": age_max,
        "publisher_platforms": platforms,
    }
    if gender_values:
        spec["genders"] = gender_values
    return spec


def request_estimate(targeting):
    url = f"{BASE_URL}/{normalize_account_id(AD_ACCOUNT_ID)}/delivery_estimate"
    params = {
        "access_token": ACCESS_TOKEN,
        "optimization_goal": "REACH",
        "targeting_spec": json.dumps(targeting, separators=(",", ":")),
        "fields": "estimate_mau_lower_bound,estimate_mau_upper_bound",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(url, params=params, timeout=60)

        if response.ok:
            payload = response.json()
            data = payload.get("data", [])
            if not data:
                return None, payload

            estimate = data[0]
            return estimate, payload

        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"raw_text": response.text}

        error = error_payload.get("error", {})
        code = error.get("code")
        subcode = error.get("error_subcode")

        if response.status_code in {429, 500, 502, 503, 504} or code in {4, 17, 32, 613}:
            wait = min(60, 2 ** attempt)
            print(
                f"Temporary API error. Waiting {wait}s. code={code} subcode={subcode}",
                file=sys.stderr,
            )
            time.sleep(wait)
            continue

        message = error.get("message", response.text)
        raise RuntimeError(
            f"Meta API request failed: HTTP {response.status_code}; "
            f"code={code}; subcode={subcode}; message={message}"
        )

    raise RuntimeError("Maximum retry count reached.")


def midpoint(lower, upper):
    if lower is None or upper is None:
        return None
    return round((lower + upper) / 2)


def collect_case(rows, raw_responses, platform_scope, platforms,
                 gender_label, gender_values, age_band, age_min, age_max):
    targeting = build_targeting(platforms, gender_values, age_min, age_max)
    estimate, raw_payload = request_estimate(targeting)
    collected_at = datetime.now(timezone.utc).isoformat()

    raw_responses.append({
        "platform_scope": platform_scope,
        "gender": gender_label,
        "age_band": age_band,
        "targeting_spec": targeting,
        "collected_at_utc": collected_at,
        "response": raw_payload,
    })

    lower = estimate.get("estimate_mau_lower_bound") if estimate else None
    upper = estimate.get("estimate_mau_upper_bound") if estimate else None

    rows.append({
        "country": COUNTRY,
        "platform_scope": platform_scope,
        "gender": gender_label,
        "age_band": age_band,
        "age_min": age_min,
        "age_max": age_max,
        "estimate_mau_lower_bound": lower,
        "estimate_mau_upper_bound": upper,
        "estimate_mau_midpoint": midpoint(lower, upper),
        "api_version": API_VERSION,
        "collected_at_utc": collected_at,
    })

    print(
        f"{platform_scope:20s} | {gender_label:6s} | {age_band:6s} | "
        f"{lower} - {upper}"
    )
    time.sleep(REQUEST_DELAY_SECONDS)


def main():
    if not ACCESS_TOKEN:
        raise SystemExit("META_ACCESS_TOKEN is not set.")
    if not AD_ACCOUNT_ID:
        raise SystemExit("META_AD_ACCOUNT_ID is not set.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    raw_responses = []

    for platform_scope, platforms in PLATFORM_SCOPES:
        for gender_label, gender_values in GENDERS:
            collect_case(
                rows, raw_responses, platform_scope, platforms,
                gender_label, gender_values, "18-65+", 18, 65
            )

        for age_band, age_min, age_max in AGE_BANDS:
            for gender_label, gender_values in GENDERS:
                collect_case(
                    rows, raw_responses, platform_scope, platforms,
                    gender_label, gender_values, age_band, age_min, age_max
                )

    fieldnames = [
        "country", "platform_scope", "gender",
        "age_band", "age_min", "age_max",
        "estimate_mau_lower_bound", "estimate_mau_upper_bound",
        "estimate_mau_midpoint",
        "api_version", "collected_at_utc",
    ]

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with RAW_JSON_PATH.open("w", encoding="utf-8") as handle:
        json.dump(raw_responses, handle, ensure_ascii=False, indent=2)

    print(f"Saved {len(rows)} estimates to {CSV_PATH}")
    print(f"Saved raw responses to {RAW_JSON_PATH}")


if __name__ == "__main__":
    main()
