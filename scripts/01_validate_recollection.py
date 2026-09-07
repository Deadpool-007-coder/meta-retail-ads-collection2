#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_CSV = ROOT / "ads_recollection_all20.csv"
PROGRESS_JSON = ROOT / "progress.json"
CONFLICT_CSV = ROOT / "audit" / "conflicting_meta_ids.csv"
DELIVERY_AUDIT_CSV = ROOT / "audit" / "repeated_meta_id_delivery_versions.csv"

OUT_DIR = ROOT / "validation"
SUMMARY_CSV = OUT_DIR / "recollection_validation_summary.csv"
BY_BRAND_CSV = OUT_DIR / "recollection_validation_by_brand.csv"
DETAILS_TXT = OUT_DIR / "recollection_validation_details.txt"

EXPECTED_COLUMNS = [
    "search_brand","sector","meta_ad_id",
    "ad_creative_bodies","ad_creative_link_titles",
    "ad_creative_link_captions","ad_creative_link_descriptions",
    "publisher_platforms","target_ages","target_gender",
    "ad_delivery_start_date_time","ad_delivery_stop_date_time",
    "collection_timestamp","de_male","de_female","de_unknown",
    "de_age_13_17","de_age_18_24","de_age_25_34","de_age_35_44",
    "de_age_45_54","de_age_55_64","de_age_65_plus","de_age_unknown",
]

EXPECTED_BRANDS = {
    "Aldi Nord","Aldi Süd","Penny","Lidl","Kaufland","Edeka Südwest",
    "Bonprix","Zalando","New Yorker","Zara","About You",
    "dm","Rossmann","Douglas","Müller","Flaconi",
    "Bauhaus","OBI","IKEA","Hornbach",
}

GENDER_COLUMNS = ["de_male","de_female","de_unknown"]
AGE_COLUMNS = [
    "de_age_13_17","de_age_18_24","de_age_25_34","de_age_35_44",
    "de_age_45_54","de_age_55_64","de_age_65_plus","de_age_unknown",
]
ADULT_AGE_COLUMNS = [
    "de_age_18_24","de_age_25_34","de_age_35_44",
    "de_age_45_54","de_age_55_64","de_age_65_plus",
]

def blank(v):
    return v is None or str(v).strip() == ""

def num(v):
    if blank(v):
        return None
    try:
        x = float(v)
    except Exception:
        return None
    return x if math.isfinite(x) else None

def isum(row, cols):
    vals = []
    for c in cols:
        x = num(row.get(c))
        if x is None:
            return None
        vals.append(x)
    return sum(vals)

