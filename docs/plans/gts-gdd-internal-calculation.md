---
title: Internal GTS & GDD calculation
status: draft
version_target: custom_components/lawn_vision/manifest.json → 0.7.0
owner: schwarzbr0t
created: 2026-05-29
---

# Goal

Replace the pass-through behaviour of `SENSOR_GRASSLAND_TEMPERATURE_SUM` and
`SENSOR_GROWING_DEGREE_DAYS` with real, persisted annual accumulators driven by
daily mean temperature. External entities (`CONF_GTS_ENTITY`,
`CONF_GDD_ENTITY`) remain a manual override.

## Background

Today the coordinator reads both values verbatim from the configured entity
(`coordinator.py:275-276`). `_growing_degree_days()` exists but only returns
one day's delta, not a cumulative sum. No persistence, no bootstrap, no
annual reset. Card and dashboards show whatever the source entity reports —
typically `unknown` because most users have no such sensor.

Sources we already have:
- Daily mean temperature: `inputs.mean_daily_temperature_c` (from entity) or
  Open-Meteo `daily.temperature_2m_max`/`min` average.
- Open-Meteo forecast endpoint (`weather_source.fetch_open_meteo`) — already
  used for live conditions; supports `past_days` for short historical window.
- Open-Meteo Archive API (`archive-api.open-meteo.com/v1/archive`) — free,
  no API key, returns `temperature_2m_mean` per day for arbitrary ranges.
  Latency ≈ 5 days, so it has to be combined with `past_days` from the
  forecast endpoint for full year coverage.

## Decisions (confirmed)

| Topic | Choice |
| ----- | ------ |
| Approach | Write this plan first, implement in a follow-up. |
| Persistence | `homeassistant.helpers.storage.Store` (JSON in `/config/.storage/`). |
| GDD base temperature | Derived from `CONF_GRASS_TYPE`: cool-season → 5.5 °C, warm-season → 10 °C. No new UI field. |
| Bootstrap | Hybrid: Archive API for `Jan-1 … today-5`, Forecast API `past_days` for the trailing window. |

## Formulas

### GTS (Grünlandtemperatursumme, DWD)

```
weight(month) = 0.5   if month == 1
              = 0.75  if month == 2
              = 1.0   if month >= 3
gts_day(d)    = max(0, T_mean_d) * weight(month(d))
gts_kum(year) = Σ gts_day(d)  for d in [Jan-1(year), today]
```

Reported in K. Reset on every Jan-1.

### GDD (Growing Degree Days, single base)

```
base_temp(grass_type) = 5.5  if grass_type == GRASS_COOL_SEASON
                      = 10   if grass_type == GRASS_WARM_SEASON
gdd_day(d)    = max(0, T_mean_d − base_temp(grass_type))
gdd_kum(year) = Σ gdd_day(d)  for d in [Jan-1(year), today]
```

Reset on every Jan-1. If the user changes `grass_type` mid-season, recompute
the full year from cached history (Decision: do **not** mix bases inside the
running sum).

`T_mean_d` is the canonical daily mean. Preference order:
1. Open-Meteo `temperature_2m_mean` (archive) or `(temperature_2m_max + min)/2`
   (forecast `past_days`).
2. User-configured `CONF_MEAN_DAILY_TEMPERATURE_ENTITY` for the *current* day
   only (no historical access).
3. Skip the day — leave the accumulator at the previous value and log debug.

## Architecture

### New module: `custom_components/lawn_vision/agronomy.py`

Pure functions, no `homeassistant.*` imports. Mirrors the
`actions.py`/`helpers.py` pure-core convention.

```python
GTS_THRESHOLD_K = 200

def gts_weight(month: int) -> float: ...
def gdd_base_temp(grass_type: str) -> float: ...
def gts_day(t_mean_c: float | None, month: int) -> float: ...
def gdd_day(t_mean_c: float | None, grass_type: str) -> float: ...
def accumulate_gts(
    daily_means: Sequence[tuple[date, float | None]],
) -> float: ...
def accumulate_gdd(
    daily_means: Sequence[tuple[date, float | None]],
    grass_type: str,
) -> float: ...
def year_bounds(today: date) -> tuple[date, date]:
    """(Jan-1 of year, today)."""
```

