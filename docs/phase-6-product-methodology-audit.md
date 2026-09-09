# FareIndex India — Phase 6 Product & Methodology Audit

**Document:** Product & Statistical Methodology Specification  
**Phase:** Phase 6A / 6B Transition  
**Date:** 2026-09-08  
**Project:** FareIndex India (Smart India Hackathon Baseline)  
**Status:** **Audit Completed — Methodology Specification Ready for Approval**

---

## 1. Executive Recommendation

### 1.1 Core Mission & Product Re-Orientation
FareIndex India exists to answer one fundamental question for Indian domestic aviation:

> **"Are flight fares changing, and if so, by how much?"**

In the initial prototype (Phases 1–5), the system prioritized the **Airfare Index (Base = 100)** as the primary hero metric. While mathematically sound as an economic indicator (similar to a Consumer Price Index), user feedback and product analysis reveal that the index alone is too abstract for regular travellers and media.

For Phase 6, we recommend a **Rupee-First, Direction-Driven Metric Hierarchy**:
1. **Primary Headline**: **Current Average Fare (₹)** accompanied by **₹ Change** and **% Change** relative to the previous observation period.
2. **Immediate Context**: A clear **Direction Indicator (`RISING` / `FALLING` / `STABLE`)** with deadband noise filtering, and a relative **Fare Position (`LOW` / `NORMAL` / `HIGH`)** based on historical quartiles.
3. **Primary Visual**: A large interactive **Fare-Over-Time Graph** displaying absolute Rupee prices by default, with a one-click toggle to the Index view (Base 100).
4. **Secondary Indicator**: The **Airfare Index (Base = 100)** and **Provisional Baseline (₹)**, positioned as macroeconomic and benchmark context.

### 1.2 Architectural Invariance Principle
The existing backend (FastAPI, SQLite, APScheduler, Playwright scraper) and database schema are fully operational and verified with a 100% test pass rate (27/27 tests passing). 

**In accordance with Phase 6A/6B constraints:**
- **No changes** have been made to the production codebase or database schema during this audit.
- **No redesign** is applied to the live frontend until this methodology specification is formally approved.
- All recommendations below are structured as drop-in methodology specifications for the upcoming Phase 6 implementation.

---

## 2. Mean vs. Median vs. 5% Trimmed Mean Comparison (Task 1)

### 2.1 Empirical Dataset Analysis
Using the active SQLite database (`data/fareindex.db`), we evaluated all 319 recorded observations across the two tracked routes (`HYD-DEL` and `HYD-GOI`) and 5 distinct observation calendar dates (`2026-08-28` to `2026-09-07`).

#### Table 2.1: Statistical Comparison across All Active Database Observations (N = 319)

| Route | Observation Date | Sample Size ($N$) | Arithmetic Mean (₹) | Median (₹) | 5% Trimmed Mean (₹) | 10% Trimmed Mean (₹) | Mean − Median (₹) | Diff % (Median) | Mean − 5% Trim (₹) | Diff % (5% Trim) | Min (₹) | Max (₹) | Std Dev (₹) | Skewness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HYD-DEL** | 2026-08-28 | 117 | ₹15,042.60 | ₹14,858.00 | ₹15,036.50 | ₹15,032.68 | +₹184.60 | +1.24% | +₹6.09 | +0.04% | ₹13,187 | ₹17,075 | ₹1,468.90 | +0.06 |
| **HYD-DEL** | 2026-08-29 | 36 | ₹15,146.06 | ₹14,858.00 | ₹15,146.94 | ₹15,157.30 | +₹288.06 | +1.94% | −₹0.89 | −0.01% | ₹13,187 | ₹17,075 | ₹1,454.64 | −0.04 |
| **HYD-DEL** | 2026-08-30 | 29 | ₹15,539.69 | ₹14,937.00 | ₹15,569.96 | ₹15,609.72 | +₹602.69 | +4.03% | −₹30.27 | −0.19% | ₹13,187 | ₹17,075 | ₹1,331.60 | −0.41 |
| **HYD-DEL** | 2026-08-31 | 32 | ₹15,322.81 | ₹14,937.00 | ₹15,335.60 | ₹15,376.00 | +₹385.81 | +2.58% | −₹12.79 | −0.08% | ₹13,187 | ₹17,075 | ₹1,433.05 | −0.24 |
| **HYD-DEL** | 2026-09-07 | 82 | ₹15,290.62 | ₹16,198.00 | ₹15,368.92 | ₹15,497.91 | −₹907.38 | −5.60% | −₹78.30 | −0.51% | ₹6,670 | ₹23,676 | ₹4,272.96 | −0.68 |
| **HYD-GOI** | 2026-09-07 | 23 | ₹6,558.39 | ₹6,164.00 | ₹6,427.10 | ₹6,401.95 | +₹394.39 | +6.40% | +₹131.30 | +2.04% | ₹4,475 | ₹11,399 | ₹1,719.01 | +1.25 |

