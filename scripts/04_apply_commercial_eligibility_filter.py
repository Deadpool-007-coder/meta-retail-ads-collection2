#!/usr/bin/env python3

"""
04_apply_commercial_eligibility_filter.py

Conservative commercial-eligibility filter for the temporally eligible
Meta Ad Library recollection.

INPUT
-----
data/intermediate/ads_temporal_eligible.csv

OUTPUTS
-------
data/intermediate/ads_commercial_eligible.csv

audit/commercial_eligibility_exclusions.csv
audit/commercial_eligibility_manual_review.csv

validation/commercial_eligibility_summary.csv
validation/commercial_eligibility_by_brand.csv
validation/commercial_eligibility_by_sector.csv
validation/commercial_eligibility_by_reason.csv

CLASSIFICATION
--------------
retain_commercial
exclude_clear_noncommercial
manual_review

CORE PRINCIPLE
--------------
Automatically exclude only when the four available creative-text fields
provide high-confidence evidence that the ad's primary purpose is outside
consumer-facing commercial retail communication.

Ambiguous mixed-purpose cases are NOT automatically excluded.
They remain in the working dataset and are written to manual review.

The input file is never modified.
The genuine ad text is never rewritten.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_temporal_eligible.csv"
)

OUTPUT_CSV = (
    ROOT
    / "data"
    / "intermediate"
    / "ads_commercial_eligible.csv"
)

AUDIT_DIR = ROOT / "audit"

EXCLUSIONS_CSV = (
    AUDIT_DIR
    / "commercial_eligibility_exclusions.csv"
)

MANUAL_REVIEW_CSV = (
    AUDIT_DIR
    / "commercial_eligibility_manual_review.csv"
)

VALIDATION_DIR = ROOT / "validation"

SUMMARY_CSV = (
    VALIDATION_DIR
    / "commercial_eligibility_summary.csv"
)

BY_BRAND_CSV = (
    VALIDATION_DIR
    / "commercial_eligibility_by_brand.csv"
)

BY_SECTOR_CSV = (
    VALIDATION_DIR
    / "commercial_eligibility_by_sector.csv"
)

BY_REASON_CSV = (
    VALIDATION_DIR
    / "commercial_eligibility_by_reason.csv"
)


# ============================================================
# EXPECTED INPUT
# ============================================================

EXPECTED_INPUT_ROWS = 60329

TEXT_FIELDS = [
    "ad_creative_bodies",
    "ad_creative_link_titles",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
]

REQUIRED_COLUMNS = [
    "search_brand",
    "sector",
    "meta_ad_id",
    *TEXT_FIELDS,
]


# ============================================================
# NORMALIZATION
# ============================================================

def unpack_text_value(value) -> list[str]:
    """
    Meta creative text fields may be JSON-encoded lists.
    Convert them to plain strings for classification only.
    Original CSV content remains unchanged.
    """
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
                out.append(str(item))

        return out

    if isinstance(parsed, dict):
        return [
            json.dumps(
                parsed,
                ensure_ascii=False,
                sort_keys=True,
            )
        ]

    return [str(parsed)]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize(
        "NFKC",
        str(text or ""),
    ).casefold()

    text = re.sub(
        r"[^0-9a-zäöüß/()+\-]+",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def get_field_texts(row: dict) -> dict[str, str]:
    result = {}

    for field in TEXT_FIELDS:
        pieces = []

        for item in unpack_text_value(
            row.get(field, "")
        ):
            normalized = normalize_text(
                item
            )

            if normalized:
                pieces.append(
                    normalized
                )

        result[field] = " ".join(
            pieces
        )

    return result


def combine_texts(
    texts: dict[str, str],
) -> str:
    return " ".join(
        value
        for value in texts.values()
        if value
    )


# ============================================================
# MATCH HELPERS
# ============================================================

def normalized_phrase(
    value: str,
) -> str:
    return normalize_text(
        value
    )


def find_phrase(
    text: str,
    phrases: list[str],
) -> str | None:
    for phrase_value in phrases:
        p = normalized_phrase(
            phrase_value
        )

        if p and p in text:
            return phrase_value

    return None


def find_regex(
    text: str,
    patterns: list[str],
) -> str | None:
    for pattern in patterns:
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return pattern

    return None


def field_for_phrase(
    texts: dict[str, str],
    phrase_value: str,
) -> str:
    p = normalized_phrase(
        phrase_value
    )

    for field, text in texts.items():
        if p and p in text:
            return field

    return "combined_text"


def field_for_regex(
    texts: dict[str, str],
    pattern: str,
) -> str:
    for field, text in texts.items():
        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            return field

    return "combined_text"


def result(
    classification: str,
    reason: str = "",
    rule: str = "",
    matched_field: str = "",
    matched_text: str = "",
) -> dict:
    return {
        "commercial_eligibility":
            classification,
        "eligibility_reason":
            reason,
        "matched_rule":
            rule,
        "matched_field":
            matched_field,
        "matched_text":
            matched_text,
    }


# ============================================================
# COMMERCIAL POSITIVE SIGNALS
# ============================================================

COMMERCIAL_TERMS = [
    "rabatt",
    "sale",
    "angebot",
    "angebote",
    "coupon",
    "gutschein",
    "jetzt kaufen",
    "online kaufen",
    "bestellen",
    "shoppen",
    "shopping",
    "shop",
    "produkt",
    "produkte",
    "sortiment",
    "kollektion",
    "neu erhältlich",
    "neu erhaeltlich",
    "jetzt erhältlich",
    "jetzt erhaeltlich",
    "filiale",
    "store",
    "öffnungszeiten",
    "oeffnungszeiten",
    "eröffnung",
    "eroeffnung",
    "lieferung",
    "versand",
    "app",
    "bonus",
    "punkte",
    "gewinnspiel",
    "gewinnen",
    "einkauf",
    "einkaufen",
    "entdecke",
    "entdecken",
    "sichere dir",
    "preis",
    "aktion",
]


# ============================================================
# 1. RECRUITMENT / EMPLOYER BRANDING
# ============================================================

STRONG_RECRUITMENT_PHRASES = [
    "karriere",
    "karriere bei",
    "karrierechance",
    "karrierechancen",
    "stellenangebot",
    "stellenangebote",
    "stellenanzeige",
    "stellenanzeigen",
    "offene stelle",
    "offene stellen",
    "jobangebot",
    "jobangebote",
    "job opening",
    "job openings",
    "vacancy",
    "vacancies",
    "wir stellen ein",
    "wir suchen verstärkung",
    "wir suchen verstaerkung",
    "verstärke unser team",
    "verstaerke unser team",
    "verstärkung für unser team",
    "verstaerkung fuer unser team",
    "mitarbeiter gesucht",
    "mitarbeiterin gesucht",
    "mitarbeiterinnen gesucht",
    "werde teil unseres teams",
    "werde teil des teams",
    "komm in unser team",
    "komme in unser team",
    "join our team",
    "join the team",
    "we're hiring",
    "we are hiring",
    "now hiring",
    "ausbildungsplatz",
    "ausbildungsplätze",
    "ausbildungsplaetze",
    "ausbildung bei",
    "starte deine ausbildung",
    "duales studium",
    "werkstudent",
    "werkstudentin",
    "praktikumsplatz",
    "praktikant",
    "praktikantin",
    "traineeprogramm",
    "trainee programm",
    "graduate programme",
    "graduate program",
    "azubi",
    "auszubildende",
    "aushilfe gesucht",
    "minijob",
]

# IMPORTANT:
# No standalone m / w / d matcher is used.
# Only explicit recruitment constructions are detected.
RECRUITMENT_REGEX = [
    r"(?<![a-z0-9])m\s*/\s*w\s*/\s*d(?![a-z0-9])",
    r"(?<![a-z0-9])w\s*/\s*m\s*/\s*d(?![a-z0-9])",
    r"(?<![a-z0-9])m\s*/\s*w\s*/\s*x(?![a-z0-9])",
    r"(?<![a-z0-9])d\s*/\s*m\s*/\s*w(?![a-z0-9])",
    r"(?<![a-z0-9])m\s*w\s*d(?![a-z0-9])",
]

APPLICATION_TERMS = [
    "bewirb dich",
    "jetzt bewerben",
    "bewerbung",
    "bewerben sie sich",
    "apply now",
    "apply today",
]

EMPLOYMENT_CONTEXT_TERMS = [
    "job",
    "jobs",
    "stelle",
    "stellen",
    "karriere",
    "arbeitgeber",
    "arbeitsplatz",
    "mitarbeiter",
    "mitarbeiterin",
    "mitarbeitende",
    "kollege",
    "kollegin",
    "kollegen",
    "team",
    "ausbildung",
    "azubi",
    "praktikum",
    "praktikant",
    "werkstudent",
    "trainee",
    "duales studium",
    "vollzeit",
    "teilzeit",
    "minijob",
]


# ============================================================
# 2. CLEAR NON-COMMERCIAL EDUCATIONAL / PARTICIPATION PROGRAMMES
# ============================================================

PROGRAMME_TERMS = [
    "förderprogramm",
    "foerderprogramm",
    "förderprojekt",
    "foerderprojekt",
    "bildungsprogramm",
    "bildungsprojekt",
    "schulprojekt",
    "schulprogramm",
    "kindergartenprojekt",
    "kindergartenprogramm",
    "singende kindergärten",
    "singende kindergaerten",
    "stipendium",
    "stipendienprogramm",
    "förderpreis",
    "foerderpreis",
    "projektförderung",
    "projektfoerderung",
]


# ============================================================
# 3. CLEAR INSTITUTIONAL / CORPORATE REPORTING
# ============================================================

CORPORATE_REPORT_TERMS = [
    "geschäftsbericht",
    "geschaeftsbericht",
    "jahresbericht",
    "annual report",
    "unternehmensbericht",
    "investor relations",
    "corporate governance",
    "transparenzbericht",
    "nachhaltigkeitsbericht",
    "sustainability report",
    "menschenrechtsbericht",
]

CORPORATE_AMBIGUOUS_TERMS = [
    "klimaziel",
    "unternehmensziel",
    "lieferkette",
    "geschäftsjahr",
    "geschaeftsjahr",
    "vorstand",
    "geschäftsführung",
    "geschaeftsfuehrung",
    "investor",
    "aktionär",
    "aktionaer",
]


# ============================================================
# 4. SAFETY / RECALL SIGNALS
# MANUAL REVIEW ONLY
# ============================================================

SAFETY_RECALL_TERMS = [
    "produktrückruf",
    "produktrueckruf",
    "rückrufaktion",
    "rueckrufaktion",
    "wichtiger sicherheitshinweis",
    "sicherheitshinweis",
    "verbraucherwarnung",
    "produktwarnung",
]


# ============================================================
# 5. PURE LEGAL / COMPLIANCE NOTICES
# ============================================================

LEGAL_NOTICE_TERMS = [
    "rechtlicher hinweis",
    "gesetzlicher hinweis",
    "pflichtinformation",
    "pflichtinformationen",
    "datenschutzhinweis",
    "datenschutzinformation",
]


# ============================================================
# MANUAL-REVIEW SIGNALS
# These are NOT automatic exclusions.
# ============================================================

CSR_CHARITY_TERMS = [
    "wir spenden",
    "spende",
    "spenden",
    "charity",
    "gemeinnützig",
    "gemeinnuetzig",
    "soziales engagement",
    "gesellschaftliches engagement",
    "wir unterstützen",
    "wir unterstuetzen",
]

SUSTAINABILITY_TERMS = [
    "nachhaltigkeit",
    "nachhaltig",
    "klimaschutz",
    "umweltschutz",
    "recycling",
    "kreislaufwirtschaft",
]

SPONSORSHIP_TERMS = [
    "wir sind sponsor",
    "offizieller sponsor",
    "hauptsponsor",
    "sponsoring",
    "offizieller partner",
]

COMMUNITY_TERMS = [
    "community projekt",
    "community programm",
    "nachbarschaftsprojekt",
    "vereinsförderung",
    "vereinsfoerderung",
    "initiative",
]


# ============================================================
# CLASSIFIER
# ============================================================

def classify(
    row: dict,
) -> dict:

    texts = get_field_texts(
        row
    )

    text = combine_texts(
        texts
    )

    # No usable text: cannot determine primary purpose confidently.
    if not text:
        return result(
            "manual_review",
            "mixed_unclear",
            "no_creative_text_available",
        )

    commercial_match = find_phrase(
        text,
        COMMERCIAL_TERMS,
    )

    # --------------------------------------------------------
    # 1. Recruitment / employer branding
    # --------------------------------------------------------

    strong_recruitment = find_phrase(
        text,
        STRONG_RECRUITMENT_PHRASES,
    )

    if strong_recruitment:
        return result(
            "exclude_clear_noncommercial",
            "recruitment",
            "strong_recruitment_phrase",
            field_for_phrase(
                texts,
                strong_recruitment,
            ),
            strong_recruitment,
        )

    recruitment_regex = find_regex(
        text,
        RECRUITMENT_REGEX,
    )

    if recruitment_regex:
        return result(
            "exclude_clear_noncommercial",
            "recruitment",
            "explicit_recruitment_gender_marker",
            field_for_regex(
                texts,
                recruitment_regex,
            ),
            recruitment_regex,
        )

    application_match = find_phrase(
        text,
        APPLICATION_TERMS,
    )

    employment_match = find_phrase(
        text,
        EMPLOYMENT_CONTEXT_TERMS,
    )

    if (
        application_match
        and employment_match
    ):
        return result(
            "exclude_clear_noncommercial",
            "recruitment",
            "application_plus_employment_context",
            "combined_text",
            (
                f"{application_match} + "
                f"{employment_match}"
            ),
        )

    # --------------------------------------------------------
    # 2. Clear educational / participation programme
    # --------------------------------------------------------

    programme_match = find_phrase(
        text,
        PROGRAMME_TERMS,
    )

    if programme_match:
        if commercial_match:
            return result(
                "manual_review",
                "mixed_unclear",
                "programme_plus_commercial_signal",
                "combined_text",
                (
                    f"{programme_match} + "
                    f"{commercial_match}"
                ),
            )

        return result(
            "exclude_clear_noncommercial",
            "education_or_participation_programme",
            "clear_noncommercial_programme",
            field_for_phrase(
                texts,
                programme_match,
            ),
            programme_match,
        )

    # --------------------------------------------------------
    # 3. Clear corporate / institutional reporting
    # --------------------------------------------------------

    corporate_report_match = find_phrase(
        text,
        CORPORATE_REPORT_TERMS,
    )

    if corporate_report_match:
        if commercial_match:
            return result(
                "manual_review",
                "mixed_unclear",
                "corporate_report_plus_commercial_signal",
                "combined_text",
                (
                    f"{corporate_report_match} + "
                    f"{commercial_match}"
                ),
            )

        return result(
            "exclude_clear_noncommercial",
            "corporate_institutional_reporting",
            "clear_corporate_report",
            field_for_phrase(
                texts,
                corporate_report_match,
            ),
            corporate_report_match,
        )

    # --------------------------------------------------------
    # 4. Safety / recall
    # MANUAL REVIEW ONLY
    # --------------------------------------------------------

    safety_match = find_phrase(
        text,
        SAFETY_RECALL_TERMS,
    )

    if safety_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "safety_or_recall_signal",
            field_for_phrase(
                texts,
                safety_match,
            ),
            safety_match,
        )

    # --------------------------------------------------------
    # 5. Pure legal / compliance notice
    # --------------------------------------------------------

    legal_match = find_phrase(
        text,
        LEGAL_NOTICE_TERMS,
    )

    if legal_match:
        if commercial_match:
            return result(
                "manual_review",
                "mixed_unclear",
                "legal_notice_plus_commercial_signal",
                "combined_text",
                (
                    f"{legal_match} + "
                    f"{commercial_match}"
                ),
            )

        return result(
            "exclude_clear_noncommercial",
            "legal_or_compliance_notice",
            "clear_legal_or_compliance_notice",
            field_for_phrase(
                texts,
                legal_match,
            ),
            legal_match,
        )

    # --------------------------------------------------------
    # Manual review: ambiguous application wording
    # --------------------------------------------------------

    if application_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "application_language_without_clear_employment_context",
            field_for_phrase(
                texts,
                application_match,
            ),
            application_match,
        )

    # --------------------------------------------------------
    # Manual review: CSR / charity
    # --------------------------------------------------------

    csr_match = find_phrase(
        text,
        CSR_CHARITY_TERMS,
    )

    if csr_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "csr_or_charity_signal",
            field_for_phrase(
                texts,
                csr_match,
            ),
            csr_match,
        )

    # --------------------------------------------------------
    # Manual review: sustainability
    # --------------------------------------------------------

    sustainability_match = find_phrase(
        text,
        SUSTAINABILITY_TERMS,
    )

    if sustainability_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "sustainability_signal",
            field_for_phrase(
                texts,
                sustainability_match,
            ),
            sustainability_match,
        )

    # --------------------------------------------------------
    # Manual review: sponsorship
    # --------------------------------------------------------

    sponsorship_match = find_phrase(
        text,
        SPONSORSHIP_TERMS,
    )

    if sponsorship_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "sponsorship_signal",
            field_for_phrase(
                texts,
                sponsorship_match,
            ),
            sponsorship_match,
        )

    # --------------------------------------------------------
    # Manual review: community / initiative
    # --------------------------------------------------------

    community_match = find_phrase(
        text,
        COMMUNITY_TERMS,
    )

    if community_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "community_or_initiative_signal",
            field_for_phrase(
                texts,
                community_match,
            ),
            community_match,
        )

    # --------------------------------------------------------
    # Manual review: weak corporate / institutional context
    # --------------------------------------------------------

    corporate_ambiguous_match = find_phrase(
        text,
        CORPORATE_AMBIGUOUS_TERMS,
    )

    if corporate_ambiguous_match:
        return result(
            "manual_review",
            "mixed_unclear",
            "institutional_context_signal",
            field_for_phrase(
                texts,
                corporate_ambiguous_match,
            ),
            corporate_ambiguous_match,
        )

    # --------------------------------------------------------
    # Default: retain
    # --------------------------------------------------------

    return result(
        "retain_commercial",
        "",
        "no_high_confidence_noncommercial_rule_triggered",
    )


# ============================================================
# CSV HELPERS
# ============================================================

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
    numerator: int,
    denominator: int,
) -> float:

    if denominator == 0:
        return 0.0

    return round(
        100.0
        * numerator
        / denominator,
        4,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_CSV.exists():
        sys.exit(
            "ERROR: input file not found:\n"
            f"{INPUT_CSV}"
        )

    AUDIT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    VALIDATION_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total = 0

    retained_output_rows = []
    exclusion_rows = []
    manual_rows = []

    counts = Counter()
    by_brand = defaultdict(
        Counter
    )
    by_sector = defaultdict(
        Counter
    )
    by_reason = Counter()
    by_rule = Counter()

    with INPUT_CSV.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as src:

        reader = csv.DictReader(
            src
        )

        original_fields = (
            reader.fieldnames
            or []
        )

        missing = [
            col
            for col in REQUIRED_COLUMNS
            if col not in original_fields
        ]

        if missing:
            sys.exit(
                "ERROR: missing required columns:\n"
                + "\n".join(
                    missing
                )
            )

        for row in reader:

            total += 1

            classification = classify(
                row
            )

            cls = classification[
                "commercial_eligibility"
            ]

            reason = classification[
                "eligibility_reason"
            ]

            rule = classification[
                "matched_rule"
            ]

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

            counts[
                cls
            ] += 1

            by_brand[
                brand
            ][
                "input_rows"
            ] += 1

            by_brand[
                brand
            ][
                cls
            ] += 1

            by_sector[
                sector
            ][
                "input_rows"
            ] += 1

            by_sector[
                sector
            ][
                cls
            ] += 1

            if reason:
                by_reason[
                    reason
                ] += 1

            if rule:
                by_rule[
                    rule
                ] += 1

            audit_row = dict(
                row
            )

            audit_row.update(
                classification
            )

            if (
                cls
                == "exclude_clear_noncommercial"
            ):
                exclusion_rows.append(
                    audit_row
                )
                continue

            if (
                cls
                == "manual_review"
            ):
                manual_rows.append(
                    audit_row
                )

            # Manual-review rows remain in the working dataset.
            retained_output_rows.append(
                row
            )

    # --------------------------------------------------------
    # Guardrail
    # --------------------------------------------------------

    if total != EXPECTED_INPUT_ROWS:
        sys.exit(
            "ERROR: input row count differs from the validated "
            "temporal-eligible dataset.\n"
            f"Expected: {EXPECTED_INPUT_ROWS:,}\n"
            f"Found:    {total:,}"
        )

    # --------------------------------------------------------
    # Main working output
    # --------------------------------------------------------

    write_csv(
        OUTPUT_CSV,
        retained_output_rows,
        original_fields,
    )

    audit_fields = (
        original_fields
        + [
            "commercial_eligibility",
            "eligibility_reason",
            "matched_rule",
            "matched_field",
            "matched_text",
        ]
    )

    write_csv(
        EXCLUSIONS_CSV,
        exclusion_rows,
        audit_fields,
    )

    write_csv(
        MANUAL_REVIEW_CSV,
        manual_rows,
        audit_fields,
    )

    # --------------------------------------------------------
    # Overall summary
    # --------------------------------------------------------

    excluded = counts[
        "exclude_clear_noncommercial"
    ]

    manual = counts[
        "manual_review"
    ]

    retained_classified = counts[
        "retain_commercial"
    ]

    output_n = len(
        retained_output_rows
    )

    summary_rows = [
        {
            "metric":
                "input_temporal_eligible_rows",
            "value":
                total,
            "note":
                "",
        },
        {
            "metric":
                "classified_retain_commercial",
            "value":
                retained_classified,
            "note":
                "",
        },
        {
            "metric":
                "classified_exclude_clear_noncommercial",
            "value":
                excluded,
            "note":
                "",
        },
        {
            "metric":
                "classified_manual_review",
            "value":
                manual,
            "note":
                "",
        },
        {
            "metric":
                "automatic_exclusion_pct",
            "value":
                pct(
                    excluded,
                    total,
                ),
            "note":
                "",
        },
        {
            "metric":
                "manual_review_pct",
            "value":
                pct(
                    manual,
                    total,
                ),
            "note":
                "",
        },
        {
            "metric":
                "current_working_output_rows",
            "value":
                output_n,
            "note":
                (
                    "Manual-review cases remain included. "
                    "Only clear non-commercial cases are automatically excluded."
                ),
        },
    ]

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
    # By brand
    # --------------------------------------------------------

    brand_rows = []

    for brand in sorted(
        by_brand
    ):

        c = by_brand[
            brand
        ]

        n = c[
            "input_rows"
        ]

        brand_rows.append({
            "search_brand":
                brand,
            "input_rows":
                n,
            "retain_commercial":
                c[
                    "retain_commercial"
                ],
            "exclude_clear_noncommercial":
                c[
                    "exclude_clear_noncommercial"
                ],
            "manual_review":
                c[
                    "manual_review"
                ],
            "automatic_exclusion_pct":
                pct(
                    c[
                        "exclude_clear_noncommercial"
                    ],
                    n,
                ),
            "manual_review_pct":
                pct(
                    c[
                        "manual_review"
                    ],
                    n,
                ),
        })

    write_csv(
        BY_BRAND_CSV,
        brand_rows,
        [
            "search_brand",
            "input_rows",
            "retain_commercial",
            "exclude_clear_noncommercial",
            "manual_review",
            "automatic_exclusion_pct",
            "manual_review_pct",
        ],
    )

    # --------------------------------------------------------
    # By sector
    # --------------------------------------------------------

    sector_rows = []

    for sector in sorted(
        by_sector
    ):

        c = by_sector[
            sector
        ]

        n = c[
            "input_rows"
        ]

        sector_rows.append({
            "sector":
                sector,
            "input_rows":
                n,
            "retain_commercial":
                c[
                    "retain_commercial"
                ],
            "exclude_clear_noncommercial":
                c[
                    "exclude_clear_noncommercial"
                ],
            "manual_review":
                c[
                    "manual_review"
                ],
            "automatic_exclusion_pct":
                pct(
                    c[
                        "exclude_clear_noncommercial"
                    ],
                    n,
                ),
            "manual_review_pct":
                pct(
                    c[
                        "manual_review"
                    ],
                    n,
                ),
        })

    write_csv(
        BY_SECTOR_CSV,
        sector_rows,
        [
            "sector",
            "input_rows",
            "retain_commercial",
            "exclude_clear_noncommercial",
            "manual_review",
            "automatic_exclusion_pct",
            "manual_review_pct",
        ],
    )

    # --------------------------------------------------------
    # By reason / rule
    # --------------------------------------------------------

    reason_rows = []

    for reason, n in sorted(
        by_reason.items(),
        key=lambda x: (
            -x[1],
            x[0],
        ),
    ):

        reason_rows.append({
            "type":
                "reason",
            "label":
                reason,
            "count":
                n,
        })

    for rule, n in sorted(
        by_rule.items(),
        key=lambda x: (
            -x[1],
            x[0],
        ),
    ):

        reason_rows.append({
            "type":
                "rule",
            "label":
                rule,
            "count":
                n,
        })

    write_csv(
        BY_REASON_CSV,
        reason_rows,
        [
            "type",
            "label",
            "count",
        ],
    )

    # --------------------------------------------------------
    # Terminal report
    # --------------------------------------------------------

    print(
        "COMMERCIAL ELIGIBILITY FILTER"
    )

    print(
        "=" * 72
    )

    print(
        f"Input rows:                    {total:,}"
    )

    print(
        f"Retain commercial:             {retained_classified:,}"
    )

    print(
        f"Exclude clear non-commercial:  {excluded:,}"
    )

    print(
        f"Manual review:                 {manual:,}"
    )

    print(
        f"Current working output rows:   {output_n:,}"
    )

    print()

    print(
        "AUTOMATIC EXCLUSIONS BY REASON"
    )

    exclusion_reason_counts = Counter(
        row[
            "eligibility_reason"
        ]
        for row in exclusion_rows
    )

    if exclusion_reason_counts:

        for reason, n in sorted(
            exclusion_reason_counts.items(),
            key=lambda x: (
                -x[1],
                x[0],
            ),
        ):

            print(
                f"  {reason}: {n:,}"
            )

    else:

        print(
            "  none"
        )

    print()

    print(
        "MANUAL REVIEW BY RULE"
    )

    manual_rule_counts = Counter(
        row[
            "matched_rule"
        ]
        for row in manual_rows
    )

    if manual_rule_counts:

        for rule, n in sorted(
            manual_rule_counts.items(),
            key=lambda x: (
                -x[1],
                x[0],
            ),
        ):

            print(
                f"  {rule}: {n:,}"
            )

    else:

        print(
            "  none"
        )

    print()

    print(
        "OUTPUTS"
    )

    print(
        f"  Working dataset:\n"
        f"    {OUTPUT_CSV}"
    )

    print(
        f"  Automatic exclusions:\n"
        f"    {EXCLUSIONS_CSV}"
    )

    print(
        f"  Manual review:\n"
        f"    {MANUAL_REVIEW_CSV}"
    )

    print(
        f"  Summary:\n"
        f"    {SUMMARY_CSV}"
    )

    print(
        f"  By brand:\n"
        f"    {BY_BRAND_CSV}"
    )

    print(
        f"  By sector:\n"
        f"    {BY_SECTOR_CSV}"
    )

    print(
        f"  By reason/rule:\n"
        f"    {BY_REASON_CSV}"
    )

    print()

    print(
        "IMPORTANT: manual-review cases remain in the working dataset."
    )

    print(
        "Input temporal dataset was not modified."
    )


if __name__ == "__main__":
    main()
