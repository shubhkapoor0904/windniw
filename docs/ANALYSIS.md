# January 2026 data findings

## Coverage and response shape

The endpoints were probed on 2026-10-25. `FUELHH/stream` with
`settlementDateFrom`, `settlementDateTo`, and `fuelType=WIND` returned a JSON
array with `dataset`, `publishTime`, `startTime`, `settlementDate`,
`settlementPeriod`, `fuelType`, and `generation`. January contained **1,488**
half-hour rows: 48 on each of 31 days, no missing dates, and no duplicate
`startTime`.

`WINDFOR/stream` accepts `publishDateTimeFrom`/`publishDateTimeTo` in UTC and
returns a JSON array with `dataset`, `publishTime`, `startTime`, and
`generation`. The fetch window began on 15 December 2025 and returned **18,080**
January-target forecast versions, covering **744 hourly target times** with no
duplicate `(startTime, publishTime)` keys. The forecast cadence is hourly,
unlike the half-hourly actuals. The analysis therefore averages the two FUELHH
values for a complete target hour; no forecast interpolation is performed.

Forecast publication times ranged from 2025-12-30 02:30 UTC to 2026-01-31
22:30 UTC. Raw versions have horizons from **-25.5 to 66.5 hours**; negative
horizons are late revisions published after delivery. These are not eligible
for a D-1 decision snapshot. At the default D-1 09:00 Europe/London cutoff,
all **744 of 744** hourly periods had both an available forecast and complete
actuals (100%). Missing periods, if present in another cutoff or date range,
are excluded from paired error analysis rather than treated as zero error.

## Accuracy at the default cutoff

The table below compares each selected forecast (maximum `publishTime` at or
before D-1 09:00 London) with the mean of the corresponding pair of FUELHH
half-hour actuals. Error is forecast minus actual. Values are rounded.

| Measure | Result | Interpretation |
| --- | ---: | --- |
| Paired hourly periods | 744 | 100% of 744 hourly target periods |
| MAE | 2,142 MW | Average absolute miss |
| RMSE | 2,612 MW | Larger misses receive extra weight |
| Bias | +1,852 MW | Forecasts tended to overstate wind |
| MAPE | 22.4% | Actuals below 1 MW excluded |
| P50 absolute error | 1,788 MW | Median miss |
| P90 absolute error | 4,300 MW | 90% of absolute misses were no larger |
| P99 absolute error | 6,261 MW | 99th percentile absolute miss |
| nMAE | 18.5% | MAE as a share of mean actual generation |

The positive bias is the clearest directional result in this one-month sample:
on average, a buyer relying on the selected forecast would have expected about
1.85 GW more wind than the paired actual outturn.

## Error by forecast horizon

| Forecast horizon | Periods | MAE (MW) | Bias (MW) | P10 signed error (MW) | P90 signed error (MW) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 12–24 h | 248 | 2,405 | +2,337 | +246 | +4,856 |
| 24–36 h | 372 | 2,031 | +1,574 | -1,029 | +4,068 |
| 36–48 h | 124 | 1,951 | +1,717 | -272 | +4,269 |

MAE declines across these measured buckets in this month, but this does not
establish that longer horizons are inherently more accurate: horizon coverage
and weather conditions differ. The sample shows large errors and positive bias
in every bucket. More months are needed to separate horizon effects from
weather-regime effects.

The signed P10/P90 ranges feed the decision view's descriptive uncertainty
band. They are empirical quantiles from this single month, not guaranteed
coverage intervals.

## Highest daily MAE

| Delivery day | Paired hours | MAE (MW) | Bias (MW) |
| --- | ---: | ---: | ---: |
| 2026-01-28 | 24 | 5,375 | +5,375 |
| 2026-01-12 | 24 | 4,868 | +4,868 |
| 2026-01-11 | 24 | 4,802 | +4,802 |
| 2026-01-01 | 24 | 4,208 | +4,208 |
| 2026-01-21 | 24 | 3,658 | +3,658 |

These are the largest errors in the measured month; this analysis does not
attribute them to specific weather events or system conditions.

## Scope caveats

This is a single calendar month and one assumed decision time. National
aggregation hides regional wind variation, while forecast target cadence is
hourly. Data gaps and post-delivery forecast revisions are explicitly handled,
but the results are not sufficient to establish operational risk limits or
probabilistic band calibration.
