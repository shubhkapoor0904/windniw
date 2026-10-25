# Video script (10 minutes maximum)

## Part 1 — Customer pitch (4:45 maximum)

**0:00–0:40 — The buying problem**

“The power buying team needs to decide what to procure for tomorrow before
delivery. Wind output is uncertain, and a forecast is only useful if we know
which version was actually available when that decision was made. Northstar
makes that snapshot explicit and shows how its historical errors behave.”

**0:40–1:10 — Set the decision time**

Open Decision view. Select a January delivery day and show the cutoff control.
“The default is 09:00 on D-1 in London time. That is an assumption, not a
claimed gate closure, so the hour and minute can be changed to match the team's
process.”

**1:10–2:05 — Latest available forecast**

Walk across the hourly curve and publication detail table. Hover a point to show
its target time, publish time, and lead time. “Every point is selected by
maximum publish time at or before the cutoff. A newer revision after the
cutoff cannot leak into this view.”

**2:05–2:55 — Range and procurement example**

Point to the uncertainty band and energy/peak cards. “For a 12,000 MW wind
forecast, a historical P10–P90 error range can translate into a plausible
actual-wind interval. If the buyer plans residual demand as load minus wind,
lower wind within this range means more power may need to be procured. The band
is a planning aid, not a probability guarantee.”

**2:55–3:40 — Accuracy view**

Show the forecast/actual comparison, KPI cards, and histogram. “In January,
744 hourly decision-time pairs yielded about 2.14 GW MAE and +1.85 GW bias. A
positive error means wind was over-forecast, so the direction matters as much
as the average miss.”

**3:40–4:25 — Horizon view**

Show MAE and bias by lead-time bucket. “MAE declines across the observed
horizon buckets, but one month cannot establish that longer forecasts are
inherently more accurate. Errors are large throughout, and bias stays positive.
We should use this as evidence to investigate, not as a universal forecast
rule.”

**4:25–4:45 — Close**

“The output gives buyers a transparent forecast snapshot, measured error, and
a range they can use in a procurement conversation. The next step is to repeat
this over more months and validate the cutoff with the trading team.”

## Part 2 — Technical review (4:55 maximum)

**0:00–0:50 — Architecture**

Show `docs/ARCHITECTURE.md`. “A fetch command retrieves Elexon BMRS FUELHH and
WINDFOR in bounded windows, stores normalized values and raw JSON in SQLite,
and leaves API requests fully cache-backed. FastAPI serves typed models to the
React/Vite frontend.”

**0:50–1:45 — Data cadence and decision selection**

“The live data probe found 1,488 half-hour FUELHH rows but 744 hourly WINDFOR
targets. We preserve the hourly forecast cadence and average the two actual
half-hours for a complete hour. For each target, selection is a grouped
maximum `publishTime` subject to `publishTime <= cutoff`; UTC is used for
comparison, and London time is used to calculate the cutoff.”

**1:45–2:35 — Analytics**

Show `selection.py`, `alignment.py`, and `metrics.py`. “The sign convention is
forecast minus actual. Metrics include MAE, RMSE, bias, MAPE with a low-actual
guard, absolute-error percentiles, and nMAE. Horizon buckets return signed P10
and P90 errors; the decision UI reverses them to bound plausible actual wind.”

**2:35–3:20 — Tests and CI**

Show the backend test command and GitHub Actions file. “Tests cover exact-cutoff
selection, cutoff timezone and DST behavior, error metrics, missing data,
horizon grouping, cache boundary inclusivity, and hourly actual alignment.
CI runs Python lint/tests and frontend lint/tests/build.”

**3:20–4:00 — Containers and deployment**

Show `docker-compose.yml`. “Compose starts the API and static frontend. The
cache is mounted locally. Vercel and Render configuration is included; no live
service has been provisioned for this workspace. Production must seed the
prefetched cache before exposing the API.”

**4:00–4:55 — Tradeoffs and next steps**

“The scope is one month, national wind, and one default decision rule. Hourly
forecast cadence means no half-hour forecast is fabricated. The error bands
come from a single month and should not be called calibrated confidence
intervals. Next I would add multiple seasons, validate real gate timing, test
band coverage out of sample, and only then extend the product beyond wind.”
