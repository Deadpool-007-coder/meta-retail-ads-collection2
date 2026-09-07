#!/usr/bin/env python3

"""
02_audit_temporal_eligibility.py

Read-only temporal audit for:
    ads_recollection_all20.csv

Study API delivery window:
    2025-09-06 through 2026-09-05

Purpose:
- quantify ads starting before / inside / after the requested API window;
- quantify stop-time status relative to the same window;
- produce brand- and sector-level summaries;
- do NOT filter or modify the recollection dataset.

Outputs:
    validation/
        temporal_eligibility_summary.csv
        temporal_eligibility_by_brand.csv
        temporal_eligibility_by_sector.csv
        temporal_eligibility_details.txt
"""

from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MAIN_CSV = ROOT / "ads_recollection_all20.csv"

OUT_DIR = ROOT / "validation"

SUMMARY_CSV = (
    OUT_DIR
    / "temporal_eligibility_summary.csv"
)

BY_BRAND_CSV = (
    OUT_DIR
    / "temporal_eligibility_by_brand.csv"
)

BY_SECTOR_CSV = (
    OUT_DIR
    / "temporal_eligibility_by_sector.csv"
)

DETAILS_TXT = (
    OUT_DIR
    / "temporal_eligibility_details.txt"
)


DATE_MIN = "2025-09-06"
DATE_MAX = "2026-09-05"


START_COL = "ad_delivery_start_date_time"
STOP_COL = "ad_delivery_stop_date_time"

BRAND_COL = "search_brand"
SECTOR_COL = "sector"
ID_COL = "meta_ad_id"


def parse_date_only(value: str):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    # Meta timestamps are typically ISO-8601.
    # We only need the calendar date for window classification.
    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()

    except Exception:
        pass

    # Defensive fallback for plain YYYY-MM-DD.
    try:
        return datetime.strptime(
            text[:10],
            "%Y-%m-%d",
        ).date()

    except Exception:
        return None


WINDOW_START = datetime.strptime(
    DATE_MIN,
    "%Y-%m-%d",
).date()

WINDOW_END = datetime.strptime(
    DATE_MAX,
    "%Y-%m-%d",
).date()


def classify_start(d):
    if d is None:
        return "start_missing"

    if d < WINDOW_START:
        return "start_before_window"

    if d > WINDOW_END:
        return "start_after_window"

    return "start_inside_window"


def classify_stop(d):
    if d is None:
        return "stop_missing"

    if d < WINDOW_START:
        return "stop_before_window"

    if d > WINDOW_END:
        return "stop_after_window"

    return "stop_inside_window"


def write_csv(path, rows, fields):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(rows)


def pct(n, d):
    if not d:
        return ""
    return round(
        100.0 * n / d,
        4,
    )


