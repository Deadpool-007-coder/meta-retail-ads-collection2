# Meta Ads Delivery Collection — German Retail Advertising

This repository contains the data collection, validation, dataset construction, and statistical analysis pipeline for the Master's dissertation:

**Who Actually Sees the Ad? Audience Targeting and Algorithmic Delivery in German Retail Advertising on Meta**

The study examines disclosed audience targeting and demographic ad delivery for German retail advertising on Meta.

## Study scope

- Country: Germany
- Observation window: 6 September 2025 to 5 September 2026
- Retailers: 20
- Sectors: Grocery, Fashion, Health/Beauty, Home
- Eligible Meta ad IDs: 53,794
- Primary analytical configurations: 20,397

The primary analytical unit is defined by:

```text
creative_signature_hash
+ target_gender
+ target_ages
+ platform_category
```

## Main datasets

```text
data/ads_eligibility_locked.csv
data/ads_analysis_ready.csv
data/ads_primary_configuration_level.csv
```

The primary dissertation analyses use:

```text
data/ads_primary_configuration_level.csv
```

## Main processing scripts

```text
scripts/recollection.py
scripts/01_validate_recollection.py
scripts/02_audit_temporal_eligibility.py
scripts/03_build_temporal_eligible.py
scripts/04_apply_commercial_eligibility_filter.py
scripts/05_audit_commercial_eligibility.py
scripts/06_build_eligibility_validation_sample.py
scripts/07_apply_validated_eligibility.py
scripts/08_build_and_audit_stable_signature.py
scripts/09_summarize_stable_signature_conflicts.py
scripts/10_collect_meta_audience_benchmarks.py
scripts/11_build_analysis_ready_dataset.py
scripts/12_build_primary_configuration_dataset.py
```

## Analysis scripts

```text
data/H1 analysis.R
data/H2 analysis.R
data/H3 Analysis.R
data/H4 Analysis.R
data/H5 Analysis.R
data/H6 analysis.R
data/H7 Analysis.R
data/H7 specification check.R
data/Benchmark H4-H5.R
```

H6 and H7 use `adult_18_34_share` from the final configuration-level dataset.

## Demographic outcomes

Female delivery share:

```text
female_delivery_share = de_female / known_gender_reach
```

Adult 18–34 delivery share:

```text
adult_18_34_share =
(de_age_18_24 + de_age_25_34) / known_adult_reach
```

The final analytical dataset contains:

- 20,390 usable gender-delivery observations
- 20,393 usable adult-age observations

Missing demographic outcome values are not imputed.

## Benchmark

The contextual Meta audience benchmark is stored in:

```text
benchmark/meta_audience_estimates_germany.csv
```

The benchmark is used for contextual comparison and is not treated as a formal null distribution.

## Reproduction

Python dependencies:

```bash
pip install -r requirements.txt
```

R analysis scripts require packages including:

```text
clubSandwich
marginaleffects
openxlsx
lmtest
RcmdrMisc
dplyr
ggplot2
```

Run the R scripts from the repository root. Analysis outputs are written to:

```text
results/Thesis_Results.xlsx
```

## Data dictionary

Variable definitions for the primary analytical dataset are provided in:

```text
DATA_DICTIONARY.md
```

## Data and code availability

Repository:

```text
https://github.com/Deadpool-007-coder/meta-retail-ads-collection2
```

Code, documentation, validation outputs, and shareable research materials are provided in the repository.

Raw or derived Meta data are shared only where redistribution is permitted under applicable platform terms and data-governance requirements.

API credentials, access tokens, `.env` files, and other secrets are excluded from the repository.

## Software and reproducibility

The data-processing pipeline was implemented in Python and the statistical analyses were conducted in R.

### Python

Recommended version:

```text
Python 3.10+
```

Main dependencies:

```text
requests
numpy
pandas
```

Principal processing scripts:

```text
scripts/recollection.py
scripts/01_validate_recollection.py
scripts/03_build_temporal_eligible.py
scripts/04_apply_commercial_eligibility_filter.py
scripts/07_apply_validated_eligibility.py
scripts/08_build_and_audit_stable_signature.py
scripts/10_collect_meta_audience_benchmarks.py
scripts/11_build_analysis_ready_dataset.py
scripts/12_build_primary_configuration_dataset.py
```

Meta audience benchmark collection used:

```text
Meta Marketing API v25.0
```

### R

The dissertation analyses were implemented in:

```text
data/H1 analysis.R
data/H2 analysis.R
data/H3 Analysis.R
data/H4 Analysis.R
data/H5 Analysis.R
data/H6 analysis.R
data/H7 Analysis.R
data/H7 specification check.R
data/Benchmark H4-H5.R
```

Main R packages:

```text
clubSandwich
marginaleffects
openxlsx
lmtest
RcmdrMisc
dplyr
ggplot2
```

The final dissertation version should be identified using the final Git commit hash or release tag.