---

#### Table 2.2: Statistical Comparison for Production Data Only (Excluding DEMO - NOT LIVE, N = 283)

| Route | Observation Date | Sample Size ($N$) | Arithmetic Mean (₹) | Median (₹) | 5% Trimmed Mean (₹) | 10% Trimmed Mean (₹) | Mean − Median (₹) | Diff % (Median) | Mean − 5% Trim (₹) | Diff % (5% Trim) | Min (₹) | Max (₹) | Std Dev (₹) | Skewness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HYD-DEL** | 2026-08-28 | 117 | ₹15,042.60 | ₹14,858.00 | ₹15,036.50 | ₹15,032.68 | +₹184.60 | +1.24% | +₹6.09 | +0.04% | ₹13,187 | ₹17,075 | ₹1,468.90 | +0.06 |
| **HYD-DEL** | 2026-08-29 | 36 | ₹15,146.06 | ₹14,858.00 | ₹15,146.94 | ₹15,157.30 | +₹288.06 | +1.94% | −₹0.89 | −0.01% | ₹13,187 | ₹17,075 | ₹1,454.64 | −0.04 |
| **HYD-DEL** | 2026-08-30 | 29 | ₹15,539.69 | ₹14,937.00 | ₹15,569.96 | ₹15,609.72 | +₹602.69 | +4.03% | −₹30.27 | −0.19% | ₹13,187 | ₹17,075 | ₹1,331.60 | −0.41 |
| **HYD-DEL** | 2026-08-31 | 32 | ₹15,322.81 | ₹14,937.00 | ₹15,335.60 | ₹15,376.00 | +₹385.81 | +2.58% | −₹12.79 | −0.08% | ₹13,187 | ₹17,075 | ₹1,433.05 | −0.24 |
| **HYD-DEL** | 2026-09-07 | 64 | ₹17,315.92 | ₹16,436.00 | ₹17,159.47 | ₹17,065.33 | +₹879.92 | +5.35% | +₹156.46 | +0.91% | ₹14,915 | ₹23,676 | ₹2,074.74 | +1.12 |
| **HYD-GOI** | 2026-09-07 | 5 | ₹9,351.00 | ₹8,839.00 | ₹9,351.00 | ₹9,351.00 | +₹512.00 | +5.79% | ₹0.00 | 0.00% | ₹8,839 | ₹11,399 | ₹1,144.87 | +2.24 |

---

### 2.2 Critical Findings on Outlier Sensitivity & Metric Behavior

1. **Uniform Spot-Search Distributions (`2026-08-28` to `2026-08-31`)**:
   - For all 4 early observation days on `HYD-DEL`, prices clustered between ₹13,187 and ₹17,075 with minimal skewness ($-0.41 \le \text{Skew} \le +0.06$).
   - The **Arithmetic Mean** and **5% Trimmed Mean** differ by less than **0.20% (₹6 to ₹30)**.
   - The **Median** is discrete (snapping to specific common airline price tiers like ₹14,858 or ₹14,937), resulting in a slight 1.2%–4.0% difference from the Mean.

2. **Extreme Fares & High-Demand Scrapes (`2026-09-07`)**:
   - In production data on `2026-09-07` ($N = 64$), scraped prices ranged from ₹14,915 to ₹23,676 ($\text{Skewness} = +1.12$).
   - The presence of high flex-tier / peak-morning flights at ₹23,676 pulled the **Arithmetic Mean** up to **₹17,315.92**, which is **₹879.92 (5.35%) higher than the Median (₹16,436.00)**.
   - The **5% Trimmed Mean** (₹17,159.47) trimmed the top and bottom 5% outliers, stabilizing the metric while maintaining mathematical continuity.

3. **Small Sample Behavior (`HYD-GOI`, $N = 5$)**:
   - For small sample sizes ($N < 20$), a 5% trim ($\lfloor 5 \times 0.05 \rfloor = 0$) performs no trimming and equals the Arithmetic Mean.

