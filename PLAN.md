# PLAN.md — Wind Forecast Decision Support Tool

## Overview
Web application for a UK energy utility's day-ahead power buying team. Helps buyers see the latest wind generation forecast, evaluate forecast accuracy, and estimate uncertainty bands for procurement decisions.

**Data scope**: UK national-level wind only, Elexon BMRS data, January 2026 delivery days.

---

## Architecture

```
/backend (Python, FastAPI)
├── app/
│   ├── main.py              # FastAPI app, CORS, startup
│   ├── config.py             # Settings (env vars, defaults)
│   ├── models.py             # Pydantic schemas
│   ├── data/
│   │   ├── client.py         # Elexon BMRS API client
│   │   ├── cache.py          # SQLite cache layer
│   │   └── fetch_data.py     # CLI script to fetch & cache data
│   ├── analytics/
│   │   ├── selection.py      # Latest forecast selection logic
│   │   ├── metrics.py        # Accuracy metrics (MAE, RMSE, etc.)
│   │   └── horizon.py        # Error vs horizon analysis
│   ├── routes/
│   │   ├── health.py
│   │   ├── actuals.py
│   │   ├── forecast.py
│   │   ├── compare.py
│   │   ├── metrics.py
│   │   └── meta.py
│   └── tests/
│       ├── test_selection.py
│       ├── test_metrics.py
│       └── test_horizon.py
├── requirements.txt
└── Dockerfile

/frontend (React + TypeScript + Vite)
├── src/
│   ├── App.tsx
│   ├── api/
│   │   └── client.ts         # API client with configurable base URL
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── DatePicker.tsx
│   │   ├── KPICard.tsx
│   │   └── MetricTooltip.tsx
│   ├── views/
│   │   ├── DecisionView.tsx
│   │   ├── AccuracyView.tsx
│   │   └── HorizonView.tsx
│   └── utils/
│       ├── csv.ts
│       └── formatters.ts
├── package.json
└── Dockerfile

/docs
├── ARCHITECTURE.md
├── ANALYSIS.md
└── VIDEO_SCRIPT.md

docker-compose.yml
.env.example
Makefile
README.md
```

---

## Key Design Decisions

### Data Assumptions
1. **Decision cutoff**: Default D-1 at 09:00 Europe/London. Configurable via UI and API.
2. **Timezone**: All internal processing in UTC. Display converts to Europe/London. BMRS API returns UTC.
3. **Forecast selection**: For target time T and cutoff C, select the forecast row with `max(publishTime) WHERE publishTime <= C`.
4. **Forecast horizon**: `startTime - publishTime` in hours.
5. **FUELHH filtering**: Filter `fuelType == "WIND"` from the half-hourly generation outturn data.
6. **Forecast window**: Fetch WINDFOR from ~Dec 15 2025 through Jan 31 2026 to capture early forecasts for Jan 1 targets.
7. **Missing data**: Clearly surface gaps; exclude from metrics where actual or forecast is missing.

### Accuracy Metrics
- **Error** = forecast - actual (positive = over-forecast)
- **MAE** = mean(|error|)
- **RMSE** = sqrt(mean(error²))
- **MAPE** = mean(|error| / |actual|) * 100, guarded for zero actuals
- **Bias** = mean(error)
- **Percentiles**: P50, P90, P99 of |error|
- **nMAE** = MAE / mean(actual) * 100

### Uncertainty Band
- Group historical errors by horizon bucket (0-6h, 6-12h, 12-24h, 24-48h, 48h+)
- Calculate P10 and P90 of error for each bucket
- Apply to latest forecast: band = [forecast + P10_error, forecast + P90_error]

---

## Milestones

### M0: API Exploration (0.5h)
- [x] Add `explore_api.py`; probe both endpoints with bounded live requests
- [x] Verify query parameters and response shapes against the live API
- [x] Record January actual and forecast coverage, cadence, and quirks below

### M1: Data Layer (2h)
- [x] Elexon API client with bounded requests, retries, and rate limiting
- [x] SQLite cache for normalized and raw JSON data
- [x] `fetch_data.py` CLI script
- [x] Startup check to load cached data

### M2: Analytics Engine + Tests (2h)
- [x] Forecast selection logic (latest publishTime <= cutoff)
- [x] Horizon calculation and hourly actual alignment
- [x] Accuracy metrics (pure functions)
- [x] Uncertainty band calculation with missing-history handling
- [x] pytest tests for analytics, timezone, gaps, and cache filters