def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        rows = list(r)
        return r.fieldnames or [], rows

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def main():
    if not MAIN_CSV.exists():
        sys.exit(f"ERROR: file not found: {MAIN_CSV}")

    fields, rows = read_csv(MAIN_CSV)
    n = len(rows)

    ids = [str(r.get("meta_ad_id","")).strip() for r in rows]
    id_counts = Counter(x for x in ids if x)
    dup_ids = {k:v for k,v in id_counts.items() if v > 1}

    brands = [str(r.get("search_brand","")).strip() for r in rows]
    brand_counts = Counter(brands)
    brands_present = {b for b in brand_counts if b}

    missing_schema = [c for c in EXPECTED_COLUMNS if c not in fields]
    extra_schema = [c for c in fields if c not in EXPECTED_COLUMNS]

    counters = Counter()
    by_brand = defaultdict(Counter)

    for r in rows:
        brand = str(r.get("search_brand","")).strip()
        b = by_brand[brand]
        b["rows"] += 1

        for field, key in [
            ("target_gender","target_gender_missing"),
            ("target_ages","target_ages_missing"),
            ("publisher_platforms","platform_missing"),
            ("ad_delivery_start_date_time","start_missing"),
            ("ad_delivery_stop_date_time","stop_missing"),
        ]:
            if blank(r.get(field)):
                counters[key] += 1
                b[key] += 1

        demo_present = any(
            not blank(r.get(c))
            for c in GENDER_COLUMNS + AGE_COLUMNS
        )

        if demo_present:
            counters["demographic_rows"] += 1
            b["demographic_rows"] += 1
        else:
            counters["no_demographic_rows"] += 1
            b["no_demographic_rows"] += 1

        m = num(r.get("de_male"))
        f = num(r.get("de_female"))
        ug = num(r.get("de_unknown"))
        ua = num(r.get("de_age_unknown"))

        if m is not None and f is not None and m + f == 0:
            counters["known_gender_zero"] += 1
            b["known_gender_zero"] += 1

        if ug is not None and ug > 0:
            counters["unknown_gender_positive"] += 1
            b["unknown_gender_positive"] += 1

        if ua is not None and ua > 0:
            counters["unknown_age_positive"] += 1
            b["unknown_age_positive"] += 1

        gt = isum(r, GENDER_COLUMNS)
        at = isum(r, AGE_COLUMNS)

        if gt is not None:
            counters["gender_complete"] += 1
            b["gender_complete"] += 1

        if at is not None:
            counters["age_complete"] += 1
            b["age_complete"] += 1

        if gt is not None and at is not None:
            if gt == at:
                counters["gender_age_reconcile"] += 1
                b["gender_age_reconcile"] += 1
            else:
                counters["gender_age_mismatch"] += 1
                b["gender_age_mismatch"] += 1

        adult = isum(r, ADULT_AGE_COLUMNS)
        if adult is not None and adult == 0:
            counters["adult_age_zero"] += 1
            b["adult_age_zero"] += 1

        for c in GENDER_COLUMNS + AGE_COLUMNS:
            if blank(r.get(c)):
                continue
            x = num(r.get(c))
            if x is None or not float(x).is_integer():
                counters["invalid_demo_values"] += 1
                b["invalid_demo_values"] += 1
            elif x < 0:
                counters["negative_demo_values"] += 1
                b["negative_demo_values"] += 1

    conflict_rows = []
    delivery_rows = []

    if CONFLICT_CSV.exists():
        _, conflict_rows = read_csv(CONFLICT_CSV)

    if DELIVERY_AUDIT_CSV.exists():
        _, delivery_rows = read_csv(DELIVERY_AUDIT_CSV)

    conflict_ids = {
        str(r.get("meta_ad_id","")).strip()
        for r in conflict_rows
        if str(r.get("meta_ad_id","")).strip()
    }
    delivery_ids = {
        str(r.get("meta_ad_id","")).strip()
        for r in delivery_rows
        if str(r.get("meta_ad_id","")).strip()
    }

    conflict_tiers = Counter(
        str(r.get("difference_tier","")).strip()
        for r in conflict_rows
    )
    conflict_fields = Counter(
        str(r.get("differing_field","")).strip()
        for r in conflict_rows
    )

    progress = {}
    if PROGRESS_JSON.exists():
        with PROGRESS_JSON.open("r", encoding="utf-8") as f:
            progress = json.load(f)

    summary = []
    def add(metric, value, note=""):
        summary.append({"metric":metric,"value":value,"note":note})

    add("raw_rows", n)
    add("column_count", len(fields))
    add("exact_expected_schema", fields == EXPECTED_COLUMNS)
    add("missing_expected_columns", len(missing_schema), "; ".join(missing_schema))
    add("unexpected_columns", len(extra_schema), "; ".join(extra_schema))
    add("brands_present", len(brands_present))
    add("missing_expected_brands", len(EXPECTED_BRANDS - brands_present),
        "; ".join(sorted(EXPECTED_BRANDS - brands_present)))
    add("unexpected_brands", len(brands_present - EXPECTED_BRANDS),
        "; ".join(sorted(brands_present - EXPECTED_BRANDS)))
    add("unique_meta_ad_ids", len(id_counts))
    add("missing_meta_ad_id_rows", sum(1 for x in ids if not x))
    add("duplicate_meta_ad_id_values", len(dup_ids))
    add("duplicate_meta_ad_id_extra_rows", sum(v-1 for v in dup_ids.values()))
    add("target_gender_missing", counters["target_gender_missing"])
    add("target_ages_missing", counters["target_ages_missing"])
    add("publisher_platforms_missing", counters["platform_missing"])
    add("start_date_time_missing", counters["start_missing"])
    add("stop_date_time_missing", counters["stop_missing"])
    add("rows_with_any_demographic_data", counters["demographic_rows"])
    add("rows_without_demographic_data", counters["no_demographic_rows"])
    add("known_gender_zero_rows", counters["known_gender_zero"])
    add("unknown_gender_positive_rows", counters["unknown_gender_positive"])
    add("unknown_age_positive_rows", counters["unknown_age_positive"])
    add("gender_complete_rows", counters["gender_complete"])
    add("age_complete_rows", counters["age_complete"])
    add("gender_age_total_reconciled_rows", counters["gender_age_reconcile"])
    add("gender_age_total_mismatch_rows", counters["gender_age_mismatch"])
    add("adult_age_denominator_zero_rows", counters["adult_age_zero"])
    add("negative_demographic_values", counters["negative_demo_values"])
    add("invalid_or_noninteger_demographic_values", counters["invalid_demo_values"])
    add("structural_conflict_rows", len(conflict_rows))
    add("structural_conflict_unique_ids", len(conflict_ids))
    add("delivery_audit_rows", len(delivery_rows))
    add("delivery_audit_unique_ids", len(delivery_ids))
    add("progress_combined_rows", progress.get("combined_rows",""))
    add("progress_combined_brand_count", progress.get("combined_brand_count",""))
    add("progress_all_20_complete", progress.get("all_20_brands_complete",""))
    add("main_rows_equal_progress_rows",
        progress.get("combined_rows") == n if "combined_rows" in progress else "")

    for tier, count in sorted(conflict_tiers.items()):
        if tier:
            add(f"structural_conflict_tier::{tier}", count)

    for field, count in sorted(conflict_fields.items()):
        if field:
            add(f"structural_conflict_field::{field}", count)

    write_csv(SUMMARY_CSV, summary, ["metric","value","note"])

    brand_rows = []
    for brand in sorted(brands_present):
        c = by_brand[brand]
        brand_rows.append({
            "search_brand": brand,
            "rows": c["rows"],
            "demographic_rows": c["demographic_rows"],
            "no_demographic_rows": c["no_demographic_rows"],
            "known_gender_zero": c["known_gender_zero"],
            "unknown_gender_positive": c["unknown_gender_positive"],
            "unknown_age_positive": c["unknown_age_positive"],
            "gender_complete_rows": c["gender_complete"],
            "age_complete_rows": c["age_complete"],
            "gender_age_reconcile": c["gender_age_reconcile"],
            "gender_age_mismatch": c["gender_age_mismatch"],
            "adult_age_denominator_zero": c["adult_age_zero"],
            "target_gender_missing": c["target_gender_missing"],
            "target_ages_missing": c["target_ages_missing"],
            "platform_missing": c["platform_missing"],
            "start_missing": c["start_missing"],
            "stop_missing": c["stop_missing"],
            "negative_demographic_values": c["negative_demo_values"],
            "invalid_demographic_values": c["invalid_demo_values"],
        })

    write_csv(
        BY_BRAND_CSV,
        brand_rows,
        [
            "search_brand","rows","demographic_rows","no_demographic_rows",
            "known_gender_zero","unknown_gender_positive","unknown_age_positive",
            "gender_complete_rows","age_complete_rows","gender_age_reconcile",
            "gender_age_mismatch","adult_age_denominator_zero",
            "target_gender_missing","target_ages_missing","platform_missing",
            "start_missing","stop_missing","negative_demographic_values",
            "invalid_demographic_values",
        ],
    )

    lines = [
        "RECOLLECTION VALIDATION REPORT",
        "=" * 72,
        f"Rows: {n:,}",
        f"Columns: {len(fields)}",
        f"Brands: {len(brands_present)}",
        f"Unique Meta ad IDs: {len(id_counts):,}",
        "",
        "CORE INTEGRITY",
        f"Exact expected schema: {fields == EXPECTED_COLUMNS}",
        f"Missing IDs: {sum(1 for x in ids if not x):,}",
        f"Duplicate ID values: {len(dup_ids):,}",
        f"Duplicate extra rows: {sum(v-1 for v in dup_ids.values()):,}",
        "",
        "TARGETING / PLATFORM / TIME",
        f"target_gender missing: {counters['target_gender_missing']:,}",
        f"target_ages missing: {counters['target_ages_missing']:,}",
        f"publisher_platforms missing: {counters['platform_missing']:,}",
        f"start timestamp missing: {counters['start_missing']:,}",
        f"stop timestamp missing: {counters['stop_missing']:,}",
        "",
        "GERMANY DEMOGRAPHICS",
        f"Rows with demographic data: {counters['demographic_rows']:,}",
        f"Rows without demographic data: {counters['no_demographic_rows']:,}",
        f"Known-gender zero rows: {counters['known_gender_zero']:,}",
        f"Unknown-gender > 0 rows: {counters['unknown_gender_positive']:,}",
        f"Unknown-age > 0 rows: {counters['unknown_age_positive']:,}",
        f"Gender/age totals reconcile: {counters['gender_age_reconcile']:,}",
        f"Gender/age total mismatches: {counters['gender_age_mismatch']:,}",
        f"Adult-age denominator zero: {counters['adult_age_zero']:,}",
        "",
        "AUDITS",
        f"Structural conflict rows: {len(conflict_rows):,}",
        f"Structural conflict unique IDs: {len(conflict_ids):,}",
        f"Delivery-version audit rows: {len(delivery_rows):,}",
        f"Delivery-version unique IDs: {len(delivery_ids):,}",
        "",
        "BRAND COUNTS",
    ]

    for brand in sorted(brands_present):
        lines.append(f"  {brand}: {brand_counts[brand]:,}")

    if conflict_tiers:
        lines += ["", "CONFLICT ROWS BY TIER"]
        for tier, count in sorted(conflict_tiers.items()):
            lines.append(f"  {tier or '<blank>'}: {count:,}")

    if conflict_fields:
        lines += ["", "CONFLICT ROWS BY FIELD"]
        for field, count in sorted(conflict_fields.items()):
            lines.append(f"  {field or '<blank>'}: {count:,}")

    lines += [
        "",
        "OUTPUTS",
        f"  {SUMMARY_CSV}",
        f"  {BY_BRAND_CSV}",
        f"  {DETAILS_TXT}",
    ]

    DETAILS_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
