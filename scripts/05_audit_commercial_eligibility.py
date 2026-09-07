#!/usr/bin/env python3

"""
05_audit_commercial_eligibility.py

Audit-only script for the commercial-eligibility classification.

It does NOT delete or modify any dataset.

INPUTS
------
data/intermediate/ads_temporal_eligible.csv
audit/commercial_eligibility_exclusions.csv
audit/commercial_eligibility_manual_review.csv

OUTPUTS
-------
validation/commercial_eligibility_audit_by_brand.csv
validation/commercial_eligibility_audit_by_sector.csv
validation/commercial_eligibility_audit_by_rule.csv
validation/commercial_eligibility_brand_concentration.csv
validation/commercial_eligibility_audit_details.txt

audit/commercial_eligibility_validation_sample.csv
audit/nonrecruitment_auto_exclusions_all.csv

PURPOSE
-------
1. Check whether automatic exclusions are concentrated in particular brands.
2. Check exclusion rates by sector.
3. Break automatic exclusions down by rule and reason.
4. Export ALL non-recruitment automatic exclusions for inspection.
5. Create a reproducible stratified sample of recruitment exclusions for
   manual validation.

No source dataset is modified.
"""

from __future__ import annotations

import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TEMPORAL_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_temporal_eligible.csv"
)

EXCLUSIONS_CSV = (
    ROOT
    / "audit"
    / "commercial_eligibility_exclusions.csv"
)

MANUAL_REVIEW_CSV = (
    ROOT
    / "audit"
    / "commercial_eligibility_manual_review.csv"
)

VALIDATION_DIR = ROOT / "validation"
AUDIT_DIR = ROOT / "audit"

BY_BRAND_OUT = (
    VALIDATION_DIR
    / "commercial_eligibility_audit_by_brand.csv"
)

BY_SECTOR_OUT = (
    VALIDATION_DIR
    / "commercial_eligibility_audit_by_sector.csv"
)

BY_RULE_OUT = (
    VALIDATION_DIR
    / "commercial_eligibility_audit_by_rule.csv"
)

BRAND_CONCENTRATION_OUT = (
    VALIDATION_DIR
    / "commercial_eligibility_brand_concentration.csv"
)

DETAILS_OUT = (
    VALIDATION_DIR
    / "commercial_eligibility_audit_details.txt"
)

VALIDATION_SAMPLE_OUT = (
    AUDIT_DIR
    / "commercial_eligibility_validation_sample.csv"
)

NONRECRUITMENT_OUT = (
    AUDIT_DIR
    / "nonrecruitment_auto_exclusions_all.csv"
)

EXPECTED_TEMPORAL_ROWS = 60329

RANDOM_SEED = 20260907

# Aim for a practical manual-validation sample while ensuring
# representation across brands and matched rules.
TARGET_RECRUITMENT_SAMPLE = 400
MIN_PER_BRAND_RULE_CELL = 2


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
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
    fields: list[str],
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
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def pct(n: int, d: int) -> float:
    if not d:
        return 0.0

    return round(
        100.0 * n / d,
        4,
    )


def stratified_sample(
    rows: list[dict],
    target_n: int,
) -> list[dict]:
    """
    Reproducible sample stratified by search_brand x matched_rule.

    First allocates a small minimum to each non-empty cell, then fills the
    remainder proportionally from all unsampled rows.
    """
    rng = random.Random(
        RANDOM_SEED
    )

    cells = defaultdict(list)

    for row in rows:
        key = (
            str(
                row.get(
                    "search_brand",
                    "",
                )
            ).strip(),
            str(
                row.get(
                    "matched_rule",
                    "",
                )
            ).strip(),
        )

        cells[key].append(row)

    sampled = []
    sampled_ids = set()

    for key in sorted(cells):
        cell = cells[key][:]
        rng.shuffle(cell)

        take_n = min(
            MIN_PER_BRAND_RULE_CELL,
            len(cell),
        )

        for row in cell[:take_n]:
            meta_id = str(
                row.get(
                    "meta_ad_id",
                    "",
                )
            )

            if meta_id not in sampled_ids:
                sampled.append(row)
                sampled_ids.add(meta_id)

    remaining_target = max(
        0,
        target_n - len(sampled),
    )

    remaining = [
        row
        for row in rows
        if str(
            row.get(
                "meta_ad_id",
                "",
            )
        ) not in sampled_ids
    ]

    rng.shuffle(
        remaining
    )

    sampled.extend(
        remaining[:remaining_target]
    )

    return sampled[:target_n]


