#!/usr/bin/env python3

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "data" / "ads_analysis_ready.csv"
OUTPUT = ROOT / "data" / "ads_primary_configuration_level.csv"
AUDIT_OUTPUT = ROOT / "validation" / "primary_configuration_summary.csv"

KEY = [
    "creative_signature_hash",
    "target_gender",
    "target_ages",
    "platform_category",
]

REACH_COLUMNS = [
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


def main():

    if not INPUT.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT}")

    df = pd.read_csv(INPUT, low_memory=False)

    print("=" * 72)
    print("BUILD PRIMARY CONFIGURATION-LEVEL DATASET")
    print("=" * 72)

    print(f"\nInput: {INPUT}")
    print(f"Input rows: {len(df):,}")

    required = (
        KEY
        + REACH_COLUMNS
        + [
            "meta_ad_id",
            "search_brand",
            "sector",
            "age_scope",
        ]
    )

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(missing)
        )

    # Check configuration-key completeness.
    key_missing = df[KEY].isna().any(axis=1)

    if key_missing.any():
        raise ValueError(
            f"{int(key_missing.sum()):,} rows have missing "
            "primary configuration key values."
        )

    # Convert reach variables to numeric values.
    for col in REACH_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Check structural consistency within each configuration.
    consistency = (
        df.groupby(KEY, dropna=False)
        .agg(
            n_retailers=("search_brand", "nunique"),
            n_sectors=("sector", "nunique"),
            n_age_scopes=("age_scope", "nunique"),
        )
        .reset_index()
    )

    retailer_conflicts = int(
        (consistency["n_retailers"] > 1).sum()
    )

    sector_conflicts = int(
        (consistency["n_sectors"] > 1).sum()
    )

    age_scope_conflicts = int(
        (consistency["n_age_scopes"] > 1).sum()
    )

    if retailer_conflicts:
        raise ValueError(
            f"{retailer_conflicts:,} configurations contain "
            "more than one retailer."
        )

    if sector_conflicts:
        raise ValueError(
            f"{sector_conflicts:,} configurations contain "
            "more than one sector."
        )

    if age_scope_conflicts:
        raise ValueError(
            f"{age_scope_conflicts:,} configurations contain "
            "more than one age_scope."
        )

    # Retain configuration-level identifiers and classifications.
    meta = (
        df.groupby(KEY, dropna=False)
        .agg(
            search_brand=("search_brand", "first"),
            sector=("sector", "first"),
            age_scope=("age_scope", "first"),
            configuration_ad_id_count=("meta_ad_id", "nunique"),
        )
        .reset_index()
    )

    # Sum Meta-reported reach within each configuration.
    # min_count=1 preserves missing values when all contributing
    # observations are missing for a reach variable.
    reach = (
        df.groupby(KEY, dropna=False)[REACH_COLUMNS]
        .sum(min_count=1)
        .reset_index()
    )

    config = meta.merge(
        reach,
        on=KEY,
        how="left",
        validate="one_to_one",
    )

    # Known-gender denominator.
    config["known_gender_reach"] = (
        config["de_female"]
        + config["de_male"]
    )

    adult_cols = [
        "de_age_18_24",
        "de_age_25_34",
        "de_age_35_44",
        "de_age_45_54",
        "de_age_55_64",
        "de_age_65_plus",
    ]

    # Adult 18+ denominator.
    config["known_adult_reach"] = (
        config[adult_cols]
        .sum(axis=1, min_count=len(adult_cols))
    )

    # Delivered female share.
    config["female_delivery_share"] = np.where(
        config["known_gender_reach"] > 0,
        config["de_female"]
        / config["known_gender_reach"],
        np.nan,
    )

    # Delivered 18-34 share among adult reach.
    config["adult_18_34_share"] = np.where(
        config["known_adult_reach"] > 0,
        (
            config["de_age_18_24"]
            + config["de_age_25_34"]
        )
        / config["known_adult_reach"],
        np.nan,
    )

    # Demographic usability indicators.
    config["gender_data_usable"] = (
        config["known_gender_reach"] > 0
    ).astype(int)

    config["age_data_usable"] = (
        config["known_adult_reach"] > 0
    ).astype(int)

    # Unknown-demographic indicators.
    config["has_unknown_gender"] = np.where(
        config["de_unknown"].isna(),
        np.nan,
        (config["de_unknown"] > 0).astype(int),
    )

    config["has_unknown_age"] = np.where(
        config["de_age_unknown"].isna(),
        np.nan,
        (config["de_age_unknown"] > 0).astype(int),
    )

    # Check uniqueness of the primary configuration key.
    duplicate_configurations = int(
        config.duplicated(KEY).sum()
    )

    if duplicate_configurations:
        raise ValueError(
            f"{duplicate_configurations:,} duplicate "
            "configuration rows remain after aggregation."
        )

    # Check that derived shares remain within valid bounds.
    for variable in [
        "female_delivery_share",
        "adult_18_34_share",
    ]:
        valid = config[variable].dropna()

        if ((valid < 0) | (valid > 1)).any():
            raise ValueError(
                f"{variable} contains values outside [0, 1]."
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    config.to_csv(
        OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    repeated_configs = int(
        (config["configuration_ad_id_count"] > 1).sum()
    )

    singleton_configs = int(
        (config["configuration_ad_id_count"] == 1).sum()
    )

    ads_in_repeated_configs = int(
        config.loc[
            config["configuration_ad_id_count"] > 1,
            "configuration_ad_id_count",
        ].sum()
    )

    summary = pd.DataFrame(
        [
            ("input_ad_ids", len(df)),
            ("primary_configurations", len(config)),
            (
                "rows_removed_by_configuration_collapse",
                len(df) - len(config),
            ),
            (
                "singleton_configurations",
                singleton_configs,
            ),
            (
                "repeated_configurations",
                repeated_configs,
            ),
            (
                "ad_ids_in_repeated_configurations",
                ads_in_repeated_configs,
            ),
            (
                "maximum_ad_ids_in_one_configuration",
                int(
                    config[
                        "configuration_ad_id_count"
                    ].max()
                ),
            ),
            (
                "gender_usable_configurations",
                int(
                    config[
                        "gender_data_usable"
                    ].sum()
                ),
            ),
            (
                "gender_unusable_configurations",
                int(
                    (
                        config[
                            "gender_data_usable"
                        ]
                        == 0
                    ).sum()
                ),
            ),
            (
                "age_usable_configurations",
                int(
                    config[
                        "age_data_usable"
                    ].sum()
                ),
            ),
            (
                "age_unusable_configurations",
                int(
                    (
                        config[
                            "age_data_usable"
                        ]
                        == 0
                    ).sum()
                ),
            ),
            (
                "retailer_conflicts",
                retailer_conflicts,
            ),
            (
                "sector_conflicts",
                sector_conflicts,
            ),
            (
                "age_scope_conflicts",
                age_scope_conflicts,
            ),
        ],
        columns=["metric", "value"],
    )

    summary.to_csv(
        AUDIT_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nPRIMARY CONFIGURATION RESULTS")
    print("-" * 72)

    print(
        f"Original Meta ad IDs:            "
        f"{len(df):,}"
    )

    print(
        f"Primary configurations:          "
        f"{len(config):,}"
    )

    print(
        f"Rows collapsed:                  "
        f"{len(df) - len(config):,}"
    )

    print(
        f"Singleton configurations:        "
        f"{singleton_configs:,}"
    )

    print(
        f"Repeated configurations:         "
        f"{repeated_configs:,}"
    )

    print(
        f"Maximum IDs/configuration:       "
        f"{int(config['configuration_ad_id_count'].max()):,}"
    )

    print(
        f"Gender-usable configurations:    "
        f"{int(config['gender_data_usable'].sum()):,}"
    )

    print(
        f"Age-usable configurations:       "
        f"{int(config['age_data_usable'].sum()):,}"
    )

    print("\nREACH INTERPRETATION")
    print(
        "Reach summed across Meta ad IDs within a configuration "
        "is aggregated Meta-reported reach."
    )
    print(
        "It is not interpreted as independently verified "
        "unique individuals."
    )

    print(f"\nDataset written to:\n{OUTPUT}")
    print(f"\nAudit written to:\n{AUDIT_OUTPUT}")


if __name__ == "__main__":
    main()
