#!/usr/bin/env python3

"""
08_build_and_audit_stable_signature.py

Attach the verified Meta Page ID and a stable creative signature to the locked
eligibility dataset, then audit duplicate signature groups for structural
conflicts BEFORE any deduplication is performed.

Stable signature:
    Page ID
    + normalized ad_creative_bodies
    + normalized ad_creative_link_titles
    + normalized ad_creative_link_captions
    + normalized ad_creative_link_descriptions

INPUT
-----
data/intermediate/ads_eligibility_locked.csv

OUTPUTS
-------
data/intermediate/ads_with_stable_signature.csv
audit/stable_signature_conflicts.csv

The input dataset is never modified.

IMPORTANT
---------
This script does NOT deduplicate advertisements and does NOT aggregate reach.
Each Meta ad ID remains one row.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_eligibility_locked.csv"
)

OUTPUT_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_with_stable_signature.csv"
)

CONFLICT_CSV = (
    ROOT
    / "audit"
    / "stable_signature_conflicts.csv"
)

EXPECTED_INPUT_ROWS = 53794


# Verified Page IDs used by the collection pipeline.
PAGE_ID_BY_BRAND = {
    "Aldi Nord": "335288650611521",
    "Bonprix": "119152901485525",
    "dm": "129724513733284",
    "Aldi Süd": "168773186520269",
    "Penny": "700577889971139",
    "Bauhaus": "137379942944322",
    "OBI": "160178767369925",
    "Rossmann": "354412263434",
    "Lidl": "278565202257",
    "Zalando": "365604620536",
    "New Yorker": "110682655781",
    "Zara": "33331950906",
    "About You": "1824279721179597",
    "Douglas": "190089409661",
    "Müller": "225116334184666",
    "Flaconi": "133137093423758",
    "IKEA": "280631742051539",
    "Hornbach": "102368498017",
    "Kaufland": "132476996783723",
    "Edeka Südwest": "334601287018068",
}


TEXT_FIELDS = [
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
]

STRUCTURAL_FIELDS = [
    "publisher_platforms",
    "target_ages",
    "target_gender",
]


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


def parse_text_field(value):
    """
    Convert a serialized list or scalar text field into a list of strings.

    The genuine source columns are not changed. This parsing is used only
    for constructing the normalized signature.
    """
    if value is None:
        return []

    raw = str(value).strip()

    if raw == "":
        return []

    # First try JSON, which is the collector's normal representation.
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [
                "" if item is None else str(item)
                for item in parsed
            ]
        if parsed is None:
            return []
        return [str(parsed)]
    except Exception:
        pass

    # Defensive fallback for Python-style serialized lists.
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [
                "" if item is None else str(item)
                for item in parsed
            ]
    except Exception:
        pass

    return [raw]


def normalize_text(value) -> str:
    """
    Normalize text for signature construction only:
    - Unicode NFKC
    - casefold
    - collapse whitespace

    Punctuation and lexical content are retained.
    """
    parts = parse_text_field(value)

    normalized_parts = []

    for part in parts:
        text = unicodedata.normalize(
            "NFKC",
            str(part),
        ).casefold()

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        normalized_parts.append(
            text
        )

    return "\u241e".join(
        normalized_parts
    )


def normalized_structural(value) -> str:
    """
    Normalize a structural field only for equality comparison.
    """
    if value is None:
        return ""

    raw = str(value).strip()

    if raw == "":
        return ""

    # Canonicalize serialized lists when possible.
    try:
        parsed = json.loads(raw)

        if isinstance(parsed, list):
            vals = sorted(
                str(x).strip().casefold()
                for x in parsed
            )

            return "|".join(
                vals
            )
    except Exception:
        pass

    return re.sub(
        r"\s+",
        " ",
        unicodedata.normalize(
            "NFKC",
            raw,
        ).casefold(),
    ).strip()


def signature_hash(
    page_id: str,
    row: dict,
) -> str:
    components = [
        str(page_id).strip(),
    ]

    components.extend(
        normalize_text(
            row.get(
                field,
                "",
            )
        )
        for field in TEXT_FIELDS
    )

    payload = "\u241f".join(
        components
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


def main():
    rows, fields = read_csv(
        INPUT_CSV
    )

    if len(rows) != EXPECTED_INPUT_ROWS:
        sys.exit(
            "ERROR: locked eligibility row count mismatch.\n"
            f"Expected: {EXPECTED_INPUT_ROWS:,}\n"
            f"Found:    {len(rows):,}"
        )

    required = {
        "search_brand",
        "sector",
        "meta_ad_id",
        *TEXT_FIELDS,
        *STRUCTURAL_FIELDS,
    }

    missing = sorted(
        required
        - set(fields)
    )

    if missing:
        sys.exit(
            "ERROR: input is missing required columns:\n"
            + ", ".join(
                missing
            )
        )

    # --------------------------------------------------------
    # Validate brands and Meta IDs
    # --------------------------------------------------------

    observed_brands = {
        str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()
        for row in rows
    }

    unknown_brands = sorted(
        observed_brands
        - set(
            PAGE_ID_BY_BRAND
        )
    )

    if unknown_brands:
        sys.exit(
            "ERROR: brand(s) have no verified Page ID mapping:\n"
            + ", ".join(
                unknown_brands
            )
        )

    meta_ids = [
        str(
            row.get(
                "meta_ad_id",
                "",
            )
        ).strip()
        for row in rows
    ]

    if "" in meta_ids:
        sys.exit(
            "ERROR: blank Meta ad ID found."
        )

    if len(meta_ids) != len(
        set(
            meta_ids
        )
    ):
        sys.exit(
            "ERROR: duplicate Meta ad IDs found before signature audit."
        )

    # --------------------------------------------------------
    # Attach Page ID and stable signature
    # --------------------------------------------------------

    enriched = []

    groups = defaultdict(
        list
    )

    for row in rows:
        out = dict(
            row
        )

        brand = str(
            row.get(
                "search_brand",
                "",
            )
        ).strip()

        page_id = PAGE_ID_BY_BRAND[
            brand
        ]

        sig = signature_hash(
            page_id,
            row,
        )

        out["page_id"] = page_id
        out["creative_signature_hash"] = sig

        enriched.append(
            out
        )

        groups[
            sig
        ].append(
            out
        )

    # --------------------------------------------------------
    # Audit signature groups
    # --------------------------------------------------------

    duplicate_groups = {
        sig: members
        for sig, members in groups.items()
        if len(
            members
        ) > 1
    }

    duplicate_rows = sum(
        len(
            members
        )
        for members in duplicate_groups.values()
    )

    conflict_rows = []

    conflicting_groups = 0

    for sig, members in duplicate_groups.items():
        distinct_by_field = {}

        for field in STRUCTURAL_FIELDS:
            vals = {
                normalized_structural(
                    member.get(
                        field,
                        "",
                    )
                )
                for member in members
            }

            distinct_by_field[
                field
            ] = vals

        conflict_fields = [
            field
            for field, vals in distinct_by_field.items()
            if len(
                vals
            ) > 1
        ]

        if not conflict_fields:
            continue

        conflicting_groups += 1

        for member in members:
            conflict_rows.append({
                "creative_signature_hash":
                    sig,
                "signature_group_size":
                    len(
                        members
                    ),
                "conflict_fields":
                    "|".join(
                        conflict_fields
                    ),
                "search_brand":
                    member.get(
                        "search_brand",
                        "",
                    ),
                "page_id":
                    member.get(
                        "page_id",
                        "",
                    ),
                "meta_ad_id":
                    member.get(
                        "meta_ad_id",
                        "",
                    ),
                "publisher_platforms":
                    member.get(
                        "publisher_platforms",
                        "",
                    ),
                "target_ages":
                    member.get(
                        "target_ages",
                        "",
                    ),
                "target_gender":
                    member.get(
                        "target_gender",
                        "",
                    ),
            })

    # --------------------------------------------------------
    # Write outputs
    # --------------------------------------------------------

    output_fields = list(
        fields
    )

    # Put traceability fields near Meta ad ID.
    meta_pos = output_fields.index(
        "meta_ad_id"
    )

    output_fields.insert(
        meta_pos + 1,
        "page_id",
    )

    output_fields.insert(
        meta_pos + 2,
        "creative_signature_hash",
    )

    write_csv(
        OUTPUT_CSV,
        enriched,
        output_fields,
    )

    conflict_fields_out = [
        "creative_signature_hash",
        "signature_group_size",
        "conflict_fields",
        "search_brand",
        "page_id",
        "meta_ad_id",
        "publisher_platforms",
        "target_ages",
        "target_gender",
    ]

    write_csv(
        CONFLICT_CSV,
        conflict_rows,
        conflict_fields_out,
    )

    # --------------------------------------------------------
    # Terminal summary
    # --------------------------------------------------------

    group_sizes = Counter(
        len(
            members
        )
        for members in groups.values()
    )

    max_group_size = max(
        group_sizes,
        default=0,
    )

    print(
        "STABLE CREATIVE SIGNATURE AUDIT"
    )

    print(
        "=" * 72
    )

    print(
        f"Eligible Meta ad IDs:                 {len(rows):,}"
    )

    print(
        f"Distinct stable signatures:           {len(groups):,}"
    )

    print(
        f"Duplicate signature groups (>1 ID):   {len(duplicate_groups):,}"
    )

    print(
        f"Meta ad IDs in duplicate groups:      {duplicate_rows:,}"
    )

    print(
        f"Maximum IDs in one signature group:   {max_group_size:,}"
    )

    print(
        f"Structurally conflicting groups:      {conflicting_groups:,}"
    )

    print(
        f"Rows in conflicting groups:           {len(conflict_rows):,}"
    )

    print()

    print(
        "No deduplication or reach aggregation was performed."
    )

    print()

    print(
        "OUTPUTS"
    )

    print(
        f"  Signature-enriched dataset:\n"
        f"    {OUTPUT_CSV}"
    )

    print(
        f"  Structural-conflict audit:\n"
        f"    {CONFLICT_CSV}"
    )


if __name__ == "__main__":
    main()
