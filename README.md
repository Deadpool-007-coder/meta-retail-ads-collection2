# Meta Ads Delivery Recollection - German Retail Advertising

This repository contains the data-collection, validation, sample-construction, and analysis-ready dataset pipeline for a Master's thesis examining the relationship between advertisers' disclosed audience targeting and demographic ad delivery on Meta in the German retail sector.

The repository documents a fresh Meta Ad Library recollection designed to address methodological concerns identified in an earlier historical pipeline, especially temporal construction, commercial-eligibility filtering, stable creative identification, repeated textual creatives, demographic-data completeness, age-denominator construction, and reproducibility.

The locked pre-analysis dataset contains **53,794 Meta Ad Library ad IDs**. The primary observational unit is **one Meta ad ID**. Reach values are not aggregated across different Meta ad IDs in the primary dataset.

## Study scope

- Country: Germany (`DE`)
- Recollection query window: 6 September 2025 to 5 September 2026
- Primary retailers: 20
- Sectors: Grocery, Fashion, Drugstore/Beauty, Home/DIY
- Raw collection unit: one consolidated Meta Ad Library ad ID per row
- Primary analysis unit: one Meta Ad Library ad ID
- REWE is not part of the primary 20-retailer sample

### Retailers

**Grocery:** Aldi Nord, Aldi Süd, Penny, Lidl, Kaufland, Edeka Südwest  
**Fashion:** Bonprix, Zalando, New Yorker, Zara, About You  
**Drugstore/Beauty:** dm, Rossmann, Douglas, Müller, Flaconi  
**Home/DIY:** Bauhaus, OBI, IKEA, Hornbach

## Repository structure

```text
.
|-- README.md
|-- DATA_DICTIONARY.md
|-- requirements.txt
|-- .gitignore
|-- data/
|   |-- ads_eligibility_locked.csv
|   `-- ads_analysis_ready.csv
|-- scripts/
|   |-- recollection.py
|   |-- 01_validate_recollection.py
|   |-- 02_audit_temporal_eligibility.py
|   |-- 03_build_temporal_eligible.py
|   |-- 04_apply_commercial_eligibility_filter.py
|   |-- 05_audit_commercial_eligibility.py
|   |-- 06_build_eligibility_validation_sample.py
|   |-- 07_apply_validated_eligibility.py
|   |-- 08_build_and_audit_stable_signature.py
|   |-- 09_summarize_stable_signature_conflicts.py
|   |-- 10_collect_meta_audience_benchmarks.py
|   `-- 11_build_analysis_ready_dataset.py
|-- audit/
|   |-- commercial_eligibility_manual_decisions.csv
|   |-- excluded_validation_manual_review.csv
|   |-- retained_validation_manual_review.csv
|   `-- other_noncommercial_exclusions_full_review.csv
|-- validation/
|   |-- eligibility_validation_summary.csv
|   `-- stable_signature_conflict_summary.csv
`-- benchmark/
    |-- meta_audience_estimates_germany.csv
    |-- meta_audience_estimates_germany_raw.json
    `-- meta_audience_benchmark_full_with_formulas.xlsx
```

## Data collection

### Meta Ad Library recollection

`scripts/recollection.py` retrieves the 20 verified retailer Page IDs from the Meta Ad Library API. The collection design is:

- Germany only
- one consolidated Meta ad ID per output row
- no commercial/recruitment filtering during collection
- no creative-level deduplication during collection
- Germany-specific age/gender reach collected in the same API request as the ad metadata
- explicit retention of unknown-age and unknown-gender reach
- checkpoint/resume support
- adaptive date splitting for large API responses
- repeated Meta IDs audited rather than silently discarded

The following creative and disclosed-delivery fields are retained on the same row as demographic delivery:

- ad body
- link title
- link caption
- link description
- publisher platforms
- disclosed target ages
- disclosed target gender
- delivery start and stop timestamps
- Germany-specific gender reach
- Germany-specific age-bucket reach

Collecting these fields in one request avoids the cross-file representative-ID merge problem present in the earlier historical pipeline.

## Meta API credentials

API credentials are **not stored in this repository**.

The recollection script requires:

```text
META_ACCESS_TOKEN
```

The benchmark collector requires:

```text
META_ACCESS_TOKEN
META_AD_ACCOUNT_ID
```

