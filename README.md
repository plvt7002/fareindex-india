# FareIndex India — Domestic Airfare Market Indicator & Index Engine

> **Smart India Hackathon Prototype**  
> *A normalized market indicator tracking price dynamics and inflationary pressure across Indian domestic air routes.*

---

## 1. What is FareIndex India?

**FareIndex India** is a real-time domestic airfare price index and aviation market analytics engine. Similar to how the **Consumer Price Index (CPI)** measures household inflation or the **Sensex/Nifty** tracks equity market movements, FareIndex India converts raw, fragmented airfare observations into a standardized, baseline-anchored economic indicator.

### What it is NOT:
- ❌ **NOT** a flight booking engine.
- ❌ **NOT** a consumer flight search or ticket comparison tool.
- ❌ **NOT** a synthetic price generator.

---

## 2. Problem Statement & Motivation

Indian domestic airfares exhibit extreme volatility driven by dynamic pricing algorithms, advance booking windows, seasonal surges, and carrier concentration. However, aviation analysts, regulators, and enterprise travel managers lack a transparent, normalized benchmark to answer a fundamental question:

> *"Are Indian domestic airfares becoming more or less expensive relative to established baseline levels?"*

FareIndex India solves this by automating multi-source fare collection, aggregating daily route averages, establishing statistically grounded provisional baselines, and publishing route-level and national composite indices.

---

## 3. Core Architecture & Data Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                     │
│  ┌──────────────────────┬────────────────────────────────┐  │
│  │ Playwright Scraper   │ Amadeus API / Recovered Archive│  │
│  └──────────────────────┴────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Metadata & Ingest Timestamp
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 SQLITE DATABASE (data/fareindex.db)          │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ raw_prices: route, price_inr, search_ts, travel_date  │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    INDEX ENGINE LAYER                       │
│  1. Daily Route Averages: Σ(Prices) / N                     │
│  2. Route Baseline: Mean of initial observation averages    │
│  3. Route Index: (Daily Avg / Baseline) × 100               │
│  4. National Composite: Weighted sum of valid route indices │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND SERVICE                   │
│  REST API Endpoints: /api/health, /api/index, /api/analytics│
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON Responses
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              REACT + RECHARTS FRONTEND DASHBOARD            │
│  Institutional Analytics UI • Single Source of Truth        │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Index Methodology

### Step 1: Daily Route Average
For each tracked city-pair (e.g., `HYD → DEL`), all raw price observations recorded on observation calendar day $t$ are cleaned, deduplicated, and averaged:
$$\text{Daily Avg}(t) = \frac{\sum_{i=1}^{N} \text{Price}_i}{N}$$

### Step 2: Provisional Route Baseline
A reference price is established as the mean of available daily averages over the initial observation period:
$$\text{Baseline Fare} = \frac{\sum_{d=1}^{D} \text{Daily Avg}_d}{D} \quad (\text{Base} = 100.0)$$

### Step 3: Route-Level Index
On any observation day $t$, the route index is calculated as:
$$\text{Route Index}(t) = \left( \frac{\text{Daily Avg}(t)}{\text{Baseline Fare}} \right) \times 100$$
- **Index = 100.0**: Observed fares equal the provisional baseline.
- **Index > 100.0**: Fares are above baseline (e.g., `114.14` = +14.14% above baseline).
- **Index < 100.0**: Fares are below baseline (e.g., `95.50` = 4.50% below baseline).

### Step 4: Multi-Day Baseline Rule
To prevent statistical distortion, a route must have **at least 2 distinct observation dates** before a baseline and index are generated. Routes with only 1 observation date remain in an explicit *"Awaiting multi-day baseline"* state.

### Step 5: National Composite Index
$$\text{National Index}(t) = \frac{\sum_{r \in \text{Valid}} \left(\text{Index}_r(t) \times w_r\right)}{\sum_{r \in \text{Valid}} w_r}$$
*Only routes with a valid multi-day index contribute to the national composite.*

---

## 5. Current Data Coverage & Provenance

| Category | Verified Count | Description |
| :--- | :--- | :--- |
| **Total Observations** | **319** | All flight fare records stored in `data/fareindex.db` |
| **Live Scraped** | **34** | Automated collection via `PlaywrightProvider` (29 HYD-DEL, 5 HYD-GOI) |
| **Recovered Archive** | **249** | Verified historical dataset (96 Google Flights, 153 Initial Migration) |
| **Demo / Validation** | **36** | Controlled verification runs (`DEMO - NOT LIVE`) |
| **HYD → DEL Route** | **296** | 5 observation dates (`2026-08-28` to `2026-09-07`) |
| **HYD → GOI Route** | **23** | 1 observation date (`2026-09-07`) |
| **Travel Date Records**| **166** | Records with explicit departure date for advance booking curves |

---

## 6. Project Structure