def main():
    temporal_rows, temporal_fields = read_csv(
        TEMPORAL_CSV
    )

    exclusions, exclusion_fields = read_csv(
        EXCLUSIONS_CSV
    )

    manual_rows, manual_fields = read_csv(
        MANUAL_REVIEW_CSV
    )

    if len(temporal_rows) != EXPECTED_TEMPORAL_ROWS:
        sys.exit(
            "ERROR: temporal dataset row count differs from validated value.\n"
            f"Expected: {EXPECTED_TEMPORAL_ROWS:,}\n"
            f"Found:    {len(temporal_rows):,}"
        )

    temporal_by_brand = Counter(
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in temporal_rows
    )

    temporal_by_sector = Counter(
        str(
            row.get(
                "sector",
                "",
            )
        ).strip()
        for row in temporal_rows
    )

    exclusions_by_brand = Counter()
    exclusions_by_sector = Counter()
    manual_by_brand = Counter()
    manual_by_sector = Counter()

    recruitment_by_brand = Counter()
    nonrecruitment_by_brand = Counter()

    reason_by_brand = defaultdict(Counter)
    rule_by_brand = defaultdict(Counter)

    reason_counts = Counter()
    rule_counts = Counter()

    for row in exclusions:
        brand = str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()

        sector = str(
            row.get(
                "sector",
                "",
            )
        ).strip()

        reason = str(
            row.get(
                "eligibility_reason",
                "",
            )
        ).strip()

        rule = str(
            row.get(
                "matched_rule",
                "",
            )
        ).strip()

        exclusions_by_brand[brand] += 1
        exclusions_by_sector[sector] += 1
        reason_by_brand[brand][reason] += 1
        rule_by_brand[brand][rule] += 1
        reason_counts[reason] += 1
        rule_counts[rule] += 1

        if reason == "recruitment":
            recruitment_by_brand[brand] += 1
        else:
            nonrecruitment_by_brand[brand] += 1

    for row in manual_rows:
        brand = str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()

        sector = str(
            row.get(
                "sector",
                "",
            )
        ).strip()

        manual_by_brand[brand] += 1
        manual_by_sector[sector] += 1

    total_exclusions = len(exclusions)

    # --------------------------------------------------------
    # By brand
    # --------------------------------------------------------

    brand_rows = []

    for brand in sorted(
        temporal_by_brand
    ):
        input_n = temporal_by_brand[brand]
        excluded_n = exclusions_by_brand[brand]
        review_n = manual_by_brand[brand]

        recruitment_n = recruitment_by_brand[brand]
        nonrecruitment_n = nonrecruitment_by_brand[brand]

        brand_rows.append({
            "search_brand":
                brand,
            "temporal_eligible_rows":
                input_n,
            "automatic_exclusions":
                excluded_n,
            "automatic_exclusion_pct_within_brand":
                pct(
                    excluded_n,
                    input_n,
                ),
            "recruitment_exclusions":
                recruitment_n,
            "nonrecruitment_auto_exclusions":
                nonrecruitment_n,
            "manual_review_rows":
                review_n,
            "manual_review_pct_within_brand":
                pct(
                    review_n,
                    input_n,
                ),
            "share_of_all_auto_exclusions_pct":
                pct(
                    excluded_n,
                    total_exclusions,
                ),
        })

    write_csv(
        BY_BRAND_OUT,
        brand_rows,
        [
            "search_brand",
            "temporal_eligible_rows",
            "automatic_exclusions",
            "automatic_exclusion_pct_within_brand",
            "recruitment_exclusions",
            "nonrecruitment_auto_exclusions",
            "manual_review_rows",
            "manual_review_pct_within_brand",
            "share_of_all_auto_exclusions_pct",
        ],
    )

    # --------------------------------------------------------
    # Brand concentration diagnostic
    # --------------------------------------------------------

    concentration_rows = []

    sorted_brands = sorted(
        brand_rows,
        key=lambda r: (
            -int(
                r[
                    "automatic_exclusions"
                ]
            ),
            r[
                "search_brand"
            ],
        ),
    )

    cumulative = 0

    for rank, row in enumerate(
        sorted_brands,
        start=1,
    ):
        excluded_n = int(
            row[
                "automatic_exclusions"
            ]
        )

        cumulative += excluded_n

        concentration_rows.append({
            "rank":
                rank,
            "search_brand":
                row[
                    "search_brand"
                ],
            "automatic_exclusions":
                excluded_n,
            "share_of_all_auto_exclusions_pct":
                pct(
                    excluded_n,
                    total_exclusions,
                ),
            "cumulative_share_of_all_auto_exclusions_pct":
                pct(
                    cumulative,
                    total_exclusions,
                ),
            "within_brand_exclusion_pct":
                row[
                    "automatic_exclusion_pct_within_brand"
                ],
        })

    write_csv(
        BRAND_CONCENTRATION_OUT,
        concentration_rows,
        [
            "rank",
            "search_brand",
            "automatic_exclusions",
            "share_of_all_auto_exclusions_pct",
            "cumulative_share_of_all_auto_exclusions_pct",
            "within_brand_exclusion_pct",
        ],
    )

    # --------------------------------------------------------
    # By sector
    # --------------------------------------------------------

    sector_rows = []

    for sector in sorted(
        temporal_by_sector
    ):
        input_n = temporal_by_sector[sector]
        excluded_n = exclusions_by_sector[sector]
        review_n = manual_by_sector[sector]

        sector_rows.append({
            "sector":
                sector,
            "temporal_eligible_rows":
                input_n,
            "automatic_exclusions":
                excluded_n,
            "automatic_exclusion_pct_within_sector":
                pct(
                    excluded_n,
                    input_n,
                ),
            "manual_review_rows":
                review_n,
            "manual_review_pct_within_sector":
                pct(
                    review_n,
                    input_n,
                ),
            "share_of_all_auto_exclusions_pct":
                pct(
                    excluded_n,
                    total_exclusions,
                ),
        })

    write_csv(
        BY_SECTOR_OUT,
        sector_rows,
        [
            "sector",
            "temporal_eligible_rows",
            "automatic_exclusions",
            "automatic_exclusion_pct_within_sector",
            "manual_review_rows",
            "manual_review_pct_within_sector",
            "share_of_all_auto_exclusions_pct",
        ],
    )

    # --------------------------------------------------------
    # Rule/reason counts
    # --------------------------------------------------------

    rule_rows = []

    for reason, n in sorted(
        reason_counts.items(),
        key=lambda x: (
            -x[1],
            x[0],
        ),
    ):
        rule_rows.append({
            "type":
                "reason",
            "label":
                reason,
            "count":
                n,
            "pct_of_all_auto_exclusions":
                pct(
                    n,
                    total_exclusions,
                ),
        })

    for rule, n in sorted(
        rule_counts.items(),
        key=lambda x: (
            -x[1],
            x[0],
        ),
    ):
        rule_rows.append({
            "type":
                "rule",
            "label":
                rule,
            "count":
                n,
            "pct_of_all_auto_exclusions":
                pct(
                    n,
                    total_exclusions,
                ),
        })

    write_csv(
        BY_RULE_OUT,
        rule_rows,
        [
            "type",
            "label",
            "count",
            "pct_of_all_auto_exclusions",
        ],
    )

    # --------------------------------------------------------
    # ALL non-recruitment auto exclusions
    # --------------------------------------------------------

    nonrecruitment_rows = [
        row
        for row in exclusions
        if str(
            row.get(
                "eligibility_reason",
                "",
            )
        ).strip()
        != "recruitment"
    ]

    write_csv(
        NONRECRUITMENT_OUT,
        nonrecruitment_rows,
        exclusion_fields,
    )

    # --------------------------------------------------------
    # Reproducible recruitment validation sample
    # --------------------------------------------------------

    recruitment_rows = [
        row
        for row in exclusions
        if str(
            row.get(
                "eligibility_reason",
                "",
            )
        ).strip()
        == "recruitment"
    ]

    sample_rows = stratified_sample(
        recruitment_rows,
        min(
            TARGET_RECRUITMENT_SAMPLE,
            len(recruitment_rows),
        ),
    )

    validation_fields = (
        exclusion_fields
        + [
            "manual_decision",
            "manual_notes",
        ]
    )

    validation_rows = []

    for row in sample_rows:
        out = dict(row)
        out[
            "manual_decision"
        ] = ""
        out[
            "manual_notes"
        ] = ""
        validation_rows.append(out)

    write_csv(
        VALIDATION_SAMPLE_OUT,
        validation_rows,
        validation_fields,
    )

    # --------------------------------------------------------
    # Concentration metrics
    # --------------------------------------------------------

    top1 = (
        concentration_rows[0]
        if concentration_rows
        else None
    )

    top3_count = sum(
        int(
            row[
                "automatic_exclusions"
            ]
        )
        for row in concentration_rows[:3]
    )

    top5_count = sum(
        int(
            row[
                "automatic_exclusions"
            ]
        )
        for row in concentration_rows[:5]
    )

    lines = []

    lines.append(
        "COMMERCIAL ELIGIBILITY AUDIT"
    )
    lines.append(
        "=" * 72
    )
    lines.append(
        f"Temporal-eligible rows: {len(temporal_rows):,}"
    )
    lines.append(
        f"Automatic exclusions:   {len(exclusions):,}"
    )
    lines.append(
        f"Manual-review rows:      {len(manual_rows):,}"
    )
    lines.append("")

    lines.append(
        "AUTOMATIC EXCLUSIONS BY BRAND"
    )

    for row in sorted_brands:
        lines.append(
            "  "
            f"{row['search_brand']}: "
            f"{int(row['automatic_exclusions']):,} "
            f"({row['automatic_exclusion_pct_within_brand']}% of brand; "
            f"{row['share_of_all_auto_exclusions_pct']}% of all exclusions)"
        )

    lines.append("")

    if top1:
        lines.append(
            "CONCENTRATION"
        )
        lines.append(
            f"Top brand: {top1['search_brand']} = "
            f"{top1['share_of_all_auto_exclusions_pct']}% "
            "of all automatic exclusions"
        )
        lines.append(
            f"Top 3 brands = {pct(top3_count, total_exclusions)}% "
            "of all automatic exclusions"
        )
        lines.append(
            f"Top 5 brands = {pct(top5_count, total_exclusions)}% "
            "of all automatic exclusions"
        )
        lines.append("")

    lines.append(
        "AUTOMATIC EXCLUSIONS BY SECTOR"
    )

    for row in sector_rows:
        lines.append(
            "  "
            f"{row['sector']}: "
            f"{int(row['automatic_exclusions']):,} "
            f"({row['automatic_exclusion_pct_within_sector']}% of sector)"
        )

    lines.append("")
    lines.append(
        f"Recruitment validation sample: {len(validation_rows):,}"
    )
    lines.append(
        f"All non-recruitment auto exclusions exported: {len(nonrecruitment_rows):,}"
    )

    DETAILS_OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    DETAILS_OUT.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(
        "\n".join(lines)
    )

    print()
    print(
        "OUTPUTS"
    )
    print(
        f"  By brand:\n    {BY_BRAND_OUT}"
    )
    print(
        f"  Brand concentration:\n    {BRAND_CONCENTRATION_OUT}"
    )
    print(
        f"  By sector:\n    {BY_SECTOR_OUT}"
    )
    print(
        f"  By rule/reason:\n    {BY_RULE_OUT}"
    )
    print(
        f"  Recruitment validation sample:\n    {VALIDATION_SAMPLE_OUT}"
    )
    print(
        f"  All non-recruitment auto exclusions:\n    {NONRECRUITMENT_OUT}"
    )
    print(
        f"  Details:\n    {DETAILS_OUT}"
    )
    print()
    print(
        "No source dataset was modified."
    )


if __name__ == "__main__":
    main()