### M3: Backend API (2h)
- [x] FastAPI app with all endpoints
- [x] Pydantic models for all requests/responses
- [x] Input validation (dates restricted to Jan 2026)
- [x] CORS configuration

### M4: Frontend Foundation (3h)
- [x] Vite + React + TypeScript setup
- [x] Design system (colors, typography, layout)
- [x] API client with configurable base URL
- [x] Navigation and layout components

### M5: Frontend Views (3h)
- [x] Decision View with forecast chart + uncertainty band
- [x] Accuracy View with overlays, error charts, KPI cards
- [x] Horizon View with error vs horizon charts

### M6: Polish & Features (1.5h)
- [x] Loading/error states
- [x] Tooltips for metrics
- [x] CSV export
- [x] Responsive layout
- [x] Typography and micro-animations

### M7: Docker & Deployment (1h)
- [x] Backend Dockerfile
- [x] Frontend Dockerfile
- [x] docker-compose.yml
- [x] Vercel/Render deployment config
- [ ] Deploy public services (requires deployment account credentials)

### M8: Documentation (1h)
- [x] README.md
- [x] docs/ARCHITECTURE.md
- [x] docs/ANALYSIS.md
- [x] docs/VIDEO_SCRIPT.md

---

## API Exploration Findings

Live API probes were run against `https://data.elexon.co.uk/bmrs/api/v1` on
2026-10-25. The documentation site is a JavaScript-rendered SPA; the endpoint
parameters were also verified with successful requests against the documented
stream paths.

### FUELHH (Actuals)
- **Endpoint**: `GET /datasets/FUELHH/stream`
- **Verified query params**: `settlementDateFrom`, `settlementDateTo` (`yyyy-MM-dd`), and `fuelType=WIND`
- **Response**: JSON array; fields observed: `dataset`, `publishTime`, `startTime`,
  `settlementDate`, `settlementPeriod`, `fuelType`, `generation`
- **January 2026 result**: 1,488 WIND rows; 48 rows on each of 31 days; no missing
  dates or duplicate `startTime` values. Targets cover
  `2026-01-01T00:00:00Z` through `2026-01-31T23:30:00Z`.
- **Quirk**: The API accepts the `fuelType=WIND` filter and returns 48 rows for
  a day. Without it, a single day returned 960 records across 20 fuel types.

### WINDFOR (Forecasts)
- **Endpoint**: `GET /datasets/WINDFOR/stream`
- **Verified query params**: `publishDateTimeFrom`, `publishDateTimeTo` (UTC ISO 8601)
- **Response**: JSON array; fields observed: `dataset`, `publishTime`, `startTime`,
  `generation`
- **Sample result**: a six-hour publish window returned 146 records; a 24-hour
  window returned 584. A target may occur in multiple publications, including
  publications for dates before and after the target range.
- **January fetch result**: 18,080 rows across 744 unique target hours, with no
  duplicate `(startTime, publishTime)` pairs. WINDFOR target times are hourly
  (`:00` only), not half-hourly like FUELHH. A comparison uses the mean of the
  two corresponding FUELHH half-hour values and does not interpolate forecast
  values.
- **Horizon quirk**: raw publication rows span -25.5 to 66.5 hours, including
  revisions published after target delivery. They cannot be considered
  decision-time forecasts; selection is strictly limited to publish times at
  or before the D-1 cutoff. The observed target/publication range is
  `2026-01-01T00:00Z`–`2026-01-31T23:00Z` and
  `2025-12-30T02:30Z`–`2026-01-31T22:30Z`, respectively.
- **Fetch behavior**: partition the complete publish window into bounded
  six-hour requests, filter targets to January 2026, and de-duplicate by
  `(startTime, publishTime)`. All 744 hourly forecast target periods had a
  matching forecast available at the default decision cutoff. The complete
  cache contains 18,080 forecast versions and 1,488 actual intervals.

## Completion notes

- Backend suite: 55 tests pass; Ruff passes.
- Frontend lint, 6 tests, and production build pass.
- All API endpoints were smoke-tested against the prefetched local cache.
- Docker files are configured, but the local Docker daemon is unavailable for
  image/compose verification.
- Render and Vercel configuration is prepared. No deployment token/account was
  available, so there is no live URL yet.
