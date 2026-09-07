#!/usr/bin/env python3

"""
07_apply_validated_eligibility.py

Apply validated commercial-eligibility decisions and build the locked
eligibility dataset.

INPUTS
------
data/intermediate/ads_temporal_eligible.csv
audit/commercial_eligibility_exclusions.csv
audit/commercial_eligibility_manual_decisions.csv

OUTPUTS
-------
data/intermediate/ads_eligibility_locked.csv
audit/commercial_eligibility_final_exclusion_ledger.csv
validation/commercial_eligibility_final_summary.csv

IMPORTANT
---------
The independent positive and negative validation samples are diagnostic only.
They are NOT used to alter individual production rows.

This script applies:
1. all automatic exclusions from Script 04; and
2. only manual-review observations explicitly adjudicated as "exclude".

The temporal-eligible source dataset is never modified.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

TEMPORAL_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_temporal_eligible.csv"
)

AUTO_EXCLUSIONS_CSV = (
    ROOT
    / "audit"
    / "commercial_eligibility_exclusions.csv"
)

MANUAL_DECISIONS_CSV = (
    ROOT
    / "audit"
    / "commercial_eligibility_manual_decisions.csv"
)

OUTPUT_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_eligibility_locked.csv"
)

FINAL_LEDGER_CSV = (
    ROOT
    / "audit"
    / "commercial_eligibility_final_exclusion_ledger.csv"
)

SUMMARY_CSV = (
    ROOT
    / "validation"
    / "commercial_eligibility_final_summary.csv"
)


# ============================================================
# EXPECTED COUNTS
# ============================================================

EXPECTED_TEMPORAL_ROWS = 60329
EXPECTED_AUTO_EXCLUSIONS = 6480
EXPECTED_MANUAL_EXCLUSIONS = 55
EXPECTED_FINAL_ROWS = 53794


# ============================================================
# HELPERS
# ============================================================

def read_csv(path: Path):
    if not path.exists():
        sys.exit(
            "ERROR: required file not found:\n"
            f"{path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as f:
        reader = csv.DictReader(f)
        return list(reader), (reader.fieldnames or [])


def write_csv(
    path: Path,
    rows: list[dict],
    fieldnames: list[str],
):
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
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def pct(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        100.0 * numerator / denominator,
        4,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    temporal, temporal_fields = read_csv(
        TEMPORAL_CSV
    )

    automatic, _ = read_csv(
        AUTO_EXCLUSIONS_CSV
    )

    manual, manual_fields = read_csv(
        MANUAL_DECISIONS_CSV
    )

    # --------------------------------------------------------
    # Basic schema checks
    # --------------------------------------------------------

    required_temporal = {
        "meta_ad_id",
        "search_brand",
        "sector",
    }

    if not required_temporal.issubset(
        set(temporal_fields)
    ):
        sys.exit(
            "ERROR: temporal dataset is missing required columns."
        )

    required_manual = {
        "meta_ad_id",
        "final_classification",
        "final_manual_category",
    }

    if not required_manual.issubset(
        set(manual_fields)
    ):
        sys.exit(
            "ERROR: manual-decision file is missing required columns."
        )

    # --------------------------------------------------------
    # Count guardrails
    # --------------------------------------------------------

    if len(temporal) != EXPECTED_TEMPORAL_ROWS:
        sys.exit(
            "ERROR: temporal row count mismatch.\n"
            f"Expected: {EXPECTED_TEMPORAL_ROWS:,}\n"
            f"Found:    {len(temporal):,}"
        )

    if len(automatic) != EXPECTED_AUTO_EXCLUSIONS:
        sys.exit(
            "ERROR: automatic exclusion count mismatch.\n"
            f"Expected: {EXPECTED_AUTO_EXCLUSIONS:,}\n"
            f"Found:    {len(automatic):,}"
        )

    # --------------------------------------------------------
    # Validate Meta IDs
    # --------------------------------------------------------

    temporal_ids = [
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()
        for row in temporal
    ]

    if "" in temporal_ids:
        sys.exit(
            "ERROR: blank Meta ad ID in temporal dataset."
        )

    if len(
        temporal_ids
    ) != len(
        set(
            temporal_ids
        )
    ):
        sys.exit(
            "ERROR: duplicate Meta ad IDs in temporal dataset."
        )

    temporal_id_set = set(
        temporal_ids
    )

    auto_ids = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()
        for row in automatic
    }

    if "" in auto_ids:
        sys.exit(
            "ERROR: blank Meta ad ID in automatic exclusions."
        )

    if not auto_ids.issubset(
        temporal_id_set
    ):
        sys.exit(
            "ERROR: at least one automatic exclusion ID "
            "is absent from the temporal dataset."
        )

    # --------------------------------------------------------
    # Manual exclusions
    # --------------------------------------------------------

    manual_exclude_rows = [
        row
        for row in manual
        if str(
            row.get(
                "final_classification",
                "",
            )
        ).strip().casefold()
        == "noncommercial"
    ]

    manual_exclude_ids = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()
        for row in manual_exclude_rows
    }

    if "" in manual_exclude_ids:
        sys.exit(
            "ERROR: blank Meta ad ID among manual exclusions."
        )

    if len(
        manual_exclude_ids
    ) != EXPECTED_MANUAL_EXCLUSIONS:
        sys.exit(
            "ERROR: manual exclusion count mismatch.\n"
            f"Expected: {EXPECTED_MANUAL_EXCLUSIONS:,}\n"
            f"Found:    {len(manual_exclude_ids):,}"
        )

    if not manual_exclude_ids.issubset(
        temporal_id_set
    ):
        sys.exit(
            "ERROR: at least one manual exclusion ID "
            "is absent from the temporal dataset."
        )

    overlap = (
        auto_ids
        & manual_exclude_ids
    )

    if overlap:
        sys.exit(
            "ERROR: automatic and manual exclusion sets overlap.\n"
            f"Overlap count: {len(overlap):,}"
        )

    # --------------------------------------------------------
    # Build locked dataset
    # --------------------------------------------------------

    final_exclude_ids = (
        auto_ids
        | manual_exclude_ids
    )

    retained = [
        row
        for row in temporal
        if str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()
        not in final_exclude_ids
    ]

    if len(
        retained
    ) != EXPECTED_FINAL_ROWS:
        sys.exit(
            "ERROR: locked eligibility row count mismatch.\n"
            f"Expected: {EXPECTED_FINAL_ROWS:,}\n"
            f"Found:    {len(retained):,}"
        )

    # --------------------------------------------------------
    # Final exclusion ledger
    # --------------------------------------------------------

    temporal_lookup = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip(): row
        for row in temporal
    }

    ledger = []

    for row in automatic:
        meta_id = str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()

        base = temporal_lookup[
            meta_id
        ]

        ledger.append({
            "meta_ad_id":
                meta_id,
            "search_brand":
                base.get(
                    "search_brand",
                    "",
                ),
            "sector":
                base.get(
                    "sector",
                    "",
                ),
            "exclusion_stage":
                "automatic",
            "exclusion_reason":
                row.get(
                    "eligibility_reason",
                    "",
                ),
            "exclusion_rule":
                row.get(
                    "matched_rule",
                    "",
                ),
            "manual_category":
                "",
        })

    manual_lookup = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip(): row
        for row in manual_exclude_rows
    }

    for meta_id in sorted(
        manual_exclude_ids
    ):
        base = temporal_lookup[
            meta_id
        ]

        decision = manual_lookup[
            meta_id
        ]

        ledger.append({
            "meta_ad_id":
                meta_id,
            "search_brand":
                base.get(
                    "search_brand",
                    "",
                ),
            "sector":
                base.get(
                    "sector",
                    "",
                ),
            "exclusion_stage":
                "manual_review",
            "exclusion_reason":
                decision.get(
                    "final_manual_category",
                    "",
                ),
            "exclusion_rule":
                "",
            "manual_category":
                decision.get(
                    "final_manual_category",
                    "",
                ),
        })

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    write_csv(
        OUTPUT_CSV,
        retained,
        temporal_fields,
    )

    ledger_fields = [
        "meta_ad_id",
        "search_brand",
        "sector",
        "exclusion_stage",
        "exclusion_reason",
        "exclusion_rule",
        "manual_category",
    ]

    write_csv(
        FINAL_LEDGER_CSV,
        ledger,
        ledger_fields,
    )

    summary_rows = [
        {
            "metric":
                "temporal_eligible_rows",
            "value":
                len(
                    temporal
                ),
        },
        {
            "metric":
                "automatic_exclusions",
            "value":
                len(
                    auto_ids
                ),
        },
        {
            "metric":
                "manual_review_exclusions",
            "value":
                len(
                    manual_exclude_ids
                ),
        },
        {
            "metric":
                "total_final_exclusions",
            "value":
                len(
                    final_exclude_ids
                ),
        },
        {
            "metric":
                "locked_eligibility_rows",
            "value":
                len(
                    retained
                ),
        },
        {
            "metric":
                "overall_exclusion_pct",
            "value":
                pct(
                    len(
                        final_exclude_ids
                    ),
                    len(
                        temporal
                    ),
                ),
        },
    ]

    write_csv(
        SUMMARY_CSV,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    # --------------------------------------------------------
    # Terminal report
    # --------------------------------------------------------

    print(
        "VALIDATED ELIGIBILITY BUILD"
    )

    print(
        "=" * 72
    )

    print(
        f"Temporal-eligible rows:       {len(temporal):,}"
    )

    print(
        f"Automatic exclusions:         {len(auto_ids):,}"
    )

    print(
        f"Manual-review exclusions:     {len(manual_exclude_ids):,}"
    )

    print(
        f"Total final exclusions:       {len(final_exclude_ids):,}"
    )

    print(
        f"Locked eligibility rows:      {len(retained):,}"
    )

    print()

    print(
        "IMPORTANT: positive/negative validation samples were diagnostic only "
        "and were not used to alter individual production rows."
    )

    print()

    print(
        "OUTPUTS"
    )

    print(
        f"  Locked dataset:\n"
        f"    {OUTPUT_CSV}"
    )

    print(
        f"  Final exclusion ledger:\n"
        f"    {FINAL_LEDGER_CSV}"
    )

    print(
        f"  Summary:\n"
        f"    {SUMMARY_CSV}"
    )

    print()

    print(
        "Temporal source dataset was not modified."
    )


if __name__ == "__main__":
    main()