### 2.3 Methodological Recommendation for Daily Route Fare Statistic

| Metric Candidate | Advantages | Disadvantages | Recommendation |
| :--- | :--- | :--- | :--- |
| **Arithmetic Mean** | • Linearly aggregable into weighted composites.<br>• Mathematically transparent ($ \sum p_i / N $).<br>• Fully consistent with current production engine. | • Sensitive to extreme one-off business-class or flex-fare spikes scraped inadvertently in economy searches. | **Primary Baseline Aggregation Metric** (Preserve current engine, with automated outlier threshold bounds $Q_3 + 1.5 \times \text{IQR}$). |
| **Median** | • Robust against extreme price spikes.<br>• Represents exact 50th percentile flight fare. | • Non-linear (cannot be aggregated across routes using DGCA passenger weights).<br>• Jumps discontinuously when discrete fare buckets shift. | **Supporting Metric** in Raw Observation table and Route Analytics modal. |
| **5% Trimmed Mean** | • Eliminates top/bottom 5% scraping artifacts.<br>• Preserves aggregability across dates. | • Reduces sample size slightly; complex for users to understand without detailed methodology footnotes. | **Recommended for Future Phase 7 Outlier Engine**, but retain standard Arithmetic Mean for Phase 6. |

---

## 3. Definition of "Current Average Fare" (Task 2)

### 3.1 Formal Definition
In the user-facing product, **"Current Average Fare"** for any route $R$ is formally defined as:

> **The arithmetic average of all valid, non-synthetic economy flight price observations recorded on the latest verified observation calendar date for that route.**

### 3.2 Mathematical Formulation
Let:
- $\mathcal{D}_R = \{d_1, d_2, \dots, d_T\}$ be the sorted set of distinct observation dates (in IST, `YYYY-MM-DD`) recorded for route $R$.
- $d_{\text{latest}} = \max(\mathcal{D}_R) = d_T$ be the latest observation date.
- $\mathcal{P}(R, d_{\text{latest}}) = \{p_1, p_2, \dots, p_N\}$ be the set of valid prices ($p_i > 0$, non-demo) observed on date $d_{\text{latest}}$.

$$\text{Current Average Fare}(R) = \bar{p}_{R, d_{\text{latest}}} = \frac{1}{N} \sum_{i=1}^N p_i$$

### 3.3 Observation Date Period vs. Single Scraper Batch
1. **The Trap of "Latest Scraper Batch"**:
   - A single scraper execution may run at 06:00, 12:00, 18:00, or 23:00.
   - A single run may capture only a subset of carriers (e.g., IndiGo morning departures) or a specific booking window (e.g., 3-day lead time only), resulting in artificial price distortion.
2. **The Period Rule**:
   - The product must always group observations by **Observation Calendar Date (IST)**.
   - If multiple scraper runs occur within the same date, all observations for that date are pooled to form the definitive **Daily Market Average**.
   - The UI must display the date stamp clearly: e.g., *"Latest Observation: 07 Sep 2026 (64 observations across 3 airlines)"*.

---

## 4. Definition of "Fare Change" (Task 3)

### 4.1 Evaluation of Comparative Frameworks

We evaluated four alternative methods for answering *"Are fares changing?"*:

| Comparison Method | Mathematical Formula | Meaning / User Interpretation | Trade-offs & Evaluation |
| :--- | :--- | :--- | :--- |
| **1. Day-over-Day (DoD) Change** *(Previous Observation Date)* | $$\Delta \text{Fare}_{\text{DoD}} = \bar{p}_t - \bar{p}_{t-1}$$ <br> $$\% \Delta \text{Fare}_{\text{DoD}} = \left( \frac{\bar{p}_t - \bar{p}_{t-1}}{\bar{p}_{t-1}} \right) \times 100$$ | Immediate price momentum: *"Did fares increase or decrease since yesterday's observation?"* | **Recommended as Primary Headline.** Immediate, actionable, and reflects direct market movement. |
| **2. Baseline Change** *(vs. Multi-Day Benchmark)* | $$\Delta \text{Fare}_{\text{Base}} = \bar{p}_t - \text{Baseline}$$ <br> $$\% \Delta \text{Fare}_{\text{Base}} = \text{Index}_t - 100$$ | Macroeconomic price level: *"Are fares currently above or below historical normal?"* | **Recommended as Secondary Supporting Metric.** Directly connects the Rupee price to the Airfare Index. |
| **3. Rolling Moving Average** *(e.g., 7-Day MA)* | $$\bar{p}_{\text{7d}} = \frac{1}{7} \sum_{k=0}^6 \bar{p}_{t-k}$$ | Smoothed medium-term trend line. | **Recommended for Future 30+ Day Series.** Currently impractical on a 5-day observation dataset. |
| **4. Week-over-Week (WoW)** | $$\Delta \text{Fare}_{\text{WoW}} = \bar{p}_t - \bar{p}_{t-7}$$ | Eliminates day-of-week seasonality (e.g., Friday surge). | **Recommended as a Secondary Toggle** once continuous 14+ day collection is operational. |