```
fareindex_backend_starter/
├── app/
│   ├── config.py           # Configuration, weights, booking windows
│   ├── db.py               # SQLite connection management & migrations
│   ├── index_engine.py     # Core mathematical index & analytics engine
│   ├── main.py             # FastAPI app, routing, and APScheduler
│   ├── providers.py        # Playwright, Amadeus, and Demo scraper providers
│   └── scrape_service.py   # Collection runner, locking, and duplicate prevention
├── data/
│   └── fareindex.db        # Primary SQLite database (raw_prices & index_values)
├── docs/
│   └── phase-5-readiness-report.md  # Detailed audit & readiness checklist
├── frontend/
│   ├── src/
│   │   ├── api/client.js   # API client for backend communication
│   │   ├── components/     # Institutional UI components (Chart, Table, Hero, Modal)
│   │   ├── App.jsx         # Dashboard state & layout orchestration
│   │   └── index.css       # Minimal light theme tokens
│   ├── package.json        # Frontend dependencies (React, Recharts, Lucide)
│   └── vite.config.js      # Vite build & proxy configuration
├── tests/
│   ├── test_api.py          # API endpoint contract tests
│   ├── test_index_engine.py # Mathematical calculation unit tests
│   └── test_scraper.py      # Provider & ingestion integration tests
├── requirements.txt        # Python backend dependencies
└── README.md               # Project documentation
```

---

## 7. Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# From repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run FastAPI backend
.venv/bin/uvicorn app.main:app --port 8000 --reload
```
- API Documentation (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Service Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2. Frontend Setup
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```
- Dashboard URL: [http://localhost:5173](http://localhost:5173)

---

## 8. API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status and database connection |
| `GET` | `/api/routes` | List of all tracked city-pair route codes |
| `GET` | `/api/routes/summary` | Summary metrics, baseline fares, and index status |
| `GET` | `/api/index/national` | National Composite Airfare Index time series |
| `GET` | `/api/index/route/{route}` | Route-level index time series (returns 404 if unindexed) |
| `GET` | `/api/analytics/booking-curve` | Advance booking lead-time fare distribution |
| `GET` | `/api/analytics/airlines` | Carrier price dispersion and market share |
| `GET` | `/api/prices/latest?route=...`| Latest batch of underlying flight observations |
| `GET` | `/api/admin/scrape-status` | Latest crawler execution status and record counts |
| `POST`| `/api/admin/rebuild-index` | Recalculate all route baselines and indices |
| `POST`| `/api/admin/scrape-now` | On-demand collection trigger across tracked routes |

---

## 9. Running Tests

### Backend Automated Tests (Pytest)
```bash
.venv/bin/pytest -v
```
*Current result: 27 passed, 0 failed (100% pass rate).*

### Frontend Production Build
```bash
cd frontend
npm run build
```
*Current result: Built cleanly with zero compilation errors.*

---

## 10. Judge Demonstration Sequence

1. **Service Connectivity**: Open `http://localhost:5173` and note the `● Data service connected` live status indicator.
2. **National Overview**: Inspect the **India Airfare Index (100.15)**, the `Base = 100.0` reference, and the single contributing route count (`1 / 2 indexed routes`).
3. **Methodology Modal**: Click *"How is this calculated?"* to explain the 5-step mathematical pipeline.
4. **Analysis Controls**:
   - Switch route scope from `National Composite` to `HYD → DEL`.
   - Inspect the route-specific baseline (₹15,268.36) and daily index series.
   - Toggle metric view to `Average Fare (₹)` to inspect absolute rupee trends.
   - Select observation date ranges and demonstrate the 1-click `Reset` action.
5. **Unindexed Route Handling**:
   - Switch to `HYD → GOI`. Show the transparent empty state explaining that 23 observations are recorded, but a multi-day baseline requires $\ge 2$ observation dates.
6. **Lead-Time Dynamics**: Review *"How Fare Changes as Departure Approaches"* to see authentic observed lead times (3 to 60 days).
7. **Carrier Dispersion**: Review *"Average Fare by Airline"* to compare IndiGo, Air India, and Akasa Air.
8. **Data Provenance**: Scroll to the underlying observation table to show explicit `Observation Date` vs `Travel Date` columns and provenance tags.

---

## 11. Known Limitations (Hackathon MVP Scope)

1. **Two Tracked Routes**: Currently covers `HYD-DEL` and `HYD-GOI`. Additional trunk routes (`DEL-BOM`, `BLR-DEL`) are staged for future phases.
2. **HYD-GOI Baseline Pending**: `HYD-GOI` contains observations from 1 date; a 2nd observation date is required before publishing its index.
3. **Provisional Configured Weights**: Weights are currently set via configurable demonstration parameters (`HYD-DEL: 1.0`, `HYD-GOI: 0.6`).
4. **Initial Reference Period**: Baselines are established over the initial observation dates of the project dataset.

---

## 12. Future Roadmap

- Integration of official DGCA domestic passenger traffic share weights.
- Expansion to top 20 domestic city-pairs across Tier-1 and Tier-2 routes.
- 30-day and 90-day rolling baseline methodologies.
- Route inflation alert webhooks for enterprise travel procurement.