All accumulators take a list of `(date, T_mean)` pairs — keeps them
trivially unit-testable and lets the coordinator be the only impure caller.

### New module: `custom_components/lawn_vision/history.py`

Impure side. Owns the `Store` instance and the Open-Meteo Archive fetch.

```python
STORAGE_VERSION = 1
STORAGE_KEY_TEMPLATE = "lawn_vision.{entry_id}.history"

@dataclass
class DailyMean:
    day: date          # ISO date
    t_mean_c: float

class TemperatureHistoryStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None: ...
    async def async_load(self) -> list[DailyMean]: ...
    async def async_save(self, items: list[DailyMean]) -> None: ...

async def fetch_open_meteo_archive(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    start: date,
    end: date,
) -> list[DailyMean]: ...

async def fetch_open_meteo_recent(
    hass: HomeAssistant,
    latitude: float,
    longitude: float,
    past_days: int,
) -> list[DailyMean]: ...
```

Storage layout (JSON):

```json
{
  "version": 1,
  "year": 2026,
  "last_full_day": "2026-05-28",
  "daily_means": [
    {"day": "2026-01-01", "t_mean_c": -1.4},
    ...
  ]
}
```

Only the *current year* is retained. Switching years truncates and re-bootstraps.

### Coordinator integration (`coordinator.py`)

1. **Construction.** In `LawnVisionCoordinator.__init__`, instantiate
   `TemperatureHistoryStore(hass, entry.entry_id)` and stash on `self._history_store`.
   Add `self._history: list[DailyMean] | None = None`.