### 4.2 Primary vs. Secondary Recommendation
- **Primary Hero Comparison**: **Day-over-Day (DoD) Change** from previous observation date.
  - Formatted in UI as: **`+₹1,993 (+13.0%) vs previous observation`** (Production) or **`-₹32 (-0.2%)`** (Current working state).
- **Secondary Baseline Comparison**: Displayed in the metric strip as:
  - **`+₹1,643 (+10.5%) vs Baseline (₹15,673)`** (Index = 110.5).
- **UI Separation Rule**: The UI must display the comparison baseline explicitly to avoid user ambiguity between *"change since yesterday"* and *"change relative to the 30-day baseline"*.

---

## 5. Definition of Trend Direction (Task 4)

### 5.1 The Problem of Numerical Noise
In commercial aviation pricing, daily average fares exhibit minor fluctuations ($\pm 0.2\% \text{ to } \pm 1.0\%$) due to seat inventory churning, slight changes in morning vs. evening flight availability, and dynamic pricing adjustments. 

Declaring a $+0.15\%$ change as `RISING` or a $-0.21\%$ change as `FALLING` triggers false alarms and damages product credibility.

### 5.2 Recommended Deadband Threshold ($\epsilon = \pm 1.5\%$)

$$\text{Trend Direction} = \begin{cases} 
\textbf{RISING} \quad (\text{▲ Red/Rose}) & \text{if } \% \Delta \text{Fare}_{\text{DoD}} > +1.5\% \\
\textbf{FALLING} \quad (\text{▼ Green/Emerald}) & \text{if } \% \Delta \text{Fare}_{\text{DoD}} < -1.5\% \\
\textbf{STABLE} \quad (\text{— Slate/Gray}) & \text{if } -1.5\% \le \% \Delta \text{Fare}_{\text{DoD}} \le +1.5\% 
\end{cases}$$

### 5.3 Historical Validation of the 1.5% Threshold on HYD-DEL Data

| Observation Date | Daily Average (Prod) | DoD ₹ Change | DoD % Change | 1.0% Threshold | **1.5% Threshold (Recommended)** | 2.0% Threshold | Rationale |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2026-08-28** | ₹15,042.60 | — | — | — | **—** | — | Initial observation baseline |
| **2026-08-29** | ₹15,146.06 | +₹103.46 | +0.69% | `STABLE` | **`STABLE`** | `STABLE` | Normal minor daily fluctuation |
| **2026-08-30** | ₹15,539.69 | +₹393.63 | +2.60% | `RISING` | **`RISING`** | `RISING` | True upward weekend surge |
| **2026-08-31** | ₹15,322.81 | −₹216.88 | −1.40% | `FALLING` | **`STABLE`** | `STABLE` | Minor post-weekend correction within normal band |
| **2026-09-07** | ₹17,315.92 | +₹1,993.11 | +13.01% | `RISING` | **`RISING`** | `RISING` | Significant market spike |

*Result:* The $\pm 1.5\%$ threshold filters out the $-1.40\%$ noise on 2026-08-31 while decisively capturing the $+2.60\%$ surge on 2026-08-30 and $+13.01\%$ spike on 2026-09-07.

---

## 6. Definition of Fare Position (Task 5)

### 6.1 Regulatory & Product Constraint
FareIndex India is a **market indicator**, not a travel agency or booking advisory.
- **Strict Prohibition**: The system must **NEVER** display advice such as *"BUY NOW"*, *"DON'T BUY"*, *"GREAT TIME TO BOOK"*, or *"WAIT FOR FARES TO DROP"*.
- **Objective Standard**: It must solely describe the current fare's **statistical position** relative to historical observations on that route.

### 6.2 Percentile Methodology Evaluation

We evaluated two statistical positioning models across the historical distribution of prices:

```
Method A: Equal Terciles (33.3% / 33.3% / 33.3%)
┌──────────────────┬──────────────────┬──────────────────┐
│    LOW (0-33%)   │  NORMAL (33-67%) │   HIGH (67-100%) │
└──────────────────┴──────────────────┴──────────────────┘

Method B: Interquartile Bands (25% / 50% / 25%) [RECOMMENDED]
┌─────────┬──────────────────────────────┬─────────┐
│   LOW   │            NORMAL            │  HIGH   │
│ (0-25%) │           (25-75%)           │(75-100%)│
└─────────┴──────────────────────────────┴─────────┘
```

### 6.3 Recommendation: Interquartile Positioning (25th / 75th Percentiles)

In aviation economics, fares naturally cluster around standard fare classes for the majority of dates. A wider "Normal" band (the middle 50%) accurately reflects standard market equilibrium, whereas "Low" (bottom 25%) and "High" (top 25%) represent notable deviations.

#### Mathematical Thresholds for Fare Position:

$$\text{Fare Position}(R, \bar{p}_t) = \begin{cases}
\textbf{LOW} & \text{if } \bar{p}_t \le P_{25}(R) \\
\textbf{NORMAL} & \text{if } P_{25}(R) < \bar{p}_t < P_{75}(R) \\
\textbf{HIGH} & \text{if } \bar{p}_t \ge P_{75}(R)
\end{cases}$$

Where $P_{25}(R)$ and $P_{75}(R)$ are calculated from the historical distribution of daily route averages:
- **`HYD-DEL` Historical Daily Quartiles**:
  - $P_{25} = \text{₹15,146.06}$
  - $P_{50} (\text{Median}) = \text{₹15,290.62}$
  - $P_{75} = \text{₹15,322.81}$ (All Data) / $\text{₹15,539.69}$ (Prod Data)
- **Position Status on 2026-09-07**:
  - Current fare of ₹15,290.62 (with Demo) $\rightarrow$ **`NORMAL`** (48th percentile).
  - Current fare of ₹17,315.92 (Prod Only) $\rightarrow$ **`HIGH`** (100th percentile / all-time high).

---

## 7. Definition of Fare Volatility (Task 6)

### 7.1 Statistical Framework
Airfare volatility can be measured across two distinct dimensions:
1. **Intra-Day Volatility (Price Dispersion)**: The standard deviation of flight prices across different airlines and departure times on a single observation day.
2. **Inter-Day Volatility (Price Stability)**: The day-to-day fluctuation of the daily route average over time, expressed as the **Coefficient of Variation ($CV$)**:

$$CV = \left( \frac{\sigma_{\text{daily}}}{\mu_{\text{daily}}} \right) \times 100$$

### 7.2 Empirical Volatility on HYD-DEL Dataset
- **Inter-Day Volatility (All Data)**: $\sigma = \text{₹189.08}, \mu = \text{₹15,268.36} \implies CV = \mathbf{1.24\%}$ (`LOW`).
- **Inter-Day Volatility (Prod Only)**: $\sigma = \text{₹937.37}, \mu = \text{₹15,673.42} \implies CV = \mathbf{5.98\%}$ (`MODERATE`).
- **Intra-Day Volatility (Single Date Price Dispersion)**:
  - 2026-08-28: $\sigma = \text{₹1,468.90} \implies CV = 9.76\%$
  - 2026-08-30: $\sigma = \text{₹1,331.60} \implies CV = 8.57\%$
  - 2026-09-07: $\sigma = \text{₹2,074.74} \implies CV = 11.98\%$

### 7.3 Volatility Classification Scale

| Volatility Rating | Coefficient of Variation ($CV$) | Market Meaning |
| :--- | :---: | :--- |
| **`LOW VOLATILITY`** | $CV < 3.0\%$ | Predictable pricing; fares remain steady day-to-day. |
| **`MODERATE VOLATILITY`** | $3.0\% \le CV \le 8.0\%$ | Standard commercial airline yield management and weekend shifts. |
| **`HIGH VOLATILITY`** | $CV > 8.0\%$ | Sharp price swings, holiday booking surges, or airline capacity disruptions. |

### 7.4 Product Recommendation
- **Status for Phase 6**: Keep Volatility as an **Advanced / Analytical Indicator** located in the Route Analytics section. Do not display it as a primary headline metric to avoid overwhelming regular travellers.

---