`META_API_VERSION` is optional for the benchmark collector. If it is not provided, the benchmark script uses its documented default version.

The scripts read credentials from environment variables. Do not paste access tokens into source files or commit them to GitHub.

Example in PowerShell:

```powershell
$env:META_ACCESS_TOKEN="your_token_here"
$env:META_AD_ACCOUNT_ID="your_ad_account_id_here"
```

Example in Bash/Zsh:

```bash
export META_ACCESS_TOKEN="your_token_here"
export META_AD_ACCOUNT_ID="your_ad_account_id_here"
```

## Pipeline

The scripts are numbered in execution order after recollection.

### `recollection.py`

Collects one consolidated row per Meta ad ID, including the four creative-text fields, disclosed targeting, platform information, delivery dates, and Germany-specific demographic reach.

### `01_validate_recollection.py`

Validates the raw recollection, including:

- schema and required columns
- expected retailers
- uniqueness and presence of Meta ad IDs
- targeting/platform/date missingness
- presence of demographic data
- zero known-gender reach
- unknown-gender and unknown-age reach
- reconciliation of summed gender and age totals
- adult-age denominator availability
- repeated-ID audit files produced during recollection

### `02_audit_temporal_eligibility.py`

Audits reported start and stop dates relative to the study window without modifying the source data.

### `03_build_temporal_eligible.py`

Applies the strict launch-cohort rule described below.

### `04_apply_commercial_eligibility_filter.py`

Classifies clear non-commercial exclusions, clear commercial observations, and cases requiring manual review using all four available creative-text fields.

### `05_audit_commercial_eligibility.py`

Audits the concentration and composition of automatic exclusions before the production eligibility dataset is locked.

### `06_build_eligibility_validation_sample.py`

Constructs reproducible signature-level validation samples so repeated versions of the same textual creative do not dominate manual validation.

### `07_apply_validated_eligibility.py`

Applies the predefined automatic exclusions and the adjudicated decisions from the predefined manual-review bucket. Independent validation samples remain diagnostic and are not selectively used to alter production rows.

### `08_build_and_audit_stable_signature.py`

Attaches the verified Meta Page ID and constructs a stable textual creative signature from Page ID plus the four normalized text fields. It audits repeated-signature groups without deduplicating the primary dataset.

### `09_summarize_stable_signature_conflicts.py`

Summarizes targeting and platform conflicts within repeated textual creative-signature groups.

### `10_collect_meta_audience_benchmarks.py`

Collects contextual Meta monthly-audience estimates for Germany for Facebook + Instagram, Facebook-only, and Instagram-only scopes.

### `11_build_analysis_ready_dataset.py`

Builds the final 53,794-row analysis-ready dataset from the locked eligibility dataset. The script preserves all 24 original fields, adds 12 analytical/support variables, reproduces the stable textual creative signature, and validates row counts, identifiers, demographic denominators, derived shares, targeting categories, platform categories, and demographic reconciliation.

The final derived analytical classifications are:

| Variable | Category | N |
|---|---|---:|
| `age_scope` | Broad | 39,271 |
|  | Narrow | 14,523 |
| `platform_category` | Both | 22,950 |
|  | Facebook-only | 5,057 |
|  | Instagram-only | 8,447 |
|  | Other | 17,340 |


## Sample construction

| Stage | Meta ad IDs |
|---|---:|
| Fresh recollection | 62,436 |
| Pre-window starts excluded | -2,107 |
| Temporal eligible | 60,329 |
| Automatic commercial-eligibility exclusions | -6,480 |
| Manual-review exclusions | -55 |
| **Final locked eligibility dataset** | **53,794** |

The final locked dataset is:

```text
data/ads_eligibility_locked.csv
```

## Analysis-ready dataset

The final analysis-ready dataset is:

```text
data/ads_analysis_ready.csv
```

It contains **53,794 Meta ad IDs and 36 variables**:

- 24 original variables from the locked eligibility dataset;
- 12 derived analytical and support variables.

The primary observational unit remains **one Meta ad ID**. No deduplication, reach aggregation, or demographic imputation is performed during construction.

The analysis-ready dataset is produced reproducibly by:

```text
scripts/11_build_analysis_ready_dataset.py
```

## Temporal construction

The Meta API was queried for the period 2025-09-06 through 2026-09-05. Because ads returned by the API can begin before the query period, temporal eligibility is defined using the reported delivery start date.