def main():
    if not MAIN_CSV.exists():
        sys.exit(
            "ERROR: main recollection file not found:\n"
            f"{MAIN_CSV}"
        )

    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total = 0

    overall = Counter()
    by_brand = defaultdict(Counter)
    by_sector = defaultdict(Counter)

    invalid_start_parse = 0
    invalid_stop_parse = 0

    earliest_start = None
    latest_start = None

    earliest_stop = None
    latest_stop = None

    with MAIN_CSV.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        reader = csv.DictReader(f)

        required = {
            ID_COL,
            BRAND_COL,
            SECTOR_COL,
            START_COL,
            STOP_COL,
        }

        missing = required - set(
            reader.fieldnames or []
        )

        if missing:
            sys.exit(
                "ERROR: missing required column(s): "
                + ", ".join(
                    sorted(missing)
                )
            )

        for row in reader:
            total += 1

            brand = str(
                row.get(
                    BRAND_COL,
                    "",
                )
            ).strip()

            sector = str(
                row.get(
                    SECTOR_COL,
                    "",
                )
            ).strip()

            start_raw = row.get(
                START_COL,
                ""
            )

            stop_raw = row.get(
                STOP_COL,
                ""
            )

            start_date = parse_date_only(
                start_raw
            )

            stop_date = parse_date_only(
                stop_raw
            )

            if (
                str(start_raw or "").strip()
                and start_date is None
            ):
                invalid_start_parse += 1

            if (
                str(stop_raw or "").strip()
                and stop_date is None
            ):
                invalid_stop_parse += 1

            start_class = classify_start(
                start_date
            )

            stop_class = classify_stop(
                stop_date
            )

            overall[start_class] += 1
            overall[stop_class] += 1

            by_brand[brand]["rows"] += 1
            by_brand[brand][start_class] += 1
            by_brand[brand][stop_class] += 1

            by_sector[sector]["rows"] += 1
            by_sector[sector][start_class] += 1
            by_sector[sector][stop_class] += 1

            if start_date is not None:
                if (
                    earliest_start is None
                    or start_date < earliest_start
                ):
                    earliest_start = start_date

                if (
                    latest_start is None
                    or start_date > latest_start
                ):
                    latest_start = start_date

            if stop_date is not None:
                if (
                    earliest_stop is None
                    or stop_date < earliest_stop
                ):
                    earliest_stop = stop_date

                if (
                    latest_stop is None
                    or stop_date > latest_stop
                ):
                    latest_stop = stop_date

    # --------------------------------------------------------
    # Derived cohort quantities
    # --------------------------------------------------------

    start_inside = overall[
        "start_inside_window"
    ]

    start_before = overall[
        "start_before_window"
    ]

    start_after = overall[
        "start_after_window"
    ]

    start_missing = overall[
        "start_missing"
    ]

    stop_inside = overall[
        "stop_inside_window"
    ]

    stop_before = overall[
        "stop_before_window"
    ]

    stop_after = overall[
        "stop_after_window"
    ]

    stop_missing = overall[
        "stop_missing"
    ]

    summary_rows = []

    def add(metric, value, note=""):
        summary_rows.append({
            "metric": metric,
            "value": value,
            "note": note,
        })

    add(
        "raw_rows",
        total,
    )

    add(
        "api_window_start",
        DATE_MIN,
    )

    add(
        "api_window_end",
        DATE_MAX,
    )

    add(
        "earliest_start_date",
        earliest_start.isoformat()
        if earliest_start
        else "",
    )

    add(
        "latest_start_date",
        latest_start.isoformat()
        if latest_start
        else "",
    )

    add(
        "earliest_stop_date",
        earliest_stop.isoformat()
        if earliest_stop
        else "",
    )

    add(
        "latest_stop_date",
        latest_stop.isoformat()
        if latest_stop
        else "",
    )

    add(
        "start_before_window",
        start_before,
        f"{pct(start_before, total)}%",
    )

    add(
        "start_inside_window",
        start_inside,
        f"{pct(start_inside, total)}%",
    )

    add(
        "start_after_window",
        start_after,
        f"{pct(start_after, total)}%",
    )

    add(
        "start_missing",
        start_missing,
        f"{pct(start_missing, total)}%",
    )

    add(
        "stop_before_window",
        stop_before,
        f"{pct(stop_before, total)}%",
    )

    add(
        "stop_inside_window",
        stop_inside,
        f"{pct(stop_inside, total)}%",
    )

    add(
        "stop_after_window",
        stop_after,
        f"{pct(stop_after, total)}%",
    )

    add(
        "stop_missing",
        stop_missing,
        f"{pct(stop_missing, total)}%",
    )

    add(
        "launch_cohort_rows_if_start_inside_window",
        start_inside,
        (
            "Rows that would remain if analytical "
            "eligibility were defined by start date "
            "inside 2025-09-06 through 2026-09-05."
        ),
    )

    add(
        "delivery_window_rows_current_raw_collection",
        total,
        (
            "All rows returned by the API delivery-date "
            "window before any temporal analytical filter."
        ),
    )

    add(
        "difference_delivery_window_vs_launch_cohort",
        total - start_inside,
        (
            "Rows in current raw collection that would not "
            "belong to a strict launch cohort."
        ),
    )

    add(
        "invalid_nonblank_start_timestamp_parse",
        invalid_start_parse,
    )

    add(
        "invalid_nonblank_stop_timestamp_parse",
        invalid_stop_parse,
    )

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "metric",
            "value",
            "note",
        ],
    )

    # --------------------------------------------------------
    # By-brand / sector tables
    # --------------------------------------------------------

    detail_fields = [
        "group",
        "rows",
        "start_before_window",
        "start_inside_window",
        "start_after_window",
        "start_missing",
        "stop_before_window",
        "stop_inside_window",
        "stop_after_window",
        "stop_missing",
        "pct_start_before_window",
        "pct_start_inside_window",
        "pct_stop_after_window",
        "pct_stop_missing",
    ]

    brand_rows = []

    for brand in sorted(
        by_brand
    ):
        c = by_brand[brand]
        n = c["rows"]

        brand_rows.append({
            "group": brand,
            "rows": n,
            "start_before_window":
                c["start_before_window"],
            "start_inside_window":
                c["start_inside_window"],
            "start_after_window":
                c["start_after_window"],
            "start_missing":
                c["start_missing"],
            "stop_before_window":
                c["stop_before_window"],
            "stop_inside_window":
                c["stop_inside_window"],
            "stop_after_window":
                c["stop_after_window"],
            "stop_missing":
                c["stop_missing"],
            "pct_start_before_window":
                pct(
                    c["start_before_window"],
                    n,
                ),
            "pct_start_inside_window":
                pct(
                    c["start_inside_window"],
                    n,
                ),
            "pct_stop_after_window":
                pct(
                    c["stop_after_window"],
                    n,
                ),
            "pct_stop_missing":
                pct(
                    c["stop_missing"],
                    n,
                ),
        })

    write_csv(
        BY_BRAND_CSV,
        brand_rows,
        detail_fields,
    )

    sector_rows = []

    for sector in sorted(
        by_sector
    ):
        c = by_sector[sector]
        n = c["rows"]

        sector_rows.append({
            "group": sector,
            "rows": n,
            "start_before_window":
                c["start_before_window"],
            "start_inside_window":
                c["start_inside_window"],
            "start_after_window":
                c["start_after_window"],
            "start_missing":
                c["start_missing"],
            "stop_before_window":
                c["stop_before_window"],
            "stop_inside_window":
                c["stop_inside_window"],
            "stop_after_window":
                c["stop_after_window"],
            "stop_missing":
                c["stop_missing"],
            "pct_start_before_window":
                pct(
                    c["start_before_window"],
                    n,
                ),
            "pct_start_inside_window":
                pct(
                    c["start_inside_window"],
                    n,
                ),
            "pct_stop_after_window":
                pct(
                    c["stop_after_window"],
                    n,
                ),
            "pct_stop_missing":
                pct(
                    c["stop_missing"],
                    n,
                ),
        })

    write_csv(
        BY_SECTOR_CSV,
        sector_rows,
        detail_fields,
    )

    # --------------------------------------------------------
    # Human-readable report
    # --------------------------------------------------------

    lines = [
        "TEMPORAL ELIGIBILITY AUDIT",
        "=" * 72,
        f"Rows: {total:,}",
        f"API window: {DATE_MIN} to {DATE_MAX}",
        "",
        "START DATE CLASSIFICATION",
        f"Before window: {start_before:,} ({pct(start_before, total)}%)",
        f"Inside window: {start_inside:,} ({pct(start_inside, total)}%)",
        f"After window:  {start_after:,} ({pct(start_after, total)}%)",
        f"Missing:       {start_missing:,} ({pct(start_missing, total)}%)",
        "",
        "STOP DATE CLASSIFICATION",
        f"Before window: {stop_before:,} ({pct(stop_before, total)}%)",
        f"Inside window: {stop_inside:,} ({pct(stop_inside, total)}%)",
        f"After window:  {stop_after:,} ({pct(stop_after, total)}%)",
        f"Missing:       {stop_missing:,} ({pct(stop_missing, total)}%)",
        "",
        "DATE RANGES",
        f"Earliest start: {earliest_start}",
        f"Latest start:   {latest_start}",
        f"Earliest stop:  {earliest_stop}",
        f"Latest stop:    {latest_stop}",
        "",
        "COHORT COMPARISON",
        f"Current delivery-window collection: {total:,}",
        f"Strict launch cohort (start inside window): {start_inside:,}",
        f"Difference: {total - start_inside:,}",
        "",
        "TIMESTAMP PARSING",
        f"Invalid nonblank start timestamps: {invalid_start_parse:,}",
        f"Invalid nonblank stop timestamps:  {invalid_stop_parse:,}",
        "",
        "OUTPUTS",
        f"  {SUMMARY_CSV}",
        f"  {BY_BRAND_CSV}",
        f"  {BY_SECTOR_CSV}",
        f"  {DETAILS_TXT}",
    ]

    DETAILS_TXT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(
        "\n".join(lines)
    )


if __name__ == "__main__":
    main()
