#!/usr/bin/env python3

"""
recollection.py

Meta Ad Library recollection:
2025-09-06 through 2026-09-05

Permanent outputs:
    recollection.py
    ads_recollection_all20.csv
    progress.json
    audit/
        conflicting_meta_ids.csv
        repeated_meta_id_delivery_versions.csv

Temporary crash-recovery files are stored in _work/ and are deleted
after all 20 brands successfully complete.

Design:
- Germany only
- one Meta ad ID per consolidated row
- no recruitment filtering during collection
- no creative deduplication during collection
- no snapshot URL
- Germany age/gender reach collected in same API request
- explicit preservation of Unknown age reach
- checkpoint/resume
- adaptive date splitting
- repeated Meta IDs audited rather than silently discarded
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MAIN_CSV = ROOT / "ads_recollection_all20.csv"

PROGRESS_PATH = ROOT / "progress.json"

AUDIT_DIR = ROOT / "audit"

CONFLICT_PATH = (
    AUDIT_DIR
    / "conflicting_meta_ids.csv"
)

DELIVERY_VERSION_PATH = (
    AUDIT_DIR
    / "repeated_meta_id_delivery_versions.csv"
)

WORK_DIR = ROOT / "_work"

SEGMENT_DIR = WORK_DIR / "segments"

COMPLETED_BRAND_DIR = (
    WORK_DIR
    / "completed_brands"
)

BRAND_AUDIT_DIR = (
    WORK_DIR
    / "brand_audits"
)


# ============================================================
# API SETTINGS
# ============================================================

API_VERSION = "v23.0"

COUNTRY = "DE"

DATE_MIN = "2025-09-06"

DATE_MAX = "2026-09-05"

AD_ACTIVE_STATUS = "ALL"

PAGE_LIMITS = [250, 100, 50, 25]

PAGE_DELAY_SECONDS = 1.0

MAX_NETWORK_RETRIES = 5

MAX_RATE_WAITS = 8

DEFAULT_RATE_WAIT_SECONDS = 300


# ============================================================
# RETAILERS
# ============================================================

BRANDS = [
    ("Aldi Nord", "grocery", "335288650611521"),
    ("Aldi Süd", "grocery", "168773186520269"),
    ("Penny", "grocery", "700577889971139"),
    ("Lidl", "grocery", "278565202257"),
    ("Kaufland", "grocery", "132476996783723"),
    ("Edeka Südwest", "grocery", "334601287018068"),

    ("Bonprix", "fashion", "119152901485525"),
    ("Zalando", "fashion", "365604620536"),
    ("New Yorker", "fashion", "110682655781"),
    ("Zara", "fashion", "33331950906"),
    ("About You", "fashion", "1824279721179597"),

    ("dm", "health_beauty", "129724513733284"),
    ("Rossmann", "health_beauty", "354412263434"),
    ("Douglas", "health_beauty", "190089409661"),
    ("Müller", "health_beauty", "225116334184666"),
    ("Flaconi", "health_beauty", "133137093423758"),

    ("Bauhaus", "home", "137379942944322"),
    ("OBI", "home", "160178767369925"),
    ("IKEA", "home", "280631742051539"),
    ("Hornbach", "home", "102368498017"),
]


# ============================================================
# META FIELDS
# ============================================================

META_FIELDS = (
    "id,"
    "ad_creative_bodies,"
    "ad_creative_link_titles,"
    "ad_creative_link_captions,"
    "ad_creative_link_descriptions,"
    "publisher_platforms,"
    "target_ages,"
    "target_gender,"
    "ad_delivery_start_time,"
    "ad_delivery_stop_time,"
    "age_country_gender_reach_breakdown"
)


# ============================================================
# MAIN DATASET — 24 COLUMNS
# ============================================================

CSV_COLUMNS = [
    "search_brand",
    "sector",
    "meta_ad_id",

    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",

    "publisher_platforms",
    "target_ages",
    "target_gender",

    "ad_delivery_start_date_time",
    "ad_delivery_stop_date_time",

    "collection_timestamp",

    "de_male",
    "de_female",
    "de_unknown",

    "de_age_13_17",
    "de_age_18_24",
    "de_age_25_34",
    "de_age_35_44",
    "de_age_45_54",
    "de_age_55_64",
    "de_age_65_plus",
    "de_age_unknown",
]


DEMOGRAPHIC_COLUMNS = [
    "de_male",
    "de_female",
    "de_unknown",

    "de_age_13_17",
    "de_age_18_24",
    "de_age_25_34",
    "de_age_35_44",
    "de_age_45_54",
    "de_age_55_64",
    "de_age_65_plus",
    "de_age_unknown",
]


CREATIVE_COLUMNS = [
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
]


TARGETING_COLUMNS = [
    "target_ages",
    "target_gender",
]


START_COLUMN = (
    "ad_delivery_start_date_time"
)

STOP_COLUMN = (
    "ad_delivery_stop_date_time"
)

PLATFORM_COLUMN = (
    "publisher_platforms"
)


AGE_COLUMN_MAP = {
    "13-17": "de_age_13_17",
    "18-24": "de_age_18_24",
    "25-34": "de_age_25_34",
    "35-44": "de_age_35_44",
    "45-54": "de_age_45_54",
    "55-64": "de_age_55_64",
    "65+": "de_age_65_plus",
    "unknown": "de_age_unknown",
}


# ============================================================
# AUDIT COLUMNS
# ============================================================

CONFLICT_COLUMNS = [
    "search_brand",
    "meta_ad_id",

    "difference_tier",
    "differing_field",

    "earlier_value",
    "later_value",

    "earlier_collection_timestamp",
    "later_collection_timestamp",

    "earlier_query_date_min",
    "earlier_query_date_max",

    "later_query_date_min",
    "later_query_date_max",
]


DELIVERY_AUDIT_COLUMNS = [
    "query_date_min",
    "query_date_max",
    *CSV_COLUMNS,
]


# ============================================================
# BASIC HELPERS
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat(
        timespec="seconds"
    )


def slug(text):

    return "".join(
        c.lower()
        if c.isalnum()
        else "_"
        for c in text
    ).strip("_")


def compact_json(value):

    if value is None:
        return ""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def get_token():

    token = os.environ.get(
        "META_ACCESS_TOKEN"
    )

    if not token:

        sys.exit(
            "ERROR: META_ACCESS_TOKEN is not set."
        )

    return token


def load_progress():

    if not PROGRESS_PATH.exists():
        return {}

    with open(
        PROGRESS_PATH,
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_progress(progress):

    temp = (
        PROGRESS_PATH
        .with_suffix(".json.tmp")
    )

    with open(
        temp,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            progress,
            f,
            indent=2,
            ensure_ascii=False,
        )

    temp.replace(
        PROGRESS_PATH
    )


# ============================================================
# JSON/LIST HELPERS
# ============================================================

def parse_json_list(value):

    if value is None:
        return []

    value = str(value).strip()

    if not value:
        return []

    try:
        parsed = json.loads(value)

    except Exception:
        return [value]

    if parsed is None:
        return []

    if isinstance(parsed, list):
        return parsed

    return [parsed]


def normalized_list(value):

    values = []

    for item in parse_json_list(
        value
    ):

        if isinstance(
            item,
            dict,
        ):

            values.append(
                json.dumps(
                    item,
                    sort_keys=True,
                    ensure_ascii=False,
                )
            )

        else:

            values.append(
                str(item).strip()
            )

    return tuple(
        sorted(values)
    )


def values_equal(
    field,
    left,
    right,
):

    if field in (
        CREATIVE_COLUMNS
        + ["target_ages"]
    ):

        return (
            normalized_list(left)
            ==
            normalized_list(right)
        )

    return (
        str(left or "").strip()
        ==
        str(right or "").strip()
    )


# ============================================================
# DEMOGRAPHIC PARSER
# ============================================================

def blank_demographics():

    return {
        column: ""
        for column
        in DEMOGRAPHIC_COLUMNS
    }


def safe_int(value):

    if value is None:
        return 0

    if value == "":
        return 0

    return int(value)


def normalize_age_label(value):

    text = str(
        value or ""
    ).strip()

    if text.casefold() == "unknown":
        return "unknown"

    return text


def extract_germany_demographics(
    breakdown,
):

    if not breakdown:

        return blank_demographics()


    germany = [
        item
        for item in breakdown
        if str(
            item.get(
                "country",
                "",
            )
        ).upper() == "DE"
    ]


    if not germany:

        return blank_demographics()


    if len(germany) != 1:

        raise RuntimeError(
            "Unexpected API structure: "
            "multiple Germany entries returned."
        )


    age_rows = (
        germany[0]
        .get(
            "age_gender_breakdowns"
        )
        or []
    )


    if not age_rows:

        return blank_demographics()


    result = {
        "de_male": 0,
        "de_female": 0,
        "de_unknown": 0,

        "de_age_13_17": 0,
        "de_age_18_24": 0,
        "de_age_25_34": 0,
        "de_age_35_44": 0,
        "de_age_45_54": 0,
        "de_age_55_64": 0,
        "de_age_65_plus": 0,
        "de_age_unknown": 0,
    }


    seen_ages = set()


    for row in age_rows:

        age = normalize_age_label(
            row.get(
                "age_range",
                ""
            )
        )


        if age not in AGE_COLUMN_MAP:

            raise RuntimeError(
                "Unexpected Germany age range "
                f"returned by Meta: {age!r}"
            )


        if age in seen_ages:

            raise RuntimeError(
                "Duplicate Germany age range "
                f"returned by Meta: {age!r}"
            )


        seen_ages.add(age)


        male = safe_int(
            row.get("male")
        )

        female = safe_int(
            row.get("female")
        )

        unknown_gender = safe_int(
            row.get("unknown")
        )


        # Gender totals use every age category,
        # INCLUDING Unknown age.

        result[
            "de_male"
        ] += male

        result[
            "de_female"
        ] += female

        result[
            "de_unknown"
        ] += unknown_gender


        # Age total includes all gender categories.

        result[
            AGE_COLUMN_MAP[age]
        ] = (
            male
            + female
            + unknown_gender
        )


    return result


# ============================================================
# API RESPONSE -> MAIN ROW
# ============================================================

def convert_ad(
    ad,
    brand,
    sector,
):

    demographics = (
        extract_germany_demographics(
            ad.get(
                "age_country_gender_reach_breakdown"
            )
        )
    )


    row = {
        "search_brand":
            brand,

        "sector":
            sector,

        "meta_ad_id":
            str(
                ad.get(
                    "id",
                    "",
                )
                or ""
            ).strip(),

        "ad_creative_bodies":
            compact_json(
                ad.get(
                    "ad_creative_bodies"
                )
            ),

        "ad_creative_link_titles":
            compact_json(
                ad.get(
                    "ad_creative_link_titles"
                )
            ),

        "ad_creative_link_captions":
            compact_json(
                ad.get(
                    "ad_creative_link_captions"
                )
            ),

        "ad_creative_link_descriptions":
            compact_json(
                ad.get(
                    "ad_creative_link_descriptions"
                )
            ),

        "publisher_platforms":
            compact_json(
                ad.get(
                    "publisher_platforms"
                )
            ),

        "target_ages":
            compact_json(
                ad.get(
                    "target_ages"
                )
            ),

        "target_gender":
            ad.get(
                "target_gender",
                "",
            )
            or "",

        "ad_delivery_start_date_time":
            ad.get(
                "ad_delivery_start_time",
                "",
            )
            or "",

        "ad_delivery_stop_date_time":
            ad.get(
                "ad_delivery_stop_time",
                "",
            )
            or "",

        "collection_timestamp":
            utc_now(),

        **demographics,
    }


    if not row["meta_ad_id"]:

        raise RuntimeError(
            "Meta returned an ad without an ID."
        )


    return row


# ============================================================
# HTTP HANDLING
# ============================================================

def error_message(response):

    try:

        return (
            response.json()
            .get(
                "error",
                {},
            )
            .get(
                "message",
                "",
            )
            or response.text[:500]
        )

    except Exception:

        return response.text[:500]


def is_rate_limit(response):

    try:

        error = (
            response.json()
            .get(
                "error",
                {},
            )
        )

    except Exception:

        return False


    return (
        error.get("code")
        in {
            4,
            17,
            32,
            613,
        }
        or bool(
            error.get(
                "is_transient"
            )
        )
    )


def request_page(
    session,
    url,
    params,
):

    network_attempt = 0

    rate_attempt = 0


    while True:

        try:

            response = session.get(
                url,
                params=params,
                timeout=(
                    20,
                    180,
                ),
            )


        except requests.RequestException as exc:

            network_attempt += 1

            if (
                network_attempt
                > MAX_NETWORK_RETRIES
            ):

                raise RuntimeError(
                    f"Network failure: {exc}"
                ) from exc


            delay = min(
                60 * network_attempt,
                300,
            )


            print(
                f"    network error; "
                f"waiting {delay}s",
                flush=True,
            )

            time.sleep(delay)

            continue


        if response.ok:

            return response


        if (
            is_rate_limit(response)
            and
            rate_attempt
            < MAX_RATE_WAITS
        ):

            rate_attempt += 1


            retry_after = (
                response.headers
                .get(
                    "Retry-After"
                )
            )


            if retry_after:

                try:

                    delay = max(
                        30,
                        int(
                            float(
                                retry_after
                            )
                        ),
                    )

                except Exception:

                    delay = (
                        DEFAULT_RATE_WAIT_SECONDS
                    )

            else:

                delay = min(
                    DEFAULT_RATE_WAIT_SECONDS
                    * rate_attempt,
                    1800,
                )


            print(
                f"    rate limit; "
                f"waiting {delay}s",
                flush=True,
            )

            time.sleep(delay)

            continue


        return response


# ============================================================
# DATE SPLITTING
# ============================================================

class SplitRequired(
    RuntimeError
):
    pass


def should_split(response):

    if response.status_code >= 500:
        return True


    message = (
        error_message(
            response
        )
        .casefold()
    )


    return any(
        phrase in message
        for phrase in [
            "reduce the amount of data",
            "reduce the amount",
            "too much data",
        ]
    )


def split_dates(
    start,
    end,
):

    d1 = datetime.strptime(
        start,
        "%Y-%m-%d",
    ).date()

    d2 = datetime.strptime(
        end,
        "%Y-%m-%d",
    ).date()


    if d1 >= d2:

        raise RuntimeError(
            "Cannot split one-day query."
        )


    midpoint = (
        d1
        + timedelta(
            days=(
                d2 - d1
            ).days // 2
        )
    )


    left = (
        d1.isoformat(),
        midpoint.isoformat(),
    )


    right = (
        (
            midpoint
            + timedelta(
                days=1
            )
        ).isoformat(),
        d2.isoformat(),
    )


    return left, right


# ============================================================
# COLLECT ONE SEGMENT
# ============================================================


def collect_segment(
    session,
    token,
    brand,
    sector,
    page_id,
    date_min,
    date_max,
    output_path,
):

    base_url = (
        f"https://graph.facebook.com/"
        f"{API_VERSION}/ads_archive"
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = (
        output_path
        .with_suffix(".csv.part")
    )

    last_error = None


    # --------------------------------------------------------
    # Try progressively smaller page sizes.
    # --------------------------------------------------------

    for page_limit in PAGE_LIMITS:

        print(
            f"    trying page limit = {page_limit}",
            flush=True,
        )

        url = base_url

        params = {

            "search_page_ids":
                json.dumps(
                    [page_id]
                ),

            "ad_reached_countries":
                json.dumps(
                    [COUNTRY]
                ),

            "ad_active_status":
                AD_ACTIVE_STATUS,

            "ad_delivery_date_min":
                date_min,

            "ad_delivery_date_max":
                date_max,

            "fields":
                META_FIELDS,

            "limit":
                page_limit,

            "access_token":
                token,
        }


        pages = 0
        rows = 0


        try:

            with open(
                temp,
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=CSV_COLUMNS,
                )

                writer.writeheader()


                while True:

                    response = request_page(
                        session,
                        url,
                        params,
                    )


                    if not response.ok:

                        message = error_message(
                            response
                        )


                        if should_split(
                            response
                        ):

                            raise SplitRequired(
                                message
                            )


                        raise RuntimeError(
                            f"HTTP "
                            f"{response.status_code}: "
                            f"{message}"
                        )


                    payload = response.json()


                    records = (
                        payload.get(
                            "data",
                            [],
                        )
                        or []
                    )


                    pages += 1


                    for ad in records:

                        writer.writerow(
                            convert_ad(
                                ad,
                                brand,
                                sector,
                            )
                        )

                        rows += 1


                    f.flush()


                    print(
                        f"      page "
                        f"{pages:>3} | "
                        f"rows {rows:>7,}",
                        flush=True,
                    )


                    next_url = (
                        payload
                        .get(
                            "paging",
                            {},
                        )
                        .get("next")
                    )


                    if not next_url:

                        break


                    url = next_url

                    params = None


                    time.sleep(
                        PAGE_DELAY_SECONDS
                    )


            temp.replace(
                output_path
            )


            return {

                "date_min":
                    date_min,

                "date_max":
                    date_max,

                "page_limit_used":
                    page_limit,

                "pages":
                    pages,

                "rows":
                    rows,

                "file":
                    str(
                        output_path
                    ),

                "completed_at_utc":
                    utc_now(),
            }


        except SplitRequired as exc:

            last_error = exc


            # ------------------------------------------------
            # If page size can still be reduced, retry the
            # exact same date interval with a smaller limit.
            # ------------------------------------------------

            if (
                page_limit
                != PAGE_LIMITS[-1]
            ):

                print(
                    f"    request still too large "
                    f"at limit={page_limit}; "
                    "retrying same dates with "
                    "smaller page size",
                    flush=True,
                )

                continue


            # ------------------------------------------------
            # Even limit 25 failed.
            # Now tell collect_brand() to split the date.
            # ------------------------------------------------

            raise SplitRequired(
                str(exc)
            )


    raise SplitRequired(
        str(last_error)
        if last_error
        else "Meta request too large."
    )
# ============================================================
# LOAD SEGMENT VERSIONS
# ============================================================

def load_versions(
    brand_status,
):

    versions = defaultdict(
        list
    )


    segments = sorted(
        brand_status[
            "completed_segments"
        ].values(),
        key=lambda x: (
            x["date_min"],
            x["date_max"],
        ),
    )


    for segment in segments:

        path = Path(
            segment["file"]
        )


        with open(
            path,
            newline="",
            encoding="utf-8-sig",
        ) as f:

            reader = csv.DictReader(f)


            if reader.fieldnames != CSV_COLUMNS:

                raise RuntimeError(
                    f"Unexpected columns in {path}"
                )


            for row in reader:

                row = dict(row)


                row[
                    "_query_date_min"
                ] = segment[
                    "date_min"
                ]


                row[
                    "_query_date_max"
                ] = segment[
                    "date_max"
                ]


                versions[
                    row[
                        "meta_ad_id"
                    ]
                ].append(row)


    return versions


# ============================================================
# REPEATED-ID HELPERS
# ============================================================

def latest_row(rows):

    return max(
        rows,
        key=lambda r:
            str(
                r.get(
                    "collection_timestamp",
                    "",
                )
            )
    )


def has_demographics(row):

    return any(
        str(
            row.get(
                c,
                "",
            )
        ).strip()
        != ""
        for c
        in DEMOGRAPHIC_COLUMNS
    )


def latest_with_demographics(
    rows,
):

    candidates = [
        row
        for row in rows
        if has_demographics(row)
    ]

    return latest_row(
        candidates
        or rows
    )


def union_platforms(rows):

    values = set()


    for row in rows:

        for value in parse_json_list(
            row.get(
                PLATFORM_COLUMN,
                "",
            )
        ):

            value = str(
                value
            ).strip()

            if value:
                values.add(value)


    if not values:
        return ""


    return json.dumps(
        sorted(values),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def add_conflict(
    conflicts,
    brand,
    ad_id,
    tier,
    field,
    earlier,
    later,
):

    conflicts.append({
        "search_brand":
            brand,

        "meta_ad_id":
            ad_id,

        "difference_tier":
            tier,

        "differing_field":
            field,

        "earlier_value":
            earlier.get(
                field,
                "",
            ),

        "later_value":
            later.get(
                field,
                "",
            ),

        "earlier_collection_timestamp":
            earlier.get(
                "collection_timestamp",
                "",
            ),

        "later_collection_timestamp":
            later.get(
                "collection_timestamp",
                "",
            ),

        "earlier_query_date_min":
            earlier.get(
                "_query_date_min",
                "",
            ),

        "earlier_query_date_max":
            earlier.get(
                "_query_date_max",
                "",
            ),

        "later_query_date_min":
            later.get(
                "_query_date_min",
                "",
            ),

        "later_query_date_max":
            later.get(
                "_query_date_max",
                "",
            ),
    })


# ============================================================
# RECONCILE REPEATED META ID
# ============================================================

def reconcile_id(
    brand,
    ad_id,
    rows,
    conflicts,
    delivery_versions,
):

    ordered = sorted(
        rows,
        key=lambda r:
            str(
                r.get(
                    "collection_timestamp",
                    "",
                )
            )
    )


    final = dict(
        latest_row(
            ordered
        )
    )


    stats = {
        "repeated":
            len(ordered) > 1,

        "delivery_drift":
            False,

        "creative_conflict":
            False,

        "targeting_conflict":
            False,

        "start_conflict":
            False,

        "platform_variation":
            False,
    }


    if len(ordered) == 1:

        final.pop(
            "_query_date_min",
            None,
        )

        final.pop(
            "_query_date_max",
            None,
        )

        return final, stats


    # --------------------------------------------------------
    # PLATFORM
    # --------------------------------------------------------

    platform_states = {
        normalized_list(
            row.get(
                PLATFORM_COLUMN,
                "",
            )
        )
        for row in ordered
    }


    if len(platform_states) > 1:

        stats[
            "platform_variation"
        ] = True


    final[
        PLATFORM_COLUMN
    ] = union_platforms(
        ordered
    )


    # --------------------------------------------------------
    # DELIVERY / REACH DRIFT
    # --------------------------------------------------------

    delivery_fields = [
        STOP_COLUMN,
        *DEMOGRAPHIC_COLUMNS,
    ]


    delivery_states = {
        tuple(
            str(
                row.get(
                    field,
                    "",
                )
            ).strip()
            for field
            in delivery_fields
        )
        for row in ordered
    }


    if len(delivery_states) > 1:

        stats[
            "delivery_drift"
        ] = True


        for row in ordered:

            audit = {
                "query_date_min":
                    row.get(
                        "_query_date_min",
                        "",
                    ),

                "query_date_max":
                    row.get(
                        "_query_date_max",
                        "",
                    ),
            }


            for column in CSV_COLUMNS:

                audit[column] = (
                    row.get(
                        column,
                        "",
                    )
                )


            delivery_versions.append(
                audit
            )


    demographic_source = (
        latest_with_demographics(
            ordered
        )
    )


    for column in DEMOGRAPHIC_COLUMNS:

        final[column] = (
            demographic_source.get(
                column,
                "",
            )
        )


    # Latest nonblank stop timestamp

    stop_rows = [
        row
        for row in ordered
        if str(
            row.get(
                STOP_COLUMN,
                "",
            )
        ).strip()
    ]


    if stop_rows:

        final[
            STOP_COLUMN
        ] = (
            latest_row(
                stop_rows
            )
            .get(
                STOP_COLUMN,
                "",
            )
        )


    # --------------------------------------------------------
    # STRUCTURAL ANOMALIES
    # --------------------------------------------------------

    for index in range(
        1,
        len(ordered),
    ):

        earlier = ordered[
            index - 1
        ]

        later = ordered[
            index
        ]


        for field in CREATIVE_COLUMNS:

            if not values_equal(
                field,
                earlier.get(
                    field,
                    "",
                ),
                later.get(
                    field,
                    "",
                ),
            ):

                stats[
                    "creative_conflict"
                ] = True


                add_conflict(
                    conflicts,
                    brand,
                    ad_id,
                    "creative",
                    field,
                    earlier,
                    later,
                )


        for field in TARGETING_COLUMNS:

            if not values_equal(
                field,
                earlier.get(
                    field,
                    "",
                ),
                later.get(
                    field,
                    "",
                ),
            ):

                stats[
                    "targeting_conflict"
                ] = True


                add_conflict(
                    conflicts,
                    brand,
                    ad_id,
                    "targeting",
                    field,
                    earlier,
                    later,
                )


        if not values_equal(
            START_COLUMN,
            earlier.get(
                START_COLUMN,
                "",
            ),
            later.get(
                START_COLUMN,
                "",
            ),
        ):

            stats[
                "start_conflict"
            ] = True


            add_conflict(
                conflicts,
                brand,
                ad_id,
                "start_date_time",
                START_COLUMN,
                earlier,
                later,
            )


    final.pop(
        "_query_date_min",
        None,
    )

    final.pop(
        "_query_date_max",
        None,
    )


    return final, stats


# ============================================================
# CONSOLIDATE BRAND
# ============================================================

def consolidate_brand(
    brand,
    status,
):

    versions = load_versions(
        status
    )


    conflicts = []
    delivery_versions = []
    final_rows = []


    summary = {
        "unique_meta_ad_ids":
            len(versions),

        "repeated_meta_ids":
            0,

        "delivery_drift_ids":
            0,

        "platform_variation_ids":
            0,

        "creative_conflict_ids":
            0,

        "targeting_conflict_ids":
            0,

        "start_conflict_ids":
            0,
    }


    for ad_id, rows in versions.items():

        final, stats = (
            reconcile_id(
                brand,
                ad_id,
                rows,
                conflicts,
                delivery_versions,
            )
        )


        final_rows.append(
            final
        )


        for key, output_key in [
            (
                "repeated",
                "repeated_meta_ids",
            ),
            (
                "delivery_drift",
                "delivery_drift_ids",
            ),
            (
                "platform_variation",
                "platform_variation_ids",
            ),
            (
                "creative_conflict",
                "creative_conflict_ids",
            ),
            (
                "targeting_conflict",
                "targeting_conflict_ids",
            ),
            (
                "start_conflict",
                "start_conflict_ids",
            ),
        ]:

            if stats[key]:

                summary[
                    output_key
                ] += 1


    COMPLETED_BRAND_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    brand_file = (
        COMPLETED_BRAND_DIR
        / f"{slug(brand)}.csv"
    )


    temp = (
        brand_file
        .with_suffix(
            ".csv.part"
        )
    )


    with open(
        temp,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=CSV_COLUMNS,
        )

        writer.writeheader()

        writer.writerows(
            final_rows
        )


    temp.replace(
        brand_file
    )


    BRAND_AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    conflict_file = (
        BRAND_AUDIT_DIR
        / f"{slug(brand)}_conflicts.csv"
    )


    delivery_file = (
        BRAND_AUDIT_DIR
        / f"{slug(brand)}_delivery.csv"
    )


    with open(
        conflict_file,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
                CONFLICT_COLUMNS,
        )

        writer.writeheader()

        writer.writerows(
            conflicts
        )


    with open(
        delivery_file,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
                DELIVERY_AUDIT_COLUMNS,
        )

        writer.writeheader()

        writer.writerows(
            delivery_versions
        )


    return summary


# ============================================================
# REBUILD ONE MAIN CSV
# ============================================================

def rebuild_main_csv(
    progress,
):

    temp = (
        MAIN_CSV
        .with_suffix(
            ".csv.part"
        )
    )


    total = 0
    brands_written = []


    with open(
        temp,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as output:

        writer = csv.DictWriter(
            output,
            fieldnames=CSV_COLUMNS,
        )

        writer.writeheader()


        for (
            brand,
            _sector,
            _page_id,
        ) in BRANDS:

            status = (
                progress
                .get(
                    "brands",
                    {},
                )
                .get(
                    brand,
                    {},
                )
            )


            if not status.get(
                "complete"
            ):

                continue


            path = (
                COMPLETED_BRAND_DIR
                / f"{slug(brand)}.csv"
            )


            if not path.exists():

                raise RuntimeError(
                    f"{brand} is marked complete "
                    "but its temporary completed "
                    "file is missing."
                )


            with open(
                path,
                newline="",
                encoding="utf-8-sig",
            ) as f:

                reader = csv.DictReader(
                    f
                )


                if (
                    reader.fieldnames
                    != CSV_COLUMNS
                ):

                    raise RuntimeError(
                        f"Unexpected columns in {path}"
                    )


                for row in reader:

                    writer.writerow(
                        row
                    )

                    total += 1


            brands_written.append(
                brand
            )


    temp.replace(
        MAIN_CSV
    )


    return (
        total,
        brands_written,
    )


# ============================================================
# REBUILD PERMANENT AUDITS
# ============================================================

def rebuild_audits(
    progress,
):

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    all_conflicts = []
    all_delivery = []


    for (
        brand,
        _sector,
        _page_id,
    ) in BRANDS:

        status = (
            progress
            .get(
                "brands",
                {},
            )
            .get(
                brand,
                {},
            )
        )


        if not status.get(
            "complete"
        ):

            continue


        conflict_file = (
            BRAND_AUDIT_DIR
            / f"{slug(brand)}_conflicts.csv"
        )


        delivery_file = (
            BRAND_AUDIT_DIR
            / f"{slug(brand)}_delivery.csv"
        )


        if conflict_file.exists():

            with open(
                conflict_file,
                newline="",
                encoding="utf-8-sig",
            ) as f:

                all_conflicts.extend(
                    csv.DictReader(f)
                )


        if delivery_file.exists():

            with open(
                delivery_file,
                newline="",
                encoding="utf-8-sig",
            ) as f:

                all_delivery.extend(
                    csv.DictReader(f)
                )


    with open(
        CONFLICT_PATH,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
                CONFLICT_COLUMNS,
        )

        writer.writeheader()

        writer.writerows(
            all_conflicts
        )


    with open(
        DELIVERY_VERSION_PATH,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=
                DELIVERY_AUDIT_COLUMNS,
        )

        writer.writeheader()

        writer.writerows(
            all_delivery
        )


# ============================================================
# COLLECT ONE BRAND
# ============================================================

def collect_brand(
    session,
    token,
    brand,
    sector,
    page_id,
    progress,
):

    status = (
        progress
        .setdefault(
            "brands",
            {},
        )
        .setdefault(
            brand,
            {},
        )
    )


    if status.get(
        "complete"
    ):

        print(
            f"[{brand}] already complete; skipping",
            flush=True,
        )

        return


    if (
        not status.get(
            "pending"
        )
        and
        not status.get(
            "completed_segments"
        )
    ):

        status[
            "pending"
        ] = [
            [
                DATE_MIN,
                DATE_MAX,
            ]
        ]


        status[
            "completed_segments"
        ] = {}


        save_progress(
            progress
        )


    brand_segment_dir = (
        SEGMENT_DIR
        / slug(brand)
    )


    brand_segment_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    while status[
        "pending"
    ]:

        start, end = (
            status[
                "pending"
            ][0]
        )


        key = (
            f"{start}__{end}"
        )


        segment_file = (
            brand_segment_dir
            / f"{key}.csv"
        )


        print(
            f"[{brand}] "
            f"{start} to {end}",
            flush=True,
        )


        try:

            result = collect_segment(
                session,
                token,
                brand,
                sector,
                page_id,
                start,
                end,
                segment_file,
            )


        except SplitRequired as exc:

            d1 = datetime.strptime(
                start,
                "%Y-%m-%d",
            ).date()


            d2 = datetime.strptime(
                end,
                "%Y-%m-%d",
            ).date()


            if d1 >= d2:

                raise RuntimeError(
                    f"{brand}: Meta rejected "
                    f"even single-day query "
                    f"{start}: {exc}"
                ) from exc


            left, right = (
                split_dates(
                    start,
                    end,
                )
            )


            print(
                "    request too large; "
                "splitting into:",
                flush=True,
            )


            print(
                f"      {left[0]} "
                f"to {left[1]}",
                flush=True,
            )


            print(
                f"      {right[0]} "
                f"to {right[1]}",
                flush=True,
            )


            status[
                "pending"
            ] = [
                list(left),
                list(right),
                *status[
                    "pending"
                ][1:],
            ]


            save_progress(
                progress
            )


            continue


        status[
            "completed_segments"
        ][key] = result


        status[
            "pending"
        ].pop(0)


        progress[
            "updated_at_utc"
        ] = utc_now()


        save_progress(
            progress
        )


    summary = consolidate_brand(
        brand,
        status,
    )


    status.update(
        summary
    )


    status[
        "complete"
    ] = True


    status[
        "completed_at_utc"
    ] = utc_now()


    progress[
        "updated_at_utc"
    ] = utc_now()


    save_progress(
        progress
    )


    print(
        f"    DONE: "
        f"{status['unique_meta_ad_ids']:,} "
        "unique Meta ad IDs",
        flush=True,
    )


    if status[
        "repeated_meta_ids"
    ]:

        print(
            "    repeated IDs across "
            "split queries: "
            f"{status['repeated_meta_ids']:,}",
            flush=True,
        )


    if status[
        "delivery_drift_ids"
    ]:

        print(
            "    delivery/reach drift: "
            f"{status['delivery_drift_ids']:,}",
            flush=True,
        )


    structural = (
        status[
            "creative_conflict_ids"
        ]
        +
        status[
            "targeting_conflict_ids"
        ]
        +
        status[
            "start_conflict_ids"
        ]
    )


    if structural:

        print(
            "    structural anomalies "
            "logged; collection continued",
            flush=True,
        )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--brands",
        default="",
        help=(
            "Optional comma-separated subset, "
            'e.g. "Aldi Nord,dm"'
        ),
    )


    args = parser.parse_args()


    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    progress = (
        load_progress()
    )


    if (
        progress.get(
            "all_20_brands_complete"
        )
        and
        MAIN_CSV.exists()
    ):

        print(
            "All 20 brands are already complete."
        )

        print(
            f"Main file: {MAIN_CSV}"
        )

        return


    if progress:

        expected = {
            "api_version":
                API_VERSION,

            "country":
                COUNTRY,

            "date_min":
                DATE_MIN,

            "date_max":
                DATE_MAX,
        }


        differences = [
            (
                f"{key}: "
                f"existing="
                f"{progress.get(key)!r}, "
                f"requested={value!r}"
            )
            for key, value
            in expected.items()
            if (
                progress.get(key)
                != value
            )
        ]


        if differences:

            sys.exit(
                "ERROR: checkpoint settings "
                "differ from this script.\n"
                + "\n".join(
                    differences
                )
            )


    progress.update({
        "api_version":
            API_VERSION,

        "country":
            COUNTRY,

        "date_min":
            DATE_MIN,

        "date_max":
            DATE_MAX,

        "main_columns":
            CSV_COLUMNS,

        "updated_at_utc":
            utc_now(),

        "brands":
            progress.get(
                "brands",
                {},
            ),
    })


    save_progress(
        progress
    )


    requested = {
        x.strip().casefold()
        for x
        in args.brands.split(",")
        if x.strip()
    }


    selected = [
        item
        for item
        in BRANDS
        if (
            not requested
            or
            item[0]
            .casefold()
            in requested
        )
    ]


    unknown = (
        requested
        - {
            x[0].casefold()
            for x
            in BRANDS
        }
    )


    if unknown:

        sys.exit(
            "ERROR: unknown brand(s): "
            + ", ".join(
                sorted(unknown)
            )
        )


    token = get_token()

    session = requests.Session()


    print("=" * 72)

    print(
        "META AD LIBRARY RECOLLECTION"
    )

    print("=" * 72)

    print(
        f"Period:       "
        f"{DATE_MIN} to {DATE_MAX}"
    )

    print(
        f"Country:      {COUNTRY}"
    )

    print(
        f"Brands:       {len(selected)}"
    )

    print(
        "Recruitment filtering:  False"
    )

    print(
        "Creative deduplication: False"
    )

    print(
        "Snapshot URL:           False"
    )

    print(
        "Unknown age retained:   True"
    )

    print()


    for (
        brand,
        sector,
        page_id,
    ) in selected:

        try:

            collect_brand(
                session,
                token,
                brand,
                sector,
                page_id,
                progress,
            )


            total, included = (
                rebuild_main_csv(
                    progress
                )
            )


            rebuild_audits(
                progress
            )


            progress[
                "combined_rows"
            ] = total


            progress[
                "combined_brands"
            ] = included


            progress[
                "combined_brand_count"
            ] = len(
                included
            )


            progress.pop(
                "last_error",
                None,
            )


            save_progress(
                progress
            )


        except Exception as exc:

            progress[
                "last_error"
            ] = {
                "brand":
                    brand,

                "timestamp":
                    utc_now(),

                "message":
                    str(exc),
            }


            save_progress(
                progress
            )


            print()


            print(
                f"STOPPED at "
                f"{brand}: {exc}",
                flush=True,
            )


            print(
                "Checkpoint saved. "
                "Run the same command "
                "again to resume.",
                flush=True,
            )


            return


    all_complete = all(
        progress
        .get(
            "brands",
            {},
        )
        .get(
            brand,
            {},
        )
        .get(
            "complete",
            False,
        )
        for (
            brand,
            _sector,
            _page_id,
        )
        in BRANDS
    )


    progress[
        "all_20_brands_complete"
    ] = all_complete


    if all_complete:

        total, included = (
            rebuild_main_csv(
                progress
            )
        )


        rebuild_audits(
            progress
        )


        progress[
            "combined_rows"
        ] = total


        progress[
            "combined_brands"
        ] = included


        progress[
            "combined_brand_count"
        ] = len(
            included
        )


        progress[
            "completed_at_utc"
        ] = utc_now()


        save_progress(
            progress
        )


        if WORK_DIR.exists():

            shutil.rmtree(
                WORK_DIR
            )


    print()

    print("=" * 72)

    print(
        f"Completed brands: "
        f"{progress.get('combined_brand_count', 0)}"
    )

    print(
        f"Main rows: "
        f"{progress.get('combined_rows', 0):,}"
    )

    print(
        f"All 20 complete: "
        f"{all_complete}"
    )

    print(
        f"Main CSV:\n"
        f"{MAIN_CSV}"
    )

    print(
        f"Checkpoint:\n"
        f"{PROGRESS_PATH}"
    )

    print(
        f"Conflict audit:\n"
        f"{CONFLICT_PATH}"
    )

    print(
        f"Delivery audit:\n"
        f"{DELIVERY_VERSION_PATH}"
    )


if __name__ == "__main__":

    main()