## 8. Demo Data Policy & Segregation (Task 7)

### 8.1 Empirical Findings on Synthetic Demo Data
Our database audit identified **36 records** marked with `source = 'DEMO - NOT LIVE'` (18 for `HYD-DEL`, 18 for `HYD-GOI` on `2026-09-07`).

#### The Impact on HYD-DEL:
- The synthetic demo generator created mock prices ranging from **₹6,670 to ₹9,456** (Mean: **₹8,089.56**).
- When mixed with the 64 real scraped observations (Mean: **₹17,315.92**), the synthetic data artificially depressed the true daily average down to **₹15,290.62** (a ₹2,025 / 11.7% distortion).

#### The Impact on HYD-GOI:
- Synthetic demo data ($N = 18$, Mean: **₹5,782.67**) combined with live Playwright scrapes ($N = 5$, Mean: **₹9,351.00**) to yield a diluted average of **₹6,558.39**.

### 8.2 Recommended Production Policy

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RAW_PRICES (SQLite DB)                          │
│                                                                        │
│  ┌───────────────────────────────┐   ┌──────────────────────────────┐  │
│  │     Production Observations   │   │     Synthetic Demo Data      │  │
│  │   • Playwright Scraper (34)   │   │   • DEMO - NOT LIVE (36)     │  │
│  │   • Recovered Archive (249)   │   │                              │  │
│  └───────────────┬───────────────┘   └──────────────┬───────────────┘  │
└──────────────────┼──────────────────────────────────┼──────────────────┘
                   │                                  │
                   ▼                                  ▼
      [Public Calculation Engine]           [Isolated Demo Sandbox]
      WHERE source NOT LIKE '%DEMO%'        Used ONLY when DEMO_MODE=true
                   │
                   ▼
      Public Indices & Daily Averages
```

1. **Database Retention**: **Do NOT delete** DEMO rows from `data/fareindex.db`. They serve as valuable seed records for testing offline environments and verifying scraper fallbacks.
2. **Query Isolation Rule**: All production index and aggregation queries in `app/index_engine.py` should include an explicit filter:
   ```sql
   WHERE price_inr > 0 AND source NOT LIKE '%DEMO%' AND source NOT LIKE '%NOT LIVE%'
   ```
3. **Admin Transparency**: Provide an explicit toggle in the Admin Control Panel:
   - `Mode: Production Data Only (283 obs)` [Default]
   - `Mode: Include Synthetic Demo Sandbox (319 obs)` [Testing]

---

## 9. National Composite Index Recommendation (Task 8)

### 9.1 Current State Analysis
- **Tracked Routes**: `HYD-DEL` ($N = 296$) and `HYD-GOI` ($N = 23$).
- **Baseline Eligibility**: `HYD-DEL` has 5 observation dates ($\ge 2$ required) and is fully indexed. `HYD-GOI` has only 1 observation date (`2026-09-07`) and cannot establish a multi-day baseline.
- **National Composite Reality**: The current "National Composite Index" is mathematically **100% composed of `HYD-DEL`** ($100.15$).

### 9.2 Evaluation of Strategic Options

| Strategy | Description | Pros | Cons | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Hero Status** | Keep National Index as the primary dashboard headline. | Highlights macroeconomic vision. | Misleading; 1 route does not represent all of India. | **REJECT** |
| **Option B: Hide Completely** | Remove National Index until 10+ routes exist. | Completely eliminates criticism of low route count. | Loses the core hackathon deliverable and composite architecture. | **REJECT** |
| **Option C: Secondary Provisional** | Make Route Selector primary (`HYD-DEL`), demote National Index to a secondary tab with a "Provisional 1-Route Composite" badge. | • Transparent & credible.<br>• Demonstrates the working composite weighting engine without overstating national coverage. | Requires clear UI badging. | **RECOMMENDED** |

### 9.3 Recommended Implementation
- Default the dashboard view to **`HYD → DEL (Hyderabad – Delhi)`** as the primary active route.
- Allow users to switch to **`National Composite (Provisional)`** via the Route Selector.
- When `National Composite` is selected, render a clear informational notice:
  > *"Provisional National Composite — Currently aggregating 1 indexed metro trunk route (HYD-DEL). Additional trunk routes will automatically join the composite as multi-day baselines are established."*

---

## 10. Route Coverage & National Benchmark Criteria (Task 9)

### 10.1 Minimum Criteria for a Credible "India Domestic Airfare Index"
To transition from a *route-level market indicator* to an authoritative *National Domestic Airfare Benchmark*, the system must fulfill three minimum criteria:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CRITERIA FOR NATIONAL BENCHMARK READINESS                   │
├──────────────────────────────┬──────────────────────────────┬───────────────┤
│ 1. Route Representation      │ 2. Temporal Depth            │ 3. Sample Size│
│ Top 6 High-Density Metros    │ 14 Consecutive Days          │ ≥ 20 Flights  │
│ (>60% of DGCA Traffic)       │ (Full 2-week cycle)          │ per Route/Day │
└──────────────────────────────┴──────────────────────────────┴───────────────┘
```

