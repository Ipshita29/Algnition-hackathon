# Input CSV Schema Analysis
*Real challenge dataset - `data/` now holds the actual files from the AIgnition_dataset Drive folder linked in the brief, not synthetic samples.*

## Overview

Three channel CSV files, three genuinely different raw export schemas - not variations on one convention. `generate_features.py` detects which schema a file matches by a distinctive column name (`segments_date` for Google, `TimePeriod` for Bing, `date_start` for Meta) and maps each explicitly; see `docs/ASSUMPTIONS.md` for the full mapping and the reasoning behind each transform.

| File | Rows | Date range | Campaigns | Schema marker column |
|---|---|---|---|---|
| `google_ads_campaign_stats.csv` | 19,272 | 2024-01-01 → 2026-06-04 | 92 | `segments_date` |
| `bing_campaign_stats.csv` | 2,873 | 2024-05-25 → 2026-06-05 | 28 | `TimePeriod` |
| `meta_ads_campaign_stats.csv` | 3,417 | 2024-05-23 → 2026-06-05 | 16 | `date_start` |

Channel is inferred from the **filename** (keyword match: `google`, `bing`/`microsoft`/`ms`), not from any column. Bing's file is named `bing_campaign_stats.csv` - no `ms_ads_` prefix - so channel inference matches on the keyword `bing` and maps it to channel `ms`.

---

## Column definitions (raw, per platform)

| Standardized field | Google Ads | Bing Ads | Meta Ads |
|---|---|---|---|
| `date` | `segments_date` | `TimePeriod` | `date_start` |
| `campaign_name` | `campaign_name` | `CampaignName` | `campaign_name` |
| `campaign_type` | `campaign_advertising_channel_type` | `CampaignType` | *(absent - inferred from name)* |
| `spend` | `metrics_cost_micros` **÷ 1,000,000** | `Spend` | `spend` |
| `revenue` | `metrics_conversions_value` | `Revenue` | `conversion` **(this is revenue, not a count - see below)** |
| `impressions` | `metrics_impressions` | `Impressions` | `impressions` |
| `clicks` | `metrics_clicks` | `Clicks` | `clicks` |
| `conversions` | `metrics_conversions` (fractional) | `Conversions` | *(absent - filled with 0)* |

Each file also has an unnamed leading index column (`Unnamed: 0`, a pandas row index accidentally exported) - ignored.

---

## Spend & Revenue by channel (verified against the raw files)

| Channel | Total spend | Total revenue | Implied ROAS |
|---|---|---|---|
| Google | $1,946,126 | $9,266,678 | 4.76x |
| Bing (ms) | $39,430 | $172,028 | 4.36x |
| Meta | not computed the same way - see note below | | |

These figures were computed directly from the raw CSVs and cross-checked against `generate_features.py`'s parsed output - they match to the cent.

---

## Anomalies and platform-specific quirks

- **Meta's `conversion` column is conversion *value* (revenue in dollars), not a count.** Verified: values are fractional currency amounts (e.g. `163.20`, `286.77`), frequently exceed the click count for that row, and there is no separate conversion-count column anywhere in this export. If it were treated as a count, implied "ROAS" would compute to 8.44x using the count as a revenue proxy - which is what happens if you mistakenly treat it as a count and divide by itself; it's actually just revenue directly. Meta's `conversions` (count) field is therefore absent and filled with 0 - CVR is not computable for Meta from this export.
- **Google's spend is in micros** (`metrics_cost_micros`) - a Google Ads API convention where all currency values are integers scaled ×1,000,000 to avoid floating-point rounding in their systems. Must be divided by 1,000,000 to get dollars; a raw sum of the column is 1.9 trillion, not $1.9M.
- **27 campaign names collide between Google and Bing** (e.g. `Pmax_NTM_Campaign_01` through `_19`, `Search_TM_Campaign_02` through `_06`) as entirely unrelated campaigns on different platforms. `campaign_name` is **not** globally unique - only unique within `(channel, campaign_name)`. See `docs/ASSUMPTIONS.md` for how the pipeline handles this.
- **`_TM_`/`_NTM_` in Google/Bing search campaign names is a real, exploitable signal**: TM = trademark (brand-term search), NTM = non-trademark (generic/non-brand search) - standard paid-search naming convention. `generate_features.py` uses it to refine the raw `SEARCH`/`Search` campaign type into our `brand` vs `search` buckets. Verified `_tm_` does not falsely match inside `_ntm_` as a substring.
- **Raw campaign-type enums differ by platform and casing** (`PERFORMANCE_MAX` vs `PerformanceMax`, `Audience` for Bing's Demand Gen equivalent, `VIDEO`/`DEMAND_GEN` on Google with no Display-bucket equivalent) - normalized to our `shopping/brand/search/retargeting/display/other` vocabulary via a whitespace/underscore-insensitive lookup.
- **Null analysis**: `campaign_budget_amount` (Google) has 14 nulls, `daily_budget` (Meta) has 7 nulls - both unused by the pipeline currently (budget is derived from `revenue_p50/roas_p50` in the UI instead), so these nulls don't propagate anywhere.
- **Spend = 0 / revenue = 0 days** are common in all three files (up to ~34% of Google rows have zero revenue) - handled by the existing divide-by-zero guards in ROAS/CVR/CPC.
- **No duplicate (campaign, date) rows** in any of the three files, and no negative spend values were found in this dataset (the negative-spend drop in `clean()` is defensive, for whatever the held-out test set contains).

---

## Notes for the model layer

- 89 of 136 campaigns have ≥60 days of history and get a Prophet fit; the remaining 47 rely on XGBoost + Ridge alone (ensemble weights renormalized).
- Real spend/revenue data is far noisier than a synthetic sample would be: 300 of 408 output rows (30/60/90-day forecasts × 136 campaigns) land in HIGH uncertainty, concentrated in data-rich Shopping/PMax campaigns where Prophet, XGBoost, and Ridge genuinely diverge on volatile daily patterns - not a bug, but a real reflection of how much these three models can disagree on messy production data (see `docs/ASSUMPTIONS.md`).
