# Data Dictionary

This document defines the variables contained in the primary dataset and the separate Meta audience benchmark used in the thesis.

The primary dataset is:

`data/ads_eligibility_locked.csv`

It contains **53,794 observations** and **24 variables**.

One row represents one Meta Ad Library ad ID. The primary observational unit is therefore the Meta ad ID.

---

# 1. Primary dataset variables

| Variable | Source | Type | Unit / coding | Definition | Missingness / analytical treatment |
|---|---|---|---|---|---|
| `search_brand` | Collection configuration | Categorical text | Retailer name | Retailer associated with the verified Meta Page ID used for collection. | Complete in the locked dataset. |
| `sector` | Retailer classification | Categorical text | `grocery`, `fashion`, `health_beauty`, `home` | Retail sector assigned to each retailer. | Complete in the locked dataset. |
| `meta_ad_id` | Meta Ad Library API | Identifier/text | Meta ad ID | Meta-provided advertisement identifier and primary observation identifier. | Complete and unique across all 53,794 rows. |
| `ad_creative_bodies` | Meta Ad Library API | Serialized text field | JSON-formatted list where populated | Meta-provided advertisement body text. The original returned text is retained unchanged. | May be empty when no body text is returned. Not imputed. |
| `ad_creative_link_titles` | Meta Ad Library API | Serialized text field | JSON-formatted list where populated | Meta-provided creative link title. | May be empty. Not imputed. |
| `ad_creative_link_captions` | Meta Ad Library API | Serialized text field | JSON-formatted list where populated | Meta-provided creative link caption. | May be empty. Not imputed. |
| `ad_creative_link_descriptions` | Meta Ad Library API | Serialized text field | JSON-formatted list where populated | Meta-provided creative link description. | May be empty. Not imputed. |
| `publisher_platforms` | Meta Ad Library API | Serialized categorical field | JSON-formatted platform list | Publisher platforms returned by Meta for the ad. Examples include `["facebook"]`, `["instagram"]`, and `["facebook","instagram"]`, as well as configurations containing additional Meta platforms. | Complete in the locked dataset. Original values are retained. |
| `target_ages` | Meta Ad Library API | Serialized categorical field | JSON-formatted minimum/maximum age values | Meta-returned disclosed age-targeting range. For example, `["18","65"]` represents the full returned 18-to-65 range used in this dataset. | Complete in the locked dataset. Original values are retained. |
| `target_gender` | Meta Ad Library API | Categorical text | `All`, `Women`, `Men` | Meta-returned disclosed gender-targeting category. | Complete in the locked dataset. |
| `ad_delivery_start_date_time` | Meta Ad Library API | Datetime | Date/time | Meta-reported advertisement delivery start. Used for temporal eligibility. | Complete in the locked dataset. |
| `ad_delivery_stop_date_time` | Meta Ad Library API | Datetime | Date/time | Meta-reported advertisement delivery stop where available. | May be missing. A missing stop date does not by itself make an observation ineligible. |
| `collection_timestamp` | Collection script | Datetime | Timestamp | Timestamp at which the advertisement record was collected. | Complete in the locked dataset. |
| `de_male` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach for male users. | May be unavailable when the complete demographic breakdown is unavailable. |
| `de_female` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach for female users. | May be unavailable when the complete demographic breakdown is unavailable. |
| `de_unknown` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach assigned to unknown gender. | Retained separately and excluded from the primary female-share denominator. |
| `de_age_13_17` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 13-17. | Retained separately and excluded from the adult 18+ denominator. |
| `de_age_18_24` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 18-24. | Included in the adult-age denominator. |
| `de_age_25_34` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 25-34. | Included in the adult-age denominator. |
| `de_age_35_44` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 35-44. | Included in the adult-age denominator. |
| `de_age_45_54` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 45-54. | Included in the adult-age denominator. |
| `de_age_55_64` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 55-64. | Included in the adult-age denominator. |
| `de_age_65_plus` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach aged 65 and above. | Included in the adult-age denominator. |
| `de_age_unknown` | Meta demographic reach breakdown | Numeric count | Meta-reported reach count | Germany-specific reported reach assigned to unknown age. | Retained separately and excluded from the primary adult-age denominator. |

---

# 2. Demographic reach interpretation

Variables beginning with `de_` are **Meta-reported reach counts for Germany**.

They are not:

- impression counts;
- delivery frequency;
- independently verified counts of unique individuals across different Meta ad IDs.

The primary dataset remains at Meta-ad-ID level.

Reach is not aggregated across different Meta ad IDs in the primary dataset.

