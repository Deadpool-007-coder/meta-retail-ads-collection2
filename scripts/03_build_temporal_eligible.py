#!/usr/bin/env python3

"""
03_build_temporal_eligible.py

Build the temporal-eligible intermediate dataset from the untouched
raw recollection.

Input:
    ads_recollection_all20.csv

Eligibility rule:
    2025-09-06 <= ad_delivery_start_date_time <= 2026-09-05

Output:
    data/intermediate/ads_temporal_eligible.csv

Also writes:
    validation/temporal_filter_summary.csv

The raw recollection file is never modified.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = ROOT / "ads_recollection_all20.csv"

OUT_DIR = ROOT / "data" / "intermediate"

OUTPUT_CSV = (
    OUT_DIR
    / "ads_temporal_eligible.csv"
)

VALIDATION_DIR = ROOT / "validation"

SUMMARY_CSV = (
    VALIDATION_DIR
    / "temporal_filter_summary.csv"
)


DATE_MIN = datetime.strptime(
    "2025-09-06",
    "%Y-%m-%d",
).date()

DATE_MAX = datetime.strptime(
    "2026-09-05",
    "%Y-%m-%d",
).date()

START_COL = "ad_delivery_start_date_time"

EXPECTED_RAW_ROWS = 62436
EXPECTED_ELIGIBLE_ROWS = 60329
EXPECTED_EXCLUDED_ROWS = 2107


def parse_date(value):
    text = str(
        value or ""
    ).strip()

    if not text:
        return None

    try:
        return datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        ).date()
    except Exception:
        pass

    try:
        return datetime.strptime(
            text[:10],
            "%Y-%m-%d",
        ).date()
    except Exception:
        return None


def write_summary(rows):
    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with SUMMARY_CSV.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "metric",
                "value",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    if not INPUT_CSV.exists():
        sys.exit(
            "ERROR: input file not found:\n"
            f"{INPUT_CSV}"
        )

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_output = (
        OUTPUT_CSV
        .with_suffix(
            ".csv.part"
        )
    )

    total = 0
    eligible = 0
    excluded_before = 0
    excluded_after = 0
    excluded_missing = 0
    invalid_nonblank = 0

    brand_included = Counter()
    brand_excluded_before = Counter()

    with INPUT_CSV.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as src:

        reader = csv.DictReader(
            src
        )

        fields = (
            reader.fieldnames
            or []
        )

        if START_COL not in fields:
            sys.exit(
                f"ERROR: missing required column: {START_COL}"
            )

        with temp_output.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as dst:

            writer = csv.DictWriter(
                dst,
                fieldnames=fields,
            )

            writer.writeheader()

            for row in reader:
                total += 1

                raw_start = row.get(
                    START_COL,
                    "",
                )

                start_date = parse_date(
                    raw_start
                )

                if (
                    str(
                        raw_start
                        or ""
                    ).strip()
                    and
                    start_date is None
                ):
                    invalid_nonblank += 1

                if start_date is None:
                    excluded_missing += 1
                    continue

                if start_date < DATE_MIN:
                    excluded_before += 1

                    brand = str(
                        row.get(
                            "search_brand",
                            "",
                        )
                    ).strip()

                    brand_excluded_before[
                        brand
                    ] += 1

                    continue

                if start_date > DATE_MAX:
                    excluded_after += 1
                    continue

                writer.writerow(
                    row
                )

                eligible += 1

                brand = str(
                    row.get(
                        "search_brand",
                        "",
                    )
                ).strip()

                brand_included[
                    brand
                ] += 1

    # Guardrails against accidentally using the wrong input/version.
    if total != EXPECTED_RAW_ROWS:
        temp_output.unlink(
            missing_ok=True
        )
        sys.exit(
            "ERROR: raw row count differs from validated collection.\n"
            f"Expected: {EXPECTED_RAW_ROWS:,}\n"
            f"Found:    {total:,}"
        )

    if eligible != EXPECTED_ELIGIBLE_ROWS:
        temp_output.unlink(
            missing_ok=True
        )
        sys.exit(
            "ERROR: temporal-eligible row count does not reproduce "
            "the completed audit.\n"
            f"Expected: {EXPECTED_ELIGIBLE_ROWS:,}\n"
            f"Found:    {eligible:,}"
        )

    excluded_total = (
        excluded_before
        + excluded_after
        + excluded_missing
    )

    if excluded_total != EXPECTED_EXCLUDED_ROWS:
        temp_output.unlink(
            missing_ok=True
        )
        sys.exit(
            "ERROR: temporal exclusion count does not reproduce "
            "the completed audit.\n"
            f"Expected: {EXPECTED_EXCLUDED_ROWS:,}\n"
            f"Found:    {excluded_total:,}"
        )

    if invalid_nonblank != 0:
        temp_output.unlink(
            missing_ok=True
        )
        sys.exit(
            "ERROR: one or more nonblank start timestamps "
            "could not be parsed."
        )

    temp_output.replace(
        OUTPUT_CSV
    )

    summary = [
        {
            "metric": "raw_rows",
            "value": total,
        },
        {
            "metric": "eligible_rows",
            "value": eligible,
        },
        {
            "metric": "excluded_total",
            "value": excluded_total,
        },
        {
            "metric": "excluded_start_before_window",
            "value": excluded_before,
        },
        {
            "metric": "excluded_start_after_window",
            "value": excluded_after,
        },
        {
            "metric": "excluded_missing_start",
            "value": excluded_missing,
        },
        {
            "metric": "invalid_nonblank_start_timestamp",
            "value": invalid_nonblank,
        },
    ]

    for brand in sorted(
        set(
            brand_included
        )
        | set(
            brand_excluded_before
        )
    ):
        summary.append({
            "metric":
                f"brand_included::{brand}",
            "value":
                brand_included[
                    brand
                ],
        })

        summary.append({
            "metric":
                f"brand_excluded_before::{brand}",
            "value":
                brand_excluded_before[
                    brand
                ],
        })

    write_summary(
        summary
    )

    print(
        "TEMPORAL FILTER BUILD"
    )

    print(
        "=" * 72
    )

    print(
        f"Raw rows:                 {total:,}"
    )

    print(
        f"Eligible rows:            {eligible:,}"
    )

    print(
        f"Excluded total:           {excluded_total:,}"
    )

    print(
        f"  Start before window:    {excluded_before:,}"
    )

    print(
        f"  Start after window:     {excluded_after:,}"
    )

    print(
        f"  Missing start:          {excluded_missing:,}"
    )

    print()

    print(
        f"Output:\n{OUTPUT_CSV}"
    )

    print(
        f"Summary:\n{SUMMARY_CSV}"
    )

    print()

    print(
        "Raw recollection was not modified."
    )


if __name__ == "__main__":
    main()
