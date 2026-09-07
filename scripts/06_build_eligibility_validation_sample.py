#!/usr/bin/env python3

"""
06_build_eligibility_validation_sample.py

Audit-only sampling script for validating the commercial-eligibility classifier.

This script DOES NOT:
- delete rows,
- modify the temporal dataset,
- modify the current commercial-eligible working dataset,
- perform production deduplication.

It uses normalized four-field creative text only to avoid asking the reviewer
to manually classify the same textual creative repeatedly inside the audit.

INPUTS
------
data/intermediate/ads_temporal_eligible.csv
audit/commercial_eligibility_exclusions.csv
audit/commercial_eligibility_manual_review.csv

OUTPUTS
-------
audit/excluded_validation_sample.csv
audit/retained_validation_sample.csv
audit/nonrecruitment_exclusions_full_review.csv
audit/manual_review_full_review.csv

validation/eligibility_validation_sampling_summary.csv
validation/eligibility_validation_sampling_by_brand.csv
validation/eligibility_validation_sampling_by_rule.csv

SAMPLING DESIGN
---------------
Positive validation:
    Sample distinct recruitment-flagged creative-text signatures,
    stratified by brand x matched rule.

Negative validation:
    Sample distinct retained creative-text signatures,
    stratified across all brands.

Non-recruitment automatic exclusions:
    Export ALL for manual review.

Manual-review cases:
    Export ALL for manual decision.

IMPORTANT
---------
The audit signature is:
    search_brand + normalized body + title + caption + description

This signature is used ONLY to avoid repeated textual creatives in manual
validation. It is NOT the final thesis production deduplication key.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
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

AUDIT_DIR = ROOT / "audit"
VALIDATION_DIR = ROOT / "validation"

POSITIVE_SAMPLE_OUT = (
    AUDIT_DIR
    / "excluded_validation_sample.csv"
)

NEGATIVE_SAMPLE_OUT = (
    AUDIT_DIR
    / "retained_validation_sample.csv"
)

NONRECRUITMENT_FULL_OUT = (
    AUDIT_DIR
    / "nonrecruitment_exclusions_full_review.csv"
)

MANUAL_FULL_OUT = (
    AUDIT_DIR
    / "manual_review_full_review.csv"
)

SUMMARY_OUT = (
    VALIDATION_DIR
    / "eligibility_validation_sampling_summary.csv"
)

BY_BRAND_OUT = (
    VALIDATION_DIR
    / "eligibility_validation_sampling_by_brand.csv"
)

BY_RULE_OUT = (
    VALIDATION_DIR
    / "eligibility_validation_sampling_by_rule.csv"
)


# ============================================================
# EXPECTATIONS / SAMPLING PARAMETERS
# ============================================================

EXPECTED_TEMPORAL_ROWS = 60329

RANDOM_SEED = 20260907

TARGET_POSITIVE_SIGNATURES = 400
TARGET_NEGATIVE_SIGNATURES = 1000

MIN_POSITIVE_PER_BRAND_RULE_CELL = 2
MIN_NEGATIVE_PER_BRAND = 20

TEXT_FIELDS = [
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
]

REQUIRED_TEMPORAL_COLUMNS = [
    "search_brand",
    "sector",
    "meta_ad_id",
    *TEXT_FIELDS,
]

REQUIRED_AUDIT_COLUMNS = [
    *REQUIRED_TEMPORAL_COLUMNS,
    "commercial_eligibility",
    "eligibility_reason",
    "matched_rule",
    "matched_field",
    "matched_text",
]


# ============================================================
# TEXT / SIGNATURE HELPERS
# ============================================================

def unpack_text_value(value) -> list[str]:
    if value is None:
        return []

    raw = str(value).strip()

    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except Exception:
        return [raw]

    if parsed is None:
        return []

    if isinstance(parsed, list):
        out = []

        for item in parsed:
            if item is None:
                continue

            if isinstance(item, dict):
                out.append(
                    json.dumps(
                        item,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
            else:
                out.append(
                    str(item)
                )

        return out

    if isinstance(parsed, dict):
        return [
            json.dumps(
                parsed,
                ensure_ascii=False,
                sort_keys=True,
            )
        ]

    return [
        str(parsed)
    ]


def normalize_text(value) -> str:
    pieces = unpack_text_value(
        value
    )

    joined = " ".join(
        pieces
    )

    text = unicodedata.normalize(
        "NFKC",
        joined,
    ).casefold()

    text = re.sub(
        r"[^0-9a-zäöüß]+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def audit_signature(
    row: dict,
) -> str:
    parts = [
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip().casefold()
    ]

    for field in TEXT_FIELDS:
        parts.append(
            normalize_text(
                row.get(
                    field,
                    "",
                )
            )
        )

    joined = "\x1f".join(
        parts
    )

    return hashlib.sha256(
        joined.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(
    path: Path,
    required: list[str],
) -> tuple[list[dict], list[str]]:

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

        reader = csv.DictReader(
            f
        )

        fields = (
            reader.fieldnames
            or []
        )

        missing = [
            col
            for col in required
            if col not in fields
        ]

        if missing:
            sys.exit(
                "ERROR: missing required columns in "
                f"{path.name}:\n"
                + "\n".join(
                    missing
                )
            )

        return list(
            reader
        ), fields


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
        writer.writerows(
            rows
        )


def pct(
    n: int,
    d: int,
) -> float:

    if not d:
        return 0.0

    return round(
        100.0 * n / d,
        4,
    )


# ============================================================
# SIGNATURE COLLAPSE FOR AUDIT SAMPLING ONLY
# ============================================================

def collapse_to_signatures(
    rows: list[dict],
) -> list[dict]:
    """
    One representative row per audit signature.
    Adds:
        audit_creative_signature
        signature_meta_id_count
        signature_meta_ids
    """
    groups = {}

    for row in rows:
        sig = audit_signature(
            row
        )

        if sig not in groups:
            groups[sig] = {
                "representative":
                    dict(row),
                "meta_ids":
                    [],
            }

        groups[sig][
            "meta_ids"
        ].append(
            str(
                row.get(
                    "meta_ad_id",
                    "",
                )
            )
        )

    out = []

    for sig, group in groups.items():
        representative = dict(
            group[
                "representative"
            ]
        )

        meta_ids = sorted(
            {
                x
                for x in group[
                    "meta_ids"
                ]
                if x
            }
        )

        representative[
            "audit_creative_signature"
        ] = sig

        representative[
            "signature_meta_id_count"
        ] = len(
            meta_ids
        )

        representative[
            "signature_meta_ids"
        ] = "|".join(
            meta_ids
        )

        out.append(
            representative
        )

    return out


# ============================================================
# POSITIVE SAMPLE
# ============================================================

def sample_positive(
    signature_rows: list[dict],
    target_n: int,
) -> list[dict]:

    rng = random.Random(
        RANDOM_SEED
    )

    cells = defaultdict(
        list
    )

    for row in signature_rows:

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

        cells[
            key
        ].append(
            row
        )

    selected = []
    selected_sigs = set()

    # Minimum representation per brand x rule cell.
    for key in sorted(
        cells
    ):

        cell = cells[
            key
        ][:]

        rng.shuffle(
            cell
        )

        take_n = min(
            MIN_POSITIVE_PER_BRAND_RULE_CELL,
            len(
                cell
            ),
        )

        for row in cell[:take_n]:

            sig = row[
                "audit_creative_signature"
            ]

            if sig in selected_sigs:
                continue

            selected.append(
                row
            )

            selected_sigs.add(
                sig
            )

    remaining_target = max(
        0,
        target_n
        - len(
            selected
        ),
    )

    remaining = [
        row
        for row in signature_rows
        if row[
            "audit_creative_signature"
        ]
        not in selected_sigs
    ]

    rng.shuffle(
        remaining
    )

    selected.extend(
        remaining[
            :remaining_target
        ]
    )

    return selected[
        :target_n
    ]


# ============================================================
# NEGATIVE SAMPLE
# ============================================================

def sample_negative(
    signature_rows: list[dict],
    target_n: int,
) -> list[dict]:

    rng = random.Random(
        RANDOM_SEED + 1
    )

    by_brand = defaultdict(
        list
    )

    for row in signature_rows:

        brand = str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()

        by_brand[
            brand
        ].append(
            row
        )

    selected = []
    selected_sigs = set()

    # Guarantee representation from every brand where possible.
    for brand in sorted(
        by_brand
    ):

        rows = by_brand[
            brand
        ][:]

        rng.shuffle(
            rows
        )

        take_n = min(
            MIN_NEGATIVE_PER_BRAND,
            len(
                rows
            ),
        )

        for row in rows[:take_n]:

            sig = row[
                "audit_creative_signature"
            ]

            if sig in selected_sigs:
                continue

            selected.append(
                row
            )

            selected_sigs.add(
                sig
            )

    remaining_target = max(
        0,
        target_n
        - len(
            selected
        ),
    )

    remaining = [
        row
        for row in signature_rows
        if row[
            "audit_creative_signature"
        ]
        not in selected_sigs
    ]

    rng.shuffle(
        remaining
    )

    selected.extend(
        remaining[
            :remaining_target
        ]
    )

    return selected[
        :target_n
    ]


# ============================================================
# MAIN
# ============================================================

def main():

    temporal_rows, temporal_fields = read_csv(
        TEMPORAL_CSV,
        REQUIRED_TEMPORAL_COLUMNS,
    )

    exclusions, exclusion_fields = read_csv(
        EXCLUSIONS_CSV,
        REQUIRED_AUDIT_COLUMNS,
    )

    manual_rows, manual_fields = read_csv(
        MANUAL_REVIEW_CSV,
        REQUIRED_AUDIT_COLUMNS,
    )

    if len(
        temporal_rows
    ) != EXPECTED_TEMPORAL_ROWS:

        sys.exit(
            "ERROR: temporal dataset row count differs from "
            "validated value.\n"
            f"Expected: {EXPECTED_TEMPORAL_ROWS:,}\n"
            f"Found:    {len(temporal_rows):,}"
        )

    exclusion_ids = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        )
        for row in exclusions
    }

    manual_ids = {
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        )
        for row in manual_rows
    }

    # Retained-negative pool:
    # temporal rows that are neither automatically excluded nor manual review.
    #
    # This tests clear-retain cases rather than ambiguous cases.
    retained_negative_pool = [
        row
        for row in temporal_rows
        if str(
            row.get(
                "meta_ad_id",
                "",
            )
        )
        not in exclusion_ids
        and str(
            row.get(
                "meta_ad_id",
                "",
            )
        )
        not in manual_ids
    ]

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

    # --------------------------------------------------------
    # Collapse only for audit sampling
    # --------------------------------------------------------

    recruitment_signatures = collapse_to_signatures(
        recruitment_rows
    )

    retained_signatures = collapse_to_signatures(
        retained_negative_pool
    )

    # --------------------------------------------------------
    # Samples
    # --------------------------------------------------------

    positive_sample = sample_positive(
        recruitment_signatures,
        min(
            TARGET_POSITIVE_SIGNATURES,
            len(
                recruitment_signatures
            ),
        ),
    )

    negative_sample = sample_negative(
        retained_signatures,
        min(
            TARGET_NEGATIVE_SIGNATURES,
            len(
                retained_signatures
            ),
        ),
    )

    # --------------------------------------------------------
    # Add manual-review columns
    # --------------------------------------------------------

    review_columns = [
        "manual_decision",
        "manual_category",
        "manual_notes",
    ]

    positive_output = []

    for row in positive_sample:

        out = dict(
            row
        )

        out[
            "manual_decision"
        ] = ""

        out[
            "manual_category"
        ] = ""

        out[
            "manual_notes"
        ] = ""

        positive_output.append(
            out
        )

    negative_output = []

    for row in negative_sample:

        out = dict(
            row
        )

        out[
            "manual_decision"
        ] = ""

        out[
            "manual_category"
        ] = ""

        out[
            "manual_notes"
        ] = ""

        negative_output.append(
            out
        )

    nonrecruitment_output = []

    for row in nonrecruitment_rows:

        out = dict(
            row
        )

        out[
            "manual_decision"
        ] = ""

        out[
            "manual_category"
        ] = ""

        out[
            "manual_notes"
        ] = ""

        nonrecruitment_output.append(
            out
        )

    manual_output = []

    for row in manual_rows:

        out = dict(
            row
        )

        out[
            "manual_decision"
        ] = ""

        out[
            "manual_category"
        ] = ""

        out[
            "manual_notes"
        ] = ""

        manual_output.append(
            out
        )

    signature_fields = [
        "audit_creative_signature",
        "signature_meta_id_count",
        "signature_meta_ids",
    ]

    positive_fields = (
        exclusion_fields
        + signature_fields
        + review_columns
    )

    negative_fields = (
        temporal_fields
        + signature_fields
        + review_columns
    )

    full_review_fields = (
        exclusion_fields
        + review_columns
    )

    manual_review_fields = (
        manual_fields
        + review_columns
    )

    write_csv(
        POSITIVE_SAMPLE_OUT,
        positive_output,
        positive_fields,
    )

    write_csv(
        NEGATIVE_SAMPLE_OUT,
        negative_output,
        negative_fields,
    )

    write_csv(
        NONRECRUITMENT_FULL_OUT,
        nonrecruitment_output,
        full_review_fields,
    )

    write_csv(
        MANUAL_FULL_OUT,
        manual_output,
        manual_review_fields,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary_rows = [
        {
            "metric":
                "temporal_eligible_rows",
            "value":
                len(
                    temporal_rows
                ),
        },
        {
            "metric":
                "automatic_exclusion_rows",
            "value":
                len(
                    exclusions
                ),
        },
        {
            "metric":
                "recruitment_exclusion_rows",
            "value":
                len(
                    recruitment_rows
                ),
        },
        {
            "metric":
                "distinct_recruitment_audit_signatures",
            "value":
                len(
                    recruitment_signatures
                ),
        },
        {
            "metric":
                "positive_validation_sample_signatures",
            "value":
                len(
                    positive_output
                ),
        },
        {
            "metric":
                "nonrecruitment_auto_exclusions_full_review",
            "value":
                len(
                    nonrecruitment_output
                ),
        },
        {
            "metric":
                "manual_review_rows_full_review",
            "value":
                len(
                    manual_output
                ),
        },
        {
            "metric":
                "clear_retained_rows_negative_pool",
            "value":
                len(
                    retained_negative_pool
                ),
        },
        {
            "metric":
                "distinct_clear_retained_audit_signatures",
            "value":
                len(
                    retained_signatures
                ),
        },
        {
            "metric":
                "negative_validation_sample_signatures",
            "value":
                len(
                    negative_output
                ),
        },
        {
            "metric":
                "random_seed",
            "value":
                RANDOM_SEED,
        },
    ]

    write_csv(
        SUMMARY_OUT,
        summary_rows,
        [
            "metric",
            "value",
        ],
    )

    # --------------------------------------------------------
    # By-brand sampling diagnostics
    # --------------------------------------------------------

    positive_population_by_brand = Counter(
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in recruitment_signatures
    )

    positive_sample_by_brand = Counter(
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in positive_output
    )

    negative_population_by_brand = Counter(
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in retained_signatures
    )

    negative_sample_by_brand = Counter(
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in negative_output
    )

    brands = sorted(
        set(
            positive_population_by_brand
        )
        | set(
            negative_population_by_brand
        )
    )

    brand_rows = []

    for brand in brands:

        brand_rows.append({
            "search_brand":
                brand,
            "distinct_recruitment_signatures":
                positive_population_by_brand[
                    brand
                ],
            "positive_sample_signatures":
                positive_sample_by_brand[
                    brand
                ],
            "positive_sample_coverage_pct":
                pct(
                    positive_sample_by_brand[
                        brand
                    ],
                    positive_population_by_brand[
                        brand
                    ],
                ),
            "distinct_clear_retained_signatures":
                negative_population_by_brand[
                    brand
                ],
            "negative_sample_signatures":
                negative_sample_by_brand[
                    brand
                ],
            "negative_sample_coverage_pct":
                pct(
                    negative_sample_by_brand[
                        brand
                    ],
                    negative_population_by_brand[
                        brand
                    ],
                ),
        })

    write_csv(
        BY_BRAND_OUT,
        brand_rows,
        [
            "search_brand",
            "distinct_recruitment_signatures",
            "positive_sample_signatures",
            "positive_sample_coverage_pct",
            "distinct_clear_retained_signatures",
            "negative_sample_signatures",
            "negative_sample_coverage_pct",
        ],
    )

    # --------------------------------------------------------
    # By-rule positive diagnostics
    # --------------------------------------------------------

    population_by_rule = Counter(
        str(
            row.get(
                "matched_rule",
                "",
            )
        ).strip()
        for row in recruitment_signatures
    )

    sample_by_rule = Counter(
        str(
            row.get(
                "matched_rule",
                "",
            )
        ).strip()
        for row in positive_output
    )

    rule_rows = []

    for rule in sorted(
        population_by_rule
    ):

        rule_rows.append({
            "matched_rule":
                rule,
            "distinct_recruitment_signatures":
                population_by_rule[
                    rule
                ],
            "sample_signatures":
                sample_by_rule[
                    rule
                ],
            "sample_coverage_pct":
                pct(
                    sample_by_rule[
                        rule
                    ],
                    population_by_rule[
                        rule
                    ],
                ),
        })

    write_csv(
        BY_RULE_OUT,
        rule_rows,
        [
            "matched_rule",
            "distinct_recruitment_signatures",
            "sample_signatures",
            "sample_coverage_pct",
        ],
    )

    # --------------------------------------------------------
    # Terminal report
    # --------------------------------------------------------

    print(
        "ELIGIBILITY VALIDATION SAMPLING"
    )

    print(
        "=" * 72
    )

    print(
        f"Temporal-eligible rows:                  {len(temporal_rows):,}"
    )

    print(
        f"Automatic exclusion rows:               {len(exclusions):,}"
    )

    print(
        f"Recruitment exclusion rows:             {len(recruitment_rows):,}"
    )

    print(
        f"Distinct recruitment text signatures:   {len(recruitment_signatures):,}"
    )

    print(
        f"Positive validation sample:             {len(positive_output):,}"
    )

    print(
        f"Non-recruitment exclusions full review: {len(nonrecruitment_output):,}"
    )

    print(
        f"Manual-review rows full review:         {len(manual_output):,}"
    )

    print(
        f"Clear retained rows:                    {len(retained_negative_pool):,}"
    )

    print(
        f"Distinct retained text signatures:      {len(retained_signatures):,}"
    )

    print(
        f"Negative validation sample:             {len(negative_output):,}"
    )

    print()

    print(
        "POSITIVE SAMPLE BY BRAND"
    )

    for row in sorted(
        brand_rows,
        key=lambda x: (
            -int(
                x[
                    "positive_sample_signatures"
                ]
            ),
            x[
                "search_brand"
            ],
        ),
    ):

        if int(
            row[
                "positive_sample_signatures"
            ]
        ) > 0:

            print(
                "  "
                f"{row['search_brand']}: "
                f"{row['positive_sample_signatures']} / "
                f"{row['distinct_recruitment_signatures']} "
                "distinct recruitment signatures"
            )

    print()

    print(
        "OUTPUTS"
    )

    print(
        f"  Positive recruitment validation:\n"
        f"    {POSITIVE_SAMPLE_OUT}"
    )

    print(
        f"  Negative retained validation:\n"
        f"    {NEGATIVE_SAMPLE_OUT}"
    )

    print(
        f"  Non-recruitment exclusions full review:\n"
        f"    {NONRECRUITMENT_FULL_OUT}"
    )

    print(
        f"  Manual-review full review:\n"
        f"    {MANUAL_FULL_OUT}"
    )

    print(
        f"  Sampling summary:\n"
        f"    {SUMMARY_OUT}"
    )

    print(
        f"  Sampling by brand:\n"
        f"    {BY_BRAND_OUT}"
    )

    print(
        f"  Positive sampling by rule:\n"
        f"    {BY_RULE_OUT}"
    )

    print()

    print(
        "No source dataset was modified."
    )


if __name__ == "__main__":
    main()
