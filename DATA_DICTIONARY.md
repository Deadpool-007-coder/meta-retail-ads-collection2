# Data Dictionary

# Data Dictionary

This document describes the variables used in the final primary analytical dataset, `data/ads_primary_configuration_level.csv`.

| Variable | Meaning | Construction / Coding | Analytical use |
|---|---|---|---|
| `creative_signature_hash` | Stable textual creative identifier | Hash based on retailer Page ID and normalised creative-text fields | Identifies repeated textual creatives and forms part of configuration key |
| `target_gender` | Disclosed gender targeting | All, Women, or Men | Main targeting variable for RQ1–RQ3; H1a, H2–H5 |
| `target_ages` | Disclosed age-targeting range | Original disclosed age range retained | Source variable for age-targeting analysis |
| `platform_category` | Analytical platform category | Facebook-only, Instagram-only, Both, or Other | Platform comparison and interaction variable |
| `search_brand` | Retailer identity | One of the 20 selected retailers | Retailer grouping and clustering |
| `sector` | Retail sector | Grocery, Fashion, Health/Beauty, or Home | Main explanatory variable across RQs |
| `age_scope` | Breadth of disclosed age targeting | Full 18–65 range = Broad; narrower range = Narrow | Outcome for H1b |
| `configuration_ad_id_count` | Number of Meta ad IDs represented by one configuration | Count of ad IDs sharing the same configuration key | Descriptive and sensitivity analysis |
| `de_male` | Germany-specific male delivered reach | Meta-reported reach summed within configuration | Gender outcome component |
| `de_female` | Germany-specific female delivered reach | Meta-reported reach summed within configuration | Gender outcome component |
| `de_unknown` | Germany-specific unknown-gender reach | Meta-reported unknown-gender reach summed within configuration | Missingness and sensitivity analysis |
| `de_age_13_17` | Delivered reach aged 13–17 | Meta-reported reach summed within configuration | Descriptive; excluded from adult denominator |
| `de_age_18_24` | Delivered reach aged 18–24 | Meta-reported reach summed within configuration | Numerator component for age outcome |
| `de_age_25_34` | Delivered reach aged 25–34 | Meta-reported reach summed within configuration | Numerator component for age outcome |
| `de_age_35_44` | Delivered reach aged 35–44 | Meta-reported reach summed within configuration | Adult-age denominator component |
| `de_age_45_54` | Delivered reach aged 45–54 | Meta-reported reach summed within configuration | Adult-age denominator component |
| `de_age_55_64` | Delivered reach aged 55–64 | Meta-reported reach summed within configuration | Adult-age denominator component |
| `de_age_65_plus` | Delivered reach aged 65+ | Meta-reported reach summed within configuration | Adult-age denominator component |
| `de_age_unknown` | Delivered reach with unknown age | Meta-reported unknown-age reach summed within configuration | Missingness and descriptive analysis |
| `known_gender_reach` | Total delivery with known binary gender | `de_female + de_male` | Denominator for `female_delivery_share` |
| `known_adult_reach` | Total known delivered reach aged 18+ | Sum of age groups 18–24 through 65+ | Denominator for `adult_18_34_share` |
| `female_delivery_share` | Female share of known-gender delivery | `de_female / known_gender_reach` | Primary dependent variable for H2–H5 |
| `adult_18_34_share` | Share of known adult delivery aged 18–34 | `(de_age_18_24 + de_age_25_34) / known_adult_reach` | Primary dependent variable for H6–H7 |
| `gender_data_usable` | Whether gender outcome can be calculated | 1 where known-gender reach > 0; otherwise 0 | Missing-data and analytical-sample check |
| `age_data_usable` | Whether age outcome can be calculated | 1 where known-adult reach > 0; otherwise 0 | Missing-data and analytical-sample check |
| `has_unknown_gender` | Presence of positive unknown-gender reach | 1 if `de_unknown > 0`; 0 otherwise where reported | Missingness and sensitivity analysis |
| `has_unknown_age` | Presence of positive unknown-age reach | 1 if `de_age_unknown > 0`; 0 otherwise where reported | Missingness and descriptive analysis |