2. **First refresh.** Add `async def _async_ensure_history(today: date) -> None`
   called at the top of `_async_update_data`:
   - Load from store. If empty / year mismatch → bootstrap:
     - `fetch_open_meteo_archive(start=Jan-1, end=today − 5d)`
     - `fetch_open_meteo_recent(past_days=7)` and merge by date
     (forecast wins over archive for overlapping days because it's fresher).
   - Persist immediately.
3. **Daily tick.** Before computing metrics, walk from `last_full_day + 1` to
   `today − 1`, fill each missing day from Open-Meteo recent (or skip if
   unavailable) and append to history.
4. **Calculation.** Replace lines 507-509 with:
   ```python
   if inputs.grassland_temperature_sum is None:
       grassland_temperature_sum = accumulate_gts(history_pairs)
   else:
       grassland_temperature_sum = inputs.grassland_temperature_sum
   if inputs.growing_degree_days is None:
       growing_degree_days = accumulate_gdd(history_pairs, inputs.grass_type)
   else:
       growing_degree_days = inputs.growing_degree_days
   ```
   `history_pairs` is built from `self._history` + today's
   `inputs.mean_daily_temperature_c` (best-effort).
5. **Grass-type change.** Detect via `entry.options` reload listener
   (`_async_update_listener` in `__init__.py`) — the existing reload path
   already re-builds the coordinator, so no extra hook needed. History
   survives because storage is keyed by `entry_id`, not by grass type.

### Open-Meteo client (`weather_source.py`)

Add a sibling helper `fetch_open_meteo_archive(...)` and
`fetch_open_meteo_past(...)`. Keep them in `weather_source.py` rather than
`history.py` if the URL/JSON-shape concerns live next to the existing client
(decision: yes, keep network code centralised; `history.py` only owns
`Store` + orchestration).

Endpoints:
- Archive: `https://archive-api.open-meteo.com/v1/archive` with
  `daily=temperature_2m_mean`, `start_date`, `end_date`, `timezone=auto`.
- Forecast past: existing forecast URL +
  `daily=temperature_2m_mean&past_days=N&forecast_days=1`.

Reuse the existing 15 s timeout, `aiohttp.ClientError` handling, and warning
log convention.

### Sensors (`sensor.py`)

No structural change. `value_fn` already reads
`data[SENSOR_GRASSLAND_TEMPERATURE_SUM]` and `data[SENSOR_GROWING_DEGREE_DAYS]`.

Add an `extra_fn` returning:

```python
{
    "calculated": True,                # False when external entity supplies it
    "source": "open_meteo_archive" | "open_meteo_forecast" | "entity" | "mixed",
    "days_counted": int,
    "year": int,
    "base_temp_c": 5.5 | 10,           # GDD only
    "threshold_k": 200,                # GTS only
    "vegetation_started": bool,        # GTS only — gts_kum >= 200
}
```

Mirrors the existing `estimated: true` convention used for soil temperature
and moisture.

### Config flow (`config_flow.py`)

No mandatory changes. The existing optional `CONF_GTS_ENTITY` /
`CONF_GDD_ENTITY` fields keep working as overrides. Update the
field-description translations to clarify "leave empty to let Lawn Vision
calculate it from Open-Meteo".

Optional: a future "Reset history" button / service can come later — out of
scope for this plan.

## Edge cases

- **No Open-Meteo configured.** If `CONF_USE_OPEN_METEO` is off *and* no
  external GTS/GDD entity is set, history bootstrap is impossible.
  Resolution: skip bootstrap, accumulate only forward from the day the user
  enables Open-Meteo (document this in README). Surface `source: "local"`
  with `days_counted=0` until coverage starts.
- **Latitude/Longitude missing.** Archive endpoint needs coordinates. Gate
  the bootstrap on `(CONF_LATITUDE, CONF_LONGITUDE)` already present in the
  entry; fall back to `hass.config.latitude/longitude` if not. Same fallback
  the live Open-Meteo path already uses.
- **HA restart mid-year.** `Store` survives restarts. On reload the
  coordinator picks up cached history and only fetches the missing tail.
- **Jan-1 rollover.** When `today.year != stored.year`, archive the previous
  year (out of scope for v1: just drop it), then re-bootstrap for the new
  year. GTS/GDD report 0 for Jan-1 itself.
- **DST / timezone.** Use `dt_util.now().date()` for "today"; Open-Meteo
  daily payloads are already in the local TZ when `timezone=auto`.
- **External override mid-year.** If the user sets `CONF_GTS_ENTITY` later,
  the override wins immediately. History keeps accumulating in the
  background — no data loss when they remove the override again.

## Testing

Add to `tests/test_lawn_vision.py`:

- `TestAgronomy`:
  - `test_gts_weight_january_february_march`
  - `test_gts_day_clamps_negative_to_zero`
  - `test_gdd_day_cool_vs_warm_base`
  - `test_accumulate_gts_known_dwd_example` (hand-computed reference)
  - `test_accumulate_gdd_threshold_crossing`
  - `test_accumulate_skips_none_temperatures`
  - `test_year_bounds_jan1`
- `TestHistoryMerge` (pure merge helper that picks fresher source per day):
  - `test_recent_overrides_archive_when_overlap`
  - `test_missing_days_left_as_gap`

No new HA submodules need stubbing — `Store` is only touched by the impure
`history.py`, which won't be unit-tested in this suite (matches the existing
pattern for `weather_source.fetch_open_meteo`).

## Migration / compatibility

- Existing installs: on first run after upgrade, history is empty → bootstrap
  triggers automatically. No user action required.
- External GTS/GDD entities continue to win. No breaking change to
  `SENSOR_*` keys, units, or attribute names already used by the card.
- The card (`www/lawn-vision-card.js`) needs no change — `gts` and `gdd`
  values come through the same sensor IDs. `CARD_VERSION` stays unchanged.

## Versioning

- `manifest.json` → `0.7.0` (behaviour change).
- `CARD_VERSION` unchanged.
- Translations: add new `data_description` strings for the two override fields
  in `de.json`, `en.json`, and `strings.json`.

## CI parity checklist (before declaring done)

- [ ] `python -m unittest tests.test_lawn_vision -v`
- [ ] `python -m compileall -q custom_components tests`
- [ ] JSON-lint one-liner from CLAUDE.md
- [ ] Mention that hassfest + HACS action only reproduce in GitHub Actions.

## Out of scope (follow-ups)

- Persisting completed previous years for trend charts.
- "Reset history" service / button.
- Alternative GDD methods (single sine, Baskerville-Emin, …).
- Soil-temperature-based GTS variant.
- Configurable archive provider (DWD CDC direct).
