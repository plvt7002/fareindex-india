# FareIndex India — Phase 5 Readiness Report

**Generated:** 2026-09-07  
**Project:** FareIndex India (Smart India Hackathon Baseline)  
**Status:** **Hackathon Demo-Ready Baseline**

---

## 1. Verified System State Summary

```
Total Observations:          319
├── Live (Playwright):        34  (29 HYD-DEL, 5 HYD-GOI)
├── Recovered Archive:       249  (96 Google Flights, 153 Initial Migration)
└── Demo / Validation Runs:   36  (18 HYD-DEL, 18 HYD-GOI)

Route Observations:
├── HYD → DEL:               296  (across 5 observation dates: 2026-08-28 to 2026-09-07)
└── HYD → GOI:                23  (across 1 observation date: 2026-09-07)

Validated HYD-DEL Mathematical Metrics:
├── Latest Observed Average:  ₹15,290.62
├── Provisional Baseline:     ₹15,268.36
└── Latest Route Index:       100.15

National Composite Status:
├── National Index:           100.15
├── Contributing Routes:      1 / 2 (HYD-DEL active, HYD-GOI awaiting baseline)
└── Weighted Average Fare:    ₹15,290.62 (Latest Indexed Route Average)
```

---

## 2. Evaluation Results (PASS / WARNING / FAIL)

### A. PASS

1. **Application Startup & Local Dev (`PASS`)**:
   - Backend cleanly starts with `.venv/bin/uvicorn app.main:app --port 8000 --reload`.
   - Frontend starts with `cd frontend && npm run dev` on port 5173.
   - Vite proxy forwards `/api/*` to FastAPI on port 8000 seamlessly.
   - Health endpoint `GET /api/health` returns HTTP 200 `{"status": "online", "database": "connected"}`.

2. **Database Integrity & Safety (`PASS`)**:
   - Primary database remains strictly `data/fareindex.db`.
   - `raw_prices` (319 rows) and `index_values` (5 rows) are preserved across restarts and rebuilds.
   - No data corruption or unintentional deletions occurred.

3. **Index Rebuild Safety (`PASS`)**:
   - `POST /api/admin/rebuild-index` executes deterministically.
   - Preserves exact HYD-DEL metrics (₹15,290.62 average, ₹15,268.36 baseline, 100.15 index).
   - Rebuilding does not create duplicate observations or alter `raw_prices`.

4. **Provenance Transparency (`PASS`)**:
   - Full 319-observation dataset transparently categorized:
     - 🟢 `Playwright Scraper` (34 live rows)
     - 🔵 `Recovered Data` (249 archived rows)
     - 🟠 `DEMO - NOT LIVE` (36 demonstration rows)
   - StatusBadge component accurately renders badges without falling back to "Unknown".
   - Demo and recovered rows are never falsely represented as live.

5. **API Robustness (`PASS`)**:
   - All 11 endpoints (`/api/health`, `/api/routes`, `/api/routes/summary`, `/api/index/national`, `/api/index/route/{route}`, `/api/analytics/booking-curve`, `/api/analytics/airlines`, `/api/prices/latest`, `/api/admin/scrape-status`, `/api/admin/rebuild-index`, `/api/admin/scrape-now`) tested and verified.
   - Unindexed route query (`/api/index/route/HYD-GOI`) returns HTTP 404 with structured error JSON, handled gracefully by the UI.

6. **Frontend Reliability & Exploration (`PASS`)**:
   - Single source of truth in `AnalysisControls.jsx` for route switching, date range selection, and metric views.
   - Reset button restores full observation period cleanly.
   - Professional empty state rendered for `HYD-GOI` (*"Index not yet available: 23 observations are recorded, but a multi-day baseline has not yet been established"*).
   - "How is this calculated?" methodology modal explains the 5-step index engine clearly.
   - Smooth scroll from route cards / empty states to the underlying raw observations table.

7. **Test Suite & Build (`PASS`)**:
   - Automated Pytest suite: **27 passed, 0 failed** (`100% pass rate`).
   - Frontend production build: `npm run build` compiled client bundle in **255ms** with zero errors.

---

### B. WARNING (Documented MVP Limitations)

1. **Single Contributing Route to National Composite (`WARNING`)**:
   - `HYD-DEL` is currently the sole route contributing to the national composite index because `HYD-GOI` has only 1 observation date. A minimum of 2 observation dates is required to form a multi-day baseline.
2. **Provisional Configured Weights (`WARNING`)**:
   - National composite weighting uses configurable demonstration weights (`1.0` for `HYD-DEL`, `0.6` for `HYD-GOI`). In future production phases, these will be upgraded with official DGCA traffic share datasets.
3. **Travel Date Granularity (`WARNING`)**:
   - 166 of 319 records contain explicit departure travel dates for lead-time booking curve analysis; 153 spot-search observations without departure dates are isolated from the booking curve.

---

### C. FAIL

- **None (`0 FAILURES`)**. All pipeline stages, data models, APIs, and dashboard views operate with complete stability.

---

## 3. Demo Walkthrough Sequence for Judges

1. **Start Services**:
   - Terminal 1: `.venv/bin/uvicorn app.main:app --port 8000 --reload`
   - Terminal 2: `cd frontend && npm run dev`
2. **Open Dashboard**: Visit `http://localhost:5173`.
3. **Demonstrate Health Indicator**: Point out the live `● Data service connected` status indicator and last-updated time.
4. **Explain Hero Index (Base = 100)**:
   - Point to `India Airfare Index: 100.15` and explain that values above 100 reflect upward price pressure relative to the provisional baseline.
5. **Open Methodology Modal**: Click *"How is this calculated?"* to walk through the 5-step pipeline: Data Ingestion → Daily Route Averages → Route Baseline → Route Index → National Composite.
6. **Demonstrate Analysis Controls**:
   - Switch from `National Composite` to `HYD → DEL` to show the route-specific baseline (₹15,268.36) and daily index series.
   - Switch metric view from `Index (Base 100)` to `Average Fare (₹)` to display absolute rupee prices.
   - Filter observation date range and demonstrate the 1-click `Reset` action.
7. **Demonstrate Unindexed Route Rationale**:
   - Switch to `HYD → GOI`. Show the professional empty state explaining that 23 observations exist, but a multi-day baseline requires $\ge 2$ observation dates.
8. **Demonstrate Analytics Grid**:
   - Show *"How Fare Changes as Departure Approaches"* (booking curve lead time from 3 to 60 days).
   - Show *"Average Fare by Airline"* (IndiGo vs Air India vs Akasa Air price dispersion and market share).
9. **Inspect Underlying Observations & Provenance**:
   - Show the observation table with explicit `Observation Date` vs `Travel Date` columns.
   - Point out the provenance tags (🟢 `Playwright Scraper`, 🔵 `Recovered Data`, 🟠 `DEMO - NOT LIVE`).
10. **Explain MVP Scope & Credible Limitations**:
    - Summarize that FareIndex India is an economic market indicator (CPI for airfare), not a flight booking engine.
