#!/usr/bin/env python3

"""
11_build_analysis_ready_dataset.py

Build the analysis-ready Meta ad dataset from the locked eligibility dataset.

INPUT
-----
data/ads_eligibility_locked.csv

OUTPUT
------
data/ads_analysis_ready.csv

The input file is never modified.

One row remains one Meta Ad Library ad ID. No deduplication and no reach
aggregation are performed.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = ROOT / "data" / "ads_eligibility_locked.csv"
OUTPUT_CSV = ROOT / "data" / "ads_analysis_ready.csv"

EXPECTED_ROWS = 53794

ORIGINAL_FIELDS = [
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

DERIVED_FIELDS = [
    "female_delivery_share",
    "adult_18_34_share",
    "age_scope",
    "platform_category",
    "month",
    "known_gender_reach",
    "known_adult_reach",
    "gender_data_usable",
    "age_data_usable",
    "has_unknown_gender",
    "has_unknown_age",
    "creative_signature_hash",
]

TEXT_FIELDS = [
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
]

ADULT_AGE_FIELDS = [
    "de_age_18_24",
    "de_age_25_34",
    "de_age_35_44",
    "de_age_45_54",
    "de_age_55_64",
    "de_age_65_plus",
]

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


def fail(message: str) -> None:
    sys.exit(f"ERROR: {message}")


def read_csv(path: Path):
    if not path.exists():
        fail(f"required file not found:\n{path}")

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    return rows, fields


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_serialized_list(value) -> list[str] | None:
    if value is None:
        return None

    raw = str(value).strip()
    if raw == "":
        return None

    try:
        parsed = json.loads(raw)
    except Exception:
        try:
            parsed = ast.literal_eval(raw)
        except Exception:
            return None

    if not isinstance(parsed, list):
        return None

    return [str(x).strip() for x in parsed if x is not None]


def parse_number(value) -> float | None:
    if value is None:
        return None

    raw = str(value).strip()
    if raw == "":
        return None

    try:
        number = float(raw)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None

    return number


def format_number(value: float | None) -> str:
    if value is None:
        return ""

    if float(value).is_integer():
        return str(int(value))

    return format(value, ".15g")


def format_share(value: float | None) -> str:
    if value is None:
        return ""

    return format(value, ".15g")


def derive_age_scope(value) -> str:
    ages = parse_serialized_list(value)
    if ages is None or len(ages) != 2:
        return ""

    try:
        age_min = int(ages[0])
        age_max = int(ages[1])
    except ValueError:
        return ""

    if age_min == 18 and age_max == 65:
        return "Broad"

    if 0 <= age_min <= age_max:
        return "Narrow"

    return ""


def derive_platform_category(value) -> str:
    platforms = parse_serialized_list(value)
    if platforms is None:
        return ""

    normalized = [x.casefold() for x in platforms]
    unique = set(normalized)

    if len(normalized) == 1 and unique == {"facebook"}:
        return "Facebook-only"

    if len(normalized) == 1 and unique == {"instagram"}:
        return "Instagram-only"

    if len(normalized) == 2 and unique == {"facebook", "instagram"}:
        return "Both"

    return "Other"


def derive_month(value) -> str:
    raw = "" if value is None else str(value).strip()
    if raw == "":
        return ""

    candidate = raw[:10]

    try:
        date = datetime.strptime(candidate, "%Y-%m-%d")
    except ValueError:
        return ""

    return date.strftime("%Y-%m")


def parse_text_field(value):
    if value is None:
        return []

    raw = str(value).strip()
    if raw == "":
        return []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return ["" if item is None else str(item) for item in parsed]
        if parsed is None:
            return []
        return [str(parsed)]
    except Exception:
        pass

    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return ["" if item is None else str(item) for item in parsed]
    except Exception:
        pass

    return [raw]


def normalize_text(value) -> str:
    parts = parse_text_field(value)
    normalized_parts = []

    for part in parts:
        text = unicodedata.normalize("NFKC", str(part)).casefold()
        text = re.sub(r"\s+", " ", text).strip()
        normalized_parts.append(text)

    return "\u241e".join(normalized_parts)


def signature_hash(page_id: str, row: dict) -> str:
    components = [str(page_id).strip()]
    components.extend(normalize_text(row.get(field, "")) for field in TEXT_FIELDS)
    payload = "\u241f".join(components)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    rows, fields = read_csv(INPUT_CSV)

    if len(rows) != EXPECTED_ROWS:
        fail(
            "locked dataset row count mismatch.\n"
            f"Expected: {EXPECTED_ROWS:,}\n"
            f"Found:    {len(rows):,}"
        )

    if fields != ORIGINAL_FIELDS:
        missing = [x for x in ORIGINAL_FIELDS if x not in fields]
        extra = [x for x in fields if x not in ORIGINAL_FIELDS]
        fail(
            "locked dataset schema does not match the expected 24-column schema.\n"
            f"Missing: {missing}\n"
            f"Extra:   {extra}\n"
            f"Observed order: {fields}"
        )

    meta_ids = [str(row["meta_ad_id"]).strip() for row in rows]

    if any(x == "" for x in meta_ids):
        fail("blank meta_ad_id found.")

    if len(meta_ids) != len(set(meta_ids)):
        fail("duplicate meta_ad_id values found.")

    unknown_brands = sorted(
        {
            str(row["search_brand"]).strip()
            for row in rows
            if str(row["search_brand"]).strip() not in PAGE_ID_BY_BRAND
        }
    )

    if unknown_brands:
        fail(
            "brand(s) have no verified Meta Page ID mapping:\n"
            + ", ".join(unknown_brands)
        )

    output_rows = []

    no_demographic_data = 0
    zero_known_gender_complete = 0
    gender_unusable = 0
    positive_unknown_gender = 0
    zero_adult_complete = 0
    age_unusable = 0
    positive_unknown_age = 0
    reconciliation_mismatches = 0
    comparable_demographic_rows = 0

    age_scope_counts = Counter()
    platform_counts = Counter()
    month_counts = Counter()
    target_gender_counts = Counter()

    for row in rows:
        out = dict(row)

        male = parse_number(row["de_male"])
        female = parse_number(row["de_female"])
        unknown_gender = parse_number(row["de_unknown"])

        age_values = {
            field: parse_number(row[field])
            for field in [
                "de_age_13_17",
                *ADULT_AGE_FIELDS,
                "de_age_unknown",
            ]
        }

        gender_complete = all(
            value is not None
            for value in [male, female, unknown_gender]
        )
        age_complete = all(
            value is not None
            for value in age_values.values()
        )

        if not gender_complete and not age_complete:
            no_demographic_data += 1

        # Known-gender denominator and female delivery share
        if male is not None and female is not None:
            known_gender = male + female
            out["known_gender_reach"] = format_number(known_gender)

            if known_gender > 0:
                out["female_delivery_share"] = format_share(
                    female / known_gender
                )
                out["gender_data_usable"] = "1"
            else:
                out["female_delivery_share"] = ""
                out["gender_data_usable"] = "0"
                zero_known_gender_complete += 1
                gender_unusable += 1
        else:
            out["known_gender_reach"] = ""
            out["female_delivery_share"] = ""
            out["gender_data_usable"] = "0"
            gender_unusable += 1

        # Unknown-gender flag: blank means unavailable, not zero.
        if unknown_gender is None:
            out["has_unknown_gender"] = ""
        else:
            out["has_unknown_gender"] = "1" if unknown_gender > 0 else "0"
            if unknown_gender > 0:
                positive_unknown_gender += 1

        # Adult-age denominator and 18-34 share
        adult_numbers = [age_values[field] for field in ADULT_AGE_FIELDS]

        if all(value is not None for value in adult_numbers):
            known_adult = sum(adult_numbers)
            out["known_adult_reach"] = format_number(known_adult)

            if known_adult > 0:
                young_adult = (
                    age_values["de_age_18_24"]
                    + age_values["de_age_25_34"]
                )
                out["adult_18_34_share"] = format_share(
                    young_adult / known_adult
                )
                out["age_data_usable"] = "1"
            else:
                out["adult_18_34_share"] = ""
                out["age_data_usable"] = "0"
                zero_adult_complete += 1
                age_unusable += 1
        else:
            out["known_adult_reach"] = ""
            out["adult_18_34_share"] = ""
            out["age_data_usable"] = "0"
            age_unusable += 1

        age_unknown = age_values["de_age_unknown"]
        if age_unknown is None:
            out["has_unknown_age"] = ""
        else:
            out["has_unknown_age"] = "1" if age_unknown > 0 else "0"
            if age_unknown > 0:
                positive_unknown_age += 1

        # Targeting/platform/time derived fields
        out["age_scope"] = derive_age_scope(row["target_ages"])
        out["platform_category"] = derive_platform_category(
            row["publisher_platforms"]
        )
        out["month"] = derive_month(row["ad_delivery_start_date_time"])

        age_scope_counts[out["age_scope"]] += 1
        platform_counts[out["platform_category"]] += 1
        month_counts[out["month"]] += 1
        target_gender_counts[str(row["target_gender"]).strip()] += 1

        # Stable textual creative signature
        brand = str(row["search_brand"]).strip()
        page_id = PAGE_ID_BY_BRAND[brand]
        out["creative_signature_hash"] = signature_hash(page_id, row)

        # Gender-age reconciliation where both breakdowns are complete
        if gender_complete and age_complete:
            comparable_demographic_rows += 1
            gender_total = male + female + unknown_gender
            age_total = sum(age_values.values())

            if gender_total != age_total:
                reconciliation_mismatches += 1

        output_rows.append(out)

    # ------------------------------------------------------------
    # Strict validations based on the locked dataset audit
    # ------------------------------------------------------------

    if no_demographic_data != 2:
        fail(
            f"expected 2 rows with no demographic data; found {no_demographic_data}."
        )

    if zero_known_gender_complete != 14:
        fail(
            "expected 14 complete rows with zero known-gender reach; "
            f"found {zero_known_gender_complete}."
        )

    if gender_unusable != 16:
        fail(
            f"expected 16 gender-unusable rows; found {gender_unusable}."
        )

    if positive_unknown_gender != 41930:
        fail(
            "expected 41,930 rows with positive unknown-gender reach; "
            f"found {positive_unknown_gender:,}."
        )

    if zero_adult_complete != 5:
        fail(
            "expected 5 complete rows with zero adult-age denominator; "
            f"found {zero_adult_complete}."
        )

    if age_unusable != 7:
        fail(
            f"expected 7 age-unusable rows; found {age_unusable}."
        )

    if positive_unknown_age != 21829:
        fail(
            "expected 21,829 rows with positive unknown-age reach; "
            f"found {positive_unknown_age:,}."
        )

    if comparable_demographic_rows != 53792:
        fail(
            "expected 53,792 comparable demographic rows; "
            f"found {comparable_demographic_rows:,}."
        )

    if reconciliation_mismatches != 0:
        fail(
            "gender/age demographic reconciliation mismatch detected: "
            f"{reconciliation_mismatches:,} rows."
        )

    expected_gender_counts = Counter(
        {
            "All": 45010,
            "Women": 6819,
            "Men": 1965,
        }
    )

    if target_gender_counts != expected_gender_counts:
        fail(
            "target_gender counts do not match the locked dataset audit.\n"
            f"Expected: {dict(expected_gender_counts)}\n"
            f"Found:    {dict(target_gender_counts)}"
        )

    if age_scope_counts.get("", 0) != 0:
        fail(
            f"{age_scope_counts['']:,} rows could not be classified into age_scope."
        )

    if platform_counts.get("", 0) != 0:
        fail(
            f"{platform_counts['']:,} rows could not be classified into platform_category."
        )

    if month_counts.get("", 0) != 0:
        fail(
            f"{month_counts['']:,} rows could not be assigned a month."
        )

    # Derived-share range checks
    for row in output_rows:
        for field in ["female_delivery_share", "adult_18_34_share"]:
            raw = row[field]
            if raw == "":
                continue

            value = float(raw)
            if not 0.0 <= value <= 1.0:
                fail(
                    f"{field} outside [0,1] for meta_ad_id={row['meta_ad_id']}: "
                    f"{value}"
                )

        sig = row["creative_signature_hash"]
        if not re.match(r"^[0-9a-f]{64}$", sig):
            fail(
                "invalid creative_signature_hash for "
                f"meta_ad_id={row['meta_ad_id']}."
            )

    output_fields = ORIGINAL_FIELDS + DERIVED_FIELDS
    write_csv(OUTPUT_CSV, output_rows, output_fields)

    # Re-read output for final structural checks.
    written_rows, written_fields = read_csv(OUTPUT_CSV)

    if len(written_rows) != EXPECTED_ROWS:
        fail(
            "written analysis-ready dataset has incorrect row count: "
            f"{len(written_rows):,}."
        )

    if written_fields != output_fields:
        fail("written analysis-ready dataset has incorrect column schema.")

    written_ids = [row["meta_ad_id"] for row in written_rows]
    if len(written_ids) != len(set(written_ids)):
        fail("duplicate meta_ad_id values found after writing output.")

    # Verify every original source value was preserved.
    for source, written in zip(rows, written_rows):
        for field in ORIGINAL_FIELDS:
            if source[field] != written[field]:
                fail(
                    "original field changed during construction: "
                    f"meta_ad_id={source['meta_ad_id']}, field={field}"
                )

    print("ANALYSIS-READY DATASET CONSTRUCTION")
    print("=" * 72)
    print(f"Input rows:                         {len(rows):,}")
    print(f"Output rows:                        {len(written_rows):,}")
    print(f"Original variables preserved:       {len(ORIGINAL_FIELDS)}")
    print(f"Derived variables added:            {len(DERIVED_FIELDS)}")
    print(f"Final variables:                    {len(output_fields)}")
    print()
    print(f"No demographic data:                {no_demographic_data:,}")
    print(f"Zero known-gender, complete rows:   {zero_known_gender_complete:,}")
    print(f"Gender-unusable rows:               {gender_unusable:,}")
    print(f"Positive unknown-gender reach:      {positive_unknown_gender:,}")
    print(f"Zero adult denominator, complete:   {zero_adult_complete:,}")
    print(f"Age-unusable rows:                  {age_unusable:,}")
    print(f"Positive unknown-age reach:         {positive_unknown_age:,}")
    print(f"Demographic reconciliation errors:  {reconciliation_mismatches:,}")
    print()
    print("age_scope")
    for key, value in sorted(age_scope_counts.items()):
        print(f"  {key}: {value:,}")
    print()
    print("platform_category")
    for key, value in sorted(platform_counts.items()):
        print(f"  {key}: {value:,}")
    print()
    print(f"OUTPUT\n  {OUTPUT_CSV}")
    print()
    print("No deduplication, reach aggregation, or imputation was performed.")


if __name__ == "__main__":
    main()