The primary temporal rule is a **strict launch cohort**:

```text
2025-09-06 <= ad_delivery_start_date_time <= 2026-09-05
```

This produces:

- 62,436 recollected Meta ad IDs
- 2,107 pre-window starts excluded
- 60,329 temporally eligible Meta ad IDs

An ad is not excluded solely because its reported stop date is missing or occurs after 2026-09-05. Therefore, demographic reach fields are not interpreted as reach occurring exclusively inside the launch window.

## Commercial-eligibility procedure

The purpose of this stage is to retain consumer-facing retail advertising while removing high-confidence content whose primary purpose is outside that scope.

### Automatic exclusions

Automatic exclusion is deliberately conservative and relies on the four creative-text fields:

- `ad_creative_bodies`
- `ad_creative_link_titles`
- `ad_creative_link_captions`
- `ad_creative_link_descriptions`

The dominant automatic exclusion category is recruitment/employer branding. Clear non-commercial educational or participation programmes can also be excluded when there is no commercial retail signal.

Weak or ambiguous keywords are not sufficient for automatic exclusion. Cases involving mixed commercial/non-commercial communication, sustainability, CSR/charity, sponsorship, community initiatives, legal/commercial combinations, ambiguous application wording, or insufficient text are sent to manual review rather than automatically removed.

### Predefined manual-review bucket

Script 04 assigned **867 Meta ad IDs** to manual review.

- 812 were retained
- 55 were excluded

These decisions are part of the predefined classification procedure and are therefore applied to the production dataset.

### Final commercial-eligibility removals by sector

| Sector | Excluded Meta ad IDs |
|---|---:|
| Grocery | 4,602 |
| Drugstore/Beauty | 1,815 |
| Fashion | 95 |
| Home/DIY | 23 |
| **Total** | **6,535** |

### Final commercial-eligibility removals by retailer

| Retailer | Excluded Meta ad IDs |
|---|---:|
| Lidl | 4,120 |
| Rossmann | 1,602 |
| Penny | 312 |
| dm | 209 |
| Kaufland | 148 |
| New Yorker | 82 |
| OBI | 22 |
| Edeka Südwest | 20 |
| About You | 12 |
| Flaconi | 4 |
| Aldi Nord | 2 |
| Zalando | 1 |
| Hornbach | 1 |
| Aldi Süd | 0 |
| Bonprix | 0 |
| Zara | 0 |
| Douglas | 0 |
| Müller | 0 |
| Bauhaus | 0 |
| IKEA | 0 |
| **Total** | **6,535** |

## Manual validation of the commercial-eligibility classifier

Validation is performed at the level of **distinct textual creative signatures**, not individual Meta ad IDs, so repeated copies of the same text do not dominate the audit.

### Excluded-signature validation

A reproducible sample of **400 distinct recruitment-exclusion signatures** was manually reviewed.

- 389 were confirmed non-commercial exclusions
- 11 were judged commercial false positives
- observed exclusion precision: **97.25%**

Recruitment was the dominant automatic exclusion rule. The additional **16 automatic exclusions assigned to non-recruitment non-commercial categories were reviewed in full**.

The validation examines all four text fields, so evidence located in title, caption, or description is not ignored when the body field alone is insufficient.

### Retained-signature validation

A reproducible sample of **1,000 distinct retained textual signatures** was manually reviewed.

- 978 were judged correctly retained commercial content
- 22 were judged non-commercial misses
- observed validation-sample miss rate: **2.2%**

Because this sample is stratified by retailer and drawn from distinct textual signatures rather than directly from all Meta ad IDs, the 2.2% figure is treated as a classifier diagnostic rather than a direct estimate of the proportion of all retained Meta ad IDs that are misclassified.

### Validation versus adjudication

Two forms of manual review are intentionally separated:

1. **Predefined manual-review cases:** the 867 uncertain cases identified by the rule-based classifier are adjudicated and their decisions affect the production dataset.
2. **Independent validation samples:** the 400 excluded signatures and 1,000 retained signatures are used to evaluate classifier performance. Their sampled judgments are not selectively applied to production rows.

This separation preserves an independent assessment of the filtering procedure.

## Stable textual creative identity and repeated Meta IDs

A stable textual creative signature is constructed as:

```text
Page ID
+ normalized ad body
+ normalized link title
+ normalized link caption
+ normalized link description
```