### 10.2 Top 6 Priority Trunk Routes (Target Route Matrix)

| Priority | City-Pair Route | Metro Connectors | Est. DGCA Passenger Share | Recommended Initial Weight |
| :---: | :---: | :---: | :---: | :---: |
| **1** | **DEL ⇄ BOM** | Delhi – Mumbai | ~11.5% | 1.5 |
| **2** | **DEL ⇄ BLR** | Delhi – Bengaluru | ~9.2% | 1.3 |
| **3** | **BOM ⇄ BLR** | Mumbai – Bengaluru | ~8.4% | 1.2 |
| **4** | **HYD ⇄ DEL** | Hyderabad – Delhi | ~7.1% | 1.0 *(Active)* |
| **5** | **DEL ⇄ MAA** | Delhi – Chennai | ~6.3% | 0.9 |
| **6** | **DEL ⇄ CCU** | Delhi – Kolkata | ~5.8% | 0.8 |

---

## 11. Final Metric Hierarchy (Task 10)

```
========================================================================================
                                FAREINDEX INDIA — METRIC HIERARCHY
========================================================================================

1. PRIMARY LEVEL (Immediate User Clarity & Hero Section)
   ├── Current Average Fare (₹) ............. ₹15,291 (or ₹17,316 Prod)
   ├── Rupee Change (DoD) ................... -₹32 (-0.2%) vs previous observation
   ├── Trend Direction ...................... STABLE (—) [within ±1.5% noise band]
   └── Interactive Fare-Over-Time Graph ..... Large, prominent ₹ price series with hover

2. SECONDARY LEVEL (Analytical & Macroeconomic Context)
   ├── Relative Fare Position ............... NORMAL (Historical 48th Percentile)
   ├── Airfare Index Value .................. 100.15 (Base = 100.0)
   ├── Provisional Baseline Fare ............ ₹15,268.36 (Historical benchmark)
   ├── Observation Metadata ................. 82 observations, 3 airlines, Date: 07 Sep 2026
   └── Active Route Selector ................ Route pills (HYD-DEL, HYD-GOI, National)

3. ADVANCED / DRILL-DOWN LEVEL (Aviation Analysts, Media, Regulators)
   ├── Airline Breakdown .................... IndiGo vs. Air India vs. Akasa spread & share
   ├── Booking Lead-Time Curve .............. Advance purchase buckets (3, 7, 14, 21, 30, 60d)
   ├── Fare Volatility Metric ............... Intra-day dispersion & Inter-day CV
   ├── Raw Flight Observations Table ........ Paginated, searchable inspection table
   └── 5-Step Methodology Modal ............. Ingest → Average → Baseline → Index → Composite

4. HIDDEN / INTERNAL INFRASTRUCTURE (Completely removed from public dashboard)
   ├── Scraper internals .................... Playwright headless flags, Amadeus secrets
   ├── Backend frameworks ................... FastAPI, SQLite, APScheduler engine details
   └── Admin actions ........................ Manual scrape / DB rebuild (moved to /admin)
========================================================================================
```

---

## 12. What Should Change in Phase 6 UI Redesign

