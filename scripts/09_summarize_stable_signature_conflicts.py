#!/usr/bin/env python3

"""
09_summarize_stable_signature_conflicts.py

Summarize structural conflicts within stable creative-signature groups.

INPUT
-----
audit/stable_signature_conflicts.csv

OUTPUT
------
validation/stable_signature_conflict_summary.csv

This is audit-only. It does not modify or deduplicate the analytical data.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = ROOT / "audit" / "stable_signature_conflicts.csv"
OUTPUT_CSV = ROOT / "validation" / "stable_signature_conflict_summary.csv"


def main():
    if not INPUT_CSV.exists():
        sys.exit(f"ERROR: required file not found:\n{INPUT_CSV}")

    with INPUT_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    required = {
        "creative_signature_hash",
        "signature_group_size",
        "conflict_fields",
        "search_brand",
        "meta_ad_id",
        "publisher_platforms",
        "target_ages",
        "target_gender",
    }

    missing = sorted(required - set(fields))
    if missing:
        sys.exit("ERROR: missing required columns: " + ", ".join(missing))

    # One record per conflicting signature group.
    group_first = {}
    for row in rows:
        sig = row["creative_signature_hash"].strip()
        if sig and sig not in group_first:
            group_first[sig] = row

    conflict_pattern_counts = Counter()
    brand_group_counts = Counter()

    for sig, row in group_first.items():
        pattern = row["conflict_fields"].strip() or "<none>"
        brand = row["search_brand"].strip() or "<missing>"
        conflict_pattern_counts[pattern] += 1
        brand_group_counts[brand] += 1

    out = []

    for pattern, n in sorted(
        conflict_pattern_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        out.append({
            "summary_type": "conflict_pattern",
            "category": pattern,
            "n_conflicting_signature_groups": n,
        })

    for brand, n in sorted(
        brand_group_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        out.append({
            "summary_type": "brand",
            "category": brand,
            "n_conflicting_signature_groups": n,
        })

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "summary_type",
                "category",
                "n_conflicting_signature_groups",
            ],
        )
        writer.writeheader()
        writer.writerows(out)

    print("STABLE SIGNATURE CONFLICT SUMMARY")
    print("=" * 72)
    print(f"Conflicting signature groups: {len(group_first):,}")
    print()

    print("Conflict patterns")
    print("-" * 72)
    for pattern, n in sorted(
        conflict_pattern_counts.items(),
        key=lambda x: (-x[1], x[0]),
    ):
        print(f"{pattern:<55} {n:>6,}")

    print()
    print("Top brands by conflicting groups")
    print("-" * 72)
    for brand, n in sorted(
        brand_group_counts.items(),
        key=lambda x: (-x[1], x[0]),
    )[:20]:
        print(f"{brand:<30} {n:>6,}")

    print()
    print(f"Output:\n  {OUTPUT_CSV}")
    print()
    print("No production data were modified.")


if __name__ == "__main__":
    main()
