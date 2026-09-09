# Data Dictionary

This document defines the variables contained in the primary dataset and the separate Meta audience benchmark used in the thesis.

---

# 1. Primary dataset variables

| Variable name             | Conceptual meaning                                         | Original Meta field                          | Construction / transformation rule                                    | Data type                | Coding / reference category                           | Valid / missing values                                  | Analytical role                            | RQ / Hypothesis           | Limitations                                                                                            |
| ------------------------- | ---------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------------------- | ------------------------ | ----------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------ | ------------------------- | ------------------------------------------------------------------------------------------------------ |
| `brand`                   | Retailer identity                                          | Page ID / retailer mapping                   | Assigned from the verified Meta Page ID used in collection            | Categorical              | 20 retailer categories                                | Valid retailer name; no intended missing values         | Clustering / grouping variable             | All RQs                   | Only 20 retailers; configurations within a retailer may be correlated                                  |
| `sector`                  | Retail sector                                              | Derived from retailer                        | Retailers grouped into Grocery, Fashion, Drugstore/Beauty, Home/DIY   | Categorical              | One sector used as reference in regression            | Four valid categories                                   | Main explanatory variable                  | RQ1–RQ4; H1a–H7           | Sector effects may partly reflect the specific retailers included                                      |
| `creative_signature_hash` | Stable textual creative identity                           | `page_id`, body, title, caption, description | Hash constructed from Page ID plus normalized textual creative fields | String                   | Unique hash                                           | Valid hash; missing only if construction fails          | Grouping / configuration construction      | All analyses              | Does not capture image or video differences                                                            |
| `target_gender`           | Disclosed gender targeting                                 | Meta gender-targeting field                  | Harmonised to `All`, `Women`, `Men`                                   | Categorical              | `All` reference                                       | All / Women / Men                                       | Main explanatory variable                  | RQ1, RQ2, RQ3; H1a, H2–H5 | Represents disclosed targeting only; other campaign constraints are not observed                       |
| `gender_restricted`       | Presence of any disclosed gender restriction               | `target_gender`                              | `Women` or `Men` = 1; `All` = 0                                       | Binary                   | 0 = All reference                                     | 0 / 1                                                   | Adjusted outcome for H1a                   | RQ1 / H1a                 | Collapses Women and Men because sector cells are sparse; Grocery and Home/DIY remain highly imbalanced |
| `target_ages`             | Disclosed age-targeting range                              | Meta age-targeting field                     | Retained from Meta-disclosed targeting values                         | Categorical / structured | Original disclosed range                              | Valid disclosed age ranges                              | Source variable                            | RQ1 / H1b                 | Does not capture undisclosed delivery optimisation                                                     |
| `age_scope`               | Breadth of disclosed age targeting                         | `target_ages`                                | Full 18–65+ range = Broad; any narrower range = Narrow                | Binary / categorical     | Broad = reference; Narrow = 1                         | Broad / Narrow                                          | Main outcome for H1b                       | RQ1 / H1b                 | Binary coding simplifies differences in exact targeted age ranges                                      |
| `age_target_width`        | Width of disclosed age-targeting range                     | `target_ages`                                | Derived from lower and upper targeted age bounds                      | Numeric                  | Continuous                                            | Valid where age range can be derived                    | Sensitivity variable                       | RQ1 / H1b                 | Simplifies non-linear or open-ended age ranges                                                         |
| `publisher_platforms`     | Raw publisher-platform information                         | Meta `publisher_platforms`                   | Retained from Meta response                                           | Categorical / list       | Original platform values                              | Valid platform labels                                   | Source variable                            | RQ2–RQ4                   | Does not reveal how reach is divided when multiple platforms are listed                                |
| `platform_category`       | Analytical placement category                              | `publisher_platforms`                        | Classified as Facebook-only, Instagram-only, Both, or Other           | Categorical              | Facebook-only reference for direct platform contrasts | Four valid categories                                   | Main explanatory / stratification variable | RQ2–RQ4; H3, H5–H7        | `Both` does not identify platform-specific reach allocation                                            |
| `de_female`               | Germany-specific female delivered reach                    | Meta demographic delivery field              | Summed across ad IDs within an identical configuration                | Numeric                  | N/A                                                   | Non-negative; unavailable where Meta does not report it | Outcome component                          | RQ2–RQ3                   | Aggregated reported reach is not verified unique individuals                                           |
| `de_male`                 | Germany-specific male delivered reach                      | Meta demographic delivery field              | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Outcome component                          | RQ2–RQ3                   | Same aggregation limitation as `de_female`                                                             |
| `de_unknown`              | Germany-specific unknown-gender delivered reach            | Meta demographic delivery field              | Retained separately and summed within configuration                   | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Missingness / sensitivity variable         | RQ2–RQ3                   | Unknown-gender classification may be systematically related to other variables                         |
| `known_gender_reach`      | Total gender-classified delivery                           | `de_female`, `de_male`                       | `de_female + de_male`                                                 | Numeric                  | N/A                                                   | ≥ 0                                                     | Eligibility denominator                    | RQ2–RQ3                   | Zero values make female share undefined                                                                |
| `female_share`            | Delivered female proportion among known-gender delivery    | `de_female`, `de_male`                       | `de_female / (de_female + de_male)`                                   | Continuous proportion    | 0–1                                                   | Missing if known-gender reach = 0                       | Primary dependent variable                 | RQ2–RQ3; H2–H5            | Excludes unknown-gender delivery from the primary denominator                                          |
| `female_share_total`      | Female proportion including unknown-gender delivery        | `de_female`, `de_male`, `de_unknown`         | `de_female / (de_female + de_male + de_unknown)`                      | Continuous proportion    | 0–1                                                   | Missing if total denominator = 0                        | Sensitivity outcome                        | H2–H5 robustness          | Treats unknown gender as part of the denominator rather than a separate category                       |
| `de_age_18_24`            | Delivered reach aged 18–24                                 | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Outcome component                          | RQ4                       | Meta age classifications are platform-reported estimates                                               |
| `de_age_25_34`            | Delivered reach aged 25–34                                 | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Outcome component                          | RQ4                       | Same limitation                                                                                        |
| `de_age_35_44`            | Delivered reach aged 35–44                                 | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Denominator component                      | RQ4                       | Same limitation                                                                                        |
| `de_age_45_54`            | Delivered reach aged 45–54                                 | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Denominator component                      | RQ4                       | Same limitation                                                                                        |
| `de_age_55_64`            | Delivered reach aged 55–64                                 | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Denominator component                      | RQ4                       | Same limitation                                                                                        |
| `de_age_65_plus`          | Delivered reach aged 65+                                   | Meta age-delivery field                      | Summed within configuration                                           | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Denominator component                      | RQ4                       | Upper bound is open-ended                                                                              |
| `de_age_13_17`            | Delivered reach aged 13–17                                 | Meta age-delivery field                      | Retained separately; excluded from adult denominator                  | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Descriptive variable                       | RQ4                       | Not directly comparable with the 18+ Meta benchmark                                                    |
| `de_age_unknown`          | Delivered reach with unknown age                           | Meta age-delivery field                      | Retained separately                                                   | Numeric                  | N/A                                                   | Non-negative / unavailable                              | Missingness / descriptive variable         | RQ4                       | Unknown age may not be randomly distributed                                                            |
| `adult_age_reach`         | Total delivered reach aged 18+                             | Adult age-group fields                       | Sum of 18–24 through 65+ categories                                   | Numeric                  | N/A                                                   | ≥ 0                                                     | Eligibility denominator                    | RQ4                       | Zero values make adult 18–34 share undefined                                                           |
| `adult18_34_share`        | Share of delivered adult audience aged 18–34               | Adult age-delivery fields                    | `(18–24 + 25–34) / total delivered reach aged 18+`                    | Continuous proportion    | 0–1                                                   | Missing if adult-age denominator = 0                    | Primary dependent variable                 | RQ4; H6–H7                | Excludes 13–17 and unknown age; based on aggregated Meta-reported reach                                |
| `first_start`             | Earliest reported start date represented in the record     | Meta start-date field                        | Retained from eligible observations after temporal filtering          | Date                     | N/A                                                   | Valid date                                              | Descriptive / traceability variable        | Sample construction       | Not used as a campaign-month control                                                                   |
| `config_frequency`        | Number of Meta ad IDs represented by one configuration     | Meta ad IDs                                  | Count of ad IDs grouped by creative signature + targeting + platform  | Integer                  | N/A                                                   | ≥ 1                                                     | Descriptive / sensitivity variable         | Robustness                | Does not represent audience size                                                                       |
| `configuration_reach`     | Aggregated reported demographic reach within configuration | Meta demographic delivery fields             | Sum of Meta-reported reach across grouped ad IDs                      | Numeric                  | N/A                                                   | Non-negative                                            | Sensitivity weighting variable             | Robustness                | May include the same individual across more than one ad ID                                             |
| `facebook_only`           | Indicator for Facebook-only placement                      | `platform_category`                          | Facebook-only = 1, otherwise 0                                        | Binary                   | Model-specific                                        | 0 / 1                                                   | Platform contrast variable                 | RQ3–RQ4; H5–H7            | Only meaningful in models restricted to Facebook-only and Instagram-only                               |
| `instagram_only` / `IG_i` | Indicator for Instagram-only placement                     | `platform_category`                          | Instagram-only = 1; Facebook-only = 0                                 | Binary                   | Facebook-only = reference                             | 0 / 1                                                   | Main platform coefficient                  | RQ3–RQ4; H5–H7            | Fashion has no Facebook-only observations for the relevant within-sector contrasts                     |


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
