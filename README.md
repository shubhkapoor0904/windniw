# Northstar — wind forecast decision support

Northstar helps a UK day-ahead power buying team inspect the wind forecast
available at its decision cutoff and compare that forecast with January 2026
wind outturn. The application is intentionally limited to national wind and
Elexon BMRS [`WINDFOR`](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
and [`FUELHH`](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
data.

## What it does

- Selects the most recently published `WINDFOR` row for each hourly target with
  `publishTime <= cutoff`.
- Defaults to delivery day D-1 at **09:00 Europe/London**, configurable to the
  minute in the UI and API.
- Shows the forecast, publication time, horizon, and an empirical P10–P90
  plausible wind range derived from historical forecast errors.
- Compares the selected hourly forecast with the average of its two
  half-hourly FUELHH actual intervals, with MAE, RMSE, bias,
  MAPE, P90 absolute error, error distribution, and horizon buckets.
- Exports comparison records to CSV, retaining rows with missing values.

## Repository guide

| Path | Purpose |
| --- | --- |
| `backend/app/data` | Elexon client, SQLite cache, and refresh command |
| `backend/app/analytics` | Pure forecast selection and error analysis |
| `backend/app/routes` | Typed FastAPI endpoints |
| `backend/app/tests` | Selection, metrics, horizon, and cache tests |
| `frontend/src/views` | Decision, accuracy, and horizon workspaces |
| `docs/ARCHITECTURE.md` | Data flow and design decisions |
| `docs/ANALYSIS.md` | Measured January 2026 data findings |
| `docs/VIDEO_SCRIPT.md` | Customer pitch and technical walkthrough |

## Run locally without Docker

From the repository root, in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
Set-Location backend
python -m app.data.fetch_data
python -m uvicorn app.main:app --reload
```

In another terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`; the Vite server proxies `/api` to
`http://localhost:8000`. The backend can also be opened at
`http://localhost:8000/docs`. Copy `.env.example` to `.env` to configure the
cache path, CORS, or frontend API URL; Vite and the backend both load that
repository-root file.

`python -m app.data.fetch_data --force` refreshes both datasets. Fetching makes
bounded, rate-limited Elexon requests and persists normalized values plus raw
JSON records to SQLite. Requests are only made by this explicit fetch command,
not by API reads or application startup.

## Run with Docker

```powershell
docker compose up --build
```

The UI is served at `http://localhost:5173` and the API at
`http://localhost:8000`. The prefetched January SQLite cache is included under
`backend/data/` and persisted there by Compose. Run the fetch command only when
you want to refresh the source snapshot.

## Data assumptions and limitations

- All timestamps are stored and compared in UTC. User-facing delivery and
  decision times are Europe/London.
- A delivery day's decision cutoff is D-1 at 09:00 local time by default. It is
  a stated operational assumption, not an Elexon gate-closure fact; buyers can
  set another hour and minute.
- For each hourly forecast target, the selected forecast is the row with
  maximum `publishTime` no later than the cutoff. Forecasts published later are
  never used in that decision snapshot.
- FUELHH is filtered to `fuelType=WIND`. The fetch is limited to January 2026
  actual target periods. WINDFOR publication requests begin 15 December 2025
  to retain forecasts published ahead of January delivery and are then filtered
  to January targets.
- The live January WINDFOR feed is hourly (`startTime` at `:00`), while FUELHH
  is half-hourly. Northstar preserves that source cadence: it averages the two
  complete half-hour actuals for each forecast hour, excludes incomplete hours,
  and does not interpolate or duplicate hourly forecasts. The decision chart
  therefore contains at most 24 forecast points per delivery day.
- BMRS stream responses are JSON arrays, not page-token envelopes. The client
  partitions date/publish windows into bounded requests, retries transient
  failures, and de-duplicates by target and publish time in SQLite.
- Missing forecasts/actuals are shown as gaps and excluded from paired error
  metrics. MAPE excludes actuals under 1 MW. A missing metric is displayed as
  unavailable rather than zero.
- Error is forecast minus actual: positive bias means wind was over-forecast.
  MAE is mean absolute error; RMSE is the square root of mean squared error;
  bias is mean signed error. They are reported in MW. MAPE is mean absolute
  percentage error (excluding actuals below 1 MW), and nMAE is MAE divided by
  mean actual generation; both are percentages. P50/P90/P99 are percentiles of
  absolute error in MW.
- Historical error quantiles use the same selected decision-time forecasts as
  the accuracy view. Since the sample covers one delivery month, uncertainty
  bands are descriptive and should not be treated as calibrated probabilities.
- The January cache contains 1,488 actual intervals and 18,080 forecast versions
  for 744 hourly targets. All 744 hourly targets have both a D-1 09:00
  decision-time forecast and complete actuals.
- This is a scoped take-home: national aggregate data only, one month, and no
  demand, prices, asset constraints, or trading-system integration.

## API

- `GET /api/health`
- `GET /api/meta`
- `GET /api/actuals?start=2026-01-01&end=2026-01-31`
- `GET /api/forecast/latest?targetDate=2026-01-15&cutoffHour=9&cutoffMinute=0`
- `GET /api/compare?start=2026-01-01&end=2026-01-31&cutoffHour=9&cutoffMinute=0`
- `GET /api/metrics?start=2026-01-01&end=2026-01-31&cutoffHour=9&cutoffMinute=0`
- `GET /api/metrics/by-horizon?start=2026-01-01&end=2026-01-31`

Dates are validated to January 2026. FastAPI's `/docs` page describes request
and response schemas.

## Quality checks

```powershell
Set-Location backend; python -m ruff check app; python -m pytest -q
Set-Location ..\frontend; npm run lint; npm test; npm run build
```

GitHub Actions runs backend lint/tests and frontend lint/tests/build for pushes
and pull requests.

## Deployment

The frontend is configured for Vercel (`frontend/vercel.json`) and the backend
has a Render Docker blueprint (`render.yaml`). Set
`VITE_API_BASE_URL` to the public backend origin when building the frontend,
and set `WIND_CORS_ORIGINS` to the deployed Vercel origin. The Render image includes the prefetched SQLite cache; refresh and rebuild the
image to publish a new data snapshot. The service does not call Elexon during
startup.

**Live URL:** not deployed. No public frontend or backend URL has been
provisioned for this workspace.

## AI assistance

GitHub Copilot assisted with implementation and documentation. Antigravity and
Claude were not used in this build.

## Next steps

Use more delivery months and seasonal slices for robust uncertainty calibration;
compare alternative decision cutoffs; validate the cutoff against the team's
actual market process; then add demand and price context only if the product
scope expands.