The four source text fields themselves remain unchanged. Normalization is used only for constructing the signature.

The stable signature audit of the 53,794 eligible Meta ad IDs found:

- 18,709 distinct textual creative signatures
- 7,889 signature groups containing more than one Meta ad ID
- 42,974 Meta ad IDs belonging to repeated-signature groups
- maximum repeated-signature group size: 421 Meta ad IDs
- 1,747 repeated-signature groups with differences in platform and/or disclosed targeting

### Structural conflicts within repeated textual signatures

| Conflict pattern | Signature groups |
|---|---:|
| Publisher platform | 892 |
| Target age + target gender | 345 |
| Target gender | 219 |
| Target age | 139 |
| Publisher platform + target gender | 82 |
| Publisher platform + target age | 50 |
| Publisher platform + target age + target gender | 20 |
| **Total** | **1,747** |

These conflicts show that collapsing all rows solely by textual signature would remove variation in variables central to the research questions. The primary dataset is therefore retained at Meta-ad-ID level.

The signature is explicitly a **textual** creative identifier. Meta does not provide a stable visual-asset identifier in this recollection. Consequently, identical text may in principle accompany different images or videos, while the same visual asset may appear with different text.

Meta ad ID is retained separately for traceability.

## Demographic data completeness in the final 53,794-row dataset

The final locked eligibility dataset contains:

- 2 rows without Germany-specific demographic data
- 14 rows with complete demographic data but zero known-gender reach (`de_male + de_female = 0`)
- 16 rows unable to produce `female_delivery_share` in total
- 41,930 rows with positive unknown-gender reach
- 21,829 rows with positive unknown-age reach
- 5 rows with complete age data but a zero adult-age denominator
- 7 rows unable to produce `adult_18_34_share` in total
- 53,792 rows with complete gender and age demographic fields
- 0 rows where complete gender and age reach totals fail to reconcile

These categories are kept conceptually separate. No demographic values are imputed.

Model-specific analytical sample sizes will therefore depend on the outcome required for a given research question.

## Demographic reach interpretation

The Germany-specific demographic variables are **Meta-reported reach counts**.

They are not impression counts. They also should not be interpreted as independently verified unique persons across multiple Meta ad IDs.

Because the primary dataset remains at Meta-ad-ID level, reach is not summed across repeated Meta IDs for the primary analysis.

## Derived demographic outcomes

### Gender composition

Primary female delivery share:

```text
de_female / (de_female + de_male)
```

Unknown-gender reach is excluded from the primary denominator. It is retained in the dataset so alternative denominators and missingness/sensitivity checks remain possible.

### Adult age composition

For adult comparisons, the 18-34 share is defined as:

```text
(de_age_18_24 + de_age_25_34)
/
(de_age_18_24 + de_age_25_34 + de_age_35_44 + de_age_45_54 + de_age_55_64 + de_age_65_plus)
```

The 13-17 category and unknown-age category are not included in this adult denominator. They remain available as separate variables.

## Contextual Meta audience benchmark

The `benchmark/` directory contains Meta estimated monthly audience sizes for Germany collected on **28 August 2026**.

The benchmark covers:

- Facebook + Instagram
- Facebook only
- Instagram only
- all adults aged 18-65+
- adult age bands 18-24, 25-34, 35-44, 45-54, 55-64, and 65+
- all genders, male, and female estimates

Files:

```text
benchmark/meta_audience_estimates_germany.csv
benchmark/meta_audience_estimates_germany_raw.json
benchmark/meta_audience_benchmark_full_with_formulas.xlsx
```

The CSV is the cleaned benchmark table. The JSON preserves the raw Meta API targeting specifications and responses. The workbook provides a readable calculation/verification layer.

The benchmark is **contextual**. It is not treated as an intended demographic distribution and is not used as a conventional hypothesis-test null value. In particular, unrestricted (`All`) gender targeting does not imply an intended 50/50 male/female delivery split.

## Reproduction

### 1. Python

Python 3.10+ is recommended.

Install the external dependency:

```bash
pip install -r requirements.txt
```

### 2. Configure API credentials

Set the required environment variables as described in **Meta API credentials** above.

### 3. Run the recollection

From the repository root:

```bash
python scripts/recollection.py
```

The collector supports checkpoint/resume through `progress.json`. That file contains local collection state and is excluded from version control.

