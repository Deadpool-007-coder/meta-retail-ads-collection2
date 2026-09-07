# Data dictionary

The primary dataset is `data/ads_eligibility_locked.csv`. One row represents one Meta Ad Library ad ID.

| Variable | Description |
|---|---|
| `search_brand` | Retailer used for the collection query. |
| `sector` | Retail sector assigned to the retailer. |
| `meta_ad_id` | Meta Ad Library ad ID; retained as the primary observation identifier. |
| `ad_creative_bodies` | Meta-provided creative body text. |
| `ad_creative_link_titles` | Meta-provided creative link title text. |
| `ad_creative_link_captions` | Meta-provided creative link caption text. |
| `ad_creative_link_descriptions` | Meta-provided creative link description text. |
| `publisher_platforms` | Meta-disclosed publisher platform list. |
| `target_ages` | Meta-disclosed age targeting. |
| `target_gender` | Meta-disclosed gender targeting. |
| `ad_delivery_start_date_time` | Meta-reported ad delivery start. |
| `ad_delivery_stop_date_time` | Meta-reported ad delivery stop; may be missing for ads without a reported stop. |
| `collection_timestamp` | Timestamp of recollection. |
| `de_male` | Germany demographic reach count reported for male users. |
| `de_female` | Germany demographic reach count reported for female users. |
| `de_unknown` | Germany demographic reach count reported for unknown gender. |
| `de_age_13_17` | Germany reach count aged 13–17. |
| `de_age_18_24` | Germany reach count aged 18–24. |
| `de_age_25_34` | Germany reach count aged 25–34. |
| `de_age_35_44` | Germany reach count aged 35–44. |
| `de_age_45_54` | Germany reach count aged 45–54. |
| `de_age_55_64` | Germany reach count aged 55–64. |
| `de_age_65_plus` | Germany reach count aged 65+. |
| `de_age_unknown` | Germany reach count with unknown age. |

## Derived variables planned for analysis

These are deliberately not added to the locked pre-analysis dataset yet.

- Female delivery share: `de_female / (de_female + de_male)`.
- Adult 18–34 share: `(de_age_18_24 + de_age_25_34) / (de_age_18_24 + de_age_25_34 + de_age_35_44 + de_age_45_54 + de_age_55_64 + de_age_65_plus)`.
- The 13–17 and unknown-age categories are excluded from the adult age denominator.
- Unknown gender is excluded from the primary female-share denominator and will be examined in sensitivity analyses.

## Textual creative signature

Script 08 constructs `creative_signature_hash` from verified Meta Page ID plus normalized body, title, caption and description. This is a **textual** creative signature. Meta does not provide a stable visual-asset identifier in this dataset, so identical text can potentially accompany different images or videos.


## Benchmark dataset

`benchmark/meta_audience_estimates_germany.csv` is a separate contextual Meta Marketing API audience benchmark collected on 28 August 2026. It is not part of the primary ad-level dataset.

| Variable | Description |
|---|---|
| `country` | Country targeted by the benchmark request (`DE`). |
| `platform_scope` | Facebook + Instagram, Facebook only, or Instagram only. |
| `gender` | All, male, or female benchmark audience. |
| `age_band` | Adult age range used in the estimate request. |
| `age_min` | Minimum target age. |
| `age_max` | Maximum target age; 65 denotes Meta's 65+ setting in these requests. |
| `estimate_mau_lower_bound` | Meta estimated monthly audience lower bound. |
| `estimate_mau_upper_bound` | Meta estimated monthly audience upper bound. |
| `estimate_mau_midpoint` | Midpoint of the lower and upper bounds. |
| `api_version` | Meta Marketing API version used for the request. |
| `collected_at_utc` | UTC timestamp of the benchmark request. |

The raw JSON is retained for API-response traceability. The XLSX workbook contains the same estimates plus formula-based summary calculations.