Any aggregation used later for descriptive or sensitivity analysis should therefore be described as **aggregated Meta-reported reach counts**, not as a count of unique individuals.

---

# 3. Temporal eligibility

The recollection queried the period:

`2025-09-06` through `2026-09-05`

The primary temporal definition is a strict launch cohort:

```text
2025-09-06 <= ad_delivery_start_date_time <= 2026-09-05
```

Sample construction at the temporal stage:

| Stage | Meta ad IDs |
|---|---:|
| Raw recollection | 62,436 |
| Pre-window starts excluded | 2,107 |
| Temporally eligible | 60,329 |

An advertisement is not excluded solely because `ad_delivery_stop_date_time` is missing or occurs after 5 September 2026.

The demographic reach values therefore cannot be interpreted as reach occurring exclusively within the launch window.

---

# 4. Commercial eligibility

Commercial eligibility has already been applied before construction of the locked primary dataset and is therefore not stored as a separate variable in `data/ads_eligibility_locked.csv`.

Final sample construction:

| Stage | Meta ad IDs |
|---|---:|
| Fresh recollection | 62,436 |
| Pre-window starts excluded | -2,107 |
| Temporally eligible | 60,329 |
| Automatic commercial-eligibility exclusions | -6,480 |
| Manual-review exclusions | -55 |
| **Final locked dataset** | **53,794** |

The predefined manual-review bucket contained 867 Meta ad IDs:

- 812 retained;
- 55 excluded.

The independent excluded and retained validation samples were used to evaluate classification performance rather than to selectively alter sampled production observations.

---

# 5. Analytical variables derived from existing fields

These variables are not currently stored in `data/ads_eligibility_locked.csv`. They are calculated during the analytical stage.

## 5.1 `female_delivery_share`

Derived from:

- `de_female`
- `de_male`

Formula:

```text
de_female / (de_female + de_male)
```

Interpretation:

Female share of Germany-specific reach among observations with known male/female reach.

Primary denominator:

```text
de_female + de_male
```

`de_unknown` is excluded from the primary denominator.

The outcome is undefined when the denominator equals zero or the required demographic fields are unavailable.

No value is imputed.

---

## 5.2 `adult_18_34_share`

Derived from:

- `de_age_18_24`
- `de_age_25_34`
- `de_age_35_44`
- `de_age_45_54`
- `de_age_55_64`
- `de_age_65_plus`

Formula:

```text
(de_age_18_24 + de_age_25_34)
/
(de_age_18_24
 + de_age_25_34
 + de_age_35_44
 + de_age_45_54
 + de_age_55_64
 + de_age_65_plus)
```

Interpretation:

Share of known Germany-specific adult reach aged 18-34.

The denominator contains only known reach aged 18+.

The following variables are excluded from the primary adult denominator:

- `de_age_13_17`
- `de_age_unknown`

The outcome is undefined when the required age fields are unavailable or the known adult denominator equals zero.

No value is imputed.

---

## 5.3 `age_scope`

Derived from:

`target_ages`

Categories:

```text
Broad
Narrow
```

**Broad**

`target_ages` spans the complete 18-to-65 range used for the adult targeting classification, represented in the collected data as:

```text
["18","65"]
```

**Narrow**

`target_ages` contains a more restricted minimum and/or maximum age.

The original `target_ages` value remains unchanged in the locked dataset.

---

## 5.4 Analytical grouping of `publisher_platforms`

The original `publisher_platforms` field is retained unchanged.

For analyses requiring mutually exclusive platform categories, its values can be grouped as:

```text
Facebook-only
Instagram-only
Both
Other
```

**Facebook-only**

The platform list contains only Facebook.

**Instagram-only**

The platform list contains only Instagram.

**Both**

The platform list contains exactly Facebook and Instagram.

**Other**

All remaining configurations, including combinations containing additional Meta platforms.

This recoding is analytical only and does not overwrite the original `publisher_platforms` field.

---

## 5.5 `month`

Derived from:

`ad_delivery_start_date_time`

Definition:

Calendar month corresponding to the Meta-reported advertisement delivery start date.

---

# 6. `target_gender`

The original `target_gender` variable is used directly for the principal gender-targeting classification.

Observed values in the locked dataset are:

| `target_gender` | Rows |
|---|---:|
| `All` | 45,010 |
| `Women` | 6,819 |
| `Men` | 1,965 |
| **Total** | **53,794** |

The variable therefore does not require renaming for the primary three-category analysis.

Where a later statistical model requires a binary contrast, the necessary indicator can be derived from `target_gender` without changing the original field.

---

# 7. Demographic-data usability and missingness