| UI Element | Current Phase 5 Implementation | Planned Phase 6 Redesign | Rationale |
| :--- | :--- | :--- | :--- |
| **Hero Card Headline** | `India Airfare Index: 100.15` (Abstract index number) | `Current Average Fare: ₹15,291` with prominent `— STABLE (-0.2%)` badge | Solves the primary user question instantly in familiar Rupee units. |
| **Trend Badging** | Generic numeric difference | Prominent colored pill: `▲ RISING (+X%)`, `▼ FALLING (-X%)`, `— STABLE (±0%)` | Intuitive visual language with noise-filtering deadbands. |
| **Main Chart Default** | Index values (98.52 to 101.78) | **Average Fare (₹)** as default view, with a toggle button for `Index (Base 100)` | Regular users understand Rupee trajectories far better than normalized indices. |
| **Fare Position Widget** | Not present | Visual gauge/strip: `[ LOW | ● NORMAL | HIGH ]` | Gives immediate historical context without offering financial advice. |
| **Route Selector Position** | Below the National Hero card | **Top-level Navigation** (prominently placed above charts) | Encourages route-level exploration (`HYD-DEL` vs `HYD-GOI`). |
| **Data Provenance Badges** | Full-width banners | Compact, professional chips in header and footer (`● Verified Data`) | Reduces visual clutter while maintaining full data integrity. |
| **Admin Controls** | Visible at bottom of main page | Collapsed into a dedicated `/admin` drawer or discreet settings modal | Prevents test buttons from confusing end users. |

---

## 13. What Should NOT Change

To ensure absolute system stability, the following architectural invariants are strictly locked:

1. **Database Schema**:
   - `raw_prices` (14 columns) and `index_values` (7 columns) schemas remain identical.
   - All historical records ($N = 319$) are preserved with existing primary keys and foreign constraints.
2. **Backend API Contracts**:
   - All existing 11 FastAPI endpoints (`/api/health`, `/api/routes`, `/api/routes/summary`, `/api/index/national`, `/api/index/route/{route}`, `/api/analytics/booking-curve`, `/api/analytics/airlines`, `/api/prices/latest`, `/api/admin/*`) remain backward-compatible.
3. **Index Engine Core Math**:
   - Multi-day baseline formula ($ \text{Baseline} = \frac{1}{K} \sum \bar{p}_k $) and Index formula ($ \text{Index} = \frac{\bar{p}}{\text{Baseline}} \times 100 $) remain identical.
4. **Scraper Pipeline & Scheduling**:
   - Playwright scraper and Amadeus API providers in `app/providers.py` and `app/scrape_service.py` remain untouched.
5. **Automated Test Suite**:
   - All 27 Pytest test cases in `tests/test_api.py`, `tests/test_index_engine.py`, and `tests/test_scraper.py` must continue passing without modification.

---

## 14. Open Decisions Requiring Human Approval

Before executing Phase 6 frontend and pipeline implementation, sign-off is requested on the following 4 decisions:

### Decision 1: Metric Default on Main Dashboard Chart
- **Option A (Recommended)**: Default the main chart to **Average Fare (₹)**, with a clear toggle switch to view **Index (Base 100)**.
- **Option B**: Default to **Index (Base 100)** with a toggle to **Average Fare (₹)**.

### Decision 2: Demo Data Exclusion in Production API
- **Option A (Recommended)**: Exclude `DEMO - NOT LIVE` records from public calculation queries by default, while preserving them in SQLite for testing.
- **Option B**: Continue including all 319 records in calculations until more live routes are scraped.

### Decision 3: Trend Deadband Sensitivity Threshold
- **Option A (Recommended)**: **$\pm 1.5\%$** (Filters out daily churn while cleanly catching true weekend and spike moves).
- **Option B**: **$\pm 1.0\%$** (More sensitive, but may flag minor single-flight price shifts as trends).
- **Option C**: **$\pm 2.0\%$** (Conservative, flags only substantial market shifts).

### Decision 4: Fare Position Percentile Thresholds
- **Option A (Recommended)**: **Quartile Bands** ($0\text{–}25\%$ = `LOW`, $25\text{–}75\%$ = `NORMAL`, $75\text{–}100\%$ = `HIGH`).
- **Option B**: **Tercile Bands** ($0\text{–}33.3\%$ = `LOW`, $33.3\text{–}66.7\%$ = `NORMAL`, $66.7\text{–}100\%$ = `HIGH`).

---

## 15. Audit Verification & Test Execution Log

```bash
$ .venv/bin/pytest
============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/jyothipabbisetti/Downloads/fareindex_backend_starter
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 27 items

tests/test_api.py ..............                                         [ 51%]
tests/test_index_engine.py ......                                        [ 74%]
tests/test_scraper.py .......                                            [100%]

======================== 27 passed, 1 warning in 0.63s =========================
```

- **Production Code Status**: Unchanged (Zero modifications to backend logic, frontend JSX, or database).
- **Test Suite Status**: **27 / 27 PASS (100%)**.
- **Audit Deliverable**: `docs/phase-6-product-methodology-audit.md` successfully generated.
