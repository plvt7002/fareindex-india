# FareIndex India — Phase 6C Production Daily Observation Aggregation Specification & Audit

**Document:** Daily Observation Aggregation Methodology  
**Phase:** Phase 6C Implementation  
**Date:** 2026-09-08  
**Project:** FareIndex India (Smart India Hackathon Baseline)  
**Status:** **Implemented & Fully Verified**

---

## 1. Executive Overview

During live automated testing and debugging on **2026-09-08**, the Playwright scraper was executed three times across tracked routes (`HYD-DEL` and `HYD-GOI`):
- `14:15:48` (HYD-DEL: 174 obs, avg ₹18,406.70 | HYD-GOI: 43 obs, avg ₹13,351.35)
- `14:17:00` (HYD-DEL: 174 obs, avg ₹18,406.47 | HYD-GOI: 43 obs, avg ₹13,351.35)
- `14:21:00` (HYD-DEL: 174 obs, avg ₹18,406.47 | HYD-GOI: 43 obs, avg ₹13,351.35)

These runs produced **1,006 total raw records** in `data/fareindex.db`. Every raw observation is an authentic market snapshot captured from airline search pages and **must be permanently retained in the database for audit, compliance, and provenance inspection**.

To prevent multiple same-day scraper executions from disproportionately weighting the public index or distorting long-term baselines, **Phase 6C implements a clean Daily Observation Snapshot Aggregation engine**.

---

## 2. Core Methodological Principles

### 2.1 Why Multiple Same-Day Scraper Runs Are Valid Raw Observations
- In dynamic airline revenue management, seat inventory tiers, dynamic pricing algorithms, and flight availabilities change throughout the day.
- Multiple scraper collections on the same calendar day represent genuine empirical time-series observations of ticket availability at specific timestamps.
- **Data Integrity Rule**: Raw observations in `raw_prices` are **NEVER deleted or modified**. They represent the immutable audit log of all data collection runs.

### 2.2 Why Only One Run Is Used for the Public Daily Snapshot
- If one calendar date has 3 scraper runs (522 observations) and another date has 1 run (29 observations), simple pooling across runs gives 18x higher statistical weight to the multi-run day in cross-day aggregate analytics and lead-time curves.
- For public market indicators (CPI-style index calculation), each calendar date should contribute **one canonical daily market snapshot** representing the price state for that day.
- **Selection Rule**: For repeated production Playwright collections on the same date, the system selects the **LATEST successful collection run** (`MAX(search_timestamp)` for that route and date).

### 2.3 Why Cross-Day Observations Are Retained
- A flight for departure date $D$ searched on `2026-09-07` (7 days out) and again on `2026-09-08` (6 days out) represents **two distinct longitudinal observations** capturing the advance booking price trajectory.
- The system strictly distinguishes between same-day duplicate scraper passes and cross-day longitudinal observations.