Different forms of demographic incompleteness and zero denominators are treated separately.

The final dataset contains:

| Condition | Rows |
|---|---:|
| No Germany-specific demographic data | 2 |
| Complete demographic data but zero known-gender reach | 14 |
| Rows unable to produce `female_delivery_share` | 16 |
| Positive unknown-gender reach | 41,930 |
| Positive unknown-age reach | 21,829 |
| Complete age data but zero adult-age denominator | 5 |
| Rows unable to produce `adult_18_34_share` | 7 |
| Complete gender and age demographic rows | 53,792 |
| Gender/age reconciliation mismatches among comparable rows | 0 |

The 16 rows unable to produce `female_delivery_share` consist of:

- 2 rows without demographic data;
- 14 rows with available male and female fields but `de_male + de_female = 0`.

The 7 rows unable to produce `adult_18_34_share` consist of:

- 2 rows without demographic data;
- 5 rows with complete adult-age fields but a zero adult-age denominator.

---

## 7.1 No demographic data

Two observations contain no Germany-specific demographic breakdown values.

They remain part of the locked master dataset but cannot contribute to analyses requiring demographic outcomes.

---

## 7.2 Zero known-gender reach

For observations with available male and female fields, zero known-gender reach is defined as:

```text
de_male + de_female = 0
```

There are 14 such observations.

These rows cannot produce `female_delivery_share`.

---

## 7.3 Unknown-gender reach

There are 41,930 observations with positive `de_unknown`.

Positive unknown-gender reach does not automatically make an observation unusable.

`de_unknown` is excluded from the primary female-share denominator and retained for missingness and sensitivity analyses.

---

## 7.4 Zero adult-age denominator

For observations with complete required adult-age fields, the denominator is:

```text
de_age_18_24
+ de_age_25_34
+ de_age_35_44
+ de_age_45_54
+ de_age_55_64
+ de_age_65_plus
```

Five observations have a complete adult-age breakdown but a denominator equal to zero.

These rows cannot produce `adult_18_34_share`.

---

## 7.5 Unknown-age reach

There are 21,829 observations with positive `de_age_unknown`.

`de_age_unknown` is retained separately and excluded from the primary adult-age denominator.

Positive unknown-age reach does not automatically make an observation unusable when known adult-age reach is available.

---

## 7.6 Demographic reconciliation

There are 53,792 observations with complete gender and age demographic fields.

For all 53,792 of these observations:

```text
de_male + de_female + de_unknown
```

equals:

```text
de_age_13_17
+ de_age_18_24
+ de_age_25_34
+ de_age_35_44
+ de_age_45_54
+ de_age_55_64
+ de_age_65_plus
+ de_age_unknown
```

There are **0 reconciliation mismatches** among comparable observations.

---

## 7.7 Imputation

No demographic reach values are imputed.

Analytical sample size therefore depends on the variables required for each outcome and statistical model.

Model-specific N should be reported with the corresponding analysis.

---

# 8. Stable textual creative signature

Script 08 constructs:

`creative_signature_hash`

This variable is created in the separate stable-signature audit dataset and is not present in `data/ads_eligibility_locked.csv`.

The signature uses:

```text
verified Meta Page ID
+ normalized ad_creative_bodies
+ normalized ad_creative_link_titles
+ normalized ad_creative_link_captions
+ normalized ad_creative_link_descriptions
```

Text normalization consists of:

- Unicode NFKC normalization;
- case folding;
- whitespace collapsing.

The normalized components are combined and hashed using SHA-256.

Normalization is used only for signature construction. The original creative-text fields remain unchanged.

`creative_signature_hash` is used for grouping, audit, and sensitivity analysis.

It is not the primary observation identifier.

The primary observation identifier remains:

`meta_ad_id`

## Limitation

The signature captures textual identity rather than complete visual identity.

Identical text can therefore occur with different images or videos, while the same visual material can occur with different text.

For this reason, the field is described as a **stable textual creative signature**.

---

# 9. Stable-signature audit

The stable-signature audit of the locked dataset produced:

| Measure | Result |
|---|---:|
| Meta ad IDs | 53,794 |
| Distinct textual creative signatures | 18,709 |
| Signature groups containing more than one Meta ad ID | 7,889 |
| Meta ad IDs belonging to repeated-signature groups | 42,974 |
| Maximum Meta IDs in one signature group | 421 |
| Repeated-signature groups with platform and/or targeting conflicts | 1,747 |

Conflict patterns:

| Conflict pattern | Signature groups |
|---|---:|
| `publisher_platforms` | 892 |
| `target_ages` + `target_gender` | 345 |
| `target_gender` | 219 |
| `target_ages` | 139 |
| `publisher_platforms` + `target_gender` | 82 |
| `publisher_platforms` + `target_ages` | 50 |
| `publisher_platforms` + `target_ages` + `target_gender` | 20 |
| **Total** | **1,747** |

Because repeated textual signatures can differ in platform or targeting fields used in the research questions, the primary dataset is not collapsed to one row per textual signature.

---

# 10. Benchmark dataset

The separate benchmark dataset is:

`benchmark/meta_audience_estimates_germany.csv`

It contains **63 rows and 11 variables**.

The estimates were collected on **28 August 2026** using Meta Marketing API version `v25.0`.

The benchmark is separate from the 53,794-row primary dataset.

## Benchmark variables

| Variable | Source | Type | Unit / coding | Definition |
|---|---|---|---|---|
| `country` | Benchmark API targeting specification | Categorical text | `DE` | Country used in the benchmark request. |
| `platform_scope` | Benchmark collection configuration | Categorical text | `facebook_instagram`, `facebook_only`, `instagram_only` | Platform scope for which the estimate was requested. |
| `gender` | Benchmark targeting specification | Categorical text | `all`, `male`, `female` | Gender setting used for the benchmark request. |
| `age_band` | Benchmark collection configuration | Categorical text | `18-65+`, `18-24`, `25-34`, `35-44`, `45-54`, `55-64`, `65+` | Age range represented by the benchmark row. |
| `age_min` | Benchmark targeting specification | Integer | Age | Minimum age submitted in the request. |
| `age_max` | Benchmark targeting specification | Integer | Age | Maximum age value submitted in the request. |
| `estimate_mau_lower_bound` | Meta Marketing API | Numeric count | Estimated monthly audience | Lower bound returned for the estimated monthly audience. |
| `estimate_mau_upper_bound` | Meta Marketing API | Numeric count | Estimated monthly audience | Upper bound returned for the estimated monthly audience. |
| `estimate_mau_midpoint` | Calculated from API bounds | Numeric count | Estimated monthly audience | Arithmetic midpoint of `estimate_mau_lower_bound` and `estimate_mau_upper_bound`. |
| `api_version` | Benchmark collection script | Text | API version | Meta Marketing API version used for the request. All rows in the stored benchmark use `v25.0`. |
| `collected_at_utc` | Benchmark collection script | Datetime | UTC timestamp | Timestamp at which each benchmark estimate was collected. |

All 63 benchmark rows contain values for all 11 variables.

The three platform scopes contain 21 rows each.

---

# 11. Benchmark interpretation

The benchmark provides contextual Meta-estimated monthly audience ranges for Germany.

The midpoint is calculated as:

```text
(estimate_mau_lower_bound + estimate_mau_upper_bound) / 2
```

The benchmark is not treated as:

- observed advertisement delivery;
- advertiser-intended audience composition;
- a required demographic distribution;
- a conventional hypothesis-test null value.

In particular, `target_gender = All` in the ad-level dataset is not interpreted as implying an intended 50/50 male/female delivery split.

---

# 12. Dataset provenance

The primary dataset is produced through the following sequence:

```text
Fresh Meta Ad Library recollection
        |
        v
Raw-data validation
        |
        v
Temporal eligibility audit
        |
        v
Strict launch-cohort construction
        |
        v
Commercial-eligibility classification
        |
        v
Manual adjudication of uncertain cases
        |
        v
53,794-row locked primary dataset
```

Stable textual-signature construction occurs after the locked eligibility dataset is created and does not change the primary sample size.

The Meta audience benchmark is collected separately and is not merged into the primary ad-level dataset.

---

# 13. Analytical conventions

- Primary observation identifier: `meta_ad_id`.
- Primary observational unit: one Meta ad ID.
- `target_gender`, `target_ages`, and `publisher_platforms` are retained under their original variable names.
- A new variable name is used only when an analytical quantity is genuinely derived from an existing field.
- Primary female-share denominator: `de_female + de_male`.
- `de_unknown` is excluded from the primary female-share denominator.
- Primary adult-age denominator uses known reach aged 18+.
- `de_age_13_17` is excluded from the adult denominator.
- `de_age_unknown` is excluded from the primary adult denominator.
- No demographic reach values are imputed.
- Complete missingness, zero denominators, and unknown demographic categories are treated separately.
- Reach values are Meta-reported reach counts rather than impressions.
- Aggregated reach across advertisements is not interpreted as independently verified unique-person reach.
- `creative_signature_hash` is not used to collapse the primary dataset.
- The Meta audience benchmark is treated as contextual information rather than a formal null distribution.