### 4. Run validation and sample construction sequentially

```bash
python scripts/01_validate_recollection.py
python scripts/02_audit_temporal_eligibility.py
python scripts/03_build_temporal_eligible.py
python scripts/04_apply_commercial_eligibility_filter.py
python scripts/05_audit_commercial_eligibility.py
python scripts/06_build_eligibility_validation_sample.py
python scripts/07_apply_validated_eligibility.py
python scripts/08_build_and_audit_stable_signature.py
python scripts/09_summarize_stable_signature_conflicts.py
python scripts/11_build_analysis_ready_dataset.py
```

Script 11 constructs `data/ads_analysis_ready.csv` from the locked eligibility dataset and validates the final analytical fields.

### 5. Collect the contextual benchmark separately

The benchmark collector additionally requires `META_AD_ACCOUNT_ID`:

```bash
python scripts/10_collect_meta_audience_benchmarks.py
```

Benchmark collection is separate from construction of the 53,794-row ad-level analysis-ready dataset.

## Reproducibility and data handling

- Historical/upstream files are not overwritten by audit scripts.
- Meta ad IDs and Page IDs are treated as strings.
- Genuine advertisement text is retained unchanged in source fields.
- Text normalization is used only for filtering/signature logic.
- Validation sampling uses fixed random seeds where sampling is required.
- Independent validation samples are retained as audit evidence.
- The final ad-level dataset is not deduplicated by textual creative signature.
- Reach is not aggregated across Meta ad IDs in the primary dataset.
- API credentials, `.env` files, checkpoints, temporary collection files, and local virtual environments are excluded by `.gitignore`.

## Data dictionary

Variable definitions for the main ad-level dataset and benchmark files are provided in:

```text
DATA_DICTIONARY.md
```

## Current methodological status

The file `data/ads_eligibility_locked.csv` is the locked 53,794-row pre-analysis dataset produced after temporal and commercial-eligibility construction.

The file `data/ads_analysis_ready.csv` is the final 53,794-row analysis-ready dataset. It preserves the 24 original variables from the locked dataset and adds 12 derived analytical and support variables. The primary observational unit remains one Meta ad ID.

This repository documents data collection, temporal eligibility, commercial-eligibility classification, manual validation, demographic completeness, stable textual creative identification, contextual benchmark construction, and construction of the final analysis-ready dataset.

The repository does **not** present substantive Chapter 4 or Chapter 5 findings.

## Limitations relevant to dataset construction

- The 20 retailers are a purposive sample and are not statistically representative of all German retailers.
- REWE is not included in the primary 20-retailer dataset. Any REWE analysis would require a complete and directly comparable dataset and would be treated separately from the primary sample.
- Meta's disclosed age and gender targeting fields do not represent the advertiser's complete targeting specification.
- The stable creative signature is a textual identifier based on verified Page ID plus normalized body, title, caption, and description.
- The textual creative signature cannot distinguish identical text paired with different visual assets because a stable visual-asset identifier is unavailable in the recollected data.
- The same visual asset may also appear with different text and therefore receive different textual signatures.
- The primary dataset is not collapsed by textual creative signature because repeated textual signatures can differ in disclosed targeting and publisher-platform configuration.
- Meta-reported demographic reach is platform-reported measurement and should not be interpreted as independently verified unique individuals across Meta ad IDs.
- Reach is not summed across different Meta ad IDs in the primary dataset.
- The strict launch-cohort rule identifies ads by reported start date; it does not establish that all reported reach accrued inside the launch window.
- The adult age denominator uses the six 18+ age buckets. The 13-17 and unknown-age categories remain separate and are not included in the adult denominator.
- Rows without usable gender or adult-age denominators remain in the master dataset and are excluded only from analyses requiring the affected outcome. No demographic values are imputed.

## Licensing and data use

This repository contains researcher-written processing code together with data derived from Meta APIs.

No Meta access token, ad-account credential, or other private authentication material is included.

The Meta-derived data and raw API responses remain subject to the applicable Meta platform terms and policies. Their inclusion here is for academic transparency and reproducibility and should not be interpreted as granting rights beyond those permitted by the underlying platform terms.

No separate open-source license is currently granted for the researcher-written code unless a `LICENSE` file is added to the repository. In the absence of a separate license, standard copyright restrictions apply.