### 2.4 Three-Tier Data Classification Framework

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      DATA CLASSIFICATION & AGGREGATION MATRIX                    │
├─────────────────────────┬────────────────────────────┬───────────────────────────┤
│ Data Category           │ Database Handling          │ Public Calculation Policy │
├─────────────────────────┼────────────────────────────┼───────────────────────────┤
│ 1. Repeated Playwright  │ All runs stored in full in │ Deduplicated to LATEST    │
│    Same-Day Runs        │ raw_prices (audit trail)   │ search_timestamp per date │
├─────────────────────────┼────────────────────────────┼───────────────────────────┤
│ 2. Legacy Historical /  │ All rows stored in full in │ Pooled completely per     │
│    Recovered Archives   │ raw_prices                 │ date (collection identity │
│    (Google Flights/etc) │                            │ preserved without loss)   │
├─────────────────────────┼────────────────────────────┼───────────────────────────┤
│ 3. DEMO - NOT LIVE      │ Retained in raw_prices for │ Strictly EXCLUDED from    │
│    Synthetic Records    │ offline test/sandbox runs  │ public index & analytics  │
└─────────────────────────┴────────────────────────────┴───────────────────────────┘
```

---

## 3. Exact Aggregation Algorithm

The public observation snapshot pipeline is implemented in `app/index_engine.py` via `get_public_snapshot_dataframe(conn, target_route)`:

1. **Filter Invalid & Synthetic Data**:
   ```sql
   WHERE price_inr > 0
     AND search_timestamp IS NOT NULL
     AND source NOT LIKE '%DEMO%'
     AND source NOT LIKE '%NOT LIVE%'
   ```
2. **Date Extraction**: Extract calendar observation date prefix (`YYYY-MM-DD` in IST) from `search_timestamp`.
3. **Partition by Source**:
   - **Live Scrapers (`Playwright Scraper`, `Amadeus API`)**: Partition by `(route, observation_date)` and select records where `search_timestamp == MAX(search_timestamp)` for that group.
   - **Historical Archives (`Google Flights`, `Unknown`, `Recovered Data`)**: Retain all records for that date to preserve historical sample sizes.
4. **Union**: Combine the latest live snapshot with the historical archive observations into a single clean DataFrame.
5. **Downstream Aggregations**:
   - `rebuild_route_indices()`: Calculates `avg_fare` from the public snapshot, verifies multi-day baseline eligibility ($\ge 2$ distinct dates), establishes route baselines, and computes route index values.
   - `get_routes_summary()`: Uses snapshot stats for observation counts, latest date averages, and price spreads.
   - `get_national_composite_index()`: Weights all eligible routes on each observation date using configured route weights.
   - `get_booking_curve_analytics()`: Uses snapshot observations to calculate advance purchase lead-time curves without triple-counting same-day repeated runs.
   - `get_airline_analytics()`: Computes carrier market share and price dispersion from the clean snapshot.

---

## 4. Empirical Verification & Verified Results

### 4.1 Daily Averages on September 8, 2026
Following the execution of `rebuild_route_indices()`, the public daily averages for `2026-09-08` were computed as:
- **`HYD → DEL`**:
  - Selected Run: `2026-09-08T14:21:00.847973+00:00` ($N = 174$)
  - **Daily Average Fare**: **₹18,406.47** (Min: ₹15,125.00, Max: ₹29,245.00)
  - Historical Baseline (6 observation dates): **₹16,128.92**
  - Route Index: **114.12** (+14.12% vs. baseline)
- **`HYD → GOI`**:
  - Selected Run: `2026-09-08T14:21:24.975387+00:00` ($N = 43$)
  - **Daily Average Fare**: **₹13,351.35** (Min: ₹9,311.00, Max: ₹26,664.00)
  - Historical Baseline (2 observation dates: Sep 7 & Sep 8): **₹11,351.17**
  - Route Index: **117.62** (+17.62% vs. baseline)

### 4.2 Multi-Day Baseline Milestone for HYD-GOI
- With the recording of the `2026-09-08` scraper run, `HYD-GOI` now possesses **2 distinct observation dates** (`2026-09-07` at ₹9,351.00 and `2026-09-08` at ₹13,351.35).
- **Result**: `HYD-GOI` successfully crossed the multi-day baseline threshold ($\ge 2$ dates) and is now **actively indexed** in `index_values`.

### 4.3 National Composite Index Update
On `2026-09-08`, both `HYD-DEL` (weight: 1.0) and `HYD-GOI` (weight: 0.6) contributed to the National Composite:
$$\text{National Index} = \frac{(114.12 \times 1.0) + (117.62 \times 0.6)}{1.0 + 0.6} = \frac{114.12 + 70.572}{1.6} = \mathbf{115.43}$$
$$\text{National Weighted Avg Fare} = \frac{(18406.47 \times 1.0) + (13351.35 \times 0.6)}{1.6} = \mathbf{₹16,510.80}$$

---

## 5. Automated Test Suite & Verification Results

### 5.1 Pytest Execution Log
```bash
$ .venv/bin/pytest
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jyothipabbisetti/Downloads/fareindex_backend_starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 30 items

tests/test_api.py ..............                                         [ 46%]
tests/test_index_engine.py .........                                     [ 76%]
tests/test_scraper.py .......                                            [100%]

======================== 30 passed, 1 warning in 0.75s =========================
```

New unit tests added in `tests/test_index_engine.py`:
1. `test_multiple_playwright_runs_same_date_latest_selected`: Validates that earlier same-day Playwright runs are excluded from daily snapshots while the latest run is selected.
2. `test_demo_rows_excluded_from_public_calculations`: Verifies that `DEMO - NOT LIVE` rows are excluded from index and route summary computations.
3. `test_route_becomes_indexable_only_with_multi_day_baseline`: Tests that routes with 1 date remain unindexed until a 2nd observation date is added.

### 5.2 Frontend Build Validation
```bash
$ cd frontend && npm run build
vite v8.2.2 building client environment for production...
✓ 2433 modules transformed.
dist/index.html                   0.79 kB │ gzip:   0.49 kB
dist/assets/index-2qtrgGiv.css   32.86 kB │ gzip:   6.79 kB
dist/assets/index-BRqSpwax.js   648.31 kB │ gzip: 187.27 kB
✓ built in 313ms
```

---

## 6. Audit Invariants & Integrity Checklist

| Requirement | Verified State | Audit Outcome |
| :--- | :---: | :---: |
| **Raw Observation Deletions** | **0 deleted** (1,006 / 1,006 rows preserved) | `PASS` |
| **Playwright Deduplication** | Latest run (`14:21`) selected for Sep 8 | `PASS` |
| **Historical Data Retention** | Recovered Google Flights and Unknown archives pooled cleanly | `PASS` |
| **Demo Data Segregation** | Excluded from public queries, preserved for audit | `PASS` |
| **Sep 8 HYD-DEL Average** | **₹18,406.47** | `PASS` |
| **Sep 8 HYD-GOI Average** | **₹13,351.35** | `PASS` |
| **HYD-GOI Multi-Day Index** | Baseline established at ₹11,351.17 | `PASS` |
| **Pytest Test Suite** | **30 / 30 PASS (100%)** | `PASS` |
| **Frontend Production Build** | Compiled cleanly in 313ms | `PASS` |